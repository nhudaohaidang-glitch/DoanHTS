"""Reproduce only V6 historical regression; no fitting and no SoC dependency."""
import csv
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from ai_reference import infer

path = ROOT / 'frozen/model.json'
assert hashlib.sha256(path.read_bytes()).hexdigest() == '3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515'
model = json.loads(path.read_text())
cm = [[0] * 3 for _ in range(3)]
with (ROOT / 'hybrid_v3_holdout_v3test01.csv').open() as stream:
    for row in csv.DictReader(stream):
        raw = [int(row[k]) for k in ('packet_count', 'mean_ip_bytes', 'syn_ratio_q127', 'src_count', 'dst_count', 'dst_port_count')]
        if raw[0] == 0:
            continue
        q = [max(0, min(127, v // d)) for v, d in zip(raw, model['divisors'])]
        scores = infer(q, model)
        cm[int(row['label'])][max(range(3), key=lambda i: scores[i])] += 1
expected = json.loads((ROOT / 'historical_lab_regression.json').read_text())['models']['v6']['confusion_matrix']
if cm != expected:
    raise SystemExit('FAIL historical regression: ' + str(cm))
print('v6 CM', cm, 'correct', sum(cm[i][i] for i in range(3)), '/', sum(map(sum, cm)))
print('PASS historical regression reproduction; not a new independent test.')
