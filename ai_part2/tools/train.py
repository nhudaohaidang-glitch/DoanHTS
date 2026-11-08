import argparse, csv, json, math, sys, warnings
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score, f1_score
from sklearn.exceptions import ConvergenceWarning
from part2.features import NAMES,fit_divisors,quantize
from part2.integer import infer,export_model,write_vectors

def metrics(y,pred):
    cm=confusion_matrix(y,pred,labels=[0,1,2])
    normal=cm[0].sum()
    return {'accuracy':float(accuracy_score(y,pred)), 'macro_f1':float(f1_score(y,pred,average='macro',zero_division=0)),
            'false_positive_rate':float((cm[0,1]+cm[0,2])/normal) if normal else None,
            'confusion_matrix':cm.tolist(),
            'classes':classification_report(y,pred,labels=[0,1,2],output_dict=True,zero_division=0)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--output',required=True)
    p.add_argument('--allow-synthetic',action='store_true');a=p.parse_args()
    out=Path(a.output)
    if out.exists(): p.error('Output exists: choose new output directory')
    with open(a.dataset) as f: rows=list(csv.DictReader(f))
    if not rows: p.error('No rows')
    synthetic=any(r['source_kind']=='synthetic' for r in rows)
    if synthetic and not a.allow_synthetic: p.error('Synthetic data requires --allow-synthetic; metrics are pipeline checks only')
    groups={}
    for r in rows:
        split=r['split']
        if split not in ('train','val','test'): p.error('Bad split')
        groups.setdefault(r['capture_id'],set()).add(split)
    if any(len(x)!=1 for x in groups.values()): p.error('Capture leakage across splits')
    splits={}
    for split in ('train','val','test'):
        selected=[r for r in rows if r['split']==split]
        if set(int(r['label']) for r in selected)!={0,1,2}: p.error(f'{split} needs all three classes')
        splits[split]=(np.array([[int(r[k]) for k in NAMES] for r in selected],dtype=np.int64),
                       np.array([int(r['label']) for r in selected]))
    divisors=fit_divisors(splits['train'][0])
    q={s:quantize(v[0],divisors) for s,v in splits.items()}
    best=None
    # Selection uses validation only; test is not consulted until the final choice is fixed.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning)
        for seed in (11,23,47):
            clf=MLPClassifier(hidden_layer_sizes=(8,),activation='relu',solver='lbfgs',alpha=.01,max_iter=1200,random_state=seed)
            clf.fit(q['train']/128.0,splits['train'][1])
            score=f1_score(splits['val'][1],clf.predict(q['val']/128.0),average='macro')
            if best is None or score>best[0]: best=(score,seed,clf)
    _,seed,clf=best
    w1f,w2f=clf.coefs_; b1f,b2f=clf.intercepts_
    def exponent(weights):
        return max(0,min(12,int(math.floor(math.log2(127/max(float(np.max(np.abs(weights))),1e-9))))))
    p1,p2=exponent(w1f),exponent(w2f)
    train_hidden=np.maximum(0,q['train']/128.0@w1f+b1f)
    he=max(0,min(7,int(math.floor(math.log2(127/max(float(train_hidden.max()),1e-9))))))
    shift1=p1+7-he;shift2=max(0,p2+he-7)
    m={'architecture':[6,8,3], 'divisors':divisors, 'shift1':shift1,'shift2':shift2,
       'w1':np.clip(np.rint(w1f.T*2**p1),-127,127).astype(np.int64).tolist(),
       'w2':np.clip(np.rint(w2f.T*2**p2),-127,127).astype(np.int64).tolist(),
       'b1':np.rint(b1f*128*2**p1).astype(np.int64).tolist(),
       'b2':np.rint(b2f*2**he*2**p2).astype(np.int64).tolist(),
       'weight_fraction_bits':[p1,p2],'hidden_scale':2**he,'score_scale':2**(p2+he-shift2),
       'arithmetic':'weights/bias round-to-nearest-even; shifts arithmetic floor; hidden saturate [0,127]; scores saturate int16; argmax first index',
       'source_kind':'synthetic' if synthetic else 'lab_or_external','selected_seed':seed}
    for wk,bk in [('w1','b1'),('w2','b2')]:
        bound=127*np.abs(np.array(m[wk],dtype=np.int64)).sum(axis=1)+np.abs(np.array(m[bk],dtype=np.int64))
        if int(bound.max())>=2**31: raise ValueError('int32 accumulator overflow bound exceeded')
    export_model(m,out)
    report={'synthetic_only_metrics':synthetic,'group_split':True,'validation_selected_seed':seed,
            'convergence_warning_count':sum(issubclass(w.category,ConvergenceWarning) for w in caught),
            'metrics':{},'note':'Standalone model evaluation; does not measure Ethernet blocking or whole-system timing.'}
    for s in ('train','val','test'):
        report['metrics'][s]={'float':metrics(splits[s][1],clf.predict(q[s]/128.0)),
                              'integer':metrics(splits[s][1],infer(q[s],m).argmax(axis=1))}
    rng=np.random.default_rng(112)
    edges=np.vstack([np.zeros((1,6),dtype=int),np.full((1,6),127),np.eye(6,dtype=int)*127,
                      rng.integers(0,128,size=(256,6))])
    count=write_vectors(np.vstack([q['test'],edges]),m,out/'vectors.txt')
    # A transparent threshold baseline, tuned on validation only.
    best_rule=None
    train_raw=splits['train'][0]
    pkt_thresholds=sorted(set([1]+[int(np.percentile(train_raw[:,0],v)) for v in (25,50,75,90)]))
    port_thresholds=sorted(set([2]+[int(np.percentile(train_raw[:,5],v)) for v in (25,50,75,90)]))
    def rule(raw,pt,dt,st):
        return np.where((raw[:,5]>=dt)&(raw[:,2]>=st),2,np.where((raw[:,0]>=pt)&(raw[:,2]>=st),1,0))
    for pt in pkt_thresholds:
        for dt in port_thresholds:
            for st in (32,64,96):
                score=f1_score(splits['val'][1],rule(splits['val'][0],pt,dt,st),average='macro')
                if best_rule is None or score>best_rule[0]:best_rule=(score,pt,dt,st)
    _,pt,dt,st=best_rule
    report['threshold_baseline']={'packet_threshold':pt,'port_threshold':dt,'syn_ratio_q127_threshold':st,
                                 'test':metrics(splits['test'][1],rule(splits['test'][0],pt,dt,st))}
    report['rtl_vector_count']=count
    (out/'metrics.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
