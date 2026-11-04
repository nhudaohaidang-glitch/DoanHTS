"""Train a separate V4 candidate from the user's reviewed three-class folders."""
import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
KIT=HERE if (HERE/'part2').is_dir() else HERE.parent
sys.path.insert(0,str(KIT))
from part2.filtered_training_data import select_sources,extract_source,sha
from part2.filtered_training import train
from prepare_gowin import prepare,validate


def save(path,value):
    part=path.with_name(path.name+'.part');part.write_text(json.dumps(value,indent=2),encoding='utf-8');part.replace(path)


def page(output,report):
    summary=report.get('training',{})
    text='<!doctype html><html lang="vi"><meta charset="utf-8"><title>Train ba nhóm V4</title><style>body{font:18px system-ui;max-width:1150px;margin:35px auto;line-height:1.6}table{border-collapse:collapse}td,th{border:1px solid #ccd;padding:8px}.note{background:#fff0c9;padding:15px}</style>'
    text+='<h1>'+('Đã train model V4 mới' if report['status']=='complete' else 'Train V4 chưa hoàn tất')+'</h1>'
    if report.get('error'):text+='<p>'+html.escape(report['error'])+'</p>'
    text+='<p class="note">Kết quả bên dưới đo độ khớp trên dữ liệu học. Chưa có kiểm thử độc lập: SYN flood và vertical scan hiện mỗi loại chỉ có một đợt. Không chia ngẫu nhiên các giây của cùng đợt thành train/test.</p>'
    if summary:
        if summary.get('conflicting_quantized_patterns'):
            text+='<p class="note"><strong>Cần rà soát nhãn:</strong> có '+str(summary['conflicting_quantized_patterns'])+' bộ sáu giá trị lượng tử xuất hiện ở nhiều lớp. Model không thể phân biệt các mẫu có đầu vào giống hệt nhau. Giữ nguyên nhãn gốc; xem conflict_examples trong metrics.json và CSV đặc trưng của từng nguồn.</p>'
        text+='<table><tr><th>Loại</th><th>Cửa sổ học</th><th>Đúng float</th><th>Đúng số nguyên FPGA</th></tr>'
        for label,name in enumerate(('Bình thường','SYN flood','Vertical scan')):
            fm=summary['training_fit']['float']['per_class'][label];im=summary['training_fit']['integer']['per_class'][label]
            text+=f'<tr><td>{name}</td><td>{im["support"]}</td><td>{100*fm["recall"]:.2f}%</td><td>{100*im["recall"]:.2f}%</td></tr>'
        text+='</table><p>Kiến trúc 6–8–3, sáu đặc trưng và divisors [8,2,1,1,1,1]. Model V3 cũ được giữ riêng. Model mới nằm tại <a href="candidate_v4/model/model.json">model.json</a>; project tại <a href="candidate_v4/gowin/ai_core_v4.gprj">ai_core_v4.gprj</a>.</p>'
        text+='<p>Báo cáo thống kê trên toàn bộ cửa sổ đã chuẩn bị. Khi có nhiều điểm q khác nhau, bước fit lấy tối đa '+str(summary['sampling_cap_per_class'])+' điểm q phân biệt mỗi lớp bằng reservoir xác định trước. Số điểm đã thấy/đưa vào fit được ghi trong metrics.json.</p>'
        text+='<p>Các điểm lượng tử trùng được gom, rồi cân bằng số điểm giữa ba lớp khi fit. Lặp điểm để cân bằng không tạo ra phiên lưu lượng mới. Báo cáo vẫn tính độ khớp theo toàn bộ số cửa sổ đã chuẩn bị.</p>'
        text+='<p>Normal lấy từ các PCAP Benign đã lọc, mỗi IP đích /32 là một bên nhận riêng. SYN và scan chỉ lấy đích đã kiểm chứng và cửa sổ trọn vẹn trong thời gian đang tấn công. Các PCAP phụ trùng nguồn được bỏ trước khi học. Đây là đặc trưng của lưu lượng đã lọc, không khôi phục toàn bộ lưu lượng gốc.</p>'
        text+='<p>Kiểm RTL: '+html.escape(report.get('verification',{}).get('rtl','not run'))+'. Chưa đo timing sau routing, chặn Ethernet hoặc hiệu quả trên bo. Phạm vi đích và mốc cửa sổ phần cứng phải thống nhất với bước trích đặc trưng.</p>'
        text+='<p><a href="candidate_v4/model/metrics.json">Chi tiết học và giới hạn</a> | <a href="TRAIN_STATE.json">Nguồn, checksum và tiến trình</a></p>'
    text+='<table><tr><th>Nguồn</th><th>Lớp</th><th>Cửa sổ</th><th>CSV đặc trưng</th></tr>'
    for source in report.get('sources',{}).values():
        text+='<tr><td>'+html.escape(source['path'])+'</td><td>'+str(source['label'])+'</td><td>'+str(source['windows'])+'</td><td><a href="'+html.escape(source['feature_csv'],quote=True)+'">features.csv.gz</a></td></tr>'
    text+='</table>'
    (output/'MO_KET_QUA_TRAIN.html').write_text(text,encoding='utf-8')


def verify_files(root,checksums):
    for name,expected in checksums.items():
        path=root/name
        if not path.is_file() or sha(path)!=expected:raise ValueError('Saved file changed/missing: '+str(path))


def export_candidate(stage,sources,fingerprint,maximum_patterns,model_version='v4'):
    training=train(sources,stage/'model',maximum_patterns,model_version)
    prepare(stage/'model',stage/'gowin',KIT)
    header='''#ifndef AI_V4_INTEGRATION_H
#define AI_V4_INTEGRATION_H
#include "ai_quant_v4.h"
/* Validity is RAW packet count, not q0. TTL is handled by the caller. */
static inline int ai_v4_prepare_window(uint32_t packets, uint64_t ip_bytes,
 uint32_t syn_open, uint32_t src_count, uint32_t dst_count,
 uint32_t port_count, uint64_t *feat_out) {
 *feat_out=0;
 if (!packets) return 0;
 *feat_out=ai_v4_pack(packets,ip_bytes,syn_open,src_count,dst_count,port_count);
 return 1;
}
#endif
'''
    header=header.replace('V4',model_version.upper()).replace('v4',model_version)
    (stage/f'gowin/firmware/ai_{model_version}_integration.h').write_text(header)
    verification=dict(rtl='not run: Icarus tools unavailable',vectors=training['rtl_vector_count'],gowin_synthesis_executed=False)
    if shutil.which('iverilog') and shutil.which('vvp'):
        executable=stage/'gowin/verification/sim.vvp'
        commands=[['iverilog','-g2012','-Wall','-s','tb_ai_core','-o',str(executable),
                   str(stage/f'gowin/src/ai_core_model_{model_version}.v'),str(stage/'gowin/verification/tb_ai_core.v')],
                  ['vvp',str(executable),'+vectors='+str(stage/'gowin/verification/vectors.txt')]]
        log=[]
        for command in commands:
            result=subprocess.run(command,capture_output=True,text=True,timeout=180)
            log.append(result.stdout+result.stderr)
            if result.returncode:raise ValueError('RTL verification failed: '+log[-1])
        if 'PASS vectors=' not in log[-1]:raise ValueError('RTL did not report PASS')
        verification['rtl']=log[-1].strip();executable.unlink()
        (stage/'gowin/verification/RESULT.txt').write_text('\n'.join(log))
    checksums={str(p.relative_to(stage)):sha(p) for p in stage.rglob('*') if p.is_file()}
    complete=dict(fingerprint=fingerprint,training=training,verification=verification,files=checksums)
    save(stage/'CANDIDATE_COMPLETE.json',complete)
    return complete


def run(data,output,maximum_patterns=5000):
    data=Path(data).expanduser().resolve();output=Path(output).expanduser().resolve()
    if not 1<=maximum_patterns<=100000:raise ValueError('max-patterns must be 1..100000')
    selected,selection=select_sources(data)
    old_model=KIT/'gowin/hybrid_v3/model/model.json'
    if not old_model.is_file():old_model=Path.home()/'ai_part2/gowin/hybrid_v3/model/model.json'
    old_sha=sha(old_model) if old_model.is_file() else None
    code={name:sha(KIT/name) for name in ('part2/filtered_training_data.py','part2/filtered_training.py',
                                         'part2/features.py','part2/integer.py','part2/development.py')}
    fingerprint=dict(selection=selection,sources=selected,maximum_patterns=maximum_patterns,code=code,
                     driver_sha256=sha(__file__),exporter_sha256=sha(HERE/'prepare_gowin.py'))
    state=output/'TRAIN_STATE.json'
    if output.exists():
        if not state.is_file():raise ValueError('Output already exists without this job marker; use another output folder')
        report=json.loads(state.read_text())
        if report.get('fingerprint')!=fingerprint:raise ValueError('Resume inputs, settings or code differ')
    else:
        output.parent.mkdir(parents=True,exist_ok=True)
        if shutil.disk_usage(output.parent).free<4*1024**3:raise ValueError('Need 4 GiB free for features and sorting scratch')
        output.mkdir();report=dict(status='in_progress',fingerprint=fingerprint,sources={},old_v3_sha256=old_sha,
                                 training_mode='all prepared windows for learning; no independent holdout')
        save(state,report)
    report.pop('error',None)
    try:
        candidate=output/'candidate_v4'
        if candidate.exists():
            complete=json.loads((candidate/'CANDIDATE_COMPLETE.json').read_text())
            if complete['fingerprint']!=fingerprint:raise ValueError('Candidate belongs to different inputs')
            verify_files(candidate,complete['files'])
            print('Using already trained candidate with matching checksums.',flush=True)
        else:
            for index,spec in enumerate(selected,1):
                if spec['id'] in report['sources']:
                    source=report['sources'][spec['id']]
                    verify_files(output,{source['feature_csv']:source['feature_csv_sha256'],source['patterns_db']:source['patterns_db_sha256']})
                    print('REUSE features:',spec['path'],flush=True);continue
                print(f'PREPARE {index}/{len(selected)}: class {spec["label"]}; {spec["path"]}',flush=True)
                source=extract_source(data,spec,output/'features'/spec['id'])
                for key in ('feature_csv','patterns_db'):source[key]=str(Path(source[key]).relative_to(output))
                report['sources'][spec['id']]=source;save(state,report);page(output,report)
            sources=[dict(s,patterns_db=str(output/s['patterns_db'])) for s in report['sources'].values()]
            with tempfile.TemporaryDirectory(prefix='.candidate_training_',dir=output) as directory:
                stage=Path(directory)/'candidate';stage.mkdir()
                complete=export_candidate(stage,sources,fingerprint,maximum_patterns)
                stage.rename(candidate)
        if old_sha is not None and sha(old_model)!=old_sha:raise ValueError('Existing V3 model changed during this job')
        report.update(status='complete',training=complete['training'],verification=complete['verification'],
                      old_v3_preserved=old_sha is None or sha(old_model)==old_sha)
    except BaseException as error:
        report.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',error=str(error) or 'Interrupted; repeat the command')
        raise
    finally:save(state,report);page(output,report)
    print('DONE. Open:',output/'MO_KET_QUA_TRAIN.html',flush=True)
    print('New model:',output/'candidate_v4/model/model.json',flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',default=str(Path.home()/'iot23_da_loc_01'))
    parser.add_argument('--output',default=str(Path.home()/'iot23_train_v4_01'))
    parser.add_argument('--max-patterns',type=int,default=5000)
    args=parser.parse_args()
    try:run(args.data,args.output,args.max_patterns)
    except KeyboardInterrupt:parser.exit(130,'Interrupted. Repeat the same command to resume prepared sources.\n')
    except (ValueError,OSError,KeyError) as error:parser.exit(1,'ERROR: '+str(error)+'\n')
