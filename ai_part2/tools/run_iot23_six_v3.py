"""Run the frozen integer V3 on the two reproduced IoT-23 development sources."""
import argparse
from collections import Counter
import csv
import hashlib
import html
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
KIT=HERE if (HERE/'part2/integer.py').is_file() else HERE.parent
sys.path.insert(0,str(KIT))
MODEL_SHA='e10f81b3e3ec9b458c4d574ee978cf0f2efa45954b4f8fe0c86fed6a3a26c35d'
DEFAULT_MODEL=HERE/'model/model.json' if (HERE/'model/model.json').is_file() else KIT/'gowin/hybrid_v3/model/model.json'
LABELS=['Normal','SYN','Vertical scan']
SOURCES={'iot23_hue4':(0,2880),'iot23_syn34':(1,21)}


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read_csv(path, header):
    with path.open(newline='',encoding='utf-8-sig') as stream:
        reader=csv.reader(stream)
        if next(reader,None)!=header:raise ValueError('Unexpected columns: '+str(path))
        rows=list(reader)
    if not rows or any(len(row)!=len(header) for row in rows):raise ValueError('Empty or malformed CSV: '+str(path))
    return rows


def run(data,output,model_path=DEFAULT_MODEL):
    try:
        import numpy as np
        from part2.features import NAMES,quantize
        from part2.integer import infer
    except ImportError:
        raise ValueError('Run with ~/ai_part2/.venv/bin/python; NumPy and Scapy are required')
    data=Path(data).expanduser().resolve();output=Path(output).expanduser().resolve()
    model_path=Path(model_path).expanduser().resolve()
    if output.exists():raise ValueError('Output exists; choose a new folder')
    if sha(model_path)!=MODEL_SHA:raise ValueError('Model differs from the frozen V3; no evaluation written')
    model=json.loads(model_path.read_text())
    parent_report_path=data/'BAO_CAO.json'
    parent_report=json.loads(parent_report_path.read_text())
    if parent_report.get('status')!='complete' or parent_report.get('feature_names')!=NAMES:
        raise ValueError('Expected a completed six-feature recovery folder with BAO_CAO.json')
    folder=data/'du_lieu_6_cot'
    raw_rows=read_csv(folder/'X_6_raw.csv',NAMES)
    q_rows=read_csv(folder/'X_6_fpga.csv',['q0','q1','q2','q3','q4','q5'])
    y_rows=read_csv(folder/'y.csv',['class'])
    info=read_csv(folder/'THONG_TIN_DONG.csv',['row_number','capture_id','window_start'])
    expected_total=sum(count for _,count in SOURCES.values())
    if {len(raw_rows),len(q_rows),len(y_rows),len(info)}!={expected_total}:
        raise ValueError('Expected 2901 aligned rows; do not truncate or reorder the files')
    raw=np.asarray([[int(value) for value in row] for row in raw_rows],dtype=np.int64)
    q=np.asarray([[int(value) for value in row] for row in q_rows],dtype=np.int64)
    labels=np.asarray([int(row[0]) for row in y_rows],dtype=np.int64)
    if np.any(raw<0) or np.any(raw[:,0]==0):raise ValueError('Negative feature or empty raw window')
    expected_q=quantize(raw,model['divisors'])
    if not np.array_equal(q,expected_q):raise ValueError('q CSV differs from raw//divisor with clipping; do not quantize q a second time')
    counts=Counter();last_time={}
    for i,(number,source,slot) in enumerate(info):
        if int(number)!=i+1 or source not in SOURCES or int(labels[i])!=SOURCES[source][0]:
            raise ValueError('Row provenance or native-source label differs')
        timestamp=int(slot)
        if source in last_time and timestamp<=last_time[source]:raise ValueError('Duplicate or reordered source windows')
        last_time[source]=timestamp;counts[source]+=1
    if dict(counts)!={source:count for source,(_,count) in SOURCES.items()} or parent_report.get('windows')!=dict(counts):
        raise ValueError('Capture counts differ from the reviewed sources/report')
    scores=infer(q,model);predictions=scores.argmax(axis=1)
    confusion=np.zeros((3,3),dtype=np.int64)
    for true,predicted in zip(labels,predictions):confusion[true,predicted]+=1
    details=[]
    for i,((number,source,slot),true,predicted,score) in enumerate(zip(info,labels,predictions,scores)):
        details.append([int(number),source,int(slot),int(true),int(predicted),int(true==predicted),*map(int,score)])
    by_source={}
    for source,count in counts.items():
        indices=[i for i,row in enumerate(info) if row[1]==source]
        correct=int((labels[indices]==predictions[indices]).sum())
        by_source[source]=dict(label=SOURCES[source][0],rows=count,correct=correct,incorrect=count-correct)
    report=dict(kind='iot23_v3_development_reproduction',independent_test=False,
                execution='CPU Python frozen integer arithmetic; not a live FPGA run',
                model_sha256=MODEL_SHA,model_retrained=False,input_data_changed=False,
                dataset_folder=str(data),parent_report_sha256=sha(parent_report_path),
                input_sha256={p.name:sha(p) for p in folder.glob('*.csv')},
                total_rows=len(raw),correct=int((labels==predictions).sum()),
                incorrect=int((labels!=predictions).sum()),confusion_matrix=confusion.tolist(),
                matrix_rows='true class 0,1,2',matrix_columns='predicted class 0,1,2',
                by_source=by_source,observed_labels=sorted(set(map(int,labels))),missing_true_classes=[2],
                note='Hue4 and Syn34 were already used in V3 development; no independent accuracy or class2 recall claim',
                source_recovery=parent_report)
    output.mkdir(parents=True)
    with (output/'DU_DOAN.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream)
        writer.writerow(['row_number','capture_id','window_start','true_class','predicted_class','correct','score_normal','score_syn','score_scan'])
        writer.writerows(details)
    (output/'BAO_CAO_DU_DOAN.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    page='''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Dự đoán V3 trên IoT-23</title><style>body{font:17px system-ui;max-width:1100px;margin:30px auto;line-height:1.6}table{border-collapse:collapse;margin:20px 0}td,th{border:1px solid #ccd;padding:8px}th{background:#edf4fa}.note{background:#fff3d2;padding:16px}.bad{background:#ffe1df}</style>'''
    page+='<h1>Model v3 đã chạy dự đoán</h1><p class="note">Đây là tái lập trên hai nguồn đã dùng phát triển v3. Kết quả không phải test độc lập; chưa có mẫu thật lớp2 (vertical scan).</p>'
    page+=f'<p>Đúng nhãn: <b>{report["correct"]}/{len(raw)}</b>. Sai: <b>{report["incorrect"]}</b>. Mỗi dòng là một cửa sổ đầy đủ một giây có gói.</p>'
    page+='<p>Chạy bằng Python trên CPU theo phép tính số nguyên của core FPGA. Dùng nguyên model v3; không huấn luyện lại. Đây chưa phải chạy trên bo hoặc đo khả năng chặn gói.</p>'
    page+='<h2>Kết quả theo nguồn</h2><table><tr><th>Nguồn</th><th>Nhãn thật</th><th>Số dòng</th><th>Đúng</th><th>Sai</th></tr>'
    for source,result in by_source.items():
        page+='<tr><td>'+html.escape(source)+'</td><td>'+LABELS[result['label']]+'</td>'+''.join('<td>'+str(result[key])+'</td>' for key in ('rows','correct','incorrect'))+'</tr>'
    page+='</table><h2>Nhãn thật và dự đoán</h2><p>Hàng = nhãn thật; cột = model dự đoán. Lớp2 không có mẫu thật ở đây, nên chưa đánh giá được khả năng phát hiện lớp2.</p><table><tr><th>Nhãn thật</th>'+''.join('<th>Dự đoán '+name+'</th>' for name in LABELS)+'</tr>'
    for label,row in enumerate(confusion):page+='<tr><th>'+LABELS[label]+'</th>'+''.join('<td>'+str(int(value))+'</td>' for value in row)+'</tr>'
    page+='</table><h2>Xem từng dòng</h2><p>Hiện tối đa10 dòng đầu mỗi nguồn và20 dòng sai đầu tiên. Tệp CSV chứa toàn bộ dự đoán.</p><table><tr><th>Dòng</th><th>Nguồn</th><th>Nhãn thật</th><th>Dự đoán</th><th>Kết quả</th></tr>'
    shown=Counter();indices=[]
    for i,row in enumerate(details):
        if shown[row[1]]<10:indices.append(i);shown[row[1]]+=1
    indices=sorted(set(indices+[i for i,row in enumerate(details) if row[5]==0][:20]))
    for i in indices:
        number,source,_,true,predicted,correct,*_=details[i]
        page+='<tr'+(' class="bad"' if not correct else '')+'><td>'+str(number)+'</td><td>'+html.escape(source)+'</td><td>'+LABELS[true]+'</td><td>'+LABELS[predicted]+'</td><td>'+('Đúng' if correct else 'Sai')+'</td></tr>'
    page+='</table><p><a href="DU_DOAN.csv">Toàn bộ dự đoán CSV</a> | <a href="BAO_CAO_DU_DOAN.json">Báo cáo và nguồn</a></p>'
    page+='<p>Ba scores là điểm số nguyên để chọn lớp lớn nhất, không phải phần trăm xác suất. Kết quả trên hai nguồn này không xóa các giới hạn đã biết của v3: nhầm một SYN hợp lệ đơn lẻ và bỏ sót một số cửa sổ quét chậm trong lab mới.</p>'
    (output/'XEM_DU_DOAN.html').write_text(page,encoding='utf-8')
    print(f'DONE. Correct: {report["correct"]}/{len(raw)}. Reproduction of development sources, NOT an independent test.',flush=True)
    print('Open:',output/'XEM_DU_DOAN.html',flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',required=True,help='Completed recovery folder, containing BAO_CAO.json and du_lieu_6_cot/')
    parser.add_argument('--output',required=True,help='New predictions folder')
    parser.add_argument('--model',default=str(DEFAULT_MODEL))
    args=parser.parse_args()
    try:run(args.data,args.output,args.model)
    except (ValueError,OSError,OverflowError) as error:parser.exit(1,'ERROR: '+str(error)+'\n')
