"""Stream an IoT-23 tar.gz once, extract reviewed PCAPs, and reproduce six features.

Does not extract the entire dataset or train/change an AI model.
"""
import argparse
import csv
import hashlib
import html
import json
import lzma
import math
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
KIT = HERE if (HERE/'part2/features.py').is_file() else HERE.parent
sys.path.insert(0, str(KIT))
REGISTRY = HERE/'NGUON.json' if (HERE/'NGUON.json').exists() else KIT/'spec/HYBRID_V3_SOURCES.json'
IDS = {'hue4':'iot23_hue4', 'syn34':'iot23_syn34', 'echo5':'iot23_echo5'}
EXPECTED_ROWS = {'iot23_hue4':2880, 'iot23_syn34':21, 'iot23_echo5':1619}
MIB = 1024*1024


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while block := f.read(MIB): h.update(block)
    return h.hexdigest()


class Meter:
    def __init__(self, stream, size):
        self.stream, self.size, self.last = stream, size, time.monotonic()
        self.hash = hashlib.sha256()
    def read(self, size=-1):
        data = self.stream.read(size); self.hash.update(data)
        if time.monotonic()-self.last > 10:
            done = self.stream.tell()
            print(f'Reading compressed archive: {done/1e9:.2f}/{self.size/1e9:.2f} GB ({100*done/self.size:.1f}%)', flush=True)
            self.last = time.monotonic()
        return data


def dump_csv(path, names, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer=csv.writer(f); writer.writerow(names); writer.writerows(rows)


def process(archive_path, output, choices):
    # Fail early if the wrong Python interpreter lacks the kit's dependencies.
    try:
        from scapy.utils import RawPcapReader
        from part2.features import NAMES, extract, values, quantize
    except ImportError:
        raise ValueError('Run with ~/ai_part2/.venv/bin/python (NumPy and Scapy are required)')
    archive_path, output = Path(archive_path).expanduser(), Path(output).expanduser()
    if not archive_path.is_file(): raise ValueError('Archive not found: '+str(archive_path))
    if output.exists(): raise ValueError('Output exists; choose a new folder to preserve previous results')
    registry = json.loads(REGISTRY.read_text())
    sources = [next(s for s in registry if s['capture_id']==IDS[c]) for c in choices]
    output.parent.mkdir(parents=True, exist_ok=True)
    required = sum(s['pcap_bytes']+s.get('download_bytes',0)+64*MIB for s in sources)
    if shutil.disk_usage(output.parent).free < required:
        raise ValueError(f'Need at least {required/MIB:.0f} MiB free in the output drive for this selection')
    output.mkdir()
    found = {}; receipts=[]; total_bytes=0; files=0
    basenames={}
    for source in sources:
        name=Path(source['relative_pcap']).name
        basenames[name]=(source,False)
        if source.get('compression')=='xz':basenames[name+'.xz']=(source,True)
    print('Scanning archive once; only selected PCAPs/notes are saved. This may take many minutes.', flush=True)
    with archive_path.open('rb') as raw, (output/'KIEM_KE.csv').open('w',newline='',encoding='utf-8-sig') as inventory:
        meter=Meter(raw,archive_path.stat().st_size)
        writer=csv.writer(inventory);writer.writerow(['archive_path','bytes','type','selected'])
        with tarfile.open(fileobj=meter,mode='r|gz') as archive:
            for member in archive:
                name=PurePosixPath(member.name)
                safe=not name.is_absolute() and '..' not in name.parts
                match=basenames.get(name.name) if safe and member.isfile() else None
                note_source=next((s for s in sources if Path(s['relative_pcap']).parts[0] in name.parts),None)
                is_note=safe and member.isfile() and note_source and (name.name=='README.md' or (name.name=='conn.log.labeled' and 'bro' in name.parts))
                writer.writerow([member.name,member.size,'file' if member.isfile() else 'other',bool(match or is_note)])
                if member.isfile():total_bytes+=member.size;files+=1
                if match:
                    source,compressed=match;sid=source['capture_id']
                    if sid in found:continue
                    expected_size=source['download_bytes'] if compressed else source['pcap_bytes']
                    expected_sha=source['download_sha256'] if compressed else source['pcap_sha256']
                    record=dict(capture_id=sid,member=member.name,bytes=member.size,kind='pcap')
                    if member.size!=expected_size:
                        receipts.append(dict(record,status='size_differs_from_reviewed_capture'));continue
                    destination=output/'raw'/source['relative_pcap']
                    if compressed:destination=Path(str(destination)+'.xz')
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    if destination.exists():
                        receipts.append(dict(record,status='duplicate_name_needs_review'));continue
                    h=hashlib.sha256()
                    with archive.extractfile(member) as src,destination.open('wb') as dst:
                        while block:=src.read(MIB):dst.write(block);h.update(block)
                    if h.hexdigest()!=expected_sha:
                        receipts.append(dict(record,status='hash_differs_from_reviewed_capture',actual_sha256=h.hexdigest()));continue
                    if compressed:
                        expanded=destination.with_suffix('');part=Path(str(expanded)+'.part');size=0
                        with lzma.open(destination,'rb') as src,part.open('wb') as dst:
                            while block:=src.read(MIB):
                                size+=len(block)
                                if size>source['pcap_bytes']:raise ValueError('Expanded PCAP exceeds pinned size')
                                dst.write(block)
                        if size!=source['pcap_bytes'] or sha(part)!=source['pcap_sha256']:raise ValueError('Expanded PCAP differs')
                        part.replace(expanded);destination=expanded
                    found[sid]=destination
                    receipts.append(dict(record,status='verified',sha256=source['pcap_sha256']))
                    print('Verified PCAP:',sid,flush=True)
                elif is_note and member.size<=50*MIB:
                    target=output/'notes'/note_source['capture_id']/name.name
                    if target.exists():continue
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with archive.extractfile(member) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst,MIB)
        # Include any compressed trailer/trailing bytes in this local provenance hash.
        while meter.read(MIB):pass
        archive_hash=meter.hash.hexdigest()
    report=dict(archive_name=archive_path.name,archive_sha256=archive_hash,
                selected=[s['capture_id'] for s in sources],found=list(found),members=files,
                regular_file_bytes_if_fully_extracted=total_bytes,receipts=receipts,
                model_changed=False,full_archive_extracted=False)
    (output/'BAO_CAO.json').write_text(json.dumps(report,indent=2))
    missing=[s['capture_id'] for s in sources if s['capture_id'] not in found]
    if missing:raise ValueError('Selected reviewed PCAPs not found/verified: '+', '.join(missing)+'. Send BAO_CAO.json and KIEM_KE.csv; do not relabel unverified variants.')
    raw_rows=[];ys=[];info=[];counts={}
    for source in sources:
        pcap=found[source['capture_id']]
        print('Extracting six features:',source['capture_id'],flush=True)
        first,last=math.inf,-math.inf
        with RawPcapReader(str(pcap)) as reader:
            for _,meta in reader:
                t=meta.sec+meta.usec/(1e9 if reader.nano else 1e6);first,last=min(first,t),max(last,t)
        start=source.get('verified_episode_start',first);end=source.get('verified_episode_end',last)
        if not first<=start<end<=last:raise ValueError('Invalid source interval')
        windows,stats=extract(pcap,source['protected_ip']+'/32',1.,'exact')
        rows=[(slot,values(w,'exact')) for slot,w in sorted(windows.items()) if math.ceil(start)<=slot<math.floor(end)]
        rows=[(slot,r) for slot,r in rows if r[0]>0]
        if len(rows)!=EXPECTED_ROWS[source['capture_id']]:raise ValueError('Unexpected window count; inspect before using labels')
        if source['label']==1 and (stats['ingress_ipv4']!=source['verified_syn_packets'] or any(r[2]!=127 or r[5]!=1 for _,r in rows)):
            raise ValueError('SYN packet evidence differs from reviewed episode')
        for slot,row in rows:
            raw_rows.append(row);ys.append([source['label']]);info.append([len(raw_rows),source['capture_id'],slot])
        counts[source['capture_id']]=len(rows)
    data=output/'du_lieu_6_cot';data.mkdir()
    dump_csv(data/'X_6_raw.csv',NAMES,raw_rows)
    dump_csv(data/'X_6_fpga.csv',['q0','q1','q2','q3','q4','q5'],quantize(raw_rows,[8,2,1,1,1,1]).tolist())
    dump_csv(data/'y.csv',['class'],ys)
    dump_csv(data/'THONG_TIN_DONG.csv',['row_number','capture_id','window_start'],info)
    report.update(windows=counts,total_windows=len(raw_rows),feature_names=NAMES,
                  observed_labels=sorted({row[0] for row in ys}),
                  class2_note='Vertical scan is not supplied by this native registry; use controlled-lab data with verified labels',
                  purpose='Reproduce existing V3 development sources; not new independent test or retraining')
    (output/'BAO_CAO.json').write_text(json.dumps(report,indent=2))
    names_vi=['Số gói','Byte IP trung bình','SYN×127','Số IP nguồn','Số IP đích','Số cổng đích']
    body=''.join('<tr><td>'+str(i+1)+'</td>'+''.join('<td>'+str(v)+'</td>' for v in row)+'<td>'+str(ys[i][0])+'</td></tr>' for i,row in enumerate(raw_rows[:20]))
    page='''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Kết quả xử lý IoT-23</title><style>body{font:17px system-ui;max-width:1100px;margin:30px auto;line-height:1.6}td,th{padding:9px;border:1px solid #ccd}table{border-collapse:collapse}th{background:#edf4fa}</style>'''
    page+='<h1>Đã tạo đúng sáu đặc trưng</h1><p>Đã đọc archive và chỉ trích PCAP được xác minh. Không train hoặc đổi model.</p>'
    page+='<p>Số cửa sổ theo nguồn: '+html.escape(json.dumps(counts))+'</p>'
    page+='<p><a href="du_lieu_6_cot/X_6_raw.csv">X_6_raw.csv: đúng sáu cột đầu vào</a> | <a href="du_lieu_6_cot/X_6_fpga.csv">Sáu cột q</a> | <a href="du_lieu_6_cot/y.csv">y.csv: nhãn riêng</a></p>'
    page+='<p>Mỗi dòng là một giây. Nhãn0=Normal,1=đoạn SYN đã xác minh. Không có lớp2 trong các nguồn native được chọn; vertical scan của dự án lấy từ lab. Đây chưa phải bộ train mới đủ ba lớp. Các nguồn này đã dùng development v3.</p>'
    page+='<table><tr><th>Dòng</th>'+''.join('<th>'+n+'</th>' for n in names_vi)+'<th>Nhãn, không phải input</th></tr>'+body+'</table>'
    page+='<p>Tỷ lệ SYN lấy phần nguyên của127×SYN mở/số gói. Độ dài dùng IPv4 TotalLength. Mỗi cửa sổ chỉ tính hướng tới IP bảo vệ. q=clip(raw//[8,2,1,1,1,1],0,127). Không lấy sáu cột tùy ý từ bảng11cột chuẩn hóa theo flow.</p>'
    (output/'MO_KET_QUA.html').write_text(page,encoding='utf-8')
    print('DONE. Open:',output/'MO_KET_QUA.html',flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',required=True);p.add_argument('--output',required=True)
    p.add_argument('--sources',nargs='+',choices=list(IDS),default=['hue4','syn34'])
    a=p.parse_args()
    try:process(a.archive,a.output,list(dict.fromkeys(a.sources)))
    except (ValueError,OSError,tarfile.TarError,EOFError) as e:p.exit(1,'ERROR: '+str(e)+'\n')
