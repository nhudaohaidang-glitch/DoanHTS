"""Review uploaded V4 weights/metrics without fitting or changing the model."""
import argparse
import csv
import gzip
import html
import json
from pathlib import Path
import shutil
import sys

import numpy as np

KIT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(KIT))
from part2.features import NAMES,quantize
from part2.filtered_training import weighted_metrics
from part2.filtered_training_data import sha
from part2.integer import export_model,infer,write_vectors
from prepare_gowin import prepare
from check_edge_cases import check as check_probes


def scalar_scores(point,model):
    hidden=[]
    for weights,bias in zip(model['w1'],model['b1']):
        value=(sum(int(a)*int(b) for a,b in zip(point,weights))+bias)>>model['shift1']
        hidden.append(min(127,max(0,value)))
    result=[]
    for weights,bias in zip(model['w2'],model['b2']):
        value=(sum(a*b for a,b in zip(hidden,weights))+bias)>>model['shift2']
        result.append(min(32767,max(-32768,value)))
    return result


def review(model_path,metrics_path,output,reference=None):
    model_path,metrics_path,output=map(Path,(model_path,metrics_path,output))
    if output.exists():raise ValueError('Output exists; use another review folder')
    original_sha=sha(model_path);model=json.loads(model_path.read_text());metrics=json.loads(metrics_path.read_text())
    if model.get('model_version')!='v4' or model['architecture']!=[6,8,3]:raise ValueError('Expected V4 6-8-3')
    if metrics['model_sha256']!=original_sha:raise ValueError('Metrics refer to another model')
    if metrics['architecture']!=model['architecture'] or metrics['divisors']!=model['divisors']:
        raise ValueError('Architecture/quantization differs between uploaded files')
    for mode in ('float','integer'):
        cm=np.asarray(metrics['training_fit'][mode]['confusion_matrix'],dtype=np.int64)
        if cm.shape!=(3,3) or np.any(cm<0):raise ValueError('Invalid confusion matrix')
        source_sum=np.sum([s['metrics'][mode]['confusion_matrix'] for s in metrics['per_source']],axis=0)
        if not np.array_equal(cm,source_sum):raise ValueError('Per-source matrices do not add up')
        if cm.sum(axis=1).tolist()!=metrics['training_windows_by_class']:raise ValueError('Class support counts differ')
        calculated=weighted_metrics(cm)
        for key in ('accuracy','macro_f1','false_positive_rate'):
            if abs(calculated[key]-metrics['training_fit'][mode][key])>1e-12:raise ValueError('Reported metric differs: '+key)
    retained=metrics['retained_fit_patterns_by_class']
    if metrics['balanced_fit_rows']!=3*max(retained):raise ValueError('Balanced fit count differs')
    if metrics['rtl_vector_count']!=sum(retained)+264:raise ValueError('Training vector count differs')
    output.mkdir(parents=True)
    folder=output/'model';export_model(model,folder)
    (folder/'model.json').write_bytes(model_path.read_bytes())
    (folder/'metrics.json').write_bytes(metrics_path.read_bytes())
    probes=check_probes(folder,output/'probes')
    q=np.asarray([row['quantized'] for row in probes['cases']],dtype=np.int64)
    generator=np.random.default_rng(470)
    points=np.vstack([q,generator.integers(0,128,(1024,6)),np.zeros((1,6),dtype=int),np.full((1,6),127),np.eye(6,dtype=int)*127,
                      [127,20,127,1,1,1]])
    scores=infer(points,model)
    if not np.array_equal(scores,np.asarray([scalar_scores(p.tolist(),model) for p in points])):
        raise ValueError('Independent scalar arithmetic differs from vectorized model')
    vector_count=write_vectors(points,model,folder/'vectors.txt')
    prepare(folder,output/'gowin',KIT)
    guard=KIT/'examples/filtered_v4_reference/candidate_v4/gowin/firmware/ai_v4_integration.h'
    shutil.copy2(guard,output/'gowin/firmware/ai_v4_integration.h')
    failures=[]
    if reference is not None:
        with gzip.open(reference,'rt') as stream:rows=list(csv.DictReader(stream))
        raw=np.asarray([[int(row[n]) for n in NAMES] for row in rows],dtype=np.int64)
        q=quantize(raw,model['divisors']);local_scores=infer(q,model);pred=local_scores.argmax(1)
        for row,x,point,score,prediction in zip(rows,raw,q,local_scores,pred):
            if prediction!=int(row['class']):
                failures.append(dict(window_start=int(row['window_start']),target_ip=row['target_ip'],label=int(row['class']),
                                     prediction=int(prediction),raw=x.tolist(),q=point.tolist(),scores=score.tolist(),
                                     same_as_conflict=point.tolist()==[127,20,127,1,1,1]))
        source=next(s for s in metrics['per_source'] if s['label']==0 and 'Capture-34-1' in s['source_group'])
        cm=np.zeros((3,3),dtype=np.int64)
        for row,prediction in zip(rows,pred):cm[int(row['class']),prediction]+=1
        if cm.tolist()!=source['metrics']['integer']['confusion_matrix']:
            raise ValueError('Shared capture34 reference did not reproduce uploaded per-source results')
    with (output/'CUA_SO_CAN_RA_SOAT.csv').open('w',newline='') as stream:
        fields=['window_start','target_ip','label','prediction','raw','q','scores','same_as_conflict']
        writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(failures)
    failures_by_source=[]
    for source in metrics['per_source']:
        cm=np.asarray(source['metrics']['integer']['confusion_matrix'])
        count=int(cm.sum()-np.trace(cm))
        if count:failures_by_source.append(dict(source_id=source['source_id'],source_group=source['source_group'],
                                               label=source['label'],windows=source['windows'],incorrect=count))
    cm=metrics['training_fit']['integer']['confusion_matrix'];total=sum(map(sum,cm));incorrect=total-sum(cm[i][i] for i in range(3))
    bounds={name:int(max(127*sum(abs(v) for v in w)+abs(b) for w,b in zip(model[name],model['b'+name[-1]])))
            for name in ('w1','w2')}
    report=dict(kind='uploaded_full_three_class_v4_review',model_sha256=original_sha,metrics_sha256=sha(metrics_path),
                original_uploaded_weights_preserved=sha(folder/'model.json')==original_sha,
                model_retrained=False,training_report_internally_consistent=True,
                full_user_dataset_recomputed_here=False,independent_traffic_test_performed=False,
                float_metrics_recomputed_from_weights=False,
                architecture=model['architecture'],divisors=model['divisors'],shifts=[model['shift1'],model['shift2']],
                parameter_count=83,int32_accumulator_bounds=bounds,
                training_windows=total,correct=total-incorrect,incorrect=incorrect,
                exact_integer_training_metrics=metrics['training_fit']['integer'],
                conflicting_quantized_patterns=metrics['conflicting_quantized_patterns'],conflicts=metrics['conflict_examples'],
                errors_by_source=failures_by_source,shared_capture34_reference_reproduced=reference is not None,
                capture34_reference_error_windows=failures,
                unique_quantized_training_patterns=metrics['unique_quantized_patterns_by_class'],
                balanced_fit_rows=metrics['balanced_fit_rows'],
                prior_user_reported_rtl_vectors=metrics['rtl_vector_count'],
                independently_generated_arithmetic_vectors=vector_count,scalar_vectorized_scores_match=True,
                engineered_probe_count=probes['total'],failed_engineered_scenarios=probes['failed_scenario_expectations'],
                engineered_probes_are_not_pcaps_or_independent_accuracy=True,
                automatic_blocking_ready=False,
                limitations=['Classification mismatches are relative to provided labels; their real-world intent requires annotation review.',
                             'Different labels sharing an identical q input cannot be separated by a classifier using only those q values.',
                             'One fast scan episode supplies very few scan training windows; constructed probes are not independent traffic tests.',
                             'No new model selection, training, full-data reconstruction or physical FPGA measurement here.'])
    (output/'BAO_CAO_KIEM_TRA.json').write_text(json.dumps(report,indent=2)+'\n')
    page(output,model,metrics,report,probes)
    if sha(model_path)!=original_sha:raise ValueError('Uploaded source file unexpectedly changed')
    return report


def page(output,model,metrics,report,probes):
    metric=report['exact_integer_training_metrics'];cm=metric['confusion_matrix'];names=['Bình thường','SYN flood','Vertical scan']
    content='<!doctype html><html lang="vi"><meta charset="utf-8"><title>V4: kết quả chính xác</title><style>body{font:18px system-ui;max-width:1150px;margin:35px auto;line-height:1.6}td,th{border:1px solid #ccd;padding:9px}table{border-collapse:collapse}.note{background:#fff0cc;padding:15px}code{font-size:15px}</style>'
    content+='<h1>Kết quả chính xác của model V4 trên máy bạn</h1><p>Giữ nguyên model đã gửi, không train lại. SHA256: <code>'+report['model_sha256']+'</code>.</p>'
    content+='<p class="note">Các con số sau là độ khớp trên tập học theo nhãn hiện có. Chưa có kiểm thử lưu lượng độc lập. Tệp cũ làm tròn hai chữ số; số mẫu sai chính xác là '+str(report['incorrect'])+'.</p>'
    content+='<table><tr><th>Nhãn gốc</th><th>Số cửa sổ</th><th>Đúng</th><th>Sai</th><th>Tỷ lệ đúng</th></tr>'
    for i,name in enumerate(names):
        count=sum(cm[i]);correct=cm[i][i]
        content+=f'<tr><td>{name}</td><td>{count:,}</td><td>{correct:,}</td><td>{count-correct}</td><td>{100*correct/count:.8f}%</td></tr>'
    syn_predictions=sum(row[1] for row in cm);syn_true=cm[1][1]
    content+='</table><p>Accuracy tập học: '+f'{100*metric["accuracy"]:.8f}%'+f'. Trong {syn_predictions} cửa sổ được dự đoán SYN, {syn_true} cửa sổ có nhãn SYN: precision SYN theo nhãn hiện tại là <strong>{100*metric["per_class"][1]["precision"]:.2f}%</strong>. Các ma trận float/integer được kiểm tính nhất quán trong báo cáo; chỉ model số nguyên được chạy lại ở lần kiểm tra này.</p>'
    content+='<h2>Nhãn xung đột và vị trí cần xem</h2><p>Model nhận cùng một đầu vào nên phải cho cùng một kết quả. Các điểm q mang nhiều nhãn cần được kiểm tra:</p><ul>'
    for conflict in report['conflicts']:
        content+='<li>q='+html.escape(str(conflict['q']))+'; số cửa sổ theo nhãn: '+html.escape(str(conflict['counts_by_label']))+'</li>'
    content+='</ul>'
    if report['shared_capture34_reference_reproduced']:
        failures=report['capture34_reference_error_windows'];targets=sorted({f['target_ip'] for f in failures})
        content+='<p>Đã tái hiện đúng '+str(len(failures))+' lỗi của capture34 trên bản đặc trưng cùng nguồn đang có tại đây, không đọc lại toàn bộ dữ liệu của máy bạn. Các đích cần rà soát: '+html.escape(', '.join(targets))+'. Giữ nguyên nhãn nguồn. <a href="CUA_SO_CAN_RA_SOAT.csv">Danh sách cửa sổ, raw, q và scores</a>.</p>'
    content+='<h2>Kiểm tra tình huống ngoại tuyến</h2><p>Các vector bên dưới được dựng để kiểm tra phản ứng của model, không phải PCAP hoặc tập test độc lập. Chỉ dùng chúng để kiểm tra giới hạn hành vi, không coi kết quả là tỷ lệ phát hiện trên lưu lượng thực tế hoặc tự đưa chúng vào dữ liệu học.</p><table><tr><th>Tình huống</th><th>Raw 6 đặc trưng</th><th>Dự đoán</th><th>Mong đợi trong kịch bản</th></tr>'
    for row in probes['cases']:
        content+='<tr><td>'+html.escape(row['case'])+'</td><td>'+html.escape(str(list(row['raw'].values())))+'</td><td>'+names[row['prediction']]+'</td><td>'+names[row['expected_scenario_class']]+'</td></tr>'
    content+='</table><p>Cần rà soát nhãn và thu thêm phiên SYN/scan ở nhiều mức tải, đặc biệt scan chậm, rồi đánh giá riêng sau khi chốt model. Bộ core đã xuất giữ nguyên trọng số, cùng giao diện 6–8–3; chưa có đo timing/chặn trên bo và chưa dùng class_id đơn lẻ để chặn tự động.</p>'
    content+='<p><a href="BAO_CAO_KIEM_TRA.json">Báo cáo kiểm tra</a> | <a href="model/metrics.json">metrics gốc</a> | <a href="model/model.json">model gốc</a> | <a href="gowin/ai_core_v4.gprj">Project đúng bộ trọng số này</a></p>'
    (output/'MO_KET_QUA_V4_CHINH_XAC.html').write_text(content,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True);parser.add_argument('--metrics',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--reference-features',type=Path)
    args=parser.parse_args()
    result=review(args.model,args.metrics,args.output,args.reference_features)
    print(json.dumps(dict(model_sha256=result['model_sha256'],incorrect=result['incorrect'],review=str(args.output)),indent=2))
