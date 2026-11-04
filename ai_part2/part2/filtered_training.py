"""Fit a new 6-8-3 candidate on reviewed filtered classes; no fake holdout."""
from collections import Counter
import json
from pathlib import Path
import random
import sqlite3
import warnings

import numpy as np
import scipy
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPClassifier
from threadpoolctl import threadpool_limits

from part2.development import integer_model
from part2.filtered_training_data import DIVISORS,sha
from part2.integer import export_model,infer,write_vectors

SEED=23
ALPHA=.01


def unpack(packed):
    return [(int(packed)>>(8*i))&255 for i in range(6)]


def weighted_metrics(confusion):
    cm=np.asarray(confusion,dtype=np.int64);total=int(cm.sum());classes=[]
    for label in range(3):
        tp=int(cm[label,label]);support=int(cm[label].sum());predicted=int(cm[:,label].sum())
        precision=tp/predicted if predicted else 0.;recall=tp/support if support else 0.
        f1=2*precision*recall/(precision+recall) if precision+recall else 0.
        classes.append(dict(id=label,precision=precision,recall=recall,f1=f1,support=support))
    return dict(windows=total,accuracy=float(np.trace(cm)/total) if total else None,
                macro_f1=float(np.mean([c['f1'] for c in classes])),confusion_matrix=cm.tolist(),
                false_positive_rate=float(cm[0,1:].sum()/cm[0].sum()) if cm[0].sum() else None,
                per_class=classes)


def train(sources,output,maximum_patterns=5000,model_version='v4'):
    output=Path(output)
    if output.exists():raise ValueError('Candidate model folder exists; preserve it')
    output.mkdir();database=output/'training_patterns.sqlite';db=sqlite3.connect(database)
    db.execute('CREATE TABLE patterns (label INTEGER,packed INTEGER,count INTEGER,PRIMARY KEY(label,packed))')
    for source in sources:
        with sqlite3.connect(source['patterns_db']) as read:
            cursor=read.execute('SELECT packed,count FROM patterns')
            while rows:=cursor.fetchmany(10000):
                db.executemany('INSERT INTO patterns VALUES (?,?,?) ON CONFLICT(label,packed) DO UPDATE SET count=count+excluded.count',
                               ((source['label'],int(p),int(n)) for p,n in rows))
        db.commit()
    chosen=[];unique=[];window_counts=[]
    rng=random.Random(SEED)
    for label in range(3):
        reservoir=[];count=0;windows=0
        for packed,n in db.execute('SELECT packed,count FROM patterns WHERE label=? ORDER BY packed',(label,)):
            count+=1;windows+=n
            if len(reservoir)<maximum_patterns:reservoir.append(packed)
            else:
                at=rng.randrange(count)
                if at<maximum_patterns:reservoir[at]=packed
        if not reservoir:raise ValueError(f'Class {label} has no complete nonempty training window')
        chosen.append(np.asarray([unpack(p) for p in sorted(reservoir)],dtype=np.int64));unique.append(count);window_counts.append(windows)
    size=max(map(len,chosen));generator=np.random.default_rng(SEED);chunks=[]
    for points in chosen:
        order=np.tile(generator.permutation(len(points)),int(np.ceil(size/len(points))))[:size]
        chunks.append(points[order])
    xfit=np.vstack(chunks);yfit=np.repeat(np.arange(3),size)
    clf=MLPClassifier(hidden_layer_sizes=(8,),activation='relu',solver='lbfgs',alpha=ALPHA,max_iter=1600,random_state=SEED)
    print('TRAIN new candidate '+model_version.upper()+':',len(xfit),'balanced fit rows; observed windows by class:',window_counts,flush=True)
    with warnings.catch_warnings(record=True) as caught,threadpool_limits(limits=1):
        warnings.simplefilter('always',ConvergenceWarning);clf.fit(xfit/128.,yfit)
    calibration=None
    if model_version=='v5':
        from part2.filtered_calibration import calibrate_integer_model
        rows=list(db.execute('SELECT label,packed,count FROM patterns ORDER BY label,packed'))
        model,calibration=calibrate_integer_model(clf,np.asarray([unpack(p) for l,p,n in rows]),
                                                 [l for l,p,n in rows],[n for l,p,n in rows],SEED)
    else:model=integer_model(clf,xfit,SEED)
    model.update(model_version=model_version,candidate_kind='filtered_iot23_public_vertical_scan',
                 source_kind='filtered_class_pcap_training',selected_alpha=ALPHA,
                 independent_test_evaluated=False,training_receiver_scope='each destination /32; positive reviewed target only')
    export_model(model,output)
    float_model=dict(normalization_denominator=128.,w1=clf.coefs_[0].tolist(),w2=clf.coefs_[1].tolist(),
                     b1=clf.intercepts_[0].tolist(),b2=clf.intercepts_[1].tolist(),activation='relu',class_order=[0,1,2])
    (output/'float_model.json').write_text(json.dumps(float_model,indent=2))
    matrices={name:np.zeros((3,3),dtype=np.int64) for name in ('float','integer')}
    per_source=[]
    for source in sources:
        local={name:np.zeros((3,3),dtype=np.int64) for name in matrices}
        with sqlite3.connect(source['patterns_db']) as read:
            cursor=read.execute('SELECT packed,count FROM patterns')
            while rows:=cursor.fetchmany(10000):
                points=np.asarray([unpack(p) for p,n in rows],dtype=np.int64);counts=np.asarray([n for p,n in rows],dtype=np.int64)
                predictions=dict(float=clf.predict(points/128.),integer=infer(points,model).argmax(1))
                for name,pred in predictions.items():
                    for label in range(3):local[name][source['label'],label]+=counts[pred==label].sum()
        for name in matrices:matrices[name]+=local[name]
        per_source.append(dict(source_id=source['id'],source_group=source['source_group'],label=source['label'],
                               windows=source['windows'],metrics={name:weighted_metrics(cm) for name,cm in local.items()}))
    conflicts=db.execute('SELECT count(*) FROM (SELECT packed FROM patterns GROUP BY packed HAVING count(*)>1)').fetchone()[0]
    conflict_examples=[]
    for packed in db.execute('SELECT packed FROM patterns GROUP BY packed HAVING count(*)>1 LIMIT 20'):
        conflict_examples.append(dict(q=unpack(packed[0]),counts_by_label=dict(db.execute('SELECT label,count FROM patterns WHERE packed=?',packed))))
    db.close()
    generator=np.random.default_rng(112)
    edges=np.vstack([np.zeros((1,6),dtype=int),np.full((1,6),127),np.eye(6,dtype=int)*127,generator.integers(0,128,(256,6))])
    vectors=np.vstack([*chosen,edges]);vector_count=write_vectors(vectors,model,output/'vectors.txt')
    report=dict(kind=model_version+'_filtered_three_class_training_fit',architecture=[6,8,3],divisors=DIVISORS,
                library_versions=dict(numpy=np.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__),
                model_sha256=sha(output/'model.json'),independent_test_evaluated=False,
                validation_used_for_selection=False,selection=dict(seed=SEED,alpha=ALPHA,max_iter=1600,solver='lbfgs',candidate_count=1),
                training_windows_by_class=window_counts,unique_quantized_patterns_by_class=unique,
                retained_fit_patterns_by_class=[len(c) for c in chosen],balanced_fit_rows=len(xfit),
                fit_sampling='Uniform deterministic reservoir of unique q patterns, capped per class; repeat retained patterns to equal class sizes. Repeats are not new traffic.',
                sampling_cap_per_class=maximum_patterns,
                training_fit={name:weighted_metrics(cm) for name,cm in matrices.items()},per_source=per_source,
                conflicting_quantized_patterns=conflicts,conflict_examples=conflict_examples,
                candidate_status='needs_label_review' if conflicts else 'training_candidate_needs_independent_test',
                ready_for_automatic_blocking=False,
                convergence_warning_count=sum(issubclass(w.category,ConvergenceWarning) for w in caught),
                rtl_vector_count=vector_count,
                limitations=[
                    'Scores are training-fit metrics across all prepared windows, not independent test accuracy.',
                    'Only one reviewed SYN-flood episode and one public vertical-scan episode; no independent three-class holdout can be formed.',
                    'No random adjacent-window split; repeated/unique quantized rows are not independent sessions.',
                    'Different labels with identical q inputs cannot be separated by any classifier using only those q values; labels are preserved for review.',
                    'Normal uses filtered Benign-only packets, grouped by receiver /32. Both traffic directions may produce different receiver samples.',
                    'Filtered packets change traffic composition; results do not reproduce full unfiltered capture windows.',
                    'Protected destination scope and one-second clock alignment must agree with hardware.',
                    'Any Somfy data used here ceases to be an independent test for this candidate.',
                    'No Ethernet blocking, board timing, fresh lab test or superiority over V3 is established.'])
    if calibration is not None:
        report['integer_calibration']=calibration
        report['selection']['integer_calibration_candidates']=calibration['candidate_count']
    (output/'metrics.json').write_text(json.dumps(report,indent=2))
    (output/'FREEZE.json').write_text(json.dumps(dict(format=1,model_sha256=report['model_sha256'],
        metrics_sha256=sha(output/'metrics.json'),float_model_sha256=sha(output/'float_model.json'),
        data_sources=[dict(id=s['id'],sha256=s['sha256'],source_group=s['source_group'],label=s['label']) for s in sources],
        independent_test_evaluated=False),indent=2))
    return report
