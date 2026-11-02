"""Repair premature project labels and review saved CSV evidence, no archive I/O."""
import argparse
import csv
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
from urllib.parse import quote

NAMES=['packet_count','mean_ip_bytes','syn_ratio_q127','src_count','dst_count','dst_port_count']
DIVISORS=[8,2,1,1,1,1]
NOTICE='SYN-only packets in a native DDoS flow do not by themselves verify SYN flood. The automatically generated class-1 y.csv has been preserved as y_LEGACY_KHONG_DUNG_TRAIN.csv. Do not use it for training. Raw CSVs, PCAPs, native flow labels and model v3 are unchanged. No Normal label is assigned.\n'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):
    with path.open(newline='',encoding='utf-8-sig') as stream:
        reader=csv.DictReader(stream);rows=list(reader)
        if not reader.fieldnames or any(None in row or None in row.values() for row in rows):raise ValueError('Malformed CSV: '+str(path))
        return reader.fieldnames,rows


def features(folder):
    names,raw=read(folder/'X_6_raw.csv');qnames,q=read(folder/'X_6_fpga.csv')
    if names!=NAMES or qnames!=['q0','q1','q2','q3','q4','q5'] or len(raw)!=len(q):raise ValueError('Unexpected feature CSV columns/length')
    values=[]
    for source,quantized in zip(raw,q):
        row=[int(source[name]) for name in NAMES]
        if any(value<0 for value in row) or row[0]==0:raise ValueError('Invalid nonempty feature window')
        if [int(quantized[name]) for name in qnames]!=[min(127,value//div) for value,div in zip(row,DIVISORS)]:
            raise ValueError('Raw and quantized feature CSVs differ')
        values.append(row)
    return values


def write_csv(path,names,rows):
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(names);writer.writerows(rows)


def review(input_folder,output):
    source=Path(input_folder).expanduser().resolve();output=Path(output).expanduser().resolve()
    if output.exists():raise ValueError('Output exists; use a new folder')
    source_report=source/'BAO_CAO_PCAP.json';previous=json.loads(source_report.read_text())
    if previous.get('status')!='complete' or previous.get('capture_id')!='CTU-IoT-Malware-Capture-35-1':
        raise ValueError('Expected the completed capture35 extraction folder')
    verification=previous['verification'];target=verification['target']
    old=source/'syn_da_kiem_tra';new_style=source/'ung_vien_syn_chua_gan_nhan'
    candidates=old if old.is_dir() else new_style
    raw=features(source/'tat_ca_cua_so_dich');candidate_rows=features(candidates)
    _,evidence=read(source/'tat_ca_cua_so_dich/BANG_CHUNG.csv')
    _,provenance=read(candidates/'THONG_TIN_DONG.csv')
    if len(raw)!=len(evidence) or len(raw)!=verification['eligible_nonempty_complete_windows'] or len(candidate_rows)!=len(provenance):
        raise ValueError('Feature/evidence/provenance lengths differ')
    expected=verification.get('pure_native_ddos_syn_candidate_windows',verification.get('verified_syn_windows'))
    if len(candidate_rows)!=expected:raise ValueError('Candidate count differs from original extraction report')
    y=old/'y.csv';y_backup=old/'y_LEGACY_KHONG_DUNG_TRAIN.csv'
    if y.exists() and y_backup.exists():raise ValueError('Both current and legacy y files exist; preserve them for manual review')
    label_source=y if y.exists() else y_backup if y_backup.exists() else None
    if old.is_dir() and label_source is None:raise ValueError('Legacy candidate label file missing; preserve input for review')
    if label_source:
        header,labels=read(label_source)
        if header!=['class'] or len(labels)!=len(candidate_rows) or any(row['class']!='1' for row in labels):
            raise ValueError('Legacy labels differ from the old automatic class-1 export; no files changed')
    notice=source/'NHAN_SYN_FLOOD_CHUA_XAC_MINH.txt'
    if notice.exists() and notice.read_text()!=NOTICE:raise ValueError('Existing notice differs; preserve it for review')
    old_page=source/'MO_KET_QUA_PCAP.html';page_backup=source/'MO_KET_QUA_PCAP_TRUOC_SUA_NHAN.html'
    if page_backup.exists() and old_page.exists() and 'LABEL_REVIEW_V2' not in old_page.read_text():
        raise ValueError('Existing HTML backup and edited page need manual review')
    # All candidate facts are joined to the complete set, including mixed windows.
    slots={};windows=[];mismatches=0
    for i,(row,ev) in enumerate(zip(raw,evidence),1):
        if int(ev['row_number'])!=i:raise ValueError('Window row numbering differs')
        slot=int(ev['window_start']);syn=int(ev['syn_open_packets']);matched=int(ev['native_ddos_syn_packets'])
        if slot in slots or not 0<=matched<=syn<=row[0]:raise ValueError('Invalid packet evidence counts')
        mismatches+=int(row[2]!=127*syn//row[0])
        entry=dict(window_start=slot,packet_count=row[0],mean_ip_bytes=row[1],syn_ratio_q127=row[2],
                   syn_open_packets=syn,native_ddos_syn_packets=matched)
        slots[slot]=row;windows.append(entry)
    for row,info in zip(candidate_rows,provenance):
        if row!=slots.get(int(info['window_start'])) or row[2]!=127 or info['protected_ip']!=target or info.get('capture_id')!=previous['capture_id']:
            raise ValueError('Candidate does not match the full ingress window')
    if not windows:raise ValueError('No complete ingress windows to review')
    output.mkdir(parents=True);candidate_output=output/'ung_vien_syn_chua_gan_nhan';candidate_output.mkdir()
    for name in ['X_6_raw.csv','X_6_fpga.csv','THONG_TIN_DONG.csv']:shutil.copyfile(candidates/name,candidate_output/name)
    ranked=sorted(windows,key=lambda row:(row['native_ddos_syn_packets'],row['syn_open_packets']),reverse=True)
    write_csv(output/'CUA_SO_NHIEU_SYN_NHAT.csv',list(ranked[0]),[[row[name] for name in ranked[0]] for row in ranked[:20]])
    report=dict(status='complete',kind='label_correction_and_saved_window_review',input_folder=str(source),
                input_report_sha256=sha(source_report),capture_id=previous['capture_id'],target=target,
                old_pure_syn_candidate_windows=len(candidate_rows),candidate_packet_count_range=[min(r[0] for r in candidate_rows),max(r[0] for r in candidate_rows)] if candidate_rows else None,
                unique_candidate_raw_vectors=len({tuple(row) for row in candidate_rows}),
                complete_ingress_windows=len(windows),peak_syn_packets_per_second=max(row['syn_open_packets'] for row in windows),
                peak_native_ddos_syn_packets_per_second=max(row['native_ddos_syn_packets'] for row in windows),
                raw_vs_packet_audit_syn_ratio_mismatch_rows=mismatches,highest_syn_windows=ranked[:20],
                flags_recorded_in_previous_extraction=previous['pcap_extraction']['retained_tcp_flag_bytes'],
                syn_flood_verified=False,project_labels_created=False,normal_labels_created=False,
                archive_opened=False,pcap_opened=False,model_changed=False,
                native_flow_labels_changed=False,raw_and_quantized_features_changed=False,
                legacy_label_backup=str(y_backup) if label_source else None,
                legacy_label_sha256=sha(label_source) if label_source else None,
                note='Candidate packet facts are retained unlabelled. Sparse pure SYN is not proof of flood; inspect the full-window peak evidence, including mixed windows. No fixed rate threshold is introduced.')
    # Deactivate only the old tool's generated labels, reversibly; preserve all evidence.
    if y.exists():y.rename(y_backup)
    if old.is_dir():notice.write_text(NOTICE)
    if old.is_dir() and old_page.exists() and not page_backup.exists():old_page.rename(page_backup)
    if old.is_dir():
        relative=quote(os.path.relpath(output/'MO_KET_QUA_SUA.html',source),safe='/._-')
        old_page.write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><!-- LABEL_REVIEW_V2 --><h1>Nhãn SYN flood cũ chưa được xác minh</h1><p>File y.csv tự động đã được lưu lại với tên y_LEGACY_KHONG_DUNG_TRAIN.csv. Dữ liệu gốc và model giữ nguyên. Một SYN mỗi giây chưa đủ bằng chứng flood; không tự gán Normal.</p><p><a href="'+html.escape(relative,quote=True)+'">Mở báo cáo sửa nhãn và xem toàn bộ cửa sổ</a></p>',encoding='utf-8')
    (output/'BAO_CAO_SUA_NHAN.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    write_csv(output/'TOM_TAT_SUA_NHAN.csv',
        ['target','pure_syn_candidates','candidate_min_packets','candidate_max_packets','peak_syn_pps_all_windows','peak_native_ddos_syn_pps_all_windows','automatic_flood_labels'],
        [[target,len(candidate_rows),*(report['candidate_packet_count_range'] or ['', '']),report['peak_syn_packets_per_second'],report['peak_native_ddos_syn_packets_per_second'],0]])
    body='<!doctype html><html lang="vi"><meta charset="utf-8"><title>Kiểm lại nhãn capture35</title><style>body{font:18px system-ui;max-width:1100px;margin:30px auto;line-height:1.6}table{border-collapse:collapse}td,th{border:1px solid #ccd;padding:8px}</style>'
    body+='<h1>Ứng viên SYN chưa được gán nhãn flood</h1>'
    if label_source:
        body+='<p>Nhãn1 tự động của phiên bản trước được xuất quá sớm. Bản sao được giữ lại, nhưng file y.csv không còn ở đường dẫn dùng để train.</p>'
    body+='<p>Sáu đặc trưng, PCAP, nhãn flow gốc và model không đổi; không tự đổi các dòng này thành Normal.</p>'
    body+='<p>Ứng viên thuần SYN: '+str(len(candidate_rows))+'. Số gói/giây của các ứng viên: '+html.escape(str(report['candidate_packet_count_range']))+'.</p>'
    body+='<p>Đã xem cả '+str(len(windows))+' cửa sổ, gồm cửa sổ trộn SYN với lưu lượng khác. Đỉnh SYN mở: '+str(report['peak_syn_packets_per_second'])+' gói/giây; đỉnh SYN mở khớp DDoS gốc: '+str(report['peak_native_ddos_syn_packets_per_second'])+' gói/giây. Các giá trị này chưa tự tạo nhãn flood.</p>'
    body+='<table><tr><th>Giây</th><th>Tổng gói</th><th>SYN mở</th><th>SYN mở khớp DDoS</th><th>SYN×127</th></tr>'
    for row in ranked[:20]:body+='<tr>'+''.join('<td>'+str(row[key])+'</td>' for key in ('window_start','packet_count','syn_open_packets','native_ddos_syn_packets','syn_ratio_q127'))+'</tr>'
    body+='</table><p><a href="TOM_TAT_SUA_NHAN.csv">Tóm tắt</a> | <a href="BAO_CAO_SUA_NHAN.json">Báo cáo đầy đủ</a> | <a href="ung_vien_syn_chua_gan_nhan/X_6_raw.csv">Các ứng viên chưa gán nhãn</a></p><p>Bước này chỉ đọc CSV và báo cáo đã có, không đọc lại archive hoặc PCAP. Chưa kết luận toàn capture35 không có SYN flood hay vertical scan.</p>'
    (output/'MO_KET_QUA_SUA.html').write_text(body,encoding='utf-8')
    print('DONE. Legacy automatic labels preserved and disabled; no new project labels created.',flush=True)
    print('Open:',output/'MO_KET_QUA_SUA.html',flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    try:review(args.input,args.output)
    except (ValueError,OSError,KeyError) as error:parser.exit(1,'ERROR: '+str(error)+'\n')
