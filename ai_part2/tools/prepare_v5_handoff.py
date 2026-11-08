"""Prepare the unchanged trained V5 for integration; no fit or relabeling."""
import argparse
import csv
import html
import json
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np

KIT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(KIT))
from part2.features import NAMES,quantize
from part2.filtered_training_data import sha
from part2.integer import infer,write_vectors
from check_edge_cases import probes
from prepare_gowin import validate
from train_filtered_three_classes import verify_files
from train_from_v4_cache import read_base,evaluate_cache

MODEL_SHA='688f1109f77da566c542c4903a0555be79cbf3e22ea08866187de20de68b7b8e'


def source_inventory(state,data,verify_pcaps=False):
    if data is None:
        if verify_pcaps:raise ValueError('Supply --data when using --verify-pcaps')
        return dict(checked=False,reason='No local dataset directory supplied')
    data=Path(data).expanduser().resolve()
    if not data.is_dir():raise ValueError('Dataset folder missing: '+str(data))
    sources=state['base']['original_sources'];missing=[];counts=[0,0,0]
    for source in sources:
        path=data/source['path'];counts[source['label']]+=1
        if not path.is_file():missing.append(source['path']);continue
        if verify_pcaps and sha(path)!=source['sha256']:raise ValueError('PCAP differs from training provenance: '+source['path'])
    csv_counts={}
    for folder in ('binh_thuong','syn_flood','vertical_scan'):
        csv_counts[folder]=sum(p.is_file() and p.name.endswith(('.csv','.csv.gz')) for p in (data/folder/'csv').glob('*'))
    if missing:raise ValueError('Missing original selected PCAP files: '+', '.join(missing))
    return dict(checked=True,data_root=str(data),selected_pcaps_by_class=counts,
                csv_files_by_folder=csv_counts,pcap_checksums_recomputed=verify_pcaps,
                note='CSV flow files provide labels/provenance; model input is the six per-second features. File existence alone is not a checksum check.')


def integration_vectors(model):
    cases=[dict(case='empty_skip',packet_count=0,ip_byte_sum=0,syn_open_count=0,src_count=0,dst_count=0,dst_port_count=0,
                valid_window=False,raw=[0]*6,q=[0]*6,feat_hex='000000000000',feat_lo=0,feat_hi=0,
                expected_scores=None,expected_class_id=None)]
    for name,scenario,raw,expected,syn in probes():
        n,mean,ratio,src,dst,ports=raw
        q=quantize(raw,model['divisors']);packed=sum(int(v)<<(8*i) for i,v in enumerate(q))
        scores=infer(q,model)[0]
        cases.append(dict(case=name,scenario=scenario,packet_count=n,ip_byte_sum=n*mean,syn_open_count=syn,
                          src_count=src,dst_count=dst,dst_port_count=ports,valid_window=True,raw=raw,q=q.tolist(),
                          feat_hex=f'{packed:012x}',feat_lo=packed&0xffffffff,feat_hi=packed>>32,
                          expected_scores=scores.tolist(),expected_class_id=int(scores.argmax()),
                          scenario_expected_class=expected))
    return cases


def write_handoff_vectors(stage,model):
    cases=integration_vectors(model)
    result=dict(kind='numeric_integration_reference_not_network_test_or_training',model_sha256=MODEL_SHA,
                features=NAMES,divisors=model['divisors'],raw_validity_rule='packet_count > 0, including q0=0',cases=cases)
    (stage/'INTEGRATION_V5.json').write_text(json.dumps(result,indent=2)+'\n')
    c=['#ifndef AI_V5_HANDOFF_VECTORS_H','#define AI_V5_HANDOFF_VECTORS_H','#include <stdint.h>',
       '/* Numeric reference only. Bind to the real CPU register driver. */',
       '#define AI_V5_MODEL_SHA256 "'+MODEL_SHA+'"',
       'typedef struct { const char *name; uint32_t packets; uint64_t ip_bytes; uint32_t syn, src, dst, ports;',
       ' uint32_t feat_lo; uint16_t feat_hi; int16_t scores[3]; uint8_t class_id, valid; } ai_v5_check_vector_t;',
       'static const ai_v5_check_vector_t ai_v5_check_vectors[] = {']
    with (stage/'INTEGRATION_V5.csv').open('w',newline='') as stream:
        fields=['case','valid_window','packet_count','ip_byte_sum','syn_open_count','src_count','dst_count','dst_port_count',
                'raw','q','feat_hex','feat_lo','feat_hi','expected_scores','expected_class_id']
        writer=csv.DictWriter(stream,fields,extrasaction='ignore',lineterminator='\n');writer.writeheader();writer.writerows(cases)
    for case in cases:
        values=[str(case[k])+'u' for k in ('syn_open_count','src_count','dst_count','dst_port_count')]
        scores=case['expected_scores'] or [0,0,0];label=case['expected_class_id'] if case['valid_window'] else 255
        c.append(' {"'+case['case']+'", '+str(case['packet_count'])+'u, UINT64_C('+str(case['ip_byte_sum'])+'), '+', '.join(values)+
                 f', UINT32_C(0x{case["feat_lo"]:08x}), UINT16_C(0x{case["feat_hi"]:04x}), '+
                 '{'+', '.join(map(str,scores))+'}, '+str(label)+', '+str(int(case['valid_window']))+'},')
    c+=['};','#define AI_V5_CHECK_VECTOR_COUNT (sizeof(ai_v5_check_vectors)/sizeof(ai_v5_check_vectors[0]))','#endif','']
    (stage/'ai_v5_handoff_vectors.h').write_text('\n'.join(c))
    valid=[case['q'] for case in cases if case['valid_window']]
    write_vectors(valid,model,stage/'integration_vectors.txt')
    return len(cases)


def overview(stage,report):
    content='<!doctype html><html lang="vi"><meta charset="utf-8"><title>V5: chuẩn bị ghép nối</title><style>body{font:18px system-ui;max-width:1120px;margin:32px auto;line-height:1.6}table{border-collapse:collapse}td,th{border:1px solid #ccd;padding:10px}code{font-size:15px}.note{background:#fff0cc;padding:14px}</style>'
    content+='<h1>V5 đã train — bàn giao để thử ghép</h1><p class="note">Đã kiểm model, cache và vector đối chiếu bằng phần mềm. Chưa xác minh top/CPU/feat_core mới nhất, synthesis V5 và thử nghiệm trên bo. Không gọi đây là đã hoàn thiện firewall.</p>'
    content+='<p>Dùng đúng dữ liệu học đã tạo: 28 PCAP Normal IoT-23, SYN flood capture 34, vertical scan Chris Sanders và các biến thể timestamp của cùng scan. Không thêm lab MQTT vào dữ liệu học. Không train lại hoặc đổi trọng số ở bước này.</p>'
    content+='<p>Model SHA256: <code>'+MODEL_SHA+'</code>. Đã chạy lại model trên toàn bộ cache gốc: Normal 39.253.935 cửa sổ, SYN 21, scan 4; còn đúng 12 lỗi Normal cũ.</p>'
    inventory=report['local_sources']
    if inventory['checked']:
        content+='<p>Đã tìm thấy đủ 30 PCAP được chọn trong thư mục dữ liệu trên máy này. '+('Checksum từng PCAP đã đối chiếu.' if inventory['pcap_checksums_recomputed'] else 'Chưa đọc lại checksum PCAP; danh tính cache học đã được kiểm.')+'</p>'
    else:content+='<p>Chưa kiểm vị trí bộ PCAP trên máy này. Có thể chạy lại công cụ với --data để kiểm thư mục dữ liệu; model và cache đã được xác minh.</p>'
    content+='<table><tr><th>Bàn giao</th><th>Tệp và việc cần làm</th></tr>'
    content+='<tr><td>Người 1: CPU/top</td><td>firmware/ai_quant_v5.h, ai_v5_integration.h và ai_v5_handoff_vectors.h. Chạy các vector qua driver thật, đối chiếu ba scores int16 có dấu và class_id. Không suy ra địa chỉ thanh ghi từ tên trong tài liệu.</td></tr>'
    content+='<tr><td>Người 3: bộ trích đặc trưng</td><td>FEATURES_V5.md và INTEGRATION_V5.csv: khớp chiều ingress, đích /32, cửa sổ 1 giây, sáu bộ đếm, phép chia và cách đóng gói. Giữ cửa sổ 1–7 gói dù q0=0.</td></tr>'
    content+='<tr><td>Bạn: phần AI</td><td>Giữ model và checksum, chạy mô phỏng, xem lỗi phân loại và hỗ trợ đối chiếu số học. Không sửa nhãn hoặc học các vector kiểm tra để đạt điểm.</td></tr></table>'
    content+='<p><a href="LO_TRINH_V5.md">Hướng dẫn từ train đến ghép</a> | <a href="INTEGRATION_V5.json">Vector raw → q → scores</a> | <a href="READY_REPORT.json">Trạng thái kiểm tra</a> | <a href="gowin/ai_core_v5.gprj">Project core Gowin V5</a></p>'
    content+='<p>12 lỗi theo nhãn gốc vẫn còn; 11 cửa sổ Normal có q giống các cửa sổ SYN. Chạy train nhiều lần trên cùng dữ liệu không tạo thêm thông tin để phân biệt chúng. Điểm số học đúng không đồng nghĩa phân loại lưu lượng mới luôn đúng. Lab MQTT dùng để đo kết quả sau ghép; kết quả đó chưa có ở đây.</p></html>'
    (stage/'MO_BAN_GIAO_V5.html').write_text(content,encoding='utf-8')


def prepare(release,output,data=None,verify_pcaps=False):
    release,output=[Path(p).expanduser().resolve() for p in (release,output)]
    candidate=release/'candidate_v5';state=json.loads((release/'V5_STATE.json').read_text())
    complete=json.loads((candidate/'CANDIDATE_COMPLETE.json').read_text());verify_files(candidate,complete['files'])
    model,vector_count=validate(candidate/'model')
    if sha(candidate/'model/model.json')!=MODEL_SHA:raise ValueError('This handoff is pinned to the reviewed V5 weights')
    old,metrics,cache,info=read_base(release/'V4_GOC')
    if sha(cache)!=state['base']['cache_sha256'] or info['model_sha256']!=state['base']['model_sha256']:
        raise ValueError('Original cache does not match this V5 release')
    source_counts=[sum(s['label']==i for s in info['original_sources']) for i in range(3)]
    if source_counts!=[28,1,1] or info['original_sources']!=state['base']['original_sources']:
        raise ValueError('Source inventory differs from the reviewed three groups')
    before,unique,windows=evaluate_cache(cache,old);after,_,_=evaluate_cache(cache,model)
    if before['confusion_matrix']!=state['comparison']['original_base_v4']['confusion_matrix'] or after['confusion_matrix']!=state['comparison']['original_base_v5']['confusion_matrix']:
        raise ValueError('Cache metrics do not reproduce the released V4/V5 comparison')
    inventory=source_inventory(state,data,verify_pcaps)
    if output.exists():raise ValueError('Output exists; preserve it or choose another --output folder')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.v5_handoff_',dir=output.parent) as temp:
        stage=Path(temp)/'handoff';stage.mkdir()
        shutil.copytree(candidate/'model',stage/'model');shutil.copytree(candidate/'gowin',stage/'gowin')
        for filename in ('ai_quant_v5.h','ai_v5_integration.h'):
            (stage/'firmware').mkdir(exist_ok=True);shutil.copy2(candidate/'gowin/firmware'/filename,stage/'firmware'/filename)
        count=write_handoff_vectors(stage,model)
        for name in ('FEATURES_V5.md','LO_TRINH_V5.md'):
            shutil.copy2(KIT/'handoff'/name,stage/name)
        report=dict(kind='unchanged_v5_software_handoff',model_sha256=MODEL_SHA,model_retrained=False,
                    original_windows_by_class=windows,original_quantized_patterns_by_class=unique,
                    original_cache_verified=True,all_original_labels_kept=True,source_inventory_counts=source_counts,
                    original_base_integer_metrics=after,local_sources=inventory,numeric_reference_cases=count,
                    core_reference_vectors_validated=vector_count,previous_rtl=complete['verification'],
                    independent_traffic_test_complete=False,group_hardware_interface_verified=False,
                    v5_gowin_synthesis_verified=False,board_measurements_complete=False,automatic_blocking_ready=False,
                    software_handoff_prepared=True)
        (stage/'READY_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
        overview(stage,report)
        hashes={str(p.relative_to(stage)):sha(p) for p in stage.rglob('*') if p.is_file()}
        (stage/'HANDOFF_COMPLETE.json').write_text(json.dumps(dict(model_sha256=MODEL_SHA,files=hashes),indent=2)+'\n')
        stage.rename(output)
    print('V5 model/cache verified; no training performed. Open:',output/'MO_BAN_GIAO_V5.html')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release',default=str(KIT/'examples/user_v5_from_full_cache'))
    parser.add_argument('--output',default=str(Path.home()/'iot23_v5_ghep_01'))
    parser.add_argument('--data');parser.add_argument('--verify-pcaps',action='store_true')
    args=parser.parse_args()
    try:prepare(args.release,args.output,args.data,args.verify_pcaps)
    except (ValueError,OSError,KeyError) as error:parser.exit(1,'ERROR: '+str(error)+'\n')
