"""Extract selected IPv4 destinations and verify native SYN windows, no training."""
import argparse
from array import array
from bisect import bisect_right
from collections import Counter,defaultdict
import csv
import gzip
import hashlib
import html
import ipaddress
import json
import math
from pathlib import Path,PurePosixPath
import shutil
import struct
import sys
import tarfile
import time

HERE=Path(__file__).resolve().parent
KIT=HERE if (HERE/'part2/features.py').exists() else HERE.parent
sys.path.insert(0,str(KIT))
import audit_iot23_scope as audit
from part2.features import NAMES,extract,values,quantize
from scapy.utils import RawPcapReader

MIB=1024*1024
PCAPS={
 '34':('2018-12-21-15-50-14-192.168.1.195.pcap',126317980),
 '35':('2018-12-21-15-33-59-192.168.1.196.pcap',3810783348),
}


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def csv_write(path,names,rows):
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(names);writer.writerows(rows)


class Progress:
    def __init__(self,stream,total):self.stream,self.total,self.last=stream,total,time.monotonic()
    def read(self,size=-1):
        data=self.stream.read(size)
        if time.monotonic()-self.last>=10:
            print(f'Archive prefix read: {self.stream.tell()/1e9:.2f}/{self.total/1e9:.2f} GB; stops after selected PCAP and log',flush=True)
            self.last=time.monotonic()
        return data


def ipv4_offset(data,linktype):
    if linktype in (101,228):return 0 if len(data)>=20 and data[0]>>4==4 else None
    if linktype==113:
        return 16 if len(data)>=36 and int.from_bytes(data[14:16],'big')==0x800 else None
    if linktype!=1:raise ValueError('Unsupported PCAP link type')
    if len(data)<14:return None
    offset=14;kind=int.from_bytes(data[12:14],'big')
    for _ in range(2):
        if kind not in (0x8100,0x88a8):break
        if len(data)<offset+4:return None
        kind=int.from_bytes(data[offset+2:offset+4],'big');offset+=4
    return offset if kind==0x800 and len(data)>=offset+20 else None


def copy_destinations(source,expected_size,targets,output,cache_limit=2*1024*MIB):
    """Preserve each retained original global/record header and packet byte."""
    header=source.read(24)
    formats={b'\xd4\xc3\xb2\xa1':('<',10**6),b'\xa1\xb2\xc3\xd4':('>',10**6),
             b'\x4d\x3c\xb2\xa1':('<',10**9),b'\xa1\xb2\x3c\x4d':('>',10**9)}
    if len(header)!=24 or header[:4] not in formats:raise ValueError('Expected a complete classic PCAP')
    endian,scale=formats[header[:4]];record=struct.Struct(endian+'IIII')
    linktype=struct.unpack_from(endian+'I',header,20)[0]
    if linktype not in (1,113,101,228):raise ValueError('Unsupported link type')
    destinations={int(ipaddress.IPv4Address(ip)):ip for ip in targets}
    folder=output/'pcap_da_loc';folder.mkdir()
    writers={};retained=Counter();flags=defaultdict(Counter);invalid=defaultdict(Counter)
    digest=hashlib.sha256(header);read=24;stored=0;frames=0;first=math.inf;last=-math.inf;carry=b'';tick=time.monotonic()
    try:
        for ip in targets:
            path=folder/(ip+'.pcap');writers[ip]=path.open('wb');writers[ip].write(header);stored+=24
        while block:=source.read(MIB):
            read+=len(block);digest.update(block)
            data=carry+block;view=memoryview(data);at=0
            while at+16<=len(data):
                sec,fraction,caplen,wirelen=record.unpack_from(data,at)
                if caplen>16*MIB or fraction>=scale:raise ValueError('Invalid PCAP record header')
                end=at+16+caplen
                if end>len(data):break
                packet=view[at+16:end];frames+=1;t=sec+fraction/scale
                first,last=min(first,t),max(last,t)
                offset=ipv4_offset(packet,linktype)
                if offset is not None and packet[offset]>>4==4:
                    ip=destinations.get(struct.unpack_from('!I',packet,offset+16)[0])
                    if ip is not None:
                        if stored+end-at>cache_limit:raise ValueError('Selected PCAP cache exceeds 2 GiB; partial output is not complete')
                        writers[ip].write(view[at:end]);stored+=end-at;retained[ip]+=1
                        decoded,reason=audit.packet_header(packet,linktype)
                        if reason:invalid[ip][reason]+=1
                        elif decoded['proto']==6:flags[ip][f'{decoded["flags"]:02x}']+=1
                at=end
            carry=data[at:]
            if time.monotonic()-tick>=10:
                if shutil.disk_usage(output).free<128*MIB:raise ValueError('Low free space; keep partial output for diagnostics')
                print(f'PCAP processed: {read/1e9:.2f}/{expected_size/1e9:.2f} GB; cached {stored/MIB:.0f} MiB',flush=True);tick=time.monotonic()
        if carry or read!=expected_size or not frames:raise ValueError('Truncated or changed source PCAP')
    finally:
        for writer in writers.values():writer.close()
    return dict(source_pcap_bytes=read,source_pcap_sha256=digest.hexdigest(),source_frames=frames,
                source_first_timestamp=first,source_last_timestamp=last,linktype=linktype,cache_bytes=stored,
                retained_frames={ip:retained[ip] for ip in targets},
                retained_tcp_flag_bytes={ip:dict(flags[ip]) for ip in targets},
                retained_decode_exclusions={ip:dict(invalid[ip]) for ip in targets},
                cache_sha256={ip:sha(folder/(ip+'.pcap')) for ip in targets})


def copy_target_log(source,spec,targets,output):
    folder=output/'nhan_goc_theo_dich';folder.mkdir()
    targets=set(targets);headers=[];fields=None;writers={};counts=Counter();size=0;digest=hashlib.sha256();tick=time.monotonic()
    try:
        for line in source:
            digest.update(line);size+=len(line)
            if line.startswith(b'#'):
                if line.startswith(b'#fields'):
                    fields=line.decode().split()[1:]
                    if not {'id.resp_h','proto','label'}<=set(fields):raise ValueError('Invalid native labelled header')
                    proto=fields.index('proto');dst=fields.index('id.resp_h')
                headers.append(line)
                for writer in writers.values():writer.write(line)
                continue
            if not line.strip():continue
            parts=line.split()
            if fields is None or len(parts)!=len(fields):raise ValueError('Malformed full native source log')
            ip=parts[dst].decode()
            if parts[proto]==b'tcp' and ip in targets:
                if ip not in writers:
                    writers[ip]=gzip.open(folder/(ip+'.log.gz'),'wb',compresslevel=1);writers[ip].writelines(headers)
                writers[ip].write(line);counts[ip]+=1
            if time.monotonic()-tick>=10:
                if shutil.disk_usage(output).free<128*MIB:raise ValueError('Low free space while retaining target labels')
                print(f'Native log processed: {size/1e6:.0f}/{spec["source_bytes"]/1e6:.0f} MB',flush=True);tick=time.monotonic()
        if size!=spec['source_bytes'] or digest.hexdigest()!=spec['source_sha256']:
            raise ValueError('Full native log differs from the previous screening hash')
    finally:
        for writer in writers.values():writer.close()
    return dict(full_native_log_sha256=digest.hexdigest(),full_native_log_bytes=size,
                retained_native_tcp_flow_rows=dict(counts),
                native_cache_sha256={ip:sha(folder/(ip+'.log.gz')) for ip in writers})


def verify_windows(pcap,native_log,target,source_bounds,output,episode_gap=2.0,capture_id='unassigned_source'):
    """Whole ingress windows first, then strict native-DDoS/SYN evidence."""
    import numpy as np
    native,index=audit.flow_audit(native_log)
    print('Extracting canonical six features for',target,flush=True)
    windows,stats=extract(pcap,target+'/32',1.,'exact')
    evidence=defaultdict(Counter);matched_times=array('d');flags=Counter();syn_ports=defaultdict(set)
    print('Matching actual packet flags against all native target labels',flush=True)
    with RawPcapReader(str(pcap)) as reader:
        for data,meta in reader:
            t=meta.sec+meta.usec/(10**9 if reader.nano else 10**6);slot=math.floor(t)
            packet,reason=audit.packet_header(data,reader.linktype)
            if packet is None:continue
            entry=evidence[slot];entry['audited_ipv4']+=1
            if packet['proto']!=6:continue
            flags[f'{packet["flags"]:02x}']+=1
            label=audit.match_origin(index,packet,t)
            if label and label[0].casefold()=='malicious' and label[1]=='DDoS':entry['native_ddos_tcp']+=1
            else:entry['other_or_unmatched_tcp']+=1
            if packet['flags']&0x12==0x02:
                entry['syn_open']+=1;syn_ports[packet['src']].add(packet['dport'])
                if label and label[0].casefold()=='malicious' and label[1]=='DDoS':
                    entry['native_ddos_syn']+=1;matched_times.append(t)
                else:entry['other_or_unmatched_syn']+=1
    times=np.sort(np.asarray(matched_times,dtype=np.float64));episodes=[]
    if len(times):
        edges=np.r_[0,np.flatnonzero(np.diff(times)>episode_gap)+1,len(times)]
        for start,end in zip(edges[:-1],edges[1:]):
            episodes.append(dict(start=float(times[start]),end=float(times[end-1]),matched_syn_packets=int(end-start)))
    starts=[episode['start'] for episode in episodes]
    raw=[];information=[];verified=[];verified_info=[]
    for slot,w in sorted(windows.items()):
        if not math.ceil(source_bounds[0])<=slot<math.floor(source_bounds[1]):continue
        row=values(w,'exact')
        if row[0]==0:continue
        ev=evidence[slot];position=bisect_right(starts,slot)-1
        inside=position>=0 and slot+1<=episodes[position]['end']
        approved=inside and row[2]==127 and row[0]==ev['audited_ipv4']==ev['syn_open']==ev['native_ddos_syn']
        raw.append(row);information.append([len(raw),slot,ev['syn_open'],ev['native_ddos_syn'],ev['other_or_unmatched_syn'],1 if approved else ''])
        if approved:verified.append(row);verified_info.append([len(verified),capture_id,target,slot,position+1])
    all_folder=output/'tat_ca_cua_so_dich';all_folder.mkdir()
    csv_write(all_folder/'X_6_raw.csv',NAMES,raw)
    csv_write(all_folder/'X_6_fpga.csv',['q0','q1','q2','q3','q4','q5'],quantize(raw,[8,2,1,1,1,1]).tolist() if raw else [])
    csv_write(all_folder/'BANG_CHUNG.csv',['row_number','window_start','syn_open_packets','native_ddos_syn_packets','other_or_unmatched_syn_packets','verified_syn_label'],information)
    if verified:
        folder=output/'syn_da_kiem_tra';folder.mkdir()
        csv_write(folder/'X_6_raw.csv',NAMES,verified)
        csv_write(folder/'X_6_fpga.csv',['q0','q1','q2','q3','q4','q5'],quantize(verified,[8,2,1,1,1,1]).tolist())
        csv_write(folder/'y.csv',['class'],[[1] for _ in verified])
        csv_write(folder/'THONG_TIN_DONG.csv',['row_number','capture_id','protected_ip','window_start','episode_id'],verified_info)
    return dict(target=target,native_target_flow_audit=native,canonical_feature_stats=stats,
                eligible_nonempty_complete_windows=len(raw),verified_syn_windows=len(verified),
                observed_tcp_flags=dict(flags),matched_native_ddos_syn_packets=len(times),
                syn_episodes=episodes,episode_gap_seconds=episode_gap,
                max_syn_open_ports_per_source_over_whole_target_capture=max(map(len,syn_ports.values()),default=0),
                verified_packets_per_second_range=[min(r[0] for r in verified),max(r[0] for r in verified)] if verified else None,
                source_capture_group=capture_id,source_group_must_stay_in_one_split=True,training_ready=False,
                label_rule='Complete windows inside a native-matched SYN episode; all canonical ingress IPv4 packets must be SYN-open and uniquely native Malicious/DDoS. Other windows remain unlabelled.')


def write_page(output,report):
    body='<!doctype html><html lang="vi"><meta charset="utf-8"><title>Kiểm PCAP IoT-23 theo đích</title><style>body{font:18px system-ui;max-width:1100px;margin:30px auto;line-height:1.6}td,th{border:1px solid #ccd;padding:8px}table{border-collapse:collapse}</style>'
    if report['status']!='complete':
        body+='<h1>Chưa hoàn tất</h1><p>'+html.escape(report.get('error',''))+'</p>'
    else:
        result=report['verification'];body+='<h1>Đã trích và kiểm tra gói thực tế</h1>'
        body+='<p>Đích phân tích: <b>'+html.escape(result['target'])+'</b>. Đã khớp hash toàn bộ log gốc với lượt sàng lọc trước.</p>'
        body+='<table><tr><th>Nội dung</th><th>Số lượng</th></tr>'
        for label,key in [('Cửa sổ đầy đủ có gói','eligible_nonempty_complete_windows'),('Gói SYN mở khớp nhãn DDoS gốc','matched_native_ddos_syn_packets'),('Cửa sổ SYN đã kiểm tra','verified_syn_windows')]:
            body+='<tr><td>'+label+'</td><td>'+str(result[key])+'</td></tr>'
        body+='</table><p>Cờ TCP quan sát: '+html.escape(json.dumps(result['observed_tcp_flags']))+'</p>'
        body+='<p>Số gói/giây trong các cửa sổ SYN đã kiểm: '+html.escape(str(result['verified_packets_per_second_range']))+'</p>'
        if result['verified_syn_windows']:
            body+='<p><a href="syn_da_kiem_tra/X_6_raw.csv">Sáu đặc trưng SYN đã kiểm</a> | <a href="syn_da_kiem_tra/X_6_fpga.csv">Sáu q</a> | <a href="syn_da_kiem_tra/y.csv">Nhãn1 riêng</a></p>'
        else:body+='<p>Chưa có cửa sổ đủ điều kiện gán nhãn SYN. Không tạo nhãn giả cho phần còn lại.</p>'
        body+='<p><a href="tat_ca_cua_so_dich/X_6_raw.csv">Sáu đặc trưng của mọi cửa sổ hợp lệ tại đích</a> | <a href="tat_ca_cua_so_dich/BANG_CHUNG.csv">Bằng chứng từng cửa sổ</a></p>'
    body+='<p><a href="BAO_CAO_PCAP.json">Báo cáo chi tiết</a>. Giữ nguyên model v3. Chưa phải bộ train đủ ba lớp hoặc đánh giá model mới. Không gán các cửa sổ còn lại thành Normal. Các IP/đoạn từ cùng capture phải thuộc cùng một split.</p>'
    body+='<p>Cửa sổ giữ đủ lưu lượng vào đích, không chỉ các gói có SYN. Kiểm tra ở đây dùng cờ gói và nhãn flow theo hướng khởi tạo, dung sai thời gian1 ms. Không coi hai cổng trên cả log là bằng chứng vertical scan.</p>'
    (output/'MO_KET_QUA_PCAP.html').write_text(body,encoding='utf-8')


def run(archive,screen_output,profile_output,output,capture='35'):
    archive=Path(archive).expanduser();screen_output=Path(screen_output).expanduser();profile_output=Path(profile_output).expanduser();output=Path(output).expanduser()
    if output.exists():raise ValueError('Output exists; use a new folder')
    screen_path=screen_output/'BAO_CAO_LOC.json';profile_path=profile_output/'BAO_CAO_NGUON.json'
    screened=json.loads(screen_path.read_text());profiled=json.loads(profile_path.read_text())
    if screened.get('status')!='complete' or profiled.get('status')!='complete' or profiled['screening_report_sha256']!=sha(screen_path):
        raise ValueError('Screening/profile reports are incomplete or do not match')
    identity='CTU-IoT-Malware-Capture-'+capture+'-1'
    source=next(s for s in screened['sources'] if s['capture_id']==identity)
    selected=next(s for s in profiled['sources'] if s['capture_id']==identity)
    if selected.get('unshown_destination_max_syn_history_rows')!=0:
        raise ValueError('Profile omits possible SYN destinations; review before choosing a subset')
    targets=[str(ipaddress.IPv4Address(row['dst'])) for row in selected['displayed_destinations']]
    primary=max(selected['displayed_destinations'],key=lambda row:row['origin_syn_history_rows'])
    if primary['origin_syn_history_rows']==0:raise ValueError('No origin-SYN history evidence in the selected source')
    log_member=PurePosixPath(source['archive_member']);pcap_member=log_member.parent.parent/PCAPS[capture][0]
    if log_member.is_absolute() or '..' in log_member.parts:raise ValueError('Unsafe source member path')
    if not archive.is_file():raise ValueError('Archive not found')
    output.parent.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(output.parent).free<2304*MIB:raise ValueError('Need at least 2.25 GiB free for selected destination caches and results')
    output.mkdir();report=dict(status='in_progress',capture_id=identity,selected_targets=targets,primary_target=primary['dst'],
        archive_name=archive.name,archive_sha256_recorded_at_screening=screened.get('archive_sha256'),
        entire_archive_rehashed=False,screening_report_sha256=sha(screen_path),profile_report_sha256=sha(profile_path),
        pcap_member=str(pcap_member),labelled_log_member=str(log_member),model_changed=False)
    report.update(feature_names=NAMES,divisors=[8,2,1,1,1,1],
                  feature_extractor_sha256=sha(KIT/'part2/features.py'),extractor_tool_sha256=sha(Path(__file__)))
    try:
        seen=set()
        with archive.open('rb') as raw:
            with tarfile.open(fileobj=Progress(raw,archive.stat().st_size),mode='r|gz') as tar:
                for member in tar:
                    name=str(PurePosixPath(member.name))
                    if name not in (str(pcap_member),str(log_member)):continue
                    if name in seen or not member.isfile():raise ValueError('Duplicate/nonregular selected member')
                    with tar.extractfile(member) as stream:
                        if name==str(pcap_member):
                            if member.size!=PCAPS[capture][1]:raise ValueError('Source PCAP size differs from inventory')
                            report['pcap_extraction']=copy_destinations(stream,member.size,targets,output)
                        else:
                            if member.size!=source['source_bytes']:raise ValueError('Native log size changed')
                            report['native_log_extraction']=copy_target_log(stream,source,targets,output)
                    seen.add(name)
                    (output/'BAO_CAO_PCAP.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
                    if len(seen)==2:break
            report['compressed_prefix_bytes_read']=raw.tell()
        if len(seen)!=2:raise ValueError('Selected PCAP or full native log not found')
        info=report['pcap_extraction'];target=primary['dst']
        report['verification']=verify_windows(output/'pcap_da_loc'/(target+'.pcap'),output/'nhan_goc_theo_dich'/(target+'.log.gz'),
            target,(info['source_first_timestamp'],info['source_last_timestamp']),output,capture_id=identity)
        report['status']='complete'
    except Exception as error:report.update(status='failed',error=str(error));raise
    finally:
        (output/'BAO_CAO_PCAP.json').write_text(json.dumps(report,indent=2),encoding='utf-8');write_page(output,report)
    result=report['verification']
    csv_write(output/'TOM_TAT_PCAP.csv',['capture_id','target','matched_native_ddos_syn_packets','complete_ingress_windows','verified_syn_windows'],
        [[identity,result['target'],result['matched_native_ddos_syn_packets'],result['eligible_nonempty_complete_windows'],result['verified_syn_windows']]])
    print('DONE. Open:',output/'MO_KET_QUA_PCAP.html',flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True);parser.add_argument('--screen-output',required=True)
    parser.add_argument('--profile-output',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--capture',choices=list(PCAPS),default='35')
    args=parser.parse_args()
    try:run(args.archive,args.screen_output,args.profile_output,args.output,args.capture)
    except (ValueError,OSError,tarfile.TarError,EOFError,StopIteration) as error:parser.exit(1,'ERROR: '+str(error)+'\n')
