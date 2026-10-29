"""Offline assessment helpers. Never train a model or change firewall rules."""
import hashlib,json,math,statistics
from pathlib import Path
import numpy as np
from sklearn.metrics import accuracy_score,confusion_matrix,f1_score,precision_recall_fscore_support
from part2.features import NAMES,quantize
from part2.integer import infer


def classification_metrics(y,pred):
    y=np.asarray(y,dtype=int);pred=np.asarray(pred,dtype=int)
    cm=confusion_matrix(y,pred,labels=[0,1,2])
    p,r,f,s=precision_recall_fscore_support(y,pred,labels=[0,1,2],zero_division=0)
    normal=int(cm[0].sum())
    return {'windows':len(y),'accuracy':float(accuracy_score(y,pred)),
            'macro_f1':float(f1_score(y,pred,labels=[0,1,2],average='macro',zero_division=0)),
            'false_positive_rate':float(cm[0,1:].sum()/normal) if normal else None,
            'confusion_matrix':cm.tolist(),
            'per_class':[{'id':i,'precision':float(p[i]),'recall':float(r[i]),'f1':float(f[i]),'support':int(s[i])} for i in range(3)]}


def evaluate_frozen(rows,model,baseline):
    if not rows:raise ValueError('No evaluation windows')
    if {r['split'] for r in rows}!={'challenge'}:raise ValueError('Use a separate challenge manifest/dataset; do not reuse train/val/test')
    if any(r['source_kind']=='synthetic' for r in rows):raise ValueError('Challenge evaluation requires lab/external captures, not synthetic')
    raw=np.array([[int(r[k]) for k in NAMES] for r in rows],dtype=np.int64)
    if (raw<0).any():raise ValueError('Negative raw features')
    labels=np.array([int(r['label']) for r in rows])
    if not set(labels)<={0,1,2}:raise ValueError('Invalid class label')
    q=quantize(raw,model['divisors']);scores=infer(q,model);pred=scores.argmax(axis=1)
    pt,dt,st=[int(baseline[k]) for k in ('packet_threshold','port_threshold','syn_ratio_q127_threshold')]
    rules=np.where((raw[:,5]>=dt)&(raw[:,2]>=st),2,np.where((raw[:,0]>=pt)&(raw[:,2]>=st),1,0))
    captures={}
    for i,row in enumerate(rows):captures.setdefault(row['capture_id'],[]).append(i)
    per_capture=[]
    for capture,index in captures.items():
        truth=labels[index]
        per_capture.append({'capture_id':capture,'labels':sorted(set(int(v) for v in truth)),
                            'ai':classification_metrics(truth,pred[index]),'baseline':classification_metrics(truth,rules[index])})
    clipped=(raw//np.array(model['divisors']))>127
    details=[]
    for i,row in enumerate(rows):
        details.append(dict(row,prediction=int(pred[i]),baseline_prediction=int(rules[i]),
                            scores=[int(v) for v in scores[i]],quantized=[int(v) for v in q[i]]))
    report={'kind':'frozen_challenge_evaluation','model_retrained':False,'thresholds_retuned':False,
            'ai':classification_metrics(labels,pred),'baseline':classification_metrics(labels,rules),
            'missing_classes':sorted({0,1,2}-set(int(v) for v in labels)),
            'capture_count':len(captures),'per_capture':per_capture,
            'input_saturation':[{'feature':name,'clipped_windows':int(clipped[:,i].sum()),'fraction':float(clipped[:,i].mean())} for i,name in enumerate(NAMES)],
            'limits':['Scenario/window classification, not per-packet classification.',
                      'Windows from one capture are correlated; capture count matters.',
                      'No FPGA blocking, Ethernet throughput or hardware timing is measured here.']}
    return report,details


def read_jsonl(path):
    rows=[];invalid=0
    if not Path(path).exists():return rows,invalid
    with Path(path).open() as f:
        for line in f:
            if not line.strip():continue
            try:row=json.loads(line)
            except ValueError:invalid+=1;continue
            if not isinstance(row,dict):invalid+=1;continue
            rows.append(row)
    return rows,invalid


def percentile(values,p):
    return float(np.percentile(values,p)) if values else None


def session_summary(directory,shared_clock=False):
    directory=Path(directory)
    primary=directory/'sensor.jsonl'
    if not primary.is_file():raise ValueError(f'Missing {primary}')
    records=[];invalid=0;sources=[]
    files=[primary]+([directory/'sensor_extra.jsonl'] if (directory/'sensor_extra.jsonl').exists() else [])
    for path in files:
        rows,bad=read_jsonl(path);invalid+=bad
        valid=[]
        for r in rows:
            if type(r.get('ok')) is not bool or not isinstance(r.get('elapsed_ms'),(int,float)) or not math.isfinite(r['elapsed_ms']) or r['elapsed_ms']<0:
                invalid+=1;continue
            valid.append(r)
        records+=valid;sources.append({'file':path.name,'completed_attempts':len(valid),'success':sum(r['ok'] for r in valid)})
    if not records:raise ValueError('No completed sensor attempts')
    received,bad=read_jsonl(directory/'received.jsonl');invalid+=bad
    received=[r for r in received if isinstance(r.get('payload'),dict) and isinstance(r.get('received_at'),(int,float)) and math.isfinite(r['received_at'])]
    keys=set();delays=[];times=[]
    for r in received:
        payload=r['payload'];key=(str(payload.get('sensor_id','legacy')),payload.get('seq'))
        if not isinstance(key[1],int) or key in keys:continue
        keys.add(key);times.append(float(r['received_at']))
        sent=payload.get('sent_at')
        if shared_clock and isinstance(sent,(int,float)) and math.isfinite(sent):delays.append(1000*(r['received_at']-sent))
    success=sum(r['ok'] for r in records);elapsed=[r['elapsed_ms'] for r in records]
    scenario={}
    if (directory/'scenario.txt').exists():
        for line in (directory/'scenario.txt').read_text().splitlines():
            if '=' in line:k,v=line.split('=',1);scenario[k]=v
    result={'session':str(directory),'scenario':scenario,'sensor_sources':sources,
            'completed_attempts':len(records),'success':success,'failures':len(records)-success,
            'failure_rate':(len(records)-success)/len(records),'elapsed_ms_median':percentile(elapsed,50),
            'elapsed_ms_p95':percentile(elapsed,95),'received_unique_messages':len(keys),
            'received_log_records':len(received),'invalid_log_records':invalid,
            'max_receive_gap_ms':1000*max((b-a for a,b in zip(sorted(times),sorted(times)[1:])),default=0),
            'shared_clock_assumed':shared_clock,'send_to_receive_ms_p95':percentile(delays,95),
            'limits':['Elapsed time is connect/publish/disconnect, not pure network RTT.',
                      'Only completed logged attempts are counted; end-of-capture can censor an unfinished operation.',
                      'PUBACK success and subscriber reception are separate measurements.']}
    capture_log=directory/'capture.log'
    if capture_log.exists():
        import re
        text=capture_log.read_text(errors='replace');m=re.search(r'(\d+) packets dropped by kernel',text)
        result['kernel_capture_drops']=int(m.group(1)) if m else None
    snapshots,_=read_jsonl(directory/'broker_stats.jsonl')
    snapshots=[r for r in snapshots if isinstance(r.get('tcp_ext'),dict) and isinstance(r.get('tcp_states'),dict)]
    result['broker_stats_available']=bool(snapshots)
    if snapshots:
        first,last=snapshots[0].get('tcp_ext',{}),snapshots[-1].get('tcp_ext',{})
        result['broker_tcp_ext_delta']={k:(last[k]-v if last.get(k,-1)>=v else None) for k,v in first.items() if k in last}
        result['peak_syn_recv']=max(r.get('tcp_states',{}).get('SYN_RECV',0) for r in snapshots)
    return result


def compare_sessions(before,during,shared_clock=False):
    a=session_summary(before,shared_clock);b=session_summary(during,shared_clock)
    try:
        ia=float(a['scenario']['sensor_interval']);ib=float(b['scenario']['sensor_interval'])
        comparable=ia>0 and ia==ib and len(a['sensor_sources'])==len(b['sensor_sources']) and all(x['completed_attempts']>0 for x in a['sensor_sources']+b['sensor_sources'])
    except (ValueError,KeyError):comparable=False
    notes=[]
    if not comparable:notes.append('Different legitimate load/source settings: do not attribute differences solely to attack.')
    if a['failures']==0 and b['failures']==0:notes.append('No completed publish failures observed; service interruption is NOT demonstrated by these sessions.')
    else:notes.append('Failures are observations, not proof of attack causality; repeat comparable runs.')
    return {'kind':'mqtt_session_comparison','baseline':a,'during':b,'legitimate_load_comparable':comparable,
            'p95_elapsed_ratio':b['elapsed_ms_p95']/a['elapsed_ms_p95'] if a['elapsed_ms_p95'] else None,
            'notes':notes,'hardware_blocking_verified':False}
