"""Stream selected original IoT-23 flow labels; never infer SYN/vertical labels.

This is source screening before packet/window verification, not a training CSV.
"""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import time

MIB=1024*1024
REQUIRED={'ts','duration','id.orig_h','id.orig_p','id.resp_h','id.resp_p','proto','label'}
DETAILS={'detailed-label','det_label','detailedlabel','detailed_label'}


class Meter:
    def __init__(self,stream,total):
        self.stream,self.total=stream,total
        self.hash=hashlib.sha256();self.last=time.monotonic()
    def read(self,size=-1):
        data=self.stream.read(size);self.hash.update(data)
        if time.monotonic()-self.last>=10:
            print(f'Archive: {self.stream.tell()/1e9:.2f}/{self.total/1e9:.2f} GB; screening original labels',flush=True)
            self.last=time.monotonic()
        return data


def checked_inventory(path):
    with path.open(newline='',encoding='utf-8-sig') as stream:
        reader=csv.DictReader(stream)
        if not {'archive_path','bytes','type','selected'}<=set(reader.fieldnames or []):
            raise ValueError('Expected KIEM_KE.csv from the archive processor')
        logs={}
        for row in reader:
            name=PurePosixPath(row['archive_path'])
            if name.name!='conn.log.labeled':continue
            if name.is_absolute() or '..' in name.parts or row['type']!='file':
                raise ValueError('Unsafe or nonregular labelled-log inventory entry')
            parts=[p for p in name.parts if re.fullmatch(r'CTU-(?:IoT-Malware|Honeypot)-Capture-\d+-1',p)]
            if len(parts)!=1:raise ValueError('Unrecognized scenario path')
            scenario=parts[0]
            suffix=list(name.parts[name.parts.index(scenario)+1:-1])
            if suffix and suffix[-1]=='bro':suffix.pop()
            identity=scenario+('/'+'/'.join(suffix) if suffix else '')
            if str(name) in logs or any(v['capture_id']==identity for v in logs.values()):
                raise ValueError('Duplicate labelled-log identity')
            size=int(row['bytes'])
            if size<=0:raise ValueError('Invalid labelled-log size')
            logs[str(name)]=dict(capture_id=identity,bytes=size,
                                 benign_scenario=scenario.startswith('CTU-Honeypot-'))
    if not logs:raise ValueError('Inventory has no labelled logs')
    return logs


def filter_log(source,spec,output,max_export_bytes):
    """Keep original rows/header bytes; candidates stay DDoS, never renamed SYN."""
    identity=spec['capture_id'];stem=identity.replace('/','__')
    fields=None;detail=None;headers=[];labels=Counter();protocols=Counter()
    total=0;tcp_rows=0;normal_rows=0;size=0;digest=hashlib.sha256()
    tcp_path=output/'DDoS_TCP_CAN_KIEM_TRA'/(stem+'.log.gz')
    normal_path=output/'NORMAL_LOG_GOC'/(stem+'.log.gz')
    tcp=None;normal=None;last=time.monotonic()
    try:
        for line in source:
            size+=len(line);digest.update(line)
            if size>spec['bytes']:raise ValueError('Log exceeds declared inventory size')
            if line.startswith(b'#'):
                if line.startswith(b'#fields'):
                    if fields is not None:raise ValueError('Multiple labelled headers need review')
                    fields=line.decode().split()[1:]
                    aliases=DETAILS.intersection(fields)
                    if len(set(fields))!=len(fields) or not REQUIRED<=set(fields) or len(aliases)!=1:
                        raise ValueError('Unsupported labelled-log header: '+identity)
                    detail=next(iter(aliases))
                    if fields[-2:]!=['label',detail]:raise ValueError('Expected trailing original label columns')
                headers.append(line)
                if tcp:tcp.write(line)
                if normal:normal.write(line)
                continue
            if not line.strip():continue
            if fields is None:raise ValueError('Data precedes labelled header')
            # All row widths are checked. No Python flow index is retained.
            values=line.split()
            if len(values)!=len(fields):raise ValueError('Row/header mismatch in '+identity)
            coarse,detailed=values[-2].decode(),values[-1].decode()
            labels[coarse+'/'+detailed]+=1;total+=1
            if detailed=='DDoS' and coarse.casefold()=='malicious':
                proto=values[fields.index('proto')].decode();protocols[proto]+=1
                if proto=='tcp':
                    if tcp is None:
                        tcp_path.parent.mkdir(exist_ok=True)
                        tcp=gzip.open(tcp_path,'wb',compresslevel=1);tcp.writelines(headers)
                    tcp.write(line);tcp_rows+=1
            if spec['benign_scenario'] and coarse.casefold()=='benign':
                if normal is None:
                    normal_path.parent.mkdir(exist_ok=True)
                    normal=gzip.open(normal_path,'wb',compresslevel=1);normal.writelines(headers)
                normal.write(line);normal_rows+=1
            if time.monotonic()-last>=10:
                used=sum(f.fileobj.tell() for f in (tcp,normal) if f is not None)
                if used>max_export_bytes or shutil.disk_usage(output).free<64*MIB:
                    raise ValueError('Export budget/free space reached; partial candidate files are not complete')
                print(identity,f'{size/1e6:.0f}/{spec["bytes"]/1e6:.0f} MB; TCP DDoS candidates {tcp_rows}',flush=True)
                last=time.monotonic()
        if fields is None or size!=spec['bytes']:raise ValueError('Incomplete labelled log: '+identity)
    finally:
        if tcp:tcp.close()
        if normal:normal.close()
    if sum(p.stat().st_size for p in (tcp_path,normal_path) if p.exists())>max_export_bytes:
        raise ValueError('Compressed export exceeds budget')
    export_hashes={}
    for path in (tcp_path,normal_path):
        if path.is_file():
            with path.open('rb') as stream:export_hashes[str(path.relative_to(output))]=hashlib.file_digest(stream,'sha256').hexdigest()
    return dict(capture_id=identity,source_bytes=size,source_sha256=digest.hexdigest(),export_sha256=export_hashes,
                connection_records=total,native_labels=dict(labels),ddos_protocols=dict(protocols),
                tcp_ddos_candidate_rows=tcp_rows,normal_scenario_rows=normal_rows,
                tcp_candidates=str(tcp_path.relative_to(output)) if tcp_rows else None,
                normal_log=str(normal_path.relative_to(output)) if normal_rows else None)


def write_page(output,report):
    page='''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Sàng lọc nguồn IoT-23</title><style>body{font:17px system-ui;max-width:1150px;margin:30px auto;line-height:1.6}table{border-collapse:collapse}td,th{border:1px solid #ccd;padding:8px}th{background:#edf4fa}.note{background:#fff1cc;padding:16px}</style>'''
    page+='<h1>Đã sàng lọc nhãn gốc IoT-23</h1>' if report['status']=='complete' else '<h1>Sàng lọc chưa hoàn tất</h1>'
    page+='<p class="note">Đây là các flow gốc được chọn để kiểm tra nguồn, chưa phải bộ sáu đặc trưng hoặc bộ train đủ ba lớp. TCP DDoS chưa được đổi thành SYN flood. Không đổi HorizontalPortScan thành vertical scan.</p>'
    if report.get('error'):page+='<p>'+html.escape(report['error'])+'</p>'
    page+='<p>Không train hoặc thay model. Không lưu PCAP lớn ra ổ Ubuntu. Log bình thường của Somfy vẫn thuộc nhóm test đã dành riêng; không tự đưa vào train.</p>'
    page+='<p>Một dòng log là một flow, có thể kéo dài nhiều giây. Không đưa trực tiếp các dòng này vào model đang nhận sáu đặc trưng mỗi giây.</p>'
    page+='<table><tr><th>Nguồn</th><th>Flow gốc</th><th>DDoS TCP: cần kiểm PCAP</th><th>DDoS UDP: không phải SYN</th><th>Log Normal riêng</th></tr>'
    for r in report['sources']:
        link=lambda name,count:'<a href="'+html.escape(name,quote=True)+'">'+str(count)+'</a>' if name else str(count)
        page+='<tr><td>'+html.escape(r['capture_id'])+'</td><td>'+str(r['connection_records'])+'</td><td>'+link(r['tcp_candidates'],r['tcp_ddos_candidate_rows'])+'</td><td>'+str(r['ddos_protocols'].get('udp',0))+'</td><td>'+link(r['normal_log'],r['normal_scenario_rows'])+'</td></tr>'
    page+='</table><p><a href="BAO_CAO_LOC.json">Báo cáo nguồn, nhãn và checksum</a> | <a href="TONG_HOP.csv">Bảng tổng hợp CSV</a></p>'
    page+='<p>Bước sau: dùng báo cáo để chọn PCAP/đích/thời gian, kiểm cờ gói và hành vi, rồi mới tạo nhãn cửa sổ một giây với đủ lưu lượng vào đích. Chưa xác minh lớp vertical scan từ các log này; không kết luận toàn bộ PCAP không có hành vi đó.</p>'
    (output/'MO_KET_QUA_LOC.html').write_text(page,encoding='utf-8')


def screen(archive,inventory,output):
    archive=Path(archive).expanduser();inventory=Path(inventory).expanduser();output=Path(output).expanduser()
    if output.exists():raise ValueError('Output exists; use a new folder')
    wanted=checked_inventory(inventory)
    previous=inventory.with_name('BAO_CAO.json')
    previous_hash=json.loads(previous.read_text()).get('archive_sha256') if previous.is_file() else None
    if previous_hash is not None and not re.fullmatch('[0-9a-f]{64}',str(previous_hash)):
        raise ValueError('Previous archive hash has an invalid format')
    if not archive.is_file():raise ValueError('Archive not found')
    output.parent.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(output.parent).free<1024*MIB:raise ValueError('Need at least 1 GiB free for compressed candidate logs')
    output.mkdir();found=set()
    report=dict(status='in_progress',kind='native_source_screening_not_training_dataset',
                archive_name=archive.name,inventory_sha256=hashlib.sha256(inventory.read_bytes()).hexdigest(),
                previous_archive_sha256=previous_hash,
                inventory_selected_is_old_tool_selection_not_class_label=True,
                expected_labelled_logs=len(wanted),sources=[],model_changed=False,
                project_labels_created=False,vertical_class_verified=False,pcaps_saved=False)
    try:
        print('Reading archive once. Keeping compressed selected flow rows; no PCAP extraction.',flush=True)
        with archive.open('rb') as raw:
            meter=Meter(raw,archive.stat().st_size)
            with tarfile.open(fileobj=meter,mode='r|gz') as tar:
                for member in tar:
                    key=str(PurePosixPath(member.name))
                    if key not in wanted:continue
                    if key in found or not member.isfile() or member.size!=wanted[key]['bytes']:
                        raise ValueError('Duplicate, nonregular or changed labelled log: '+key)
                    exported=sum(p.stat().st_size for p in output.rglob('*.log.gz'))
                    budget=1024*MIB-exported
                    if budget<1*MIB:raise ValueError('Compressed candidate export reached 1 GiB budget')
                    with tar.extractfile(member) as source:
                        result=filter_log(source,wanted[key],output,budget)
                    report['sources'].append(dict(archive_member=member.name,**result));found.add(key)
                    (output/'BAO_CAO_LOC.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
                    print('Screened:',result['capture_id'],'TCP DDoS candidates:',result['tcp_ddos_candidate_rows'],flush=True)
            while meter.read(MIB):pass
            report['archive_sha256']=meter.hash.hexdigest()
        if previous_hash is not None and report['archive_sha256']!=previous_hash:
            raise ValueError('Archive differs from the previous BAO_CAO.json; candidate outputs need review')
        if found!=set(wanted):raise ValueError('Not all inventory logs found; do not treat partial outputs as complete')
        report.update(status='complete',total_connection_records=sum(r['connection_records'] for r in report['sources']),
                      total_tcp_ddos_candidate_rows=sum(r['tcp_ddos_candidate_rows'] for r in report['sources']))
    except Exception as error:
        report.update(status='failed',error=str(error));raise
    finally:
        (output/'BAO_CAO_LOC.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        with (output/'TONG_HOP.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.writer(stream);writer.writerow(['capture_id','flow_records','ddos_tcp_candidates','ddos_udp','normal_scenario_rows'])
            for r in report['sources']:writer.writerow([r['capture_id'],r['connection_records'],r['tcp_ddos_candidate_rows'],r['ddos_protocols'].get('udp',0),r['normal_scenario_rows']])
        write_page(output,report)
    print('DONE. Open:',output/'MO_KET_QUA_LOC.html',flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True);parser.add_argument('--inventory',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    try:screen(args.archive,args.inventory,args.output)
    except (ValueError,OSError,tarfile.TarError,EOFError,UnicodeError) as error:parser.exit(1,'ERROR: '+str(error)+'\n')
