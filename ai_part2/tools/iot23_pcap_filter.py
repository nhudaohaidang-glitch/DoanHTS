"""Preserve selected classic-PCAP records byte for byte, gzip on disk."""
from collections import Counter
import gzip
import hashlib
from pathlib import Path
import shutil
import struct
import time

from iot23_label_index import flow_key

MIB = 1024*1024
FORMATS = {b'\xd4\xc3\xb2\xa1':('<',10**6), b'\xa1\xb2\xc3\xd4':('>',10**6),
           b'\x4d\x3c\xb2\xa1':('<',10**9), b'\xa1\xb2\x3c\x4d':('>',10**9)}


class Compressed:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.raw = self.path.open('wb')
        self.gz = gzip.GzipFile(filename='', mode='wb', fileobj=self.raw, compresslevel=1, mtime=0)

    def write(self, data):
        self.gz.write(data)

    def close(self):
        self.gz.close()
        self.raw.close()


def packet(data, linktype):
    """Return key and review attributes; unsupported packets remain unlabelled."""
    if linktype in (101, 228):
        offset = 0
    elif linktype == 113:
        if len(data) < 16 or int.from_bytes(data[14:16], 'big') != 0x800:
            return None, 'non_ipv4'
        offset = 16
    elif linktype == 276:
        if len(data) < 20 or int.from_bytes(data[:2], 'big') != 0x800:
            return None, 'non_ipv4'
        offset = 20
    elif linktype == 1:
        if len(data) < 14:
            return None, 'short_ethernet'
        offset, kind = 14, int.from_bytes(data[12:14], 'big')
        for _ in range(2):
            if kind not in (0x8100, 0x88a8, 0x9100):
                break
            if len(data) < offset+4:
                return None, 'short_vlan'
            kind = int.from_bytes(data[offset+2:offset+4], 'big'); offset += 4
        if kind != 0x800:
            return None, 'non_ipv4'
    else:
        return None, 'unsupported_linktype'
    if len(data) < offset+20 or data[offset] >> 4 != 4:
        return None, 'short_or_non_ipv4'
    ihl = (data[offset] & 15)*4
    size = int.from_bytes(data[offset+2:offset+4], 'big')
    if ihl < 20 or size < ihl or len(data) < offset+size:
        return None, 'truncated_or_invalid_ipv4'
    if int.from_bytes(data[offset+6:offset+8], 'big') & 0x3fff:
        return None, 'ipv4_fragment'
    proto = data[offset+9]
    src, dst = struct.unpack_from('!II', data, offset+12)
    at = offset+ihl
    flags = 0
    if proto == 6:
        if size < ihl+20:
            return None, 'short_tcp'
        sport, dport = struct.unpack_from('!HH', data, at)
        length = (data[at+12] >> 4)*4
        if length < 20 or ihl+length > size:
            return None, 'invalid_tcp_header'
        flags = data[at+13]
    elif proto == 17:
        if size < ihl+8:
            return None, 'short_udp'
        sport, dport, length = struct.unpack_from('!HHH', data, at)
        if length < 8 or length > size-ihl:
            return None, 'invalid_udp_length'
    elif proto == 1:
        if size < ihl+8:
            return None, 'short_icmp'
        sport, dport = data[at], data[at+1]
    else:
        return None, 'unsupported_ip_protocol'
    a, b = flow_key(proto, src, sport, dst, dport)
    return (a, b, proto, src, dst, dport, flags), None


def filter_pcap(source, expected_size, index, output, stem, pure_normal=False, syn_rule=None,
                allow_incomplete_final_record=False):
    header = source.read(24)
    if len(header) != 24 or header[:4] not in FORMATS:
        raise ValueError('Expected complete classic PCAP')
    endian, scale = FORMATS[header[:4]]
    if struct.unpack_from(endian+'HH', header, 4) != (2, 4):
        raise ValueError('Unsupported PCAP version')
    linktype = struct.unpack_from(endian+'I', header, 20)[0] & 0xffff
    record = struct.Struct(endian+'IIII')
    digest = hashlib.sha256(header); size = 24; carry = b''
    counts, reasons, writers, paths = Counter(), Counter(), {}, {}
    tick = time.monotonic()
    src_syn = int.from_bytes(bytes(map(int, syn_rule['source_ip'].split('.'))), 'big') if syn_rule else None
    dst_syn = int.from_bytes(bytes(map(int, syn_rule['target_ip'].split('.'))), 'big') if syn_rule else None
    def retain(label, data):
        if label not in writers:
            path = output/label/'pcap'/(stem+'.pcap.gz.part')
            writers[label] = Compressed(path); paths[label] = path
            writers[label].write(header)
        writers[label].write(data); counts[label] += 1
    try:
        while block := source.read(2*MIB):
            digest.update(block); size += len(block)
            data = carry+block; view = memoryview(data); at = 0
            offsets, times, aa, bb, syn = [], [], [], [], []
            while at+16 <= len(data):
                sec, frac, caplen, wirelen = record.unpack_from(data, at)
                if frac >= scale or caplen > 16*MIB or caplen > wirelen:
                    raise ValueError('Invalid PCAP record header')
                end = at+16+caplen
                if end > len(data):
                    break
                counts['source_packets'] += 1
                if pure_normal:
                    retain('binh_thuong', view[at:end])
                else:
                    decoded, reason = packet(view[at+16:end], linktype)
                    if reason:
                        reasons[reason] += 1
                    else:
                        a, b, proto, src, dst, dport, flags = decoded
                        t = sec+frac/scale
                        offsets.append((at, end)); times.append(t); aa.append(a); bb.append(b)
                        syn.append(bool(syn_rule and proto == 6 and src == src_syn and dst == dst_syn
                                        and dport == syn_rule['target_port'] and flags & 0x12 == 0x02
                                        and syn_rule['start']-.001 <= t <= syn_rule['end']+.001))
                at = end
            if offsets:
                normal = index.contains(aa, bb, times)
                for (left, right), benign, is_syn in zip(offsets, normal, syn):
                    if is_syn:
                        retain('syn_flood', view[left:right])
                    elif benign:
                        retain('binh_thuong', view[left:right])
                    else:
                        counts['unmatched_or_non_benign'] += 1
            carry = data[at:]
            if time.monotonic()-tick >= 10:
                if shutil.disk_usage(output).free < 512*MIB:
                    raise ValueError('Low disk space; completed files can be resumed')
                print(f'PCAP {stem}: {size/1e9:.2f}/{expected_size/1e9:.2f} GB; Normal {counts["binh_thuong"]:,}; SYN {counts["syn_flood"]:,}', flush=True)
                tick = time.monotonic()
        if size != expected_size:
            raise ValueError(f'Source PCAP size changed: read {size} bytes, expected {expected_size}')
        if not counts['source_packets']:
            raise ValueError('Source PCAP contains no complete packet records')
        tail = None
        if carry:
            tail = dict(source_offset=size-len(carry), excluded_bytes=len(carry),
                        excluded_sha256=hashlib.sha256(carry).hexdigest(),
                        reason='incomplete_final_record_header' if len(carry) < 16 else 'incomplete_final_packet_payload')
            if len(carry) >= 16:
                sec, fraction, caplen, wirelen = record.unpack_from(carry)
                # Header validity was checked in the loop; only its final
                # payload may be missing. Never scan past corrupt record data.
                tail.update(packet_sec=sec, packet_fraction=fraction, caplen=caplen,
                            wirelen=wirelen, available_payload_bytes=len(carry)-16,
                            missing_payload_bytes=16+caplen-len(carry))
            if not allow_incomplete_final_record or syn_rule:
                raise ValueError(f'Source PCAP ends with an incomplete record: {len(carry)} trailing bytes at offset {size-len(carry)}')
            print(f'WARNING {stem}: source has an incomplete final record; excluded {len(carry)} trailing bytes; all earlier complete records processed', flush=True)
        if syn_rule and (digest.hexdigest() != syn_rule['pcap_sha256'] or counts['syn_flood'] != syn_rule['packet_metadata_sum']):
            raise ValueError('Reviewed SYN PCAP SHA/count changed; output remains partial')
    finally:
        for writer in writers.values():
            writer.close()
    files = {}
    for label, path in paths.items():
        with path.open('rb') as stream:
            checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
        files[label] = dict(path=str(path.with_suffix('').relative_to(output)),
                            sha256=checksum, packets=counts[label])
    return dict(source_pcap_bytes=size, source_pcap_sha256=digest.hexdigest(),
                source_packets=counts['source_packets'], normal_packets=counts['binh_thuong'],
                reviewed_syn_flood_packets=counts['syn_flood'], excluded_decode_reasons=dict(reasons),
                unmatched_or_non_benign=counts['unmatched_or_non_benign'], files=files,
                source_record_integrity='incomplete_final_record' if tail else 'complete',
                source_tail_excluded=tail,
                normal_policy='whole reviewed benign scenario' if pure_normal else 'native Benign tuple/time minus conflicting labels',
                linktype=linktype)
