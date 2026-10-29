"""Package a consistent frozen v2, its exported core and its existing holdout result.

Run on the student's Ubuntu after the v2 export. Never trains or collects traffic.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from zipfile import ZIP_DEFLATED, ZipFile

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))
from part2.development import evaluate_v2, verify_freeze
from part2.features import NAMES, quantize
from part2.integer import infer
from tools.prepare_gowin import firmware_header, standalone, validate


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def integration_examples(model):
    examples = []
    # Counter inputs to ai_v2_pack; not ground-truth network labels.
    for counters in ([0,0,0,0,0,0], [16,2176,2,1,1,1], [16,1040,9,2,1,2],
                     [13,754,6,2,1,6], [28,1344,21,2,1,1], [2000,80000,1992,2,1,1],
                     [800,32800,790,2,1,512]):
        packets, byte_sum, syn, src, dst, ports = counters
        raw = [packets, byte_sum//packets, 127*syn//packets, src, dst, ports] if packets else [0]*6
        q = quantize([raw], model['divisors'])[0]
        scores = infer([q], model)[0]
        examples.append(dict(counter_inputs=counters, raw=raw, quantized=q.tolist(),
                             feat_hex=f'{sum(int(v)<<(8*i) for i,v in enumerate(q)):012x}',
                             scores=scores.tolist(), class_id=int(scores.argmax())))
    return dict(purpose='Arithmetic integration examples, NOT network ground truth',
                counter_input_order=['packets','ip_byte_sum','syn_open','src_count','dst_count','port_count'],
                raw_feature_order=NAMES, examples=examples)


def package(model_dir, project, dataset, evaluation, collection, output, kit=KIT):
    model_dir, project, evaluation, output, kit = map(Path, (model_dir, project, evaluation, output, kit))
    if output.exists():
        raise ValueError('Output exists; preserve the previous handoff and choose a new filename')
    freeze = verify_freeze(model_dir)
    model, count = validate(model_dir)
    if model.get('model_version') != 'v2' or model['divisors'] != [8,2,1,1,1,1]:
        raise ValueError('This handoff requires the reviewed v2 input contract')
    manifest = json.loads((project / 'EXPORT_MANIFEST.json').read_text())
    if manifest['model_sha256'] != freeze['model_sha256'] or manifest.get('model_version') != 'v2':
        raise ValueError('Gowin export belongs to a different model/version')
    for name in ('model.json', 'metrics.json'):
        if digest(project / 'reference' / name) != digest(model_dir / name):
            raise ValueError('Gowin reference differs from frozen model: ' + name)
    rtl = project / 'src/ai_core_model_v2.v'
    expected_rtl = standalone((kit / 'rtl/ai_core.v').read_text(), model)
    if rtl.read_text() != expected_rtl or digest(rtl) != manifest['rtl_sha256']:
        raise ValueError('Exported Verilog differs from the frozen weights/source')
    if (project / 'firmware/ai_quant_v2.h').read_text() != firmware_header(model):
        raise ValueError('Firmware quantization differs from model')
    if (project / 'verification/vectors.txt').read_bytes() != (model_dir / 'vectors.txt').read_bytes():
        raise ValueError('Project uses different verification vectors')
    report, _ = evaluate_v2(dataset, model_dir, collection)
    stored = json.loads((evaluation / 'metrics.json').read_text())
    if report != stored:
        raise ValueError('Stored holdout metrics differ from frozen reevaluation; preserve and inspect both')
    log = project / 'verification/build/result.log'
    text = log.read_text() if log.is_file() else ''
    if not re.search(rf'^PASS vectors={count} cycles_min=84 cycles_max=84\b', text, re.M):
        raise ValueError('Missing matching standalone RTL simulation log; run verification/run_sim.sh first')
    files = {}
    def add(path, name):
        if path.is_symlink():
            raise ValueError('Refusing symlink in handoff: ' + str(path))
        files[name] = path.read_bytes()
    for path in sorted(project.rglob('*')):
        rel = path.relative_to(project)
        if path.is_file() and not any(p in ('build','__pycache__') for p in rel.parts):
            add(path, str(Path('gowin_ai_v2') / rel))
    add(log, 'evidence/rtl_simulation.log')
    for name in ('model.json','metrics.json','FREEZE.json','w1.hex','w2.hex','b1.hex','b2.hex','quant_params.vh','vectors.txt'):
        add(model_dir / name, 'model/' + name)
    for name in ('metrics.json','per_capture.csv','report.html'):
        add(evaluation / name, 'holdout/' + name)
    add(Path(dataset), 'holdout/features.csv')
    add(Path(dataset).with_suffix('.meta.json'), 'holdout/features.meta.json')
    add(Path(collection), 'holdout/COLLECTION.json')
    for name in ('FEATURES_V0.md','AI_INTERFACE.md'):
        add(kit / 'spec' / name, 'spec/' + name)
    files['INTEGRATION_VECTORS.json'] = json.dumps(integration_examples(model), indent=2).encode()
    # User-supplied screenshots, not vendor reports cryptographically tied to this export.
    evidence = dict(source='user_reported_screenshots_2026-10-29',
                    screenshot_to_project_hash_binding_verified=False,
                    logic=445, logic_reported_percent=6, registers=246, registers_reported_percent=4,
                    latches=0, bsram=0, dsp=1, io_ports_standalone=103,
                    synthesis_clock_mhz=50, synthesis_estimated_fmax_mhz=56.4,
                    routed_timing_verified=False, board_clock_measured=False,
                    packet_blocking_verified=False)
    files['evidence/GOWIN_USER_REPORTED.json'] = json.dumps(evidence, indent=2).encode()
    m = report['ai']; baseline = report['baseline']
    document = f'''# Bàn giao AI v2 cho người 1 và 3

Model SHA256: {freeze['model_sha256']}

Kiến trúc: 6–8–3. Divisors: {model['divisors']}. shift1={model['shift1']}, shift2={model['shift2']}.
hidden_scale={model['hidden_scale']}; score_scale={model['score_scale']}. Dùng đúng một module ai_core.

## Kết quả đã kiểm tra khi đóng gói

Holdout mới sau freeze: {m['windows']} cửa sổ, {report['capture_count']} capture, AI accuracy={m['accuracy']:.2%}, FPR={m['false_positive_rate']:.2%}, macro-F1={m['macro_f1']:.4f}.
Baseline accuracy={baseline['accuracy']:.2%}; kết quả ngang nhau không chứng minh AI tốt hơn baseline.
RTL số học khớp {count} vector, 84 chu kỳ. Không có phép đo chặn Ethernet hoặc thời gian thực trên bo.

## Người 1: CPU và driver

Thêm gowin_ai_v2/src/ai_core_model_v2.v và gowin_ai_v2/firmware/ai_quant_v2.h của CÙNG project.
Verilog này đã nhúng ROM, không cần readmemh/file HEX lúc chạy; HEX trong model/ dùng đối chiếu, không thêm generic ai_core lần nữa.
Hàm ai_v2_pack(packets, ip_byte_sum, syn_open, src_count, dst_count, port_count) trả uint64 chứa 48 bit feat.
feat[7:0]=q0, ..., feat[47:40]=q5. Ghi phần thấp/cao theo driver thực của nhóm, không tạo địa chỉ thanh ghi mới theo tài liệu này.
q=clamp(raw//divisor,0,127). Empty window cả sáu số 0. Kiểm tra helper uint64 chia số nguyên được toolchain RISC-V liên kết đầy đủ.

clk/rst_n/start/feat/busy/done/class_id/scores theo spec/AI_INTERFACE.md.
Reset đồng bộ mức thấp, bỏ phép tính đang chạy. start chỉ nhận khi busy=0, chốt feat tại cạnh nhận; start lúc busy bị bỏ qua.
done xung một chu kỳ. Score0/1/2 signed int16 nằm lần lượt ở bits 15:0 / 31:16 / 47:32. Điểm không phải xác suất.
Class 0 bình thường; 1 SYN; 2 vertical scan. Hòa điểm chọn lớp nhỏ hơn. Dùng INTEGRATION_VECTORS.json để kiểm cả score và class.

## Người 3: thống kê đầu vào

Giữ ngữ nghĩa sáu raw features trong spec/FEATURES_V0.md: ingress IPv4 tới đích bảo vệ, cửa sổ 1 giây, distinct exact.
Thứ tự: packets; floor(ip_byte_sum/packets); floor(127*syn_open/packets); số IP nguồn; số IP đích; số cổng đích TCP/UDP.
SYN mở kết nối là SYN=1, ACK=0; mẫu số gồm toàn bộ ingress IPv4 hợp lệ, không chỉ TCP.
Phần lượng tử hóa v2 dùng DIVISORS CỐ ĐỊNH ở trên; mục divisor học từ train trong spec cũ mô tả v1, không áp dụng thay cho model v2.
Nếu RTL đã lượng tử thì cập nhật divisor đồng bộ; không chia hai lần. Nếu dùng bitmap thay exact, cần đối chiếu lại Python và đánh giá lại.
Căn mốc cửa sổ/reset khi so PCAP. Đếm overflow/CRC lỗi và có chính sách gói không hỗ trợ rõ ràng.

## Kiểm ghép

1. CPU nạp các vector feat, đối chiếu score/class và số chu kỳ, rồi kiểm reset/start khi busy.
2. Chạy cùng luồng header có mốc cửa sổ xác định: so raw -> quantized -> packed giữa Python và RTL.
3. Xác minh bridge chuyển hai chiều, ARP, lọc luật cố định và counters trước khi dùng AI ra quyết định.
4. Gắn model vào chính sách chọn IP/chặn: kiểm nguồn bình thường vẫn qua, nguồn thử nghiệm bị chặn, số gói lọt và chặn nhầm.
5. Kiểm timing sau ghép và routing, xác nhận clock thật, nạp bo rồi đo từ lúc bắt đầu tấn công tới phát hiện/chặn và tác dụng lên MQTT.

AI chỉ phân loại cửa sổ; không giữ IP và không tự drop gói. Chọn IP nghi vấn, whitelist/TTL, xác nhận nhiều cửa sổ thuộc CPU/bộ lọc.
84 chu kỳ chỉ là suy luận lõi, không gồm cửa sổ 1 giây, truyền bus và chính sách xác nhận.
103 I/O trong tổng hợp core là tín hiệu giao diện; khi ghép là dây nội bộ, không phải 103 chân kit.
Gowin screenshots: logic445, FF246, DSP1, BSRAM0, latch0; synthesis Fmax ước tính56.4MHz ở clock50MHz.
Project SDC mục tiêu27MHz; clock/constraints thực khi ghép phải chốt. Chưa có routed timing hay đo bo.
Ở 27MHz, 84 chu kỳ tương ứng khoảng3.11us NẾU clock/timing thực đạt; không gọi đó là thời gian phát hiện/chặn toàn hệ thống.
Kết quả holdout giới hạn trong các phiên lab; chưa xác minh IoT-23, mạng khác hoặc mọi tình huống retry/quét cực chậm.
'''
    files['HANDOFF_V2_VI.md'] = document.encode()
    checksums = {name: hashlib.sha256(content).hexdigest() for name,content in files.items()}
    files['FILE_SHA256.json'] = json.dumps(checksums, indent=2).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            archive.writestr('ai_v2_handoff/' + name, content)
    with ZipFile(output) as archive:
        if archive.testzip():
            raise ValueError('ZIP CRC check failed')
    return dict(output=str(output), files=len(files), model_sha256=freeze['model_sha256'],
                holdout_accuracy=m['accuracy'], baseline_accuracy=baseline['accuracy'],
                hardware_blocking_verified=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir', default='build/lab_model_v2')
    p.add_argument('--project', default='build/gowin_ai_v2')
    p.add_argument('--dataset', default='build/v2_holdout_v2test01.csv')
    p.add_argument('--evaluation', default='build/v2_holdout_eval_v2test01')
    p.add_argument('--collection', default='data/v2_holdout/v2test01/COLLECTION.json')
    p.add_argument('--output', default='build/ban_giao_ai_v2.zip')
    a = p.parse_args()
    try:
        print(json.dumps(package(a.model_dir,a.project,a.dataset,a.evaluation,a.collection,a.output),indent=2))
    except (ValueError, OSError, KeyError) as e:
        p.error(str(e))
