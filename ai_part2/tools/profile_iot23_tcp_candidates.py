"""Profile previously filtered native TCP DDoS logs without opening an archive.

History markers are flow evidence, not packet flags or SYN-flood labels.
"""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import html
import json
import math
from pathlib import Path
import sys
import time

DETAILS={'det_label','detailed-label','detailedlabel','detailed_label'}


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


class FrequentTargets:
    """Misra-Gries candidates; recount exactly and disclose the omission bound."""
    def __init__(self,capacity):self.capacity=capacity;self.counts={};self.decrements=0
    def add(self,key):
        if key in self.counts:self.counts[key]+=1
        elif len(self.counts)<self.capacity:self.counts[key]=1
        else:
            self.decrements+=1
            for current in list(self.counts):
                if self.counts[current]==1:del self.counts[current]
                else:self.counts[current]-=1


def flows(path):
    fields=None
    required={'ts','duration','id.orig_h','id.resp_h','id.resp_p','proto','history','conn_state','orig_pkts','label'}
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        for line in stream:
            if line.startswith('#fields'):
                if fields is not None:raise ValueError('Multiple headers need review')
                fields=line.split()[1:]
                if not required<=set(fields) or len(DETAILS.intersection(fields))!=1 or len(set(fields))!=len(fields):
                    raise ValueError('Unsupported original flow header')
                detail=next(iter(DETAILS.intersection(fields)))
                continue
            if line.startswith('#') or not line.strip():continue
            values=line.split()
            if fields is None or len(values)!=len(fields):raise ValueError('Malformed candidate log')
            row=dict(zip(fields,values))
            if row['proto']!='tcp' or row['label'].casefold()!='malicious' or row[detail]!='DDoS':
                raise ValueError('Candidate file contains a row outside original Malicious/DDoS TCP selection')
            yield row
    if fields is None:raise ValueError('Missing original flow header')


def packet_metadata(value):
    if value in ('-','(empty)'):return None
    result=int(value)
    if result<0:raise ValueError('Negative native packet count')
    return result


def interval(row):
    timestamp=float(row['ts'])
    duration=None if row['duration'] in ('-','(empty)') else float(row['duration'])
    if not math.isfinite(timestamp) or (duration is not None and (not math.isfinite(duration) or duration<0)):
        raise ValueError('Invalid native time/duration')
    return timestamp,duration


def profile(path,capture_id,expected_rows,capacity=65536):
    all_targets=FrequentTargets(capacity);syn_targets=FrequentTargets(capacity)
    histories=Counter();states=Counter();n=0;syn_rows=0;checksum_rows=0;orig_sum=0;missing_orig=0
    last=time.monotonic()
    for row in flows(path):
        n+=1;history=row['history'];histories[history]+=1;states[row['conn_state']]+=1
        all_targets.add(row['id.resp_h'])
        if 'S' in history:syn_rows+=1;syn_targets.add(row['id.resp_h'])
        if 'C' in history:checksum_rows+=1
        packets=packet_metadata(row['orig_pkts'])
        if packets is None:missing_orig+=1
        else:orig_sum+=packets
        if time.monotonic()-last>=10:
            print(capture_id,f'pass 1: {n}/{expected_rows} original candidate flows; no archive read',flush=True)
            last=time.monotonic()
    if n!=expected_rows:raise ValueError('Candidate row count differs from the completed screening report')
    keys=set(all_targets.counts)|set(syn_targets.counts)
    targets={};recount=0;last=time.monotonic()
    for row in flows(path):
        recount+=1;destination=row['id.resp_h']
        if destination in keys:
            timestamp,duration=interval(row);port=int(row['id.resp_p'])
            if not 0<=port<=65535:raise ValueError('Invalid native destination port')
            if destination not in targets:
                targets[destination]=dict(dst=destination,flow_records=0,origin_syn_history_rows=0,
                    checksum_history_rows=0,orig_pkts_metadata_sum=0,missing_orig_pkts_rows=0,
                    ports=Counter(),first_flow_ts=timestamp,last_flow_ts=timestamp,
                    last_known_flow_end=None,missing_duration_rows=0,
                    first_origin_ip=row['id.orig_h'],multiple_origin_ips=False)
            target=targets[destination];target['flow_records']+=1
            target['origin_syn_history_rows']+=int('S' in row['history'])
            target['checksum_history_rows']+=int('C' in row['history'])
            packets=packet_metadata(row['orig_pkts'])
            if packets is None:target['missing_orig_pkts_rows']+=1
            else:target['orig_pkts_metadata_sum']+=packets
            target['ports'][port]+=1
            target['first_flow_ts']=min(target['first_flow_ts'],timestamp)
            target['last_flow_ts']=max(target['last_flow_ts'],timestamp)
            if duration is None:target['missing_duration_rows']+=1
            elif target['last_known_flow_end'] is None or timestamp+duration>target['last_known_flow_end']:
                target['last_known_flow_end']=timestamp+duration
            target['multiple_origin_ips']|=row['id.orig_h']!=target['first_origin_ip']
        if time.monotonic()-last>=10:
            print(capture_id,f'pass 2: {recount}/{expected_rows}; exact recount of retained destination candidates',flush=True)
            last=time.monotonic()
    if recount!=n:raise ValueError('Candidate row count changed between passes')
    # Prefer SYN-marked destinations, but also show dominant other TCP DDoS traffic.
    ranked=sorted(targets.values(),key=lambda r:(r['origin_syn_history_rows'],r['flow_records']),reverse=True)
    most_flows=sorted(targets.values(),key=lambda r:r['flow_records'],reverse=True)
    chosen={r['dst'] for r in ranked[:10]+most_flows[:10]}
    for target in ranked:
        if len(chosen)>=20:break
        chosen.add(target['dst'])
    shown=[r for r in ranked if r['dst'] in chosen]
    unshown=[r for r in ranked if r['dst'] not in chosen]
    unshown_flow_bound=max([all_targets.decrements]+[r['flow_records'] for r in unshown])
    unshown_syn_bound=max([syn_targets.decrements]+[r['origin_syn_history_rows'] for r in unshown])
    for target in shown:
        target['distinct_destination_ports']=len(target['ports'])
        target['ports_most_common']=target.pop('ports').most_common(12)
        target['evidence']='native flow metadata only; verify complete packet stream before labelling'
    return dict(capture_id=capture_id,flow_records=n,native_history=dict(histories),native_connection_states=dict(states),
                origin_syn_history_rows=syn_rows,checksum_history_rows=checksum_rows,
                orig_pkts_metadata_sum=orig_sum,missing_orig_pkts_rows=missing_orig,
                candidate_capacity_per_sketch=capacity,
                unretained_destination_max_flow_records=all_targets.decrements,
                unretained_destination_max_syn_history_rows=syn_targets.decrements,
                unshown_destination_max_flow_records=unshown_flow_bound,
                unshown_destination_max_syn_history_rows=unshown_syn_bound,
                retained_destinations_recounted=len(keys),displayed_destinations=shown,
                note='S marks origin SYN in Zeek history, C marks bad-checksum evidence. Neither substitutes for actual TCP flags/rate. Packet sums are log metadata, not counts decoded from PCAP.')


def page(output,report):
    text='''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Chọn nguồn SYN từ log IoT-23</title><style>body{font:17px system-ui;max-width:1200px;margin:30px auto;line-height:1.6}table{border-collapse:collapse;margin:20px 0}td,th{border:1px solid #ccd;padding:8px}th{background:#edf4fa}.note{padding:16px;background:#fff1cc}</style>'''
    text+='<h1>Phân tích ứng viên DDoS TCP</h1><p class="note">Chỉ đọc các log đã lọc. Chưa đọc PCAP, chưa gán nhãn SYN flood hoặc vertical scan, chưa tạo tập train và không đổi model.</p>'
    if report['status']!='complete':text+='<p>Chưa hoàn tất: '+html.escape(report.get('error',''))+'</p>'
    text+='<p>History S: log ghi nhận SYN khởi tạo. History C: log ghi bằng chứng checksum lỗi. Một flow có S vẫn chưa chứng minh SYN flood. orig_pkts là số gói theo log, chưa phải kết quả đếm PCAP.</p>'
    text+='<table><tr><th>Capture</th><th>Flow DDoS TCP</th><th>Flow có S</th><th>Flow có C</th><th>Tổng orig_pkts theo log</th></tr>'
    for source in report['sources']:
        text+='<tr><td>'+html.escape(source['capture_id'])+'</td>'+''.join('<td>'+str(source[key])+'</td>' for key in ('flow_records','origin_syn_history_rows','checksum_history_rows','orig_pkts_metadata_sum'))+'</tr>'
    text+='</table>'
    for source in report['sources']:
        text+='<h2>'+html.escape(source['capture_id'])+'</h2><p>Số đích được giữ để đếm lại: '+str(source['retained_destinations_recounted'])+'. Mỗi đích không hiển thị trong bảng có tối đa '+str(source['unshown_destination_max_flow_records'])+' flow DDoS TCP, trong đó tối đa '+str(source['unshown_destination_max_syn_history_rows'])+' flow có S. Đây là giới hạn của bước sàng lọc, không phải kết luận các đích đó không có tấn công.</p>'
        text+='<p>Hiển thị tối đa20 đích, gồm đích có nhiều flow mang S và đích có nhiều flow tổng. Số đếm cho mỗi đích hiển thị đã được đếm lại chính xác. Số cổng là trên cả log, chưa phải số cổng trong một giây.</p><table><tr><th>IP đích</th><th>Flow</th><th>Có S</th><th>Có C</th><th>orig_pkts theo log</th><th>Số cổng đích</th></tr>'
        for target in source['displayed_destinations']:
            text+='<tr><td>'+html.escape(target['dst'])+'</td>'+''.join('<td>'+str(target[key])+'</td>' for key in ('flow_records','origin_syn_history_rows','checksum_history_rows','orig_pkts_metadata_sum','distinct_destination_ports'))+'</tr>'
        text+='</table>'
    text+='<p><a href="TOM_TAT_TCP.csv">Tóm tắt bốn nguồn CSV</a> | <a href="BAO_CAO_NGUON.json">Báo cáo chi tiết</a> | <a href="DICH_CAN_KIEM_TRA.csv">Các IP đích và thời gian cần kiểm PCAP</a></p>'
    (output/'MO_NGUON_SYN.html').write_text(text,encoding='utf-8')


def run(screen_output,output,capacity=65536):
    if not 1<=capacity<=65536:raise ValueError('Candidate capacity must be between 1 and 65536')
    screen_output=Path(screen_output).expanduser().resolve();output=Path(output).expanduser().resolve()
    if output.exists():raise ValueError('Output exists; use a new folder')
    parent_path=screen_output/'BAO_CAO_LOC.json';parent=json.loads(parent_path.read_text())
    if parent.get('status')!='complete' or parent.get('kind')!='native_source_screening_not_training_dataset':
        raise ValueError('Expected a completed native-label screening report')
    entries=[source for source in parent['sources'] if source.get('tcp_candidates')]
    if not entries:raise ValueError('Completed screening has no TCP DDoS candidates')
    paths=[]
    for source in entries:
        relative=source['tcp_candidates'];path=(screen_output/relative).resolve()
        if not path.is_relative_to(screen_output):raise ValueError('Candidate path escapes screening folder')
        expected=source.get('export_sha256',{}).get(relative)
        if not expected or sha(path)!=expected:raise ValueError('Candidate log checksum differs: '+relative)
        paths.append(path)
    output.mkdir(parents=True)
    report=dict(status='in_progress',kind='native_tcp_candidate_profile_not_training_dataset',
                screening_report_sha256=sha(parent_path),archive_sha256_recorded=parent.get('archive_sha256'),
                archive_opened=False,pcap_opened=False,project_labels_created=False,model_changed=False,
                vertical_scan_audited=False,sources=[])
    try:
        for source,path in zip(entries,paths):
            print('Profiling saved log:',source['capture_id'],flush=True)
            result=profile(path,source['capture_id'],source['tcp_ddos_candidate_rows'],capacity)
            result.update(candidate_log=source['tcp_candidates'],candidate_log_sha256=source['export_sha256'][source['tcp_candidates']])
            report['sources'].append(result)
        report['status']='complete'
    except Exception as error:report.update(status='failed',error=str(error));raise
    finally:
        (output/'BAO_CAO_NGUON.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        with (output/'TOM_TAT_TCP.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.writer(stream);writer.writerow(['capture_id','ddos_tcp_flows','history_S_flows','history_C_flows','orig_pkts_metadata_sum'])
            for source in report['sources']:
                writer.writerow([source['capture_id'],*[source[key] for key in ('flow_records','origin_syn_history_rows','checksum_history_rows','orig_pkts_metadata_sum')]])
        with (output/'DICH_CAN_KIEM_TRA.csv').open('w',newline='',encoding='utf-8') as stream:
            names=['capture_id','dst','flow_records','origin_syn_history_rows','checksum_history_rows','orig_pkts_metadata_sum','distinct_destination_ports','first_flow_ts','last_flow_ts','last_known_flow_end','missing_duration_rows']
            writer=csv.writer(stream);writer.writerow(names)
            for source in report['sources']:
                for target in source['displayed_destinations']:writer.writerow([source['capture_id'],*[target[key] for key in names[1:]]])
        page(output,report)
    print('DONE. Open:',output/'MO_NGUON_SYN.html',flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen-output',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    try:run(args.screen_output,args.output)
    except (ValueError,OSError,EOFError) as error:parser.exit(1,'ERROR: '+str(error)+'\n')
