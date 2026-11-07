"""Verify runtime hardware counters -> C packing -> RTL against frozen V6.

This checks arithmetic/data flow, not whether a traffic label was detected.
"""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
MODEL_SHA='3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515'


def scores(q,m):
    h=[max(0,min(127,(sum(x*w for x,w in zip(q,row))+bias)>>m['shift1'])) for row,bias in zip(m['w1'],m['b1'])]
    return [max(-32768,min(32767,(sum(x*w for x,w in zip(h,row))+bias)>>m['shift2'])) for row,bias in zip(m['w2'],m['b2'])]


def check(path):
    model_path=ROOT/'rtl/part2_ai/model.json'
    if hashlib.sha256(model_path.read_bytes()).hexdigest()!=MODEL_SHA:raise ValueError('Model differs from frozen V6')
    model=json.loads(model_path.read_text());count=0;examples=[]
    with Path(path).open() as stream:rows=list(csv.DictReader(stream))
    for row in rows:
        n=int(row['pkt']);b=int(row['bytes']);s=int(row['syn'])
        if n<=0 or not 0<=s<=n:raise ValueError('Invalid counters in trace')
        raw=[n,b//n,127*s//n,*[int(row[k]) for k in ('src','dst','ports')]]
        q=[max(0,min(127,v//d)) for v,d in zip(raw,model['divisors'])]
        packed=sum(v<<(8*i) for i,v in enumerate(q));expected=scores(q,model)
        actual=[int(row['score'+str(i)]) for i in range(3)]
        label=max(range(3),key=lambda i:expected[i])
        if packed!=int(row['feat_hex'],16) or expected!=actual or label!=int(row['class_id']):
            raise ValueError('Counter/packing/score mismatch in window '+row['win'])
        count+=1
        if int(row['src'])==2 and int(row['ports'])==1 and n>390 and len(examples)<2:
            examples.append(dict(win=int(row['win']),raw=raw,q=q,scores=expected,predicted_class=label,
                                 note='SYN stimulus in the existing demo; predicted class is recorded, not assumed'))
    if count==0:raise ValueError('No runtime windows in trace')
    result=dict(model_sha256=MODEL_SHA,runtime_windows=count,raw_to_pack_and_scores_match=True,
                detection_accuracy_claimed=False,syn_demo_examples=examples)
    print('PASS V6_RUNTIME_TRACE windows='+str(count)+' counters_to_C_pack_to_RTL_match=OK')
    return result


if __name__=='__main__':
    try:result=check(sys.argv[1] if len(sys.argv)>1 else ROOT/'sim/out/v6_feature_trace.csv')
    except (ValueError,OSError) as error:raise SystemExit('ERROR: '+str(error))
    (ROOT/'sim/out').mkdir(parents=True,exist_ok=True)
    (ROOT/'sim/out/v6_trace_check.json').write_text(json.dumps(result,indent=2)+'\n')
