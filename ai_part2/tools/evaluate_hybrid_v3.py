import argparse,html,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from part2.hybrid_evaluation import evaluate_hybrid,prepare_external_test

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Frozen hybrid v3 evaluation; no training, explicit native-vs-lab results')
    p.add_argument('--model-dir',default='gowin/hybrid_v3/model')
    p.add_argument('--native-cache',default='gowin/hybrid_v3/external_test/somfy01.csv')
    p.add_argument('--prepare-native-root');p.add_argument('--lab-dataset');p.add_argument('--collection-record');p.add_argument('--output',required=True);a=p.parse_args()
    out=Path(a.output)
    if out.exists():p.error('Output exists; preserve previous evaluation')
    try:
        if a.prepare_native_root:prepare_external_test(a.prepare_native_root,a.model_dir,a.native_cache)
        report,details=evaluate_hybrid(a.model_dir,a.native_cache,a.lab_dataset,a.collection_record)
    except (ValueError,OSError,KeyError) as e:p.error(str(e))
    out.mkdir(parents=True);(out/'metrics.json').write_text(json.dumps(report,indent=2))
    (out/'predictions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in details))
    body=['<!doctype html><meta charset="utf-8"><title>Hybrid v3</title><style>body{font:17px system-ui;max-width:1050px;margin:30px auto}td,th{border:1px solid #bbb;padding:8px}table{border-collapse:collapse}</style>',
          '<h1>V3: IoT‑23 kết hợp lab có kiểm soát</h1>',
          '<p>Không huấn luyện lại, không chỉnh luật ngưỡng. Chưa đo chặn Ethernet/thời gian phần cứng.</p>',
          '<p>IoT‑23 test dành riêng ở đây chỉ có lớp bình thường. SYN và vertical scan test đến từ lab mới; không gọi đây là test ba lớp hoàn toàn từ IoT‑23.</p>']
    if report['lab'] is None:body+=['<p><strong>Chưa có bộ lab mới: chưa hoàn thành test đủ ba lớp.</strong></p>']
    for key,title in [('native_benign','IoT‑23 Somfy bình thường — chưa dùng khi chọn model'),('lab','Lab mới sau freeze'),('combined','Tổng hợp — phải đọc cùng kết quả theo nguồn')]:
        if report[key] is None:continue
        body += ['<h2>'+title+'</h2>']
        for kind in ('integer','float','baseline'):
            m=report[key][kind]
            body += [f'<h3>{kind}</h3><p>{m["windows"]} cửa sổ; Accuracy={m["accuracy"]:.2%}; FPR={m["false_positive_rate"]:.2%}; capture/class recall={m["capture_class_macro_recall"]:.2%}</p>',
                     '<p>Hàng nhãn thật; cột Bình thường / SYN / Scan.</p><table>']
            body += ['<tr>'+''.join(f'<td>{v}</td>' for v in row)+'</tr>' for row in m['confusion_matrix']];body+=['</table>']
        body+=['<table><tr><th>Phiên</th><th>AI đúng</th></tr>']
        for c in report[key]['integer']['per_capture']:body += [f'<tr><td>{html.escape(c["capture_id"])}</td><td>{c["accuracy"]:.2%}</td></tr>']
        body+=['</table>']
    body+=['<h2>Giới hạn</h2><ul>']+['<li>'+html.escape(s)+'</li>' for s in report['limitations']]+['</ul>']
    (out/'report.html').write_text('\n'.join(body))
    print(json.dumps(dict(complete=report['all_three_class_test_complete'],native_benign_integer=report['native_benign']['integer'],lab_integer=report['lab']['integer'] if report['lab'] else None),indent=2))
    print('Saved:',out)
