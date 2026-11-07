"""Disk-backed six-feature extraction from the three reviewed filtered classes.

Each destination /32 is treated as a receiver separately. Positive episodes
have reviewed bounds; no response-only scan seconds become attack samples.
"""
from collections import Counter
import csv
import gzip
import hashlib
import ipaddress
import json
import math
from pathlib import Path, PurePosixPath
import sqlite3
import struct
import time

import numpy as np
from part2.features import NAMES

DIVISORS=[8,2,1,1,1,1]
RAW=np.dtype([('slot','<i8'),('dst','<u4'),('src','<u4'),('size','<u4'),('port','<u4'),('syn','u1')])
CHUNK=100_000
MAGIC={b'\xd4\xc3\xb2\xa1':('<',10**6),b'\xa1\xb2\xc3\xd4':('>',10**6),
       b'\x4d\x3c\xb2\xa1':('<',10**9),b'\xa1\xb2\x3c\x4d':('>',10**9)}


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def relative_file(root,name):
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name:raise ValueError('Unsafe data member')
    result=root.joinpath(*path.parts)
    if not result.resolve().is_relative_to(root.resolve()):raise ValueError('Data member leaves dataset folder')
    return result


def select_sources(root):
    root=Path(root);native_path=root/'BAO_CAO_XUAT.json';scan_path=root/'vertical_scan/BAO_CAO_VERTICAL_SCAN.json'
    native=json.loads(native_path.read_text());scan=json.loads(scan_path.read_text())
    if native.get('status')!='complete' or native.get('kind')!='filtered_normal_syn_csv_and_pcap':
        raise ValueError('Need completed Normal/SYN filtering report')
    if scan.get('status')!='complete' or scan.get('kind')!='public_vertical_scan_pcap_and_derived_flow_csv':
        raise ValueError('Need installed reviewed public vertical scan')
    # Main and auxiliary cuts overlap. Choose the largest original PCAP from
    # each parent directory before looking at any feature/model result.
    primary={};excluded=[];syn=[]
    for member,result in native['pcaps'].items():
        if 'binh_thuong' in result['files']:
            group=str(PurePosixPath(member).parent)
            old=primary.get(group)
            if old is None or result['source_pcap_bytes']>old[1]['source_pcap_bytes']:
                if old:excluded.append(old[0])
                primary[group]=(member,result)
            else:excluded.append(member)
        if 'syn_flood' in result['files']:
            item=result['files']['syn_flood']
            syn.append(dict(label=1,path=item['path'],sha256=item['sha256'],source_group=str(PurePosixPath(member).parent),
                            target_ip=native['syn_review']['target_ip'],
                            start=native['syn_review']['start'],end=native['syn_review']['end'],
                            class_provenance='reviewed IoT23 capture34 SYN-flood episode'))
    selected=[]
    for group,(member,result) in sorted(primary.items()):
        item=result['files']['binh_thuong']
        selected.append(dict(label=0,path=item['path'],sha256=item['sha256'],source_group=group,
                             target_ip=None,start=None,end=None,
                             class_provenance='Native Benign filtered packets; each destination treated as its own receiver'))
    selected+=syn
    evidence=scan['evidence']
    for name,item in scan['files'].items():
        if name.startswith('pcap/') and name.endswith('.pcap'):
            selected.append(dict(label=2,path='vertical_scan/'+name,sha256=item['sha256'],
                                 source_group='ChrisSanders/synscan_one_episode',target_ip=evidence['target_ip'],
                                 start=float(evidence['verified_scan_first_syn']),end=float(evidence['verified_scan_last_syn']),
                                 class_provenance='public scan sample; one scanner probes 1000 ports on one destination'))
    if {s['label'] for s in selected}!={0,1,2}:raise ValueError('All three classes require reviewed PCAP files')
    for number,spec in enumerate(selected):
        relative_file(root,spec['path'])
        spec['id']=f'{number:03d}_class{spec["label"]}'
    return selected,dict(native_report_sha256=sha(native_path),scan_report_sha256=sha(scan_path),
                         excluded_overlapping_auxiliary_pcaps=excluded,
                         selection_rule='largest original PCAP per parent directory; retain distinct Somfy session directories',
                         normal_capture_files=len(primary),syn_episode_files=len(syn),scan_episode_files=1)


def packet_fields(data,link):
    if link in (101,228):offset=0
    elif link==113:
        if len(data)<16 or data[14:16]!=b'\x08\x00':return None
        offset=16
    elif link==276:
        if len(data)<20 or data[:2]!=b'\x08\x00':return None
        offset=20
    elif link==1:
        if len(data)<14:return None
        offset=14;kind=int.from_bytes(data[12:14],'big')
        for _ in range(2):
            if kind not in (0x8100,0x88a8,0x9100):break
            if len(data)<offset+4:return None
            kind=int.from_bytes(data[offset+2:offset+4],'big');offset+=4
        if kind!=0x800:return None
    else:raise ValueError('Unsupported PCAP link type')
    if len(data)<offset+20 or data[offset]>>4!=4:return None
    ihl=(data[offset]&15)*4;size=int.from_bytes(data[offset+2:offset+4],'big')
    if ihl<20 or size<ihl or len(data)<offset+size:return None
    if int.from_bytes(data[offset+6:offset+8],'big')&0x3fff:return None
    src,dst=struct.unpack_from('!II',data,offset+12);proto=data[offset+9];at=offset+ihl
    port=65536;syn=0
    if proto==6:
        if size<ihl+20:return None
        tcp_len=(data[at+12]>>4)*4
        if tcp_len<20 or ihl+tcp_len>size:return None
        port=struct.unpack_from('!H',data,at+2)[0];syn=int(data[at+13]&0x12==0x02)
    elif proto==17:
        if size<ihl+8:return None
        port=struct.unpack_from('!H',data,at+2)[0]
    return dst,src,size,port,syn


def metadata(path,expected_sha,output,target_ip=None):
    print('Checking PCAP checksum:',path.name,flush=True)
    if sha(path)!=expected_sha:raise ValueError('Filtered PCAP checksum changed: '+str(path))
    before=path.stat();counts=Counter();buffer=[];first=math.inf;last=-math.inf;tick=time.monotonic()
    target=int(ipaddress.IPv4Address(target_ip)) if target_ip else None
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rb') as stream,output.open('wb') as raw:
        header=stream.read(24)
        if len(header)!=24 or header[:4] not in MAGIC:raise ValueError('Classic PCAP required')
        endian,scale=MAGIC[header[:4]];record=struct.Struct(endian+'IIII')
        link=struct.unpack_from(endian+'I',header,20)[0]&0xffff;carry=b''
        while block:=stream.read(2*1024*1024):
            data=carry+block;view=memoryview(data);at=0
            while at+16<=len(data):
                sec,frac,caplen,wirelen=record.unpack_from(data,at)
                if frac>=scale or caplen>16*1024*1024 or caplen>wirelen:raise ValueError('Invalid PCAP record')
                end=at+16+caplen
                if end>len(data):break
                counts['all_frames']+=1;t=sec+frac/scale;first=min(first,t);last=max(last,t)
                fields=packet_fields(view[at+16:end],link)
                if fields is None:counts['unsupported_or_invalid']+=1
                elif target is not None and fields[0]!=target:counts['other_direction_or_receiver']+=1
                else:
                    buffer.append((sec,*fields));counts['feature_packets']+=1
                    if len(buffer)>=CHUNK:np.array(buffer,dtype=RAW).tofile(raw);buffer.clear()
                at=end
            carry=data[at:]
            if time.monotonic()-tick>=10:
                print(path.name,f'frames {counts["all_frames"]:,}; selected IPv4 {counts["feature_packets"]:,}',flush=True);tick=time.monotonic()
        if carry:raise ValueError('Filtered PCAP has an incomplete final record')
        if buffer:np.array(buffer,dtype=RAW).tofile(raw)
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('Input changed while reading')
    if not counts['all_frames']:raise ValueError('PCAP has no complete records: '+str(path))
    counts.setdefault('feature_packets',0)
    return dict(counts,first_timestamp=first,last_timestamp=last)


def extract_source(root,spec,folder):
    folder.mkdir(parents=True,exist_ok=True);raw_path=folder/'packets.tmp'
    info=metadata(relative_file(root,spec['path']),spec['sha256'],raw_path,spec['target_ip'])
    count=raw_path.stat().st_size//RAW.itemsize
    data=np.memmap(raw_path,dtype=RAW,mode='r+',shape=(count,)) if count else np.empty(0,dtype=RAW)
    print(f'{spec["id"]}: sorting {count:,} packet metadata rows on disk',flush=True)
    if count:data.sort(order=['slot','dst','src','port'],kind='quicksort');data.flush()
    start=spec['start'] if spec['start'] is not None else info['first_timestamp']
    end=spec['end'] if spec['end'] is not None else info['last_timestamp']
    left=int(np.searchsorted(data['slot'],math.ceil(start),side='left'))
    right=int(np.searchsorted(data['slot'],math.floor(end),side='left'))
    csv_part=folder/'features.csv.gz.part';database=folder/'patterns.sqlite'
    if database.exists():database.unlink()  # Own incomplete per-source scratch only.
    db=sqlite3.connect(database);db.execute('CREATE TABLE patterns (packed INTEGER PRIMARY KEY, count INTEGER NOT NULL)')
    total=0;clipped=np.zeros(6,dtype=np.int64);tick=time.monotonic()
    try:
        with gzip.open(csv_part,'wt',encoding='utf-8',newline='',compresslevel=1) as stream:
            writer=csv.writer(stream,lineterminator='\n')
            writer.writerow(['capture_id','target_ip','window_start','class']+NAMES+['q0','q1','q2','q3','q4','q5'])
            def emit(raw,slots,destinations):
                nonlocal total,clipped,tick
                raw=np.asarray(raw,dtype=np.int64).reshape(-1,6)
                q=np.clip(raw//np.asarray(DIVISORS),0,127)
                clipped+=np.sum(raw//np.asarray(DIVISORS)>127,axis=0);total+=len(raw)
                packed=np.sum(q*np.array([1<<(8*i) for i in range(6)],dtype=np.int64),axis=1)
                unique,counts=np.unique(packed,return_counts=True)
                db.executemany('INSERT INTO patterns VALUES (?,?) ON CONFLICT(packed) DO UPDATE SET count=count+excluded.count',
                               ((int(p),int(n)) for p,n in zip(unique,counts)))
                for row,qrow,slot,dst in zip(raw,q,slots,destinations):
                    writer.writerow([spec['id'],str(ipaddress.IPv4Address(int(dst))),int(slot),spec['label'],*map(int,row),*map(int,qrow)])
                if time.monotonic()-tick>=10:
                    print(spec['id'],f'complete receiver-windows {total:,}',flush=True);tick=time.monotonic();db.commit()
            def groups(begin,ends):
                starts=np.r_[begin,ends[:-1]];length=ends-starts
                single=starts[length==1]
                if len(single):
                    chosen=data[single];raw=np.ones((len(single),6),dtype=np.int64)
                    raw[:,0]=1;raw[:,1]=chosen['size'];raw[:,2]=127*chosen['syn'].astype(np.int64)
                    raw[:,5]=(chosen['port']!=65536).astype(np.int64)
                    emit(raw,chosen['slot'],chosen['dst'])
                rows=[];slots=[];destinations=[]
                for lo,hi in zip(starts[length>1],ends[length>1]):
                    selected=data[lo:hi];n=len(selected)
                    ports=selected['port'];valid_ports=ports[ports!=65536]
                    raw=[n,int(selected['size'].sum(dtype=np.uint64))//n,
                         127*int(selected['syn'].sum(dtype=np.uint64))//n,
                         len(np.unique(selected['src'])),1,len(np.unique(valid_ports))]
                    rows.append(raw);slots.append(selected['slot'][0]);destinations.append(selected['dst'][0])
                if rows:emit(rows,slots,destinations)
            pending=left
            for at in range(left,right,CHUNK):
                finish=min(right,at+CHUNK);check=max(left+1,at)
                boundaries=check+np.flatnonzero((data['slot'][check:finish]!=data['slot'][check-1:finish-1])|
                                               (data['dst'][check:finish]!=data['dst'][check-1:finish-1]))
                if len(boundaries):groups(pending,boundaries);pending=int(boundaries[-1])
            if pending<right:groups(pending,np.array([right]))
        db.commit();patterns=int(db.execute('SELECT count(*) FROM patterns').fetchone()[0])
    finally:
        db.close();del data
    csv_path=folder/'features.csv.gz';csv_part.replace(csv_path);raw_path.unlink()
    return dict(spec,**info,windows=total,unique_quantized_patterns=patterns,clipped_windows_by_feature=clipped.tolist(),
                status='complete' if total else 'skipped_no_complete_nonempty_window',
                window_start_inclusive=math.ceil(start),window_end_exclusive=math.floor(end),
                feature_csv=str(csv_path),feature_csv_sha256=sha(csv_path),patterns_db=str(database),patterns_db_sha256=sha(database))
