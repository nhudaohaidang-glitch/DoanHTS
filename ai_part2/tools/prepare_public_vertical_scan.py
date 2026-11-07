"""Prepare a reviewed public SYN vertical-scan sample as PCAP and flow CSV.

Offline conversion only. Source: Chris Sanders' public packet collection.
Flow labels are this project's behavior review, not original publisher labels.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import html
import json
from pathlib import Path
import struct

from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether
from scapy.utils import RawPcapNgReader, RawPcapReader

SOURCE = dict(
    author='Chris Sanders',
    repository='https://github.com/chrissanders/packets',
    commit='0412fb1dc0aa671128f9da6689e0dbd4459c0b51',
    file='synscan.pcapng',
    url='https://raw.githubusercontent.com/chrissanders/packets/0412fb1dc0aa671128f9da6689e0dbd4459c0b51/synscan.pcapng',
    sha256='3ef7a9011bcc2901080d3800d52fd5bb5cbcc1aeb8b5943bed3810868400aa58',
    bytes=185072,
    readme_sha256='dd48b5c27324e49bbcdbe95dfb00354373919a141fb86186633ce8093e3e244f',
    scanner_ip='172.16.0.8', target_ip='64.13.134.52',
    expected_frames=2011, expected_syn_open=1994,
    expected_target_ports=1000, expected_flow_tuples=1994,
)
STEM = 'chris_sanders_synscan_vertical'
FLOW_FIELDS = ['flow_id','ts','duration','id.orig_h','id.orig_p','id.resp_h','id.resp_p','proto',
               'orig_pkts','resp_pkts','orig_ip_bytes','resp_ip_bytes','orig_syn_open_pkts',
               'orig_tcp_flag_counts','resp_tcp_flag_counts','loai_da_loc','label_basis','source_capture']


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def seconds(microseconds):
    whole, fraction = divmod(microseconds, 1_000_000)
    return f'{whole}.{fraction:06d}'


def read_source(path):
    packets = []
    with RawPcapNgReader(str(path)) as reader:
        for raw, meta in reader:
            if meta.linktype != 1 or meta.tsresol != 1_000_000:
                raise ValueError('Reviewed source must be Ethernet with microsecond timestamps')
            timestamp = (meta.tshigh << 32) | meta.tslow
            decoded = Ether(raw)
            if IP not in decoded or TCP not in decoded:
                raise ValueError('Reviewed sample unexpectedly contains non-IPv4/TCP traffic')
            ip, tcp = decoded[IP], decoded[TCP]
            if ip.frag or int(ip.flags)&1 or len(bytes(ip)) < int(ip.len):
                raise ValueError('Fragmented/truncated packet requires a new source review')
            payload_bytes=int(ip.len)-4*int(ip.ihl)-4*int(tcp.dataofs)
            if payload_bytes < 0:
                raise ValueError('Invalid IP/TCP header length')
            pair = (ip.src, ip.dst)
            if pair == (SOURCE['scanner_ip'], SOURCE['target_ip']):
                direction = 'orig'; key = (int(tcp.sport), int(tcp.dport))
            elif pair == (SOURCE['target_ip'], SOURCE['scanner_ip']):
                direction = 'resp'; key = (int(tcp.dport), int(tcp.sport))
            else:
                raise ValueError('Unexpected third host in reviewed sample')
            packets.append(dict(raw=raw, timestamp=timestamp, wirelen=meta.wirelen,
                                direction=direction, key=key, flags=int(tcp.flags),
                                ip_bytes=int(ip.len), tcp_payload_bytes=payload_bytes))
    if any(a['timestamp'] > b['timestamp'] for a,b in zip(packets,packets[1:])):
        raise ValueError('Unexpected timestamp reversal')
    return packets


def summarize(packets):
    probes = [p for p in packets if p['direction']=='orig' and p['flags']&0x12 == 0x02]
    probe_keys = {p['key'] for p in probes}
    target_ports = {p['key'][1] for p in probes}
    all_keys = {p['key'] for p in packets}
    if (len(packets),len(probes),len(target_ports),len(all_keys)) != (
        SOURCE['expected_frames'],SOURCE['expected_syn_open'],SOURCE['expected_target_ports'],SOURCE['expected_flow_tuples']):
        raise ValueError('Reviewed packet/port/flow counts differ')
    if all_keys != probe_keys:
        raise ValueError('A flow without a scanner SYN cannot receive the reviewed label')
    groups = defaultdict(list)
    for packet in packets:
        groups[packet['key']].append(packet)
    rows = []
    for number,(key,members) in enumerate(groups.items(),1):
        orig = [p for p in members if p['direction']=='orig']
        resp = [p for p in members if p['direction']=='resp']
        def flags(part):
            return ';'.join(f'{flag:02x}:{count}' for flag,count in sorted(Counter(p['flags'] for p in part).items()))
        rows.append(dict(zip(FLOW_FIELDS,[
            f'VS{number:06d}',seconds(members[0]['timestamp']),
            seconds(members[-1]['timestamp']-members[0]['timestamp']),
            SOURCE['scanner_ip'],key[0],SOURCE['target_ip'],key[1],'tcp',
            len(orig),len(resp),sum(p['ip_bytes'] for p in orig),sum(p['ip_bytes'] for p in resp),
            sum(p['flags']&0x12 == 0x02 for p in orig),flags(orig),flags(resp),
            'vertical_scan','project_reviewed_packet_behavior',SOURCE['file']])))
    windows = defaultdict(list)
    for packet in probes:
        windows[packet['timestamp']//1_000_000].append(packet)
    evidence = dict(
        capture_frames=len(packets),flow_rows=len(rows),
        scanner_ip=SOURCE['scanner_ip'],target_ip=SOURCE['target_ip'],
        scanner_count=1,target_ip_count=1,distinct_target_ports=len(target_ports),
        scanner_source_ports=sorted({key[0] for key in probe_keys}),
        orig_packets=len(probes),response_packets=len(packets)-len(probes),
        syn_open_packets=len(probes),
        first_packet_timestamp=seconds(packets[0]['timestamp']),
        last_packet_timestamp=seconds(packets[-1]['timestamp']),
        capture_duration_seconds=seconds(packets[-1]['timestamp']-packets[0]['timestamp']),
        verified_scan_first_syn=seconds(probes[0]['timestamp']),
        verified_scan_last_syn=seconds(probes[-1]['timestamp']),
        scan_syn_duration_seconds=seconds(probes[-1]['timestamp']-probes[0]['timestamp']),
        per_second_probe_evidence=[dict(epoch_second=slot,syn_open_packets=len(part),
                                        distinct_target_ports=len({p['key'][1] for p in part}))
                                   for slot,part in sorted(windows.items())],
        packet_tcp_payload_bytes=sum(p['tcp_payload_bytes'] for p in packets),
        flow_definition='TCP 5-tuple across this 23-second sample; orig=scanner, resp=target. Retries with different source ports are separate rows.',
        label_origin='Project review of the public SYN-scan example: one scanner probes 1000 ports on one destination. No original publisher CSV labels exist.',
        late_response_windows_are_not_automatically_labelled_as_active_scan=True,
    )
    return rows,evidence


def write_page(folder, report):
    evidence=report['evidence']
    page='<!doctype html><html lang="vi"><meta charset="utf-8"><title>Vertical scan: PCAP và CSV</title><style>body{font:18px system-ui;max-width:1050px;margin:35px auto;line-height:1.6}table{border-collapse:collapse}td,th{border:1px solid #ccd;padding:8px}</style>'
    page+='<h1>Đã chuẩn bị PCAP và CSV vertical scan</h1>'
    page+='<p>Nguồn: PCAP mẫu <a href="'+html.escape(SOURCE['repository'])+'">Chris Sanders / Packets</a>, synscan.pcapng. Giữ nguyên IP, cổng, thứ tự, thời gian và dữ liệu từng gói; chuyển container PCAPNG thành PCAP Ethernet thông dụng.</p>'
    page+=f'<p><strong>{SOURCE["scanner_ip"]} quét {evidence["distinct_target_ports"]:,} cổng trên một IP đích {SOURCE["target_ip"]}.</strong> PCAP có {evidence["capture_frames"]:,} gói, gồm {evidence["syn_open_packets"]:,} SYN thăm dò và {evidence["response_packets"]} phản hồi. CSV có {evidence["flow_rows"]:,} dòng flow theo 5-tuple.</p>'
    page+='<p><a href="pcap/'+STEM+'.pcap">Mở PCAP</a> | <a href="csv/'+STEM+'.csv">Mở CSV flow</a> | <a href="BAO_CAO_VERTICAL_SCAN.json">Báo cáo nguồn và checksum</a></p>'
    page+='<p>CSV được tạo từ PCAP và gán loai_da_loc=vertical_scan theo hành vi đã kiểm tra. Đây là nhãn của dự án, không phải nhãn Zeek hay CSV do nhà cung cấp phát hành. Các cột orig/resp luôn có hướng scanner → đích và chiều phản hồi. Một cổng có thể xuất hiện trong nhiều flow do scanner đổi cổng nguồn khi thử lại.</p>'
    page+='<p>Mẫu này là một lần quét có sẵn trên Internet, không phải lưu lượng mới sinh hoặc một bộ train/test nhiều phiên độc lập. Không đổi nó thành dữ liệu IoT-23. CSV này là bảng flow, chưa phải sáu đặc trưng model mỗi giây.</p>'
    page+='<table><tr><th>Giây epoch</th><th>SYN thăm dò</th><th>Cổng đích phân biệt</th></tr>'
    for row in evidence['per_second_probe_evidence']:
        page+=f'<tr><td>{row["epoch_second"]}</td><td>{row["syn_open_packets"]}</td><td>{row["distinct_target_ports"]}</td></tr>'
    page+='</table><p>Hoạt động SYN quét kéo dài khoảng 5,14 giây; cả capture khoảng 23,09 giây do còn phản hồi muộn. Không tự gán mọi giây phản hồi muộn là một cửa sổ đang quét. Khi đối chiếu phần cứng, giữ đúng tốc độ và căn cùng cửa sổ thời gian.</p>'
    (folder/'MO_DU_LIEU_SCAN.html').write_text(page,encoding='utf-8')


def build(source, source_readme, output):
    source,source_readme,output=[Path(p) for p in (source,source_readme,output)]
    if output.exists():
        raise ValueError('Output exists; use a new folder')
    if source.stat().st_size != SOURCE['bytes'] or sha(source) != SOURCE['sha256'] or sha(source_readme) != SOURCE['readme_sha256']:
        raise ValueError('Input differs from reviewed public source')
    packets=read_source(source);rows,evidence=summarize(packets)
    folder=output/'vertical_scan'
    for name in ('pcap','csv','nguon_goc'):
        (folder/name).mkdir(parents=True,exist_ok=True)
    (folder/'nguon_goc'/SOURCE['file']).write_bytes(source.read_bytes())
    (folder/'nguon_goc/README_CHRIS_SANDERS.md').write_bytes(source_readme.read_bytes())
    pcap=folder/'pcap'/(STEM+'.pcap')
    with pcap.open('wb') as stream:
        stream.write(b'\xd4\xc3\xb2\xa1'+struct.pack('<HHiIII',2,4,0,0,65535,1))
        for packet in packets:
            sec,usec=divmod(packet['timestamp'],1_000_000)
            stream.write(struct.pack('<IIII',sec,usec,len(packet['raw']),packet['wirelen']))
            stream.write(packet['raw'])
    # Independently read the new container; preserve every raw frame, order,
    # captured/original length and the exact microsecond timestamp.
    with RawPcapReader(str(pcap)) as reader:
        converted=list(reader)
    if len(converted)!=len(packets):
        raise ValueError('PCAP conversion changed packet count')
    for original,(raw,meta) in zip(packets,converted):
        if (raw,meta.sec*1_000_000+meta.usec,meta.wirelen)!=(original['raw'],original['timestamp'],original['wirelen']):
            raise ValueError('PCAP conversion changed packet content/time/length')
    csv_path=folder/'csv'/(STEM+'.csv')
    with csv_path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=FLOW_FIELDS,lineterminator='\n');writer.writeheader();writer.writerows(rows)
    files={str(p.relative_to(folder)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in (pcap,csv_path,folder/'nguon_goc'/SOURCE['file'],folder/'nguon_goc/README_CHRIS_SANDERS.md')}
    report=dict(status='complete',kind='public_vertical_scan_pcap_and_derived_flow_csv',source=SOURCE,
                evidence=evidence,files=files,source_format='pcapng',output_format='classic Ethernet PCAP, microseconds',
                packet_bytes_times_and_order_preserved=True,project_class_id=2,
                publisher_flow_labels_available=False,synthetic_packets_created=False,
                packets_transmitted=False,model_trained_or_changed=False)
    (folder/'BAO_CAO_VERTICAL_SCAN.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    write_page(folder,report)
    print(json.dumps(dict(output=str(folder),frames=len(packets),flows=len(rows),distinct_target_ports=evidence['distinct_target_ports']),indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True);parser.add_argument('--source-readme',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    build(args.source,args.source_readme,args.output)
