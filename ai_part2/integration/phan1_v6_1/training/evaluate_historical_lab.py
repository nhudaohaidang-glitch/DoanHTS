"""Reproduce the retained historical lab regression, without fitting a model."""
import csv,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'tools'))
from check_v6_trace import scores
rows=list(csv.DictReader((ROOT/'hybrid_v3_holdout_v3test01.csv').open()))
for name,path in [('v5',ROOT.parent/'reference/v5_baseline/model.json'),('v6',ROOT/'frozen/model.json')]:
    model=json.loads(path.read_text());cm=[[0]*3 for _ in range(3)]
    for r in rows:
        raw=[int(r[k]) for k in ('packet_count','mean_ip_bytes','syn_ratio_q127','src_count','dst_count','dst_port_count')]
        if raw[0]==0:continue
        q=[max(0,min(127,x//d)) for x,d in zip(raw,model['divisors'])]
        out=scores(q,model);pred=max(range(3),key=lambda i:out[i]);cm[int(r['label'])][pred]+=1
    expected=json.loads((ROOT/'historical_lab_regression.json').read_text())['models'][name]['confusion_matrix']
    if cm!=expected:raise SystemExit('Mismatch: '+name)
    print(name,'CM',cm,'correct',sum(cm[i][i] for i in range(3)),'/',sum(map(sum,cm)))
print('PASS historical regression reproduction; not a new independent test.')
