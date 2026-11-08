"""Print actual v3 integer computations. Python standard library only; no training."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
model_path = HERE / 'model.json'
if not model_path.exists():
    model_path = HERE.parents[1] / 'gowin/hybrid_v3/model/model.json'
data = model_path.read_bytes()
if hashlib.sha256(data).hexdigest() != 'e10f81b3e3ec9b458c4d574ee978cf0f2efa45954b4f8fe0c86fed6a3a26c35d':
    raise SystemExit('This walkthrough requires the original frozen v3 model')
model = json.loads(data)
names = ['packet_count', 'mean_ip_bytes', 'syn_ratio_q127', 'src_count', 'dst_count', 'dst_port_count']
classes = ['Normal', 'SYN flood', 'Vertical scan']


def explain(name, raw, expected):
    q = [max(0, min(127, x // d)) for x, d in zip(raw, model['divisors'])]
    a = [sum(w * x for w, x in zip(weights, q)) + bias
         for weights, bias in zip(model['w1'], model['b1'])]
    h = [max(0, min(127, x >> model['shift1'])) for x in a]
    scores = [max(-32768, min(32767, (sum(w * x for w, x in zip(weights, h)) + bias) >> model['shift2']))
              for weights, bias in zip(model['w2'], model['b2'])]
    prediction = max(range(3), key=lambda i: scores[i])
    packed = sum(x << (8 * i) for i, x in enumerate(q))
    print('\nCASE:', name)
    print('  raw:    ', raw)
    print('  q:      ', q, f' packed=0x{packed:012x}')
    print('  a:      ', a)
    print('  hidden: ', h)
    print('  scores: ', scores)
    print('  result: ', classes[prediction], '; scenario label:', classes[expected],
          '; agrees:', prediction == expected)


count = sum(sum(len(row) for row in model[k]) for k in ('w1', 'w2'))
count += sum(len(model[k]) for k in ('b1', 'b2'))
print('Frozen v3, 6-8-3 MLP, learned parameter slots:', count)
print('Rows below are examples, NOT a new training dataset or accuracy benchmark.')
with (HERE / 'sample_windows.csv').open() as f:
    for row in csv.DictReader(f):
        explain(row['capture_id'] + '/' + row['window_start'],
                [int(row[k]) for k in names], int(row['label']))

# Deliberately constructed benign connection control, not a captured IoT-23 row.
explain('engineered single legitimate SYN control, NOT a captured row',
        [1, 40, 127, 1, 1, 1], 0)
