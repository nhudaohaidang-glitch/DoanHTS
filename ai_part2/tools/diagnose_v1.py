"""Recompute a diagnostic bundle using this kit's code, never uploaded Python code."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from part2.assessment import evaluate_frozen
from part2.features import NAMES, extract, quantize, values


def diagnose(root):
    root = Path(root)
    model_path = root / 'build/lab_model_v1/model.json'
    model = json.loads(model_path.read_text())
    original = json.loads((root / 'build/lab_model_v1/metrics.json').read_text())
    with (root / 'build/challenge_features_v1.csv').open() as f:
        rows = list(csv.DictReader(f))
    meta = json.loads((root / 'build/challenge_features_v1.meta.json').read_text())
    if meta['features'] != NAMES or meta['window_seconds'] != 1.0 or meta['distinct'] != 'exact':
        raise ValueError('Unexpected feature contract')
    report, predictions = evaluate_frozen(rows, model, original['threshold_baseline'])
    stored = [json.loads(line) for line in (root / 'build/challenge_eval_v1/predictions.jsonl').read_text().splitlines()]
    if len(stored) != len(predictions):
        raise ValueError('Stored predictions length mismatch')
    for a, b in zip(stored, predictions):
        for key in ('capture_id', 'window_start', 'prediction', 'baseline_prediction', 'scores', 'quantized'):
            if a[key] != b[key]:
                raise ValueError('Stored prediction differs at ' + key)
    details = []
    qlabels = {}
    for capture in meta['captures']:
        cid = capture['capture_id']
        selected = [r for r in rows if r['capture_id'] == cid]
        raw = np.array([[int(r[k]) for k in NAMES] for r in selected])
        q = quantize(raw, model['divisors'])
        for vector, row in zip(q, selected):
            qlabels.setdefault(tuple(vector), set()).add(int(row['label']))
        path = root / 'data/challenge' / capture['pcap']
        detail = dict(capture_id=cid, windows=len(selected),
                      raw_min=raw.min(0).tolist(), raw_median=np.median(raw, axis=0).tolist(),
                      raw_max=raw.max(0).tolist(), quantized_unique=np.unique(q, axis=0).tolist(),
                      pcap_recomputed=False)
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != capture['sha256']:
                raise ValueError('PCAP hash mismatch: ' + cid)
            windows, stats = extract(path, capture['target_net'])
            for row in selected:
                actual = values(windows.get(int(float(row['window_start']))), 'exact')
                if actual != [int(row[k]) for k in NAMES]:
                    raise ValueError('PCAP features differ: ' + cid)
            detail.update(pcap_recomputed=True, pcap_sha256=capture['sha256'], pcap_stats=stats)
        log = root / 'data/challenge' / cid / 'capture.log'
        if log.exists():
            match = re.search(r'(\d+) packets dropped by kernel', log.read_text())
            detail['kernel_capture_drops'] = int(match.group(1)) if match else None
        snapshots = root / 'data/challenge' / cid / 'broker_stats.jsonl'
        if snapshots.exists():
            snapshots = [json.loads(s) for s in snapshots.read_text().splitlines() if s.startswith('{')]
            if snapshots:
                first, last = snapshots[0]['tcp_ext'], snapshots[-1]['tcp_ext']
                detail['broker_counter_delta'] = {k: last[k] - v for k, v in first.items() if k in last}
                detail['initial_syn_recv'] = snapshots[0]['tcp_states'].get('SYN_RECV', 0)
                detail['peak_syn_recv'] = max(s['tcp_states'].get('SYN_RECV', 0) for s in snapshots)
        details.append(detail)
    return dict(model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
                stored_predictions_reproduced=True, metrics=report,
                cross_label_quantized_collisions=sum(len(labels) > 1 for labels in qlabels.values()),
                features=NAMES, captures=details,
                note='Only supplied PCAPs were independently re-extracted. Statistics alone do not establish service interruption.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    out = Path(a.output)
    if out.exists():
        p.error('Output exists; preserve it and choose a new path')
    result = diagnose(a.root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps({'ai': result['metrics']['ai'],
                      'pcaps_recomputed': [r['capture_id'] for r in result['captures'] if r['pcap_recomputed']]}, indent=2))
