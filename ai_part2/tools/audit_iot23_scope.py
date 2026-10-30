"""Read-only IoT-23 class-coverage audit. Never relabel flows or train a model.

Zeek detailed label aliases and whitespace-appended label columns occur in the
official files. PCAP TCP flags are inspected directly; flow history is not used
as a substitute. Matches below are audit evidence, not a training label pipeline.
"""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import hashlib
import ipaddress
import json
import math
from pathlib import Path
import socket
import struct
from scapy.utils import RawPcapReader

ALIASES = {'det_label': 'detailed-label', 'detailedlabel': 'detailed-label',
           'detailed_label': 'detailed-label'}


def fingerprint(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def labelled_flows(path):
    fields = None
    with Path(path).open() as source:
        for number, line in enumerate(source, 1):
            if line.startswith('#fields'):
                fields = [ALIASES.get(x, x) for x in line.split()[1:]]
                required = {'ts','duration','id.orig_h','id.orig_p','id.resp_h','id.resp_p','proto','label','detailed-label'}
                if len(set(fields)) != len(fields) or not required <= set(fields):
                    raise ValueError(f'{path}:{number}: invalid labelled header')
                continue
            if line.startswith('#') or not line.strip():
                continue
            values = line.split()
            if fields is None or len(values) != len(fields):
                raise ValueError(f'{path}:{number}: row/header mismatch')
            row = dict(zip(fields, values))
            # Original label strings remain available for provenance.
            row['coarse_canonical'] = row['label'].casefold()
            yield row


def flow_audit(path):
    labels, protocols = Counter(), Counter()
    ports = defaultdict(set)
    intervals = defaultdict(list)
    rows = 0
    for row in labelled_flows(path):
        rows += 1
        labels[row['label'] + '/' + row['detailed-label']] += 1
        protocols[row['detailed-label'] + '/' + row['proto']] += 1
        if row['proto'] != 'tcp':
            continue
        src, dst = int(ipaddress.IPv4Address(row['id.orig_h'])), int(ipaddress.IPv4Address(row['id.resp_h']))
        sport, dport = int(row['id.orig_p']), int(row['id.resp_p'])
        if not 0 <= sport <= 65535 or not 0 <= dport <= 65535:
            raise ValueError('Invalid TCP port')
        ports[(src, dst)].add(dport)
        t = float(row['ts'])
        duration = 0.0 if row['duration'] in ('-', '(empty)') else float(row['duration'])
        if not math.isfinite(t) or not math.isfinite(duration) or duration < 0:
            raise ValueError('Invalid flow time/duration')
        intervals[(src, dst, sport, dport)].append((t, t+duration, row['label'], row['detailed-label']))
    index = {}
    for key, values in intervals.items():
        values.sort()
        index[key] = ([r[0] for r in values], values)
    top = sorted(ports.items(), key=lambda item: len(item[1]), reverse=True)[:8]
    report = dict(path=str(path), sha256=fingerprint(path), connection_records=rows,
                  labels=dict(labels), label_protocols=dict(protocols),
                  max_tcp_destination_ports_per_directed_pair=max(map(len,ports.values()),default=0),
                  top_tcp_pairs=[dict(src=str(ipaddress.IPv4Address(key[0])),dst=str(ipaddress.IPv4Address(key[1])),
                                      ports=sorted(values)) for key, values in top])
    return report, index


def packet_header(data, linktype):
    if linktype == 1:
        if len(data) < 14:
            return None, 'short_link_header'
        offset, ethertype = 14, int.from_bytes(data[12:14], 'big')
        for _ in range(2):
            if ethertype not in (0x8100, 0x88a8):
                break
            if len(data) < offset+4:
                return None, 'short_vlan_header'
            ethertype = int.from_bytes(data[offset+2:offset+4], 'big')
            offset += 4
        if ethertype != 0x0800:
            return None, 'non_ipv4'
    elif linktype == 113:
        if len(data) < 16:
            return None, 'short_link_header'
        if int.from_bytes(data[14:16],'big') != 0x0800:
            return None, 'non_ipv4'
        offset = 16
    elif linktype in (101, 228):
        offset = 0
    else:
        raise ValueError(f'Unsupported PCAP linktype {linktype}')
    if len(data) < offset+20 or data[offset] >> 4 != 4:
        return None, 'short_or_invalid_ipv4'
    ihl = (data[offset] & 15)*4
    length = int.from_bytes(data[offset+2:offset+4], 'big')
    if ihl < 20 or length < ihl or len(data) < offset+length:
        return None, 'truncated_or_invalid_ipv4'
    if int.from_bytes(data[offset+6:offset+8], 'big') & 0x3fff:
        return None, 'ipv4_fragment'
    proto = data[offset+9]
    src, dst = struct.unpack_from('!II',data,offset+12)
    if proto != 6:
        return dict(src=src,dst=dst,proto=proto,length=length), None
    tcp = offset+ihl
    if length < ihl+20:
        return None, 'short_tcp'
    tcp_length = (data[tcp+12] >> 4)*4
    if tcp_length < 20 or ihl+tcp_length > length:
        return None, 'invalid_tcp_header'
    sport, dport = struct.unpack_from('!HH',data,tcp)
    return dict(src=src,dst=dst,proto=6,length=length,sport=sport,dport=dport,flags=data[tcp+13]), None


def match_origin(index, packet, timestamp, tolerance=.001):
    value = index.get((packet['src'],packet['dst'],packet['sport'],packet['dport']))
    if value is None:
        return None
    starts, rows = value
    position = bisect_right(starts,timestamp+tolerance)-1
    matches = []
    while position >= 0:
        row = rows[position]
        if row[0]-tolerance <= timestamp <= row[1]+tolerance:
            matches.append(row)
        # An older interval can overlap a newer short connection; do not assume
        # the newest entry is the unique owner. Stop only after inspecting all.
        position -= 1
    labels = {(r[2],r[3]) for r in matches}
    return next(iter(labels)) if len(labels) == 1 else None


def pcap_audit(path, flow_index=None):
    stats = Counter(); flags = Counter(); label_flags = defaultdict(Counter)
    ports = defaultdict(set); syn_ports = defaultdict(set); targets = defaultdict(Counter)
    tmin, tmax = math.inf, -math.inf
    with RawPcapReader(str(path)) as capture:
        if not hasattr(capture,'linktype') or not hasattr(capture,'nano'):
            raise ValueError('Classic PCAP required for this audit, not PCAPNG')
        linktype = capture.linktype
        for data, meta in capture:
            stats['frames'] += 1
            t = meta.sec + meta.usec/(1e9 if capture.nano else 1e6)
            tmin, tmax = min(tmin,t), max(tmax,t)
            packet, reason = packet_header(data,linktype)
            if packet is None:
                stats[reason] += 1
                continue
            stats['valid_ipv4'] += 1
            if packet['proto'] != 6:
                stats['other_ipv4_protocol_'+str(packet['proto'])] += 1
                continue
            stats['tcp'] += 1
            f = packet['flags']; flags[f'{f:02x}'] += 1
            ports[(packet['src'],packet['dst'])].add(packet['dport'])
            counter = targets[(packet['src'],packet['dst'],packet['dport'])]
            counter['tcp'] += 1
            if f & 0x12 == 0x02:
                stats['syn_open'] += 1;counter['syn_open'] += 1
                syn_ports[(packet['src'],packet['dst'])].add(packet['dport'])
            if flow_index is not None:
                label = match_origin(flow_index,packet,t)
                if label:
                    label_flags['/'.join(label)][f'{f:02x}'] += 1
                    stats['matched_origin_tcp'] += 1
                else:
                    stats['unmatched_or_ambiguous_tcp'] += 1
    top = sorted(ports.items(),key=lambda item:len(item[1]),reverse=True)[:8]
    top_syn = sorted(syn_ports.items(),key=lambda item:len(item[1]),reverse=True)[:8]
    top_targets = sorted(targets.items(),key=lambda item:item[1]['tcp'],reverse=True)[:10]
    return dict(path=str(path),sha256=fingerprint(path),linktype=linktype,
                first_timestamp=tmin if stats['frames'] else None,last_timestamp=tmax if stats['frames'] else None,
                counters=dict(stats),tcp_flag_bytes=dict(flags),
                origin_label_tcp_flags={key:dict(value) for key,value in label_flags.items()},
                origin_match_time_tolerance_seconds=.001,
                max_tcp_destination_ports_per_directed_pair=max(map(len,ports.values()),default=0),
                max_syn_open_destination_ports_per_directed_pair=max(map(len,syn_ports.values()),default=0),
                top_syn_open_pairs=[dict(src=str(ipaddress.IPv4Address(key[0])),dst=str(ipaddress.IPv4Address(key[1])),
                                         ports=sorted(values)) for key,values in top_syn],
                top_tcp_pairs=[dict(src=str(ipaddress.IPv4Address(key[0])),dst=str(ipaddress.IPv4Address(key[1])),
                                    ports=sorted(values)) for key,values in top],
                top_origin_targets=[dict(src=str(ipaddress.IPv4Address(key[0])),dst=str(ipaddress.IPv4Address(key[1])),
                                         port=key[2],**counter) for key,counter in top_targets],
                note='Pair-port counts cover the entire supplied PCAP, not one-second model windows. All-TCP counts include reply packets to ephemeral client ports and MUST NOT be called a vertical scan. Inspect SYN-open pair counts/behavior and labels. Flag byte 02 is SYN-only; SYN-open requires SYN=1 ACK=0. Match evidence is not a training label decision.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--log');p.add_argument('--pcap');p.add_argument('--output',required=True)
    a = p.parse_args()
    if not a.log and not a.pcap:
        p.error('Supply --log and/or --pcap')
    out=Path(a.output)
    if out.exists():p.error('Output exists; preserve previous audit')
    report=dict(training_ready=False,scope='SYN flood and vertical scan retained; no automatic mapping',
                labels_modified=False,model_trained=False)
    index=None
    if a.log:report['flows'],index=flow_audit(a.log)
    if a.pcap:report['packets']=pcap_audit(a.pcap,index)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
