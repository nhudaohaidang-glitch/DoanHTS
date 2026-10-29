"""Evaluate AI v2 on sessions collected after its freeze; never fit or retune."""
import argparse
import csv
import html
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from part2.development import evaluate_v2

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', required=True)
    p.add_argument('--model-dir', default='build/lab_model_v2')
    p.add_argument('--collection-record', default='data/v2_holdout/COLLECTION.json')
    p.add_argument('--output', default='build/holdout_eval_v2')
    a = p.parse_args()
    out = Path(a.output)
    if out.exists():
        p.error('Output exists; preserve this result and choose a new path')
    try:
        report, predictions = evaluate_v2(a.dataset, a.model_dir, a.collection_record)
    except (ValueError, OSError, KeyError) as e:
        p.error(str(e))
    out.mkdir(parents=True)
    (out / 'metrics.json').write_text(json.dumps(report, indent=2))
    (out / 'predictions.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in predictions))
    with (out / 'per_capture.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['capture_id', 'windows', 'ai_accuracy', 'baseline_accuracy', 'ai_fpr'])
        for r in report['per_capture']:
            w.writerow([r['capture_id'], r['ai']['windows'], r['ai']['accuracy'],
                        r['baseline']['accuracy'], r['ai']['false_positive_rate']])
    body = ['<!doctype html><meta charset="utf-8"><title>AI v2 holdout</title>',
            '<style>body{font:17px system-ui;max-width:1000px;margin:30px auto}td,th{border:1px solid #bbb;padding:9px}table{border-collapse:collapse}</style>',
            '<h1>AI v2 — dữ liệu kiểm tra thu sau khi đóng băng</h1>',
            '<p>Không huấn luyện lại. Không đo chặn gói hay thời gian phần cứng.</p>']
    for k in ('ai', 'baseline'):
        m = report[k]
        body += [f'<h2>{k}</h2><p>Accuracy: {m["accuracy"]:.2%}; Macro-F1: {m["macro_f1"]:.4f}; FPR: {m["false_positive_rate"]:.2%}</p>',
                 '<p>Hàng: nhãn thật; cột: Bình thường / SYN / Scan.</p><table>']
        body += ['<tr>' + ''.join(f'<td>{v}</td>' for v in row) + '</tr>' for row in m['confusion_matrix']]
        body += ['</table>']
    body += ['<h2>Theo phiên</h2><table><tr><th>Phiên</th><th>AI</th><th>Luật ngưỡng</th></tr>']
    for r in report['per_capture']:
        body += [f'<tr><td>{html.escape(r["capture_id"])}</td><td>{r["ai"]["accuracy"]:.2%}</td><td>{r["baseline"]["accuracy"]:.2%}</td></tr>']
    body += ['</table><h2>Giới hạn</h2><p>Cửa sổ cùng phiên có tương quan; đây là các phiên lab mới trong phạm vi đã thiết kế. Chưa chứng minh khái quát sang mạng khác, IoT-23 hoặc dữ liệu thực địa.</p>']
    (out / 'report.html').write_text('\n'.join(body))
    print(json.dumps({k: report[k] for k in ('ai', 'baseline', 'capture_count')}, indent=2))
    print('Saved:', out)
