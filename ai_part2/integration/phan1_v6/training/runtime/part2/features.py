"""Feature contract v0: ingress IPv4, integer arithmetic, no FPGA dependency."""
import csv, hashlib, ipaddress, json, math, warnings
from pathlib import Path
import numpy as np
from scapy.all import PcapReader, IP, TCP, UDP

NAMES = ['packet_count', 'mean_ip_bytes', 'syn_ratio_q127', 'src_count', 'dst_count', 'dst_port_count']

def cardinality(values, mode):
    if mode == 'exact':
        return len(values)
    # XOR-fold to 256 bits; defined for Python/RTL agreement, not a claim about group RTL.
    bins = {((v >> 24) ^ (v >> 16) ^ (v >> 8) ^ v) & 255 for v in values}
    return len(bins)

def extract(path, dst, width=1.0, distinct='exact'):
    if not math.isfinite(width) or width <= 0: raise ValueError('window must be finite and positive')
    destination = ipaddress.ip_network(dst, strict=False)
    if destination.version != 4: raise ValueError('IPv4 only')
    windows, stats = {}, {'frames': 0, 'ingress_ipv4': 0, 'non_ingress': 0, 'fragments_skipped': 0,
                          'truncated_skipped': 0, 'timestamp_reversals': 0, 'max_backward_seconds': 0.0}
    previous = None
    with PcapReader(str(path)) as capture:
        for packet in capture:
            stats['frames'] += 1
            t = float(packet.time)
            if not math.isfinite(t):
                raise ValueError(f'Non-finite timestamp in frame {stats["frames"]}')
            if previous is not None and t < previous:
                stats['timestamp_reversals'] += 1
                stats['max_backward_seconds'] = max(stats['max_backward_seconds'], previous-t)
            # File order does not determine the window. Retain each packet in
            # the bucket of its own timestamp; never clamp it to previous time.
            previous = t
            if IP not in packet or ipaddress.ip_address(packet[IP].dst) not in destination:
                stats['non_ingress'] += 1; continue
            ip = packet[IP]
            if ip.frag or int(ip.flags) & 1:
                stats['fragments_skipped'] += 1; continue
            if ip.len is None or ip.len < (ip.ihl or 5)*4 or len(bytes(ip)) < ip.len:
                stats['truncated_skipped'] += 1; continue
            slot = math.floor(t / width)
            w = windows.setdefault(slot, {'packets': 0, 'bytes': 0, 'syn': 0, 'src': set(), 'dst': set(), 'ports': set()})
            w['packets'] += 1; w['bytes'] += int(ip.len)
            w['src'].add(int(ipaddress.ip_address(ip.src))); w['dst'].add(int(ipaddress.ip_address(ip.dst)))
            if TCP in ip:
                tcp = ip[TCP]
                w['ports'].add(int(tcp.dport))
                if int(tcp.flags) & 0x12 == 0x02: w['syn'] += 1
            elif UDP in ip: w['ports'].add(int(ip[UDP].dport))
            stats['ingress_ipv4'] += 1
    return windows, stats

def values(w, distinct):
    if w is None: return [0]*6
    n = w['packets']
    return [n, w['bytes']//n, 127*w['syn']//n, cardinality(w['src'],distinct),
            cardinality(w['dst'],distinct), cardinality(w['ports'],distinct)]

def build_dataset(manifest, output, width=1.0, distinct='exact'):
    manifest, output = Path(manifest), Path(output)
    if output.exists(): raise ValueError('Output exists; choose a new path')
    with manifest.open() as f: entries = list(csv.DictReader(f))
    required = {'capture_id','pcap','split','label','start','end','source_kind'}
    if not entries or not required <= set(entries[0]): raise ValueError('Invalid or empty manifest')
    if len({e['capture_id'] for e in entries}) != len(entries): raise ValueError('Duplicate capture_id')
    fingerprints, rows, provenance = {}, [], []
    for e in entries:
        if e['split'] not in ('train','val','test','challenge') or e['label'] not in ('0','1','2'):
            raise ValueError('Explicit train/val/test/challenge split and label 0/1/2 are required')
        if e['source_kind'] not in ('lab','synthetic','external'): raise ValueError('Invalid source_kind')
        path = (manifest.parent / e['pcap']).resolve()
        with path.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        if digest in fingerprints: raise ValueError('Duplicate capture content: cannot reuse across sessions/splits')
        fingerprints[digest] = e['capture_id']
        try:
            windows, stats = extract(path, e.get('target_net') or '198.18.0.1/32', width, distinct)
        except ValueError as error:
            raise ValueError(f'{e["capture_id"]} ({path}): {error}') from error
        if stats['timestamp_reversals']:
            warnings.warn(f'{e["capture_id"]}: {stats["timestamp_reversals"]} timestamp reversals; '
                          f'max backward {stats["max_backward_seconds"]:.6f}s. '
                          'Packets retained in their own timestamp windows; inspect metadata.', RuntimeWarning)
        start, end = float(e['start']), float(e['end'])
        if end <= start: raise ValueError('Invalid labeled interval')
        count = 0
        # Only complete windows wholly inside the explicitly labeled interval.
        for slot in range(math.ceil(start/width), math.floor(end/width)):
            w = windows.get(slot)
            row = dict(capture_id=e['capture_id'], split=e['split'],label=int(e['label']),
                       source_kind=e['source_kind'], window_start=slot*width)
            row.update(zip(NAMES, values(w, distinct)))
            rows.append(row); count += 1
        provenance.append(dict(e, sha256=digest,stats=stats,windows=count))
    if not rows: raise ValueError('No complete labeled windows')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    metadata={'timestamp_order_policy':'Per-packet timestamp buckets; no frame discarded for reordering',
              'contract':'v0','window_seconds':width,'distinct':distinct,'features':NAMES,
              'captures':provenance,'rows':len(rows),
              'note':'Scenario/window labels, not per-packet labels; empty attack windows remain labeled and must be reviewed.'}
    output.with_suffix('.meta.json').write_text(json.dumps(metadata,indent=2))
    return metadata

def quantize(raw, divisors):
    return np.clip(np.asarray(raw,dtype=np.int64)//np.asarray(divisors,dtype=np.int64),0,127).astype(np.int64)

def fit_divisors(raw):
    # Power-of-two divisors: firmware only needs shifts; trained on train split only.
    maxima=np.asarray(raw,dtype=np.int64).max(axis=0)
    return [1 << max(0, math.ceil(math.log2(max(1,int(m))/127))) for m in maxima]
