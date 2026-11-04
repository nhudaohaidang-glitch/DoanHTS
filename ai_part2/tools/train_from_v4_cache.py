"""Fit a separate V5 from the exact V4 cache plus same-parent time variants."""
import argparse
import csv
import html
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

import numpy as np

HERE=Path(__file__).resolve().parent
KIT=HERE if (HERE/'part2').is_dir() else HERE.parent
sys.path.insert(0,str(KIT))
from part2.filtered_training_data import sha
from part2.filtered_training import unpack,weighted_metrics
from part2.integer import infer
from train_filtered_three_classes import export_candidate,save,verify_files
from check_edge_cases import check as check_probes


def read_base(base):
    candidate=base/'candidate_v4';model_path=candidate/'model/model.json';metrics_path=candidate/'model/metrics.json'
    database=candidate/'model/training_patterns.sqlite'
    complete=json.loads((candidate/'CANDIDATE_COMPLETE.json').read_text())
    verify_files(candidate,{name:complete['files'][name] for name in
                            ('model/model.json','model/metrics.json','model/training_patterns.sqlite')})
    model=json.loads(model_path.read_text());metrics=json.loads(metrics_path.read_text())
    if model.get('model_version')!='v4' or model['divisors']!=[8,2,1,1,1,1] or model['architecture']!=[6,8,3]:
        raise ValueError('Requires the reviewed V4 six-feature model')
    if metrics['model_sha256']!=sha(model_path):raise ValueError('Base metrics refer to another model')
    sources=complete['fingerprint']['sources']
    labels={s['label'] for s in sources}
    public=[s for s in sources if s['label']==2]
    if labels!={0,1,2} or len(public)!=1 or public[0]['sha256']!='dec17c51b1b9d464831edb6e1f0a5bbcbeabdc519bfb4a5a402803384adb257c':
        raise ValueError('Base V4 is not from the expected IoT23 Normal/SYN and public scan folders')
    for source in sources:
        if source['label'] in (0,1) and ('binh_thuong/pcap/' if source['label']==0 else 'syn_flood/pcap/') not in source['path']:
            raise ValueError('Unexpected base data provenance')
    info=dict(model_sha256=sha(model_path),metrics_sha256=sha(metrics_path),cache_sha256=sha(database),
              original_sources=sources,expected_windows=metrics['training_windows_by_class'],
              original_data_fingerprint=complete['fingerprint']['selection'])
    return model,metrics,database,info


def evaluate_cache(database,model):
    matrices=np.zeros((3,3),dtype=np.int64);unique=[0,0,0];windows=[0,0,0]
    with sqlite3.connect(database) as db:
        db.execute('PRAGMA query_only=ON')
        cursor=db.execute('SELECT label,packed,count FROM patterns ORDER BY label,packed')
        while rows:=cursor.fetchmany(10000):
            for label,packed,count in rows:
                if label not in (0,1,2) or not isinstance(packed,int) or not 0<=packed<2**48 or not isinstance(count,int) or count<=0 or max(unpack(packed))>127:
                    raise ValueError('Invalid cached label/quantized pattern/count')
            x=np.asarray([unpack(p) for l,p,n in rows],dtype=np.int64);pred=infer(x,model).argmax(1)
            for (label,packed,count),prediction in zip(rows,pred):
                matrices[label,int(prediction)]+=count;unique[label]+=1;windows[label]+=count
    return weighted_metrics(matrices),unique,windows


def prepare_sources(database,manifest,variants,output):
    sources=[]
    with sqlite3.connect(database) as db:
        db.execute('PRAGMA query_only=ON')
        for label in range(3):
            path=output/f'base_class{label}.sqlite'
            with sqlite3.connect(path) as dest:
                dest.execute('CREATE TABLE patterns (packed INTEGER PRIMARY KEY,count INTEGER)')
                dest.executemany('INSERT INTO patterns VALUES (?,?)',db.execute('SELECT packed,count FROM patterns WHERE label=?',(label,)))
                count=int(dest.execute('SELECT coalesce(sum(count),0) FROM patterns').fetchone()[0])
            sources.append(dict(id=f'base_v4_class{label}',label=label,source_group='base_V4_all_original_groups_training_only',
                                windows=count,patterns_db=str(path),sha256=sha(path)))
    for variant in manifest['variants']:
        path=output/(variant['id']+'.sqlite');csv_path=variants/variant['feature_csv']
        if sha(csv_path)!=variant['feature_csv_sha256'] or sha(variants/variant['pcap'])!=variant['pcap_sha256']:
            raise ValueError('Augmentation file changed: '+variant['id'])
        rows=[]
        with csv_path.open(newline='') as stream:
            for row in csv.DictReader(stream):
                if row['training_label']=='':continue
                if row['training_label']!='2' or int(row['dst_port_count'])<3:raise ValueError('Invalid augmented window label')
                q=[int(row[f'q{i}']) for i in range(6)]
                if min(q)<0 or max(q)>127:raise ValueError('Invalid augmented q input')
                rows.append((sum(v<<(8*i) for i,v in enumerate(q)),1))
        with sqlite3.connect(path) as dest:
            dest.execute('CREATE TABLE patterns (packed INTEGER PRIMARY KEY,count INTEGER)')
            dest.executemany('INSERT INTO patterns VALUES (?,?) ON CONFLICT(packed) DO UPDATE SET count=count+1',rows)
        if len(rows)!=variant['eligible_training_windows']:raise ValueError('Variant window count differs')
        sources.append(dict(id=variant['id'],label=2,source_group=manifest['original_parent_group'],
                            windows=len(rows),patterns_db=str(path),sha256=variant['pcap_sha256']))
    return sources


def overview(output,report):
    names=['Normal','SYN flood','Vertical scan']
    page='<!doctype html><html lang="vi"><meta charset="utf-8"><title>V5: cùng dữ liệu gốc, thêm scan chậm mô phỏng</title><style>body{font:18px system-ui;max-width:1150px;margin:35px auto;line-height:1.6}table{border-collapse:collapse}td,th{border:1px solid #ccd;padding:9px}.note{background:#fff0cc;padding:15px}</style><h1>Model V5 từ đúng cache dữ liệu V4</h1>'
    page+='<p class="note">Vẫn là kết quả phát triển/tập học. Các biến thể scan cùng một phiên nguồn, không phải các lần quét độc lập hoặc tập test mới. Giữ nguyên nhãn Normal/SYN gốc, kể cả các điểm xung đột.</p>'
    if report.get('error'):page+='<p>'+html.escape(report['error'])+'</p>'
    page+='<p>Model V4 gốc: <code>'+report['base']['model_sha256']+'</code>. Kiểm cache đã tái hiện chính xác ma trận V4 trước khi train V5.</p>'
    page+='<p>Dùng cache bạn gửi từ 28 PCAP Normal IoT-23, một PCAP SYN flood capture 34 và đúng PCAP scan Chris Sanders. Cache lưu các cặp (nhãn, q) cùng số lần xuất hiện; không đọc lại các PCAP Normal lớn. Giữ mọi mẫu và nhãn gốc. Khi fit, gom q trùng và cân bằng ba lớp như V4; số cửa sổ trong bảng vẫn tính đủ theo tần suất.</p>'
    if 'comparison' in report:
        page+='<table><tr><th>Nhãn trên cùng dữ liệu gốc</th><th>Tổng</th><th>Sai V4</th><th>Sai V5</th></tr>'
        before=report['comparison']['original_base_v4']['confusion_matrix'];after=report['comparison']['original_base_v5']['confusion_matrix']
        for i,name in enumerate(names):page+=f'<tr><td>{name}</td><td>{sum(before[i]):,}</td><td>{sum(before[i])-before[i][i]}</td><td>{sum(after[i])-after[i][i]}</td></tr>'
        page+='</table><p>Đây là so sánh cùng nhãn gốc, không loại 12 cửa sổ đang tranh chấp. Xem riêng độ khớp của biến thể trong metrics.json, không cộng biến thể vào để gọi đó là độ chính xác test.</p>'
        augmentation=report['comparison']['same_parent_augmented_scan']
        old=augmentation['v4']['confusion_matrix'];new=augmentation['v5']['confusion_matrix']
        page+=f'<h2>Scan biến thể từ cùng PCAP gốc</h2><p>Chỉ đổi timestamp, giữ nguyên byte gói, IP, cổng và thứ tự. Có 28 biến thể làm chậm 2–128 lần và lệch mốc cửa sổ. V4 nhận đúng {old[2][2]:,}/{sum(old[2]):,}; V5 nhận đúng {new[2][2]:,}/{sum(new[2]):,} cửa sổ đủ điều kiện đã dùng để học. Đây là độ khớp trên dữ liệu bổ sung cùng một phiên, không phải test độc lập.</p>'
        page+='<p>192 cửa sổ chỉ có 1–2 cổng vẫn được lưu trong CSV, gắn cần ngữ cảnh nhiều cửa sổ và không đưa vào fit. Không đổi chúng thành Normal. Các vector tình huống cũng không được thêm vào dữ liệu học hoặc dùng để chọn lượng tử hóa.</p>'
        page+='<h2>12 lỗi còn lại</h2><p>Theo nhãn hiện tại, 12 cửa sổ Normal vẫn bị báo SYN flood; precision SYN trên dữ liệu gốc là 21/33 = 63,64%. Trong đó 11 cửa sổ có q giống hệt 21 cửa sổ SYN. Đối chiếu log nguồn thấy các flow liên quan mang nhãn Benign; nhãn được giữ nguyên. Có đầu vào raw trùng giữa hai lớp, nên chỉ thay phép chia lượng tử không giải quyết hết xung đột. <a href="RA_SOAT_NHAN.json">Đối chiếu nhãn</a> | <a href="12_CUA_SO_V4.csv">12 cửa sổ V4 cần rà soát</a>.</p>'
        regressions=report['comparison']['known_probe_regressions']
        page+='<p>Kiểm các vector tình huống đã xem trước đây: '+str(regressions['total'])+' trường hợp, '+str(len(regressions['failed']))+' trường hợp chưa đạt mong đợi. Chỉ là regression phát triển. <a href="candidate_v5/regression_known_probes/cases.csv">Chi tiết</a>.</p>'
        page+='<p>Kiểm RTL: '+html.escape(report['verification']['rtl'])+'. Chưa đo trên bo hoặc có thử nghiệm lưu lượng độc lập.</p>'
        page+='<p>Giữ kiến trúc 6–8–3 và divisors [8,2,1,1,1,1]. V5 hiệu chỉnh thang từng neuron khi chuyển sang số nguyên, chọn trên cache học; không thay giao diện sáu đặc trưng. Kết quả float và integer được tách trong metrics.json. V4 gốc được giữ riêng; ứng viên V5 chưa được xác nhận để tự động chặn mạng.</p>'
        page+='<p><a href="candidate_v5/model/model.json">Model V5</a> | <a href="candidate_v5/gowin/ai_core_v5.gprj">Project Gowin V5</a> | <a href="V5_STATE.json">Nguồn và số liệu đầy đủ</a></p>'
    (output/'MO_KET_QUA_V5.html').write_text(page,encoding='utf-8')


def run(base,variants,output):
    base,variants,output=[Path(p).expanduser().resolve() for p in (base,variants,output)]
    model,metrics,database,info=read_base(base)
    manifest=json.loads((variants/'AUGMENTATION_MANIFEST.json').read_text())
    if manifest['original_pcap_sha256']!='dec17c51b1b9d464831edb6e1f0a5bbcbeabdc519bfb4a5a402803384adb257c' or manifest['new_independent_episodes']!=0:
        raise ValueError('Unexpected augmentation parent/protocol')
    print('BASE MODEL:',info['model_sha256'],flush=True)
    print('Verify exact base cache reproduces V4 confusion matrix before training.',flush=True)
    before,unique,windows=evaluate_cache(database,model)
    if before['confusion_matrix']!=metrics['training_fit']['integer']['confusion_matrix'] or windows!=metrics['training_windows_by_class'] or unique!=metrics['unique_quantized_patterns_by_class']:
        raise ValueError('Cached features do not reproduce this V4 model report')
    print('VERIFIED same base data. Windows:',windows,'unique q:',unique,flush=True)
    fingerprint=dict(base=info,augmentation_sha256=sha(variants/'AUGMENTATION_MANIFEST.json'),
                     driver_sha256=sha(__file__),trainer_sha256=sha(KIT/'part2/filtered_training.py'),
                     calibration_sha256=sha(KIT/'part2/filtered_calibration.py'),
                     arithmetic_sha256=sha(KIT/'part2/integer.py'),
                     base_conversion_sha256=sha(KIT/'part2/development.py'),
                     feature_code_sha256=sha(KIT/'part2/features.py'),
                     feature_data_code_sha256=sha(KIT/'part2/filtered_training_data.py'),
                     export_driver_sha256=sha(HERE/'train_filtered_three_classes.py'),exporter_sha256=sha(HERE/'prepare_gowin.py'))
    state=output/'V5_STATE.json'
    if output.exists():
        if not state.is_file():raise ValueError('Output exists without a job marker')
        report=json.loads(state.read_text())
        if report['fingerprint']!=fingerprint:raise ValueError('Inputs or code differ from saved V5 job')
    else:
        output.mkdir(parents=True)
        report=dict(status='in_progress',base=info,fingerprint=fingerprint,independent_test=False,
                    all_original_labels_kept=True,augmentation=manifest)
        save(state,report)
    try:
        target=output/'candidate_v5'
        if target.exists():
            complete=json.loads((target/'CANDIDATE_COMPLETE.json').read_text())
            if complete['fingerprint']!=fingerprint:raise ValueError('Saved candidate has different inputs')
            verify_files(target,complete['files']);print('Reusing complete V5 candidate.',flush=True)
        else:
            with tempfile.TemporaryDirectory(prefix='.train_v5_',dir=output) as temp:
                temp=Path(temp);sources=prepare_sources(database,manifest,variants,temp)
                stage=temp/'candidate';stage.mkdir()
                complete=export_candidate(stage,sources,fingerprint,5000,'v5')
                new_model=json.loads((stage/'model/model.json').read_text())
                after,_,_=evaluate_cache(database,new_model)
                merged_before,_,_=evaluate_cache(stage/'model/training_patterns.sqlite',model)
                merged_after=complete['training']['training_fit']['integer']
                augmented_before=np.asarray(merged_before['confusion_matrix'])-np.asarray(before['confusion_matrix'])
                augmented_after=np.asarray(merged_after['confusion_matrix'])-np.asarray(after['confusion_matrix'])
                if (augmented_before<0).any() or (augmented_after<0).any():raise ValueError('Augmentation comparison count mismatch')
                before_errors=[sum(row)-row[i] for i,row in enumerate(before['confusion_matrix'])]
                after_errors=[sum(row)-row[i] for i,row in enumerate(after['confusion_matrix'])]
                probes=check_probes(stage/'model',stage/'regression_known_probes')
                complete['comparison']=dict(original_base_v4=before,original_base_v5=after,
                    same_parent_augmented_scan=dict(v4=weighted_metrics(augmented_before),v5=weighted_metrics(augmented_after),
                                                    independent_test=False,used_for_training=True),
                    base_regression_gate=dict(passed=all(a<=b for a,b in zip(after_errors,before_errors)),
                                              v4_errors_by_class=before_errors,v5_errors_by_class=after_errors),
                    original_labels_unchanged=True,known_probe_regressions=dict(total=probes['total'],failed=probes['failed_scenario_expectations'],
                                                                           used_for_model_selection=False,independent_test=False))
                complete['files']={str(p.relative_to(stage)):sha(p) for p in stage.rglob('*') if p.is_file() and p.name!='CANDIDATE_COMPLETE.json'}
                save(stage/'CANDIDATE_COMPLETE.json',complete);stage.rename(target)
        if sha(base/'candidate_v4/model/model.json')!=info['model_sha256'] or sha(database)!=info['cache_sha256']:
            raise ValueError('Base V4 model or cache changed')
        report.update(status='complete',training=complete['training'],verification=complete['verification'],
                      comparison=complete['comparison'],v4_model_and_cache_preserved=True,ready_for_automatic_blocking=False,
                      candidate_status=complete['training']['candidate_status'] if complete['comparison']['base_regression_gate']['passed'] else 'rejected_on_original_data_regression')
    except BaseException as error:
        report.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',error=str(error) or 'Interrupted; repeat same command')
        raise
    finally:
        save(state,report)
        # Ship the already completed audit when available; not training input.
        for name,choices in [
            ('RA_SOAT_NHAN.json',[KIT.parent/'RA_SOAT_NHAN.json',KIT.parent/'reports/V4_NATIVE_LABEL_AUDIT_AND_SCAN_AUGMENTATION.json']),
            ('12_CUA_SO_V4.csv',[KIT.parent/'12_CUA_SO_V4.csv',KIT/'examples/user_v4_review_51050d9c/CUA_SO_CAN_RA_SOAT.csv'])]:
            source=next((p for p in choices if p.is_file()),None)
            if source is not None and not (output/name).exists():shutil.copy2(source,output/name)
        overview(output,report)
    print('DONE. Open:',output/'MO_KET_QUA_V5.html',flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-v4',default=str(Path.home()/'iot23_train_v4_01'))
    parser.add_argument('--variants',default=str(HERE/'SCAN_BIEN_THE') if (HERE/'SCAN_BIEN_THE').exists() else str(KIT/'examples/scan_time_variants_v5'))
    parser.add_argument('--output',default=str(Path.home()/'iot23_train_v5_01'))
    args=parser.parse_args()
    try:run(args.base_v4,args.variants,args.output)
    except KeyboardInterrupt:parser.exit(130,'Interrupted; repeat the same command to retry from unchanged V4 cache.\n')
    except (ValueError,OSError,KeyError,sqlite3.DatabaseError) as error:parser.exit(1,'ERROR: '+str(error)+'\n')
