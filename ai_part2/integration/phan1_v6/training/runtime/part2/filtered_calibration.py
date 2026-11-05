"""Calibrate V5 integer arithmetic on cached training patterns, never probes/test.

Positive per-neuron rescaling preserves the floating-point ReLU network. It
allows the existing shared-shift, int8-weight core to use more of each hidden
neuron's range. All candidate choices are explicitly training-set choices.
"""
import math

import numpy as np

from part2.development import integer_model
from part2.integer import infer


def calibrate_integer_model(clf, points, labels, counts, seed):
    points=np.asarray(points,dtype=np.int64)
    labels=np.asarray(labels,dtype=np.int64)
    counts=np.asarray(counts,dtype=np.int64)
    if points.shape!=(len(labels),6) or counts.shape!=labels.shape or (counts<=0).any():
        raise ValueError('Invalid calibration patterns/counts')
    if set(labels)!={0,1,2} or (points<0).any() or (points>127).any():
        raise ValueError('Requires all three training classes and six q values in 0..127')
    w1,w2=clf.coefs_;b1,b2=clf.intercepts_
    hidden=np.maximum(0,points/128.@w1+b1)
    supports=np.bincount(labels,weights=counts,minlength=3)
    unique_supports=np.bincount(labels,minlength=3)
    candidates=[]

    def score(model,parameters):
        for wk,bk in [('w1','b1'),('w2','b2')]:
            w=np.asarray(model[wk],dtype=np.int64);b=np.asarray(model[bk],dtype=np.int64)
            if (w < -128).any() or (w > 127).any() or (127*np.abs(w).sum(1)+np.abs(b)).max()>=2**31:
                return
        prediction=infer(points,model).argmax(1)
        errors=np.bincount(labels[prediction!=labels],weights=counts[prediction!=labels],minlength=3).astype(np.int64)
        unique_errors=np.bincount(labels[prediction!=labels],minlength=3)
        # Each class contributes equally, while the real window counts within
        # each class matter. A frequent benign pattern must not be discarded.
        rank=(float(np.mean(errors/supports)),float(np.mean(unique_errors/unique_supports)))
        candidates.append((rank,model,dict(parameters,window_errors_by_class=errors.tolist(),
                                          unique_pattern_errors_by_class=unique_errors.tolist(),
                                          mean_class_window_error=rank[0],mean_class_unique_error=rank[1])))

    baseline=integer_model(clf,points,seed)
    score(baseline,dict(kind='legacy_global_hidden_scale'))
    for shift1 in range(13):
        for utilization in (.5,.75,1.):
            scales=np.minimum(127*utilization/np.maximum(hidden.max(0),1e-9),
                              127*128/(2**shift1*np.maximum(np.abs(w1).max(0),1e-9)))
            scales=np.maximum(scales,1e-9)
            output_weights=w2.T/scales
            exponent=max(-12,min(15,math.floor(math.log2(127/max(float(np.abs(output_weights).max()),1e-9)))))
            scale=2.**exponent
            model=dict(baseline,shift1=shift1,shift2=0,
                       w1=np.rint(w1.T*scales[:,None]*2**shift1/128).astype(np.int64).tolist(),
                       b1=np.rint(b1*scales*2**shift1).astype(np.int64).tolist(),
                       w2=np.rint(output_weights*scale).astype(np.int64).tolist(),
                       b2=np.rint(b2*scale).astype(np.int64).tolist(),
                       hidden_scales=scales.tolist(),score_scale=scale,
                       integer_conversion='positive per-hidden-neuron rescaling; shared shift; int8 weights')
            model.pop('weight_fraction_bits',None);model.pop('hidden_scale',None)
            score(model,dict(kind='per_neuron_rescaling',shift1=shift1,hidden_utilization=utilization,
                             output_scale_exponent=exponent))
    best=min(candidates,key=lambda c:c[0])
    report=dict(kind='training_only_integer_calibration',candidate_count=len(candidates),
                selection='minimize mean per-class window error; tie-break mean per-class distinct-pattern error; stable grid order',
                calibration_unique_patterns_by_class=unique_supports.tolist(),
                calibration_windows_by_class=supports.astype(np.int64).tolist(),
                independent_validation_used=False,engineered_probes_used=False,
                selected=best[2],candidates=[c[2] for c in candidates])
    return best[1],report
