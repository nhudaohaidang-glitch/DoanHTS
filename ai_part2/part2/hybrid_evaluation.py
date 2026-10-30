"""Evaluate a frozen hybrid v3, keeping native benign and fresh lab results separate."""
from collections import Counter
import json
from pathlib import Path
import numpy as np
from part2.development import arrays,load_dataset,rule_predictions,sha256,verify_freeze
from part2.features import NAMES,quantize
from part2.hybrid_data import native_cache,read_cache
from part2.hybrid_training import grouped_metrics
from part2.integer import infer


def checked_model(model_dir):
    root=Path(model_dir);freeze=verify_freeze(root)
    if sha256(root/'float_model.json')!=freeze['float_model_sha256']:raise ValueError('Floating weights changed after freeze')
    model=json.loads((root/'model.json').read_text())
    if model.get('model_version')!='v3':raise ValueError('Expected hybrid v3 model')
    return freeze,model,json.loads((root/'float_model.json').read_text())


def prepare_external_test(native_root,model_dir,cache):
    freeze,model,floating=checked_model(model_dir)
    plan=freeze['reserved_external_test'];folder=Path(native_root)/plan['capture_id']
    receipt=json.loads((folder/'TEST_RECEIPT.json').read_text())
    if receipt['model_sha256']!=freeze['model_sha256'] or receipt['source_plan']!=plan:
        raise ValueError('External test receipt belongs to another model/plan')
    source=dict(capture_id=plan['capture_id'],role='reserved_test',label=0,protected_ip=plan['protected_ip'],
                pcap_sha256=receipt['sha256'],pcap_url=plan['pcap_url'],native_annotation='Published benign Somfy01, reserved before fitting',
                publisher_checksum_verified=False)
    result=native_cache(folder/receipt['filename'],source,cache)
    result['test_receipt']=receipt
    Path(cache).with_suffix('.meta.json').write_text(json.dumps(result,indent=2))
    return result


def predictions(rows,meta,model,floating,baseline):
    raw,labels=arrays(rows);q=quantize(raw,model['divisors'])
    scores=infer(q,model);integer=scores.argmax(1)
    hidden=np.maximum(0,q/floating['normalization_denominator']@np.asarray(floating['w1'])+np.asarray(floating['b1']))
    floats=(hidden@np.asarray(floating['w2'])+np.asarray(floating['b2'])).argmax(1)
    rules=rule_predictions(raw,baseline)
    result=dict(integer=grouped_metrics(rows,integer,meta),float=grouped_metrics(rows,floats,meta),
                baseline=grouped_metrics(rows,rules,meta),
                input_clipped_fraction=((raw//np.array(model['divisors']))>127).mean(0).tolist())
    detail=[dict(row,quantized=q[i].tolist(),scores=scores[i].tolist(),prediction=int(integer[i]),
                 float_prediction=int(floats[i]),baseline_prediction=int(rules[i])) for i,row in enumerate(rows)]
    return result,detail


def evaluate_hybrid(model_dir,native_test_cache,lab_dataset=None,collection_record=None):
    freeze,model,floating=checked_model(model_dir);native,nmeta=read_cache(native_test_cache)
    plan=freeze['reserved_external_test'];source=nmeta['source'];receipt=nmeta['test_receipt']
    if (receipt['model_sha256']!=freeze['model_sha256'] or receipt['source_plan']!=plan
            or source['capture_id']!=plan['capture_id'] or source['protected_ip']!=plan['protected_ip']
            or source['pcap_url']!=plan['pcap_url'] or source['pcap_sha256']!=receipt['sha256']
            or source['label']!=0 or source['role']!='reserved_test'):
        raise ValueError('Reserved native cache/receipt differs from frozen source plan')
    if source['pcap_sha256'] in freeze['development_capture_sha256'] or source['capture_id'] in freeze['development_capture_ids']:
        raise ValueError('Native test reuses development source')
    native=[dict(r,split='challenge') for r in native]
    ncap=dict(capture_id=source['capture_id'],label='0',source_kind='external',source_dataset='IoT-23',sha256=source['pcap_sha256'])
    all_rows=list(native);all_caps=[ncap];report=dict(kind='hybrid_v3_frozen_test',model_sha256=freeze['model_sha256'],
        model_retrained=False,thresholds_retuned=False,external_test_source=source,
        limitations=freeze['protocol']['coverage_limits'],native_empty_slots_excluded=nmeta['complete_time_slots']-len(native))
    report['native_benign'],details=predictions(native,dict(captures=[ncap]),model,floating,freeze['threshold_baseline'])
    report['native_missing_classes']=[1,2];report['lab']=None;report['all_three_class_test_complete']=False
    if (lab_dataset is None)!=(collection_record is None):raise ValueError('Supply both fresh lab dataset and collection record')
    if lab_dataset is not None:
        lab,lmeta=load_dataset(lab_dataset,{'challenge'})
        record=json.loads(Path(collection_record).read_text())
        if record['selection']!=freeze or record.get('protocol_profile')!='hybrid-v3':
            raise ValueError('Lab collection is not pinned to this hybrid-v3 model/profile')
        from lab.collect_v2 import plan as collection_plan
        suffix='_challenge_normal_small'
        if not record['capture_ids'] or not record['capture_ids'][0].endswith(suffix):raise ValueError('Invalid hybrid-v3 collection plan')
        prefix=record['capture_ids'][0][:-len(suffix)]
        _,commands=collection_plan('holdout',prefix,'hybrid-v3')
        if record.get('plan')!=commands or record['capture_ids']!=[r['capture_id'] for r in commands]:raise ValueError('Fresh collection plan differs from hybrid-v3 profile')
        if set(r['capture_id'] for r in lab)!=set(record['capture_ids']):raise ValueError('Lab capture IDs differ from collection plan')
        if set(record['capture_ids'])&set(freeze['development_capture_ids']):raise ValueError('Lab capture ID reuses development')
        if {c['sha256'] for c in lmeta['captures']}&set(freeze['development_capture_sha256']):raise ValueError('Lab PCAP reuses development')
        if any(float(c['start'])<=float(record['collection_started_at']) for c in lmeta['captures']):
            raise ValueError('Lab capture predates frozen collection record')
        nonempty=[r for r in lab if int(r['packet_count'])>0]
        if set(int(r['label']) for r in nonempty)!={0,1,2}:raise ValueError('Fresh lab needs all three classes with valid samples')
        if set(r['capture_id'] for r in nonempty)!=set(record['capture_ids']):raise ValueError('A lab capture has no valid nonempty windows')
        caps=[dict(c,source_dataset='controlled_lab') for c in lmeta['captures']]
        report['lab_empty_windows_skipped']=len(lab)-len(nonempty)
        report['lab'],ldetail=predictions(nonempty,dict(captures=caps),model,floating,freeze['threshold_baseline'])
        report['lab_dataset_sha256']=sha256(lab_dataset);report['lab_collection']=record
        all_rows+=nonempty;all_caps+=caps;details+=ldetail;report['all_three_class_test_complete']=True
    report['combined'],_=predictions(all_rows,dict(captures=all_caps),model,floating,freeze['threshold_baseline'])
    report['combined_missing_classes']=sorted({0,1,2}-{int(r['label']) for r in all_rows})
    return report,details
