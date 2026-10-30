"""Fit a separate v3 candidate; capture-aware validation, no test access."""
from collections import defaultdict
import json
from pathlib import Path
import warnings
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.exceptions import ConvergenceWarning
from part2.assessment import classification_metrics
from part2.development import arrays,integer_model,rule_predictions,sha256
from part2.features import quantize,NAMES
from part2.hybrid_data import load_hybrid
from part2.integer import export_model,infer,write_vectors

DIVISORS=[8,2,1,1,1,1]


def grouped_metrics(rows,pred,meta):
    labels=np.array([int(r['label']) for r in rows]);pred=np.asarray(pred)
    cap_info={c['capture_id']:c for c in meta['captures']}
    caps=defaultdict(list);sources=defaultdict(list)
    for i,row in enumerate(rows):
        caps[row['capture_id']].append(i)
        sources[cap_info[row['capture_id']]['source_dataset']].append(i)
    result=classification_metrics(labels,pred)
    per_class=defaultdict(list)
    result['per_capture']=[]
    for cid,ids in caps.items():
        m=classification_metrics(labels[ids],pred[ids]);label=int(labels[ids[0]])
        if len(set(labels[ids]))!=1:raise ValueError('Each registered capture slice needs one declared class')
        per_class[label].append(m['accuracy'])
        result['per_capture'].append(dict(capture_id=cid,label=label,source_dataset=cap_info[cid]['source_dataset'],**m))
    result['capture_class_macro_recall']=float(np.mean([np.mean(per_class[k]) for k in range(3) if k in per_class]))
    result['per_source']={s:classification_metrics(labels[ids],pred[ids]) for s,ids in sources.items()}
    return result


def selection_key(metrics):
    fprs=[m['false_positive_rate'] for m in metrics['per_source'].values() if m['false_positive_rate'] is not None]
    return metrics['capture_class_macro_recall'],metrics['macro_f1'],-max(fprs,default=0.)


def fit_points(q,labels,seed):
    """Equalize classes with repeated unique TRAIN points, not new traffic."""
    unique=[np.unique(q[labels==i],axis=0) for i in range(3)]
    if any(len(x)==0 for x in unique):raise ValueError('All training classes required')
    size=max(map(len,unique));rng=np.random.default_rng(seed)
    chunks=[]
    for x in unique:
        ids=np.tile(rng.permutation(len(x)),int(np.ceil(size/len(x))))[:size]
        chunks.append(x[ids])
    return np.vstack(chunks),np.repeat(np.arange(3),size),[len(x) for x in unique]


def train_hybrid(dataset,output):
    output=Path(output)
    if output.exists():raise ValueError('Output exists; never overwrite frozen lab models')
    rows,meta=load_hybrid(dataset,{'train','val'})
    protocol=meta['protocol'];splits={s:[r for r in rows if r['split']==s] for s in ('train','val')}
    for split,selected in splits.items():
        for label in range(3):
            if len({r['capture_id'] for r in selected if int(r['label'])==label})<2:
                raise ValueError(f'{split} needs two captures for class {label}')
    data={s:arrays(v) for s,v in splits.items()};q={s:quantize(raw,DIVISORS) for s,(raw,y) in data.items()}
    candidates=[];best=None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning)
        for alpha in protocol['selection']['alpha']:
            for seed in protocol['selection']['seeds']:
                xfit,yfit,unique=fit_points(q['train'],data['train'][1],seed)
                clf=MLPClassifier(hidden_layer_sizes=(8,),activation='relu',solver='lbfgs',alpha=alpha,max_iter=1600,random_state=seed)
                clf.fit(xfit/128.,yfit)
                model=integer_model(clf,xfit,seed);model.update(model_version='v3',source_kind='hybrid_iot23_controlled_lab',selected_alpha=alpha)
                m=grouped_metrics(splits['val'],infer(q['val'],model).argmax(1),meta)
                key=selection_key(m)
                candidates.append(dict(seed=seed,alpha=alpha,selection_key=list(key),integer_validation=m))
                if best is None or key>best[0]:best=key,model,clf,unique,len(xfit)
                print(f'candidate seed={seed} alpha={alpha}: capture-balanced={key[0]:.6f}, macro-F1={key[1]:.6f}, worst-source-FPR={-key[2]:.6f}',flush=True)
    _,model,clf,unique,fit_count=best
    report=dict(kind='hybrid_v3_development_validation',test_evaluated=False,model_version='v3',
                selection=protocol['selection'],candidates=candidates,metrics={},data_provenance=meta,
                dataset_sha256=sha256(dataset),
                fit_sampling=dict(unique_quantized_train_by_class=unique,repeated_fit_rows=fit_count,
                                  note='Repetitions balance training loss; they are not independent traffic windows'),
                convergence_warning_count=sum(issubclass(w.category,ConvergenceWarning) for w in caught),
                limitations=protocol['coverage_limits'])
    for s,(raw,y) in data.items():
        report['metrics'][s]=dict(float=grouped_metrics(splits[s],clf.predict(q[s]/128.),meta),
                                  integer=grouped_metrics(splits[s],infer(q[s],model).argmax(1),meta),
                                  input_clipped_fraction=((raw//np.array(DIVISORS))>127).mean(0).tolist())
    rule_best=None
    for pt in (8,16,24,32,64):
        for dt in (3,4,5,8,16):
            for st in (32,64,96):
                rule=dict(packet_threshold=pt,port_threshold=dt,syn_ratio_q127_threshold=st)
                m=grouped_metrics(splits['val'],rule_predictions(data['val'][0],rule),meta);key=selection_key(m)
                if rule_best is None or key>rule_best[0]:rule_best=key,rule,m
    report['threshold_baseline']=dict(rule_best[1],validation=rule_best[2])
    export_model(model,output)
    float_model=dict(normalization_denominator=128.,w1=clf.coefs_[0].tolist(),w2=clf.coefs_[1].tolist(),
                     b1=clf.intercepts_[0].tolist(),b2=clf.intercepts_[1].tolist(),activation='relu',class_order=[0,1,2])
    (output/'float_model.json').write_text(json.dumps(float_model,indent=2))
    rng=np.random.default_rng(112)
    edges=np.vstack([np.zeros((1,6),int),np.full((1,6),127),np.eye(6,dtype=int)*127,rng.integers(0,128,(256,6))])
    report['rtl_vector_count']=write_vectors(np.vstack([np.unique(q['val'],axis=0),edges]),model,output/'vectors.txt')
    (output/'metrics.json').write_text(json.dumps(report,indent=2))
    freeze=dict(format=1,model_sha256=sha256(output/'model.json'),metrics_sha256=sha256(output/'metrics.json'),
                float_model_sha256=sha256(output/'float_model.json'),threshold_baseline=rule_best[1],
                development_capture_sha256=[c['sha256'] for c in meta['captures']],
                development_capture_ids=[c['capture_id'] for c in meta['captures']],
                reserved_external_test=protocol['reserved_external_test'],protocol=protocol)
    (output/'FREEZE.json').write_text(json.dumps(freeze,indent=2))
    return report
