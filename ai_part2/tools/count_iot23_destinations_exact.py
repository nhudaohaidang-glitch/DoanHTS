"""Exact destination census of saved native TCP DDoS flows, no project labels.

Sort compact IPv4/packet-metadata records on disk; never turn flow totals into PPS.
"""
import argparse
from collections import Counter
import csv
import heapq
import html
import ipaddress
import json
from pathlib import Path
import shutil
import time

from profile_iot23_tcp_candidates import flows,sha,packet_metadata,interval

MIB=1024*1024
UNKNOWN=(1<<64)-1


def group_exact(records,chunk_size=131072,top_k=20):
    """Input sorted by destination; carry groups across bounded chunk boundaries."""
    import numpy as np
    count=0;flow_hist=Counter();packet_hist=Counter();heaps={name:[] for name in ('flow_records','known_orig_pkts_sum','max_orig_pkts_in_flow')}
    carry=None;max_flows=0;max_packets=0;max_flow_packets=0;missing_total=0;packet_total=0;tick=time.monotonic()
    def consume(value):
        nonlocal count,max_flows,max_packets,max_flow_packets,missing_total,packet_total
        dst,n,packets,missing,largest=value
        count+=1;flow_hist[n]+=1;packet_hist[packets]+=1
        max_flows=max(max_flows,n);max_packets=max(max_packets,packets);max_flow_packets=max(max_flow_packets,largest)
        missing_total+=missing;packet_total+=packets
        for name,metric in [('flow_records',n),('known_orig_pkts_sum',packets),('max_orig_pkts_in_flow',largest)]:
            heap=heaps[name]
            if len(heap)<top_k or metric>heap[0][0] or (metric==heap[0][0] and -dst>heap[0][1]):
                item=(metric,-dst,n,packets,missing,largest)
                if len(heap)<top_k:heapq.heappush(heap,item)
                else:heapq.heapreplace(heap,item)
    for begin in range(0,len(records),chunk_size):
        block=records[begin:begin+chunk_size];dest=block['dst'];pkts=block['packets']
        starts=np.r_[0,np.flatnonzero(dest[1:]!=dest[:-1])+1]
        ends=np.r_[starts[1:],len(block)]
        known=pkts!=UNKNOWN;numeric=np.where(known,pkts,0)
        sums=np.add.reduceat(numeric,starts);missing=np.add.reduceat((~known).astype(np.int64),starts)
        largest=np.maximum.reduceat(numeric,starts)
        for at,end,total,unknown,maximum in zip(starts,ends,sums,missing,largest):
            value=(int(dest[at]),int(end-at),int(total),int(unknown),int(maximum))
            if carry is not None and carry[0]==value[0]:
                carry=(carry[0],carry[1]+value[1],carry[2]+value[2],carry[3]+value[3],max(carry[4],value[4]))
            else:
                if carry is not None:consume(carry)
                carry=value
        if time.monotonic()-tick>=10:
            print(f'Exact grouping: {min(begin+chunk_size,len(records))}/{len(records)} flows; completed destinations {count}',flush=True);tick=time.monotonic()
    if carry is not None:consume(carry)
    selected={}
    rankings={}
    for name,heap in heaps.items():
        ranking=[]
        for metric,negative_dst,n,packets,missing,largest in sorted(heap,reverse=True):
            ip=str(ipaddress.IPv4Address(-negative_dst));ranking.append(ip)
            selected[ip]=dict(dst=ip,flow_records=n,known_orig_pkts_sum=packets,
                              missing_orig_pkts_rows=missing,max_orig_pkts_in_flow=largest)
        rankings[name]=ranking
    return dict(unique_destination_ips=count,max_flow_records_per_destination=max_flows,
                flow_records_grouped=sum(size*destinations for size,destinations in flow_hist.items()),
                max_known_orig_pkts_sum_per_destination=max_packets,max_orig_pkts_in_one_flow=max_flow_packets,
                known_orig_pkts_sum=packet_total,missing_orig_pkts_rows=missing_total,
                destination_flow_count_histogram=dict(flow_hist),destination_known_packet_sum_histogram=dict(packet_hist),
                exact_rankings=rankings,selected_destinations=selected)


def details(path,selected,expected_rows):
    results={ip:dict(flow_records_recounted=0,known_orig_pkts_recounted=0,missing_orig_pkts_recounted=0,
                     origin_syn_history_rows=0,checksum_history_rows=0,ports=Counter(),
                     first_flow_ts=None,last_flow_ts=None,last_known_flow_end=None,missing_duration_rows=0)
             for ip in selected}
    n=0;tick=time.monotonic()
    for row in flows(path):
        n+=1;value=results.get(row['id.resp_h'])
        if value is not None:
            value['flow_records_recounted']+=1
            packets=packet_metadata(row['orig_pkts'])
            if packets is None:value['missing_orig_pkts_recounted']+=1
            else:value['known_orig_pkts_recounted']+=packets
            value['origin_syn_history_rows']+=int('S' in row['history'])
            value['checksum_history_rows']+=int('C' in row['history'])
            port=int(row['id.resp_p'])
            if not 0<=port<=65535:raise ValueError('Invalid destination port')
            value['ports'][port]+=1;start,duration=interval(row)
            value['first_flow_ts']=start if value['first_flow_ts'] is None else min(value['first_flow_ts'],start)
            value['last_flow_ts']=start if value['last_flow_ts'] is None else max(value['last_flow_ts'],start)
            if duration is None:value['missing_duration_rows']+=1
            elif value['last_known_flow_end'] is None or start+duration>value['last_known_flow_end']:
                value['last_known_flow_end']=start+duration
        if time.monotonic()-tick>=10:
            print(f'Recounting selected destinations: {n}/{expected_rows} flows',flush=True);tick=time.monotonic()
    if n!=expected_rows:raise ValueError('Source row count changed during destination recount')
    for ip,value in results.items():
        exact=selected[ip]
        if (value['flow_records_recounted'],value['known_orig_pkts_recounted'],value['missing_orig_pkts_recounted'])!=(exact['flow_records'],exact['known_orig_pkts_sum'],exact['missing_orig_pkts_rows']):
            raise ValueError('Exact destination aggregation differs from the independent recount')
        value['distinct_destination_ports']=len(value['ports']);value['ports_most_common']=value.pop('ports').most_common(12)
        exact.update(value)


def write_page(output,report):
    body='<!doctype html><html lang="vi"><meta charset="utf-8"><title>Đếm chính xác IP đích IoT-23</title><style>body{font:18px system-ui;max-width:1150px;margin:30px auto;line-height:1.6}table{border-collapse:collapse}td,th{border:1px solid #ccd;padding:8px}</style>'
    body+='<h1>Đếm theo từng IP đích</h1><p>Chỉ đọc log đã lọc. Số orig_pkts là metadata của log, không phải số gói SYN đã giải mã từ PCAP và không phải gói/giây. Chưa tạo nhãn SYN flood, vertical scan hoặc Normal.</p>'
    if report['status']!='complete':body+='<p>Chưa hoàn tất: '+html.escape(report.get('error',''))+'</p>'
    else:
        result=report['exact']
        body+='<table><tr><th>Thông tin</th><th>Số lượng</th></tr>'
        for label,key in [('Flow DDoS TCP','flow_records'),('IP đích phân biệt','unique_destination_ips'),('Nhiều flow nhất vào một IP','max_flow_records_per_destination'),('Tổng orig_pkts lớn nhất tại một IP theo log','max_known_orig_pkts_sum_per_destination'),('orig_pkts lớn nhất của một flow','max_orig_pkts_in_one_flow'),('Flow thiếu orig_pkts','missing_orig_pkts_rows')]:
            body+='<tr><td>'+label+'</td><td>'+str(report['flow_records'] if key=='flow_records' else result[key])+'</td></tr>'
        body+='</table><p>Đã đếm tất cả IP trong các flow ứng viên. Các bảng top dưới đây là thứ hạng chính xác theo metadata, gồm cả đích ít flow nhưng nhiều orig_pkts. Không chia đều số gói của flow theo thời gian để tạo PPS.</p>'
        for name,title in [('known_orig_pkts_sum','IP nhiều orig_pkts nhất theo log'),('flow_records','IP nhiều flow nhất'),('max_orig_pkts_in_flow','IP có flow chứa nhiều orig_pkts nhất')]:
            body+='<h2>'+title+'</h2><table><tr><th>IP đích</th><th>Flow</th><th>orig_pkts đã biết</th><th>Flow thiếu orig_pkts</th><th>orig_pkts/flow lớn nhất</th><th>Cổng đích</th></tr>'
            for ip in result['exact_rankings'][name]:
                row=result['selected_destinations'][ip]
                body+='<tr><td>'+html.escape(ip)+'</td>'+''.join('<td>'+str(row[key])+'</td>' for key in ('flow_records','known_orig_pkts_sum','missing_orig_pkts_rows','max_orig_pkts_in_flow','distinct_destination_ports'))+'</tr>'
            body+='</table>'
    body+='<p><a href="TOM_TAT_DICH.csv">Tóm tắt CSV</a> | <a href="BAO_CAO_DICH.json">Báo cáo đầy đủ</a></p><p>Giữ nguyên model và dữ liệu nguồn. Kết quả này giúp chọn đích cần kiểm gói thực tế, không tự xác minh loại tấn công.</p>'
    (output/'MO_DICH.html').write_text(body,encoding='utf-8')


def run(screen_output,output,capture='17'):
    try:import numpy as np
    except ImportError:raise ValueError('Use ~/ai_part2/.venv/bin/python; NumPy is required')
    source_root=Path(screen_output).expanduser().resolve();output=Path(output).expanduser().resolve()
    if output.exists():raise ValueError('Output exists; use a new folder')
    parent_path=source_root/'BAO_CAO_LOC.json';parent=json.loads(parent_path.read_text())
    if parent.get('status')!='complete' or parent.get('kind')!='native_source_screening_not_training_dataset':
        raise ValueError('Expected a completed native label screening folder')
    identity=f'CTU-IoT-Malware-Capture-{capture}-1'
    source=next(item for item in parent['sources'] if item['capture_id']==identity)
    relative=source['tcp_candidates'];path=(source_root/relative).resolve()
    if not path.is_relative_to(source_root):raise ValueError('Candidate path escapes source folder')
    expected_hash=source['export_sha256'][relative]
    print('Checking saved candidate log hash; no archive or PCAP read',flush=True)
    if sha(path)!=expected_hash:raise ValueError('Candidate log hash differs from screening report')
    n_expected=source['tcp_ddos_candidate_rows'];dtype=np.dtype([('dst','<u4'),('packets','<u8')])
    required=n_expected*dtype.itemsize+64*MIB
    if n_expected<=0 or required>1024*MIB:raise ValueError('Unexpected destination-record size; review input')
    output.parent.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(output.parent).free<required:raise ValueError(f'Need {required/MIB:.0f} MiB free for temporary destination records')
    output.mkdir();temporary=output/'_destination_records.tmp';records=np.memmap(temporary,dtype=dtype,mode='w+',shape=(n_expected,))
    report=dict(status='in_progress',kind='exact_native_flow_destination_census',capture_id=identity,
                screening_report_sha256=sha(parent_path),candidate_log_sha256=expected_hash,
                archive_opened=False,pcap_opened=False,project_labels_created=False,model_changed=False,
                packet_rates_inferred_from_flows=False,source_files_changed=False)
    try:
        n=0;known_total=0;unknown_total=0;history=Counter();packet_hist=Counter();tick=time.monotonic()
        for row in flows(path):
            if n>=n_expected:raise ValueError('Candidate row count exceeds screening report')
            packets=packet_metadata(row['orig_pkts'])
            if packets is None:unknown_total+=1;encoded=UNKNOWN
            else:
                if packets>=UNKNOWN:raise ValueError('Unsupported native packet count')
                known_total+=packets;encoded=packets;packet_hist[packets]+=1
                if known_total>=UNKNOWN:raise ValueError('Native packet metadata sum exceeds exact uint64 range')
            records[n]=(int(ipaddress.IPv4Address(row['id.resp_h'])),encoded)
            history[row['history']]+=1;n+=1
            if time.monotonic()-tick>=10:
                print(f'Reading saved candidate flows: {n}/{n_expected}',flush=True);tick=time.monotonic()
        if n!=n_expected:raise ValueError('Candidate log row count differs from screening report')
        records.flush();print(f'Sorting {temporary.stat().st_size/MIB:.0f} MiB of temporary destination records; this phase may take a while',flush=True)
        records.sort(order='dst',kind='quicksort');exact=group_exact(records)
        if exact['flow_records_grouped']!=n or exact['known_orig_pkts_sum']!=known_total or exact['missing_orig_pkts_rows']!=unknown_total:
            raise ValueError('Grouped packet metadata does not match input totals')
        print('Recounting exact selected destinations in the saved log',flush=True)
        details(path,exact['selected_destinations'],n)
        if sha(path)!=expected_hash:raise ValueError('Saved candidate log changed during analysis')
        report.update(status='complete',flow_records=n,native_history=dict(history),
                      orig_pkts_per_flow_histogram=dict(packet_hist),exact=exact)
    except Exception as error:report.update(status='failed',error=str(error));raise
    finally:
        records._mmap.close()
        (output/'BAO_CAO_DICH.json').write_text(json.dumps(report,indent=2),encoding='utf-8');write_page(output,report)
    result=report['exact']
    with (output/'TOM_TAT_DICH.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream)
        writer.writerow(['capture_id','flow_records','distinct_dst_ips','max_flows_per_dst','max_known_orig_pkts_sum_per_dst','max_orig_pkts_in_one_flow','missing_orig_pkts_rows'])
        writer.writerow([identity,report['flow_records'],*[result[key] for key in ('unique_destination_ips','max_flow_records_per_destination','max_known_orig_pkts_sum_per_destination','max_orig_pkts_in_one_flow','missing_orig_pkts_rows')]])
    temporary.unlink()
    print('DONE. Open:',output/'MO_DICH.html',flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen-output',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--capture',choices=['17','34'],default='17')
    args=parser.parse_args()
    try:run(args.screen_output,args.output,args.capture)
    except (ValueError,OSError,KeyError,StopIteration,EOFError) as error:parser.exit(1,'ERROR: '+str(error)+'\n')
