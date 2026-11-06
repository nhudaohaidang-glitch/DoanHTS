"""Packet-derived IoT23 caches and explicitly reused lab DEVELOPMENT data for v3."""
import csv
import json
import math
from pathlib import Path
from scapy.utils import RawPcapReader
from part2.development import load_dataset, sha256
from part2.features import NAMES, extract, values


def csv_write(path, rows):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def native_cache(pcap, source, output):
    """source is a reviewed registry entry; no automatic DDoS/horizontal relabel."""
    pcap,output=Path(pcap),Path(output)
    if output.exists():raise ValueError('Cache exists; preserve and inspect it')
    digest=sha256(pcap)
    if digest!=source['pcap_sha256']:raise ValueError('Native PCAP differs from reviewed source')
    first,last=math.inf,-math.inf
    with RawPcapReader(str(pcap)) as capture:
        for data,meta in capture:
            t=meta.sec+meta.usec/(1e9 if capture.nano else 1e6)
            first,last=min(first,t),max(last,t)
    if not math.isfinite(first):raise ValueError('Empty PCAP')
    if source['label']==1:
        # Exact interval was verified against DDoS origin tuples and SYN-only
        # packets in the pinned source, not selected by model predictions.
        start,end=source['verified_episode_start'],source['verified_episode_end']
        if not first<=start<end<=last:raise ValueError('Episode outside PCAP')
    elif source['label']==0:
        start,end=first,last
    else:raise ValueError('Native IoT23 vertical class is not supported by this registry')
    windows,stats=extract(pcap,source['protected_ip']+'/32')
    rows=[]
    for slot,w in sorted(windows.items()):
        if math.ceil(start)<=slot<math.floor(end):
            raw=values(w,'exact')
            if raw[0]:rows.append(dict(capture_id=source['capture_id'],split='unassigned',label=source['label'],source_kind='external',window_start=slot,**dict(zip(NAMES,raw))))
    if not rows:raise ValueError('No nonempty complete native windows')
    if source['label']==1:
        if stats['ingress_ipv4']!=source['verified_syn_packets'] or any(r['syn_ratio_q127']!=127 or r['dst_port_count']!=1 for r in rows):
            raise ValueError('Pinned SYN episode no longer meets reviewed packet evidence')
    csv_write(output,rows)
    metadata=dict(features=NAMES,window_seconds=1.,distinct='exact',rows=len(rows),csv_sha256=sha256(output),
                  source=source,stats=stats,capture_start=first,capture_end=last,
                  complete_time_slots=math.floor(end)-math.ceil(start),
                  valid_rule='raw packets > 0; empty seconds not eligible for AI',
                  training_ready=source['role']!='reserved_test')
    output.with_suffix('.meta.json').write_text(json.dumps(metadata,indent=2))
    return metadata


def read_cache(path):
    path=Path(path);meta=json.loads(path.with_suffix('.meta.json').read_text())
    if meta['csv_sha256']!=sha256(path) or meta['features']!=NAMES or meta['distinct']!='exact' or meta['window_seconds']!=1.:
        raise ValueError('Native cache checksum/contract mismatch')
    with path.open() as f:rows=list(csv.DictReader(f))
    source=meta['source']
    if len(rows)!=meta['rows'] or not rows:raise ValueError('Native cache row count mismatch')
    for row in rows:
        if (row['capture_id']!=source['capture_id'] or int(row['label'])!=source['label']
                or row['source_kind']!='external' or int(row['packet_count'])<=0):
            raise ValueError('Native cache row differs from its source annotation')
    return rows,meta


def build_development(lab_v1, lab_v2, native_paths, protocol, output):
    output=Path(output)
    if output.exists():raise ValueError('Dataset exists; preserve previous development set')
    rows=[];captures=[];inputs=[]
    for path,split,prior_use in [(Path(lab_v1),'train','Former v1 challenge, now v3 DEVELOPMENT TRAIN'),
                                 (Path(lab_v2),'val','Former v2 holdout, now v3 DEVELOPMENT VALIDATION')]:
        original,meta=load_dataset(path,{'challenge'})
        inputs.append(dict(path=str(path),sha256=sha256(path),prior_use=prior_use))
        groups={}
        for row in original:
            if int(row['packet_count'])==0:continue
            r=dict(row,split=split);rows.append(r);groups.setdefault(r['capture_id'],[]).append(r)
        for old in meta['captures']:
            if old['capture_id'] not in groups:raise ValueError('Whole lab capture is empty')
            captures.append(dict(old,split=split,source_dataset='controlled_lab',prior_use=prior_use,
                                 windows=len(groups[old['capture_id']])))
    native_count=0
    for path in native_paths:
        native,meta=read_cache(path);source=meta['source'];split=source['role']
        if split not in ('train','val'):raise ValueError('Reserved external test cannot enter development')
        rows.extend(dict(r,split=split) for r in native)
        captures.append(dict(capture_id=source['capture_id'],split=split,label=str(source['label']),source_kind='external',
                             sha256=source['pcap_sha256'],source_dataset='IoT-23',windows=len(native),
                             source=source,start=meta['capture_start'],end=meta['capture_end'],
                             prior_use='External exploratory analysis' if split=='train' else 'Predeclared external validation'))
        native_count+=1
    if native_count!=3:raise ValueError('Need Hue4 train, verified SYN34 train and Echo5 validation caches')
    if len({r['capture_id'] for r in captures})!=len(captures):raise ValueError('Duplicate capture IDs')
    csv_write(output,rows)
    meta=dict(features=NAMES,contract='v0',window_seconds=1.,distinct='exact',rows=len(rows),captures=captures,
              csv_sha256=sha256(output),protocol=protocol,input_csvs=inputs,
              dataset_kind='hybrid_IoT23_and_controlled_lab',test_included=False,
              note='Old challenge/holdout captures are now DEVELOPMENT, not v3 independent tests. Native vertical data not fabricated.')
    output.with_suffix('.meta.json').write_text(json.dumps(meta,indent=2))
    load_hybrid(output,{'train','val'})
    return meta


def load_hybrid(path,splits):
    rows,meta=load_dataset(path,splits,allowed_sources=('lab','external'))
    if meta.get('csv_sha256')!=sha256(path):raise ValueError('Hybrid CSV checksum mismatch')
    if any(int(r['packet_count'])<=0 for r in rows):raise ValueError('Empty windows must be skipped by raw-count validity guard')
    if any(c.get('source',{}).get('role')=='reserved_test' for c in meta['captures']):
        raise ValueError('Reserved test data in development')
    return rows,meta
