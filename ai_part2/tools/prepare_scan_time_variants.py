"""Time-only augmentation of the reviewed public vertical scan, offline.

Frames, IPs, ports and order stay byte-exact. Every variant has the same
original capture group and is development/training data, never a new session.
"""
from collections import Counter,defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import struct

import numpy as np
from scapy.utils import RawPcapReader

KIT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(KIT))
from part2.features import NAMES,quantize
from part2.filtered_training_data import DIVISORS,packet_fields,sha

SOURCE_SHA='dec17c51b1b9d464831edb6e1f0a5bbcbeabdc519bfb4a5a402803384adb257c'
TARGET=0x400d8634  # 64.13.134.52, the original scan target.
PARENT='ChrisSanders/synscan_one_episode'
SCALES=(2,4,8,16,32,64,128)
PHASES=(0,250000,500000,750000)


def prepare(source,output):
    source,output=Path(source),Path(output)
    if output.exists():raise ValueError('Variant output exists; use another folder')
    if sha(source)!=SOURCE_SHA:raise ValueError('Expected the reviewed public scan PCAP')
    header=source.read_bytes()[:24];packets=[]
    with RawPcapReader(str(source)) as reader:
        if reader.linktype!=1 or reader.nano:raise ValueError('Expected Ethernet microsecond PCAP')
        for raw,meta in reader:
            fields=packet_fields(memoryview(raw),1)
            packets.append(dict(raw=raw,t=meta.sec*1_000_000+meta.usec,wirelen=meta.wirelen,fields=fields))
    ingress=[p for p in packets if p['fields'] and p['fields'][0]==TARGET]
    if len(packets)!=2011 or len(ingress)!=1994 or any(not p['fields'][-1] for p in ingress):
        raise ValueError('Original packet facts changed')
    first=ingress[0]['t'];last=ingress[-1]['t'];epoch=(first//1_000_000)*1_000_000
    output.mkdir(parents=True);(output/'pcap').mkdir();(output/'features').mkdir()
    specs=[];total_accepted=total_sparse=0
    for scale in SCALES:
        for phase in PHASES:
            name=f'scan_scale{scale:03d}_phase{phase:06d}'
            path=output/'pcap'/(name+'.pcap');window=defaultdict(list)
            start=epoch+phase;end=start+(last-first)*scale
            with path.open('wb') as stream:
                stream.write(header)
                for packet in packets:
                    timestamp=start+(packet['t']-first)*scale
                    sec,usec=divmod(timestamp,1_000_000)
                    raw=packet['raw'];stream.write(struct.pack('<IIII',sec,usec,len(raw),packet['wirelen']));stream.write(raw)
                    f=packet['fields']
                    if f and f[0]==TARGET:window[sec].append(f)
            rows=[];accepted=sparse=0
            for slot,members in sorted(window.items()):
                if slot*1_000_000<start or (slot+1)*1_000_000>end:continue
                n=len(members)
                raw=[n,sum(f[2] for f in members)//n,127*sum(f[4] for f in members)//n,
                     len({f[1] for f in members}),1,len({f[3] for f in members if f[3]!=65536})]
                eligible=raw[5]>=3
                # The whole stream is a known scan; sparse 1-2-port windows
                # need temporal context absent from the six-feature interface.
                # Preserve them as context-needed, not as artificial Normal.
                accepted+=int(eligible);sparse+=int(not eligible)
                q=quantize(raw,DIVISORS).tolist()
                rows.append([name,slot,2 if eligible else '',
                             'scan_window' if eligible else 'needs_multiwindow_context',*raw,*q])
            csv_path=output/'features'/(name+'.csv')
            with csv_path.open('w',newline='') as stream:
                writer=csv.writer(stream,lineterminator='\n')
                writer.writerow(['variant','window_start','training_label','window_scope']+NAMES+[f'q{i}' for i in range(6)])
                writer.writerows(rows)
            # Verify every frame and exact transformed timestamp independently.
            with RawPcapReader(str(path)) as reader:
                converted=list(reader)
            if len(converted)!=len(packets):raise ValueError('Variant lost a frame')
            for original,(raw,meta) in zip(packets,converted):
                expected=start+(original['t']-first)*scale
                if raw!=original['raw'] or meta.sec*1_000_000+meta.usec!=expected or meta.wirelen!=original['wirelen']:
                    raise ValueError('Time variant changed packet content, order or intended timestamp')
            total_accepted+=accepted;total_sparse+=sparse
            specs.append(dict(id=name,parent_group=PARENT,label=2,scale=scale,phase_microseconds=phase,
                              pcap=str(path.relative_to(output)),pcap_sha256=sha(path),
                              feature_csv=str(csv_path.relative_to(output)),feature_csv_sha256=sha(csv_path),
                              eligible_training_windows=accepted,sparse_context_windows=sparse,
                              first_scan_timestamp_us=start,last_scan_timestamp_us=end))
    manifest=dict(kind='same_parent_time_augmented_vertical_scan',original_pcap_sha256=SOURCE_SHA,
                  original_parent_group=PARENT,new_independent_episodes=0,frames_per_variant=2011,
                  scales=list(SCALES),phases_microseconds=list(PHASES),
                  packet_bytes_ips_ports_and_order_preserved=True,only_record_timestamps_changed=True,
                  all_variants_training_development_only=True,minimum_unique_ports_for_window_label=3,
                  sparse_windows_policy='Preserve as context-needed, neither train as scan nor relabel as Normal',
                  eligible_training_windows=total_accepted,sparse_context_windows=total_sparse,variants=specs)
    (output/'AUGMENTATION_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(variants=len(specs),training_windows=total_accepted,context_needed=total_sparse,
                         independent_episodes=0,output=str(output)),indent=2))
    return manifest


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();prepare(args.source,args.output)
