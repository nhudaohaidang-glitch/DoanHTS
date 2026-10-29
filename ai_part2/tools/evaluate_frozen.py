"""Evaluate frozen AI v1 and frozen thresholds on new challenge captures; never fit."""
import argparse,csv,hashlib,html,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from part2.assessment import evaluate_frozen
from part2.features import NAMES
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--dataset',required=True);p.add_argument('--model',default='build/lab_model_v1/model.json')
p.add_argument('--output',required=True)
p.add_argument('--original-meta',default='build/lab_features_v1.meta.json')
p.add_argument('--reference',default=str(Path(__file__).resolve().parents[1]/'gowin/lab_model_v1'))
a=p.parse_args();out=Path(a.output);ref=Path(a.reference)
if out.exists():p.error('Output exists; choose new directory')
expected=json.loads((ref/'EXPORT_MANIFEST.json').read_text())['model_sha256']
actual=hashlib.sha256(Path(a.model).read_bytes()).hexdigest()
if actual!=expected:p.error('Model differs from the frozen reviewed v1; do not overwrite v1 to evaluate challenge data')
meta_path=Path(a.dataset).with_suffix('.meta.json');meta=json.loads(meta_path.read_text())
if meta.get('features')!=NAMES:p.error('Feature contract/order differs from frozen v1')
if meta['distinct']!='exact' or meta['window_seconds']!=1.0:p.error('Frozen v1 requires exact distinct counts and 1-second windows')
old_meta=json.loads(Path(a.original_meta).read_text())
old_hashes={c['sha256'] for c in old_meta['captures']}
if any(c['sha256'] in old_hashes for c in meta['captures']):p.error('Challenge reuses an original capture; collect fresh sessions')
original=json.loads((ref/'reference/metrics.json').read_text())
model=json.loads(Path(a.model).read_text())
with open(a.dataset) as f:rows=list(csv.DictReader(f))
report,predictions=evaluate_frozen(rows,model,original['threshold_baseline'])
report.update(model_sha256=actual,dataset_sha256=hashlib.sha256(Path(a.dataset).read_bytes()).hexdigest(),data_provenance=meta)
out.mkdir(parents=True)
(out/'metrics.json').write_text(json.dumps(report,indent=2))
with (out/'predictions.jsonl').open('w') as f:
    for row in predictions:f.write(json.dumps(row)+'\n')
with (out/'per_capture.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['capture_id','windows','ai_accuracy','baseline_accuracy','ai_fpr'])
    for row in report['per_capture']:w.writerow([row['capture_id'],row['ai']['windows'],row['ai']['accuracy'],row['baseline']['accuracy'],row['ai']['false_positive_rate']])
body=['<!doctype html><meta charset="utf-8"><title>AI v1 challenge</title><style>body{font:16px system-ui;max-width:1000px;margin:30px auto}td,th{border:1px solid #bbb;padding:9px}table{border-collapse:collapse}</style>',
      '<h1>Đánh giá ngoại tuyến AI v1 đã đóng băng</h1><p>Không huấn luyện lại, không thay luật ngưỡng, không đo chặn FPGA.</p>']
for key in ('ai','baseline'):
    m=report[key];body += [f'<h2>{key}</h2>',f'<p>Accuracy: {m["accuracy"]:.4f}; Macro-F1: {m["macro_f1"]:.4f}; FPR: {m["false_positive_rate"]}</p>',
                           '<p>Hàng: nhãn thật; cột: Bình thường / SYN / Scan</p><table>']
    body += ['<tr>'+''.join(f'<td>{int(v)}</td>' for v in row)+'</tr>' for row in m['confusion_matrix']];body+=['</table>']
body += ['<h2>Theo phiên</h2><table><tr><th>Phiên</th><th>AI accuracy</th><th>Baseline accuracy</th></tr>']
for row in report['per_capture']:body.append(f'<tr><td>{html.escape(row["capture_id"])}</td><td>{row["ai"]["accuracy"]:.4f}</td><td>{row["baseline"]["accuracy"]:.4f}</td></tr>')
body+=['</table><h2>Giới hạn</h2><ul>']+['<li>'+html.escape(x)+'</li>' for x in report['limits']]+['</ul>']
(out/'report.html').write_text('\n'.join(body))
print(json.dumps({k:report[k] for k in ['ai','baseline','capture_count','missing_classes','input_saturation']},indent=2))
print('Saved:',out)
