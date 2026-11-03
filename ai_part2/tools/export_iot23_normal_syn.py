"""Export original IoT-23 Normal and reviewed SYN-flood CSV + PCAP files.

Two streaming archive passes; original data and AI model are never modified.
CSV rows are native flows. PCAP records are byte-preserved packets.
"""
import argparse
from collections import Counter
import csv
import hashlib
import html
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import time

from iot23_label_index import Builder, Index
from iot23_pcap_filter import Compressed, filter_pcap

MIB = 1024*1024
GIB = 1024*MIB
DETAILS = {'det_label','detailed-label','detailedlabel','detailed_label'}
SYN_REVIEW = dict(
    capture_id='CTU-IoT-Malware-Capture-34-1',
    reference_log_sha256='d69e49b2aae8c1bd33286936531658202dec47d989f0439bad3f8be180467a6e',
    selected_flow_signature='adb44657c824541c0297c14db2f7d1992e84fe8449f95984dc5db545f2b2cbfb',
    pcap_sha256='92ec7e2f6658ee4b007d0b816986c46cc0338bc5e2bec6ceaaca566c695e4699',
    pcap_name='2018-12-21-15-50-14-192.168.1.195.pcap',
    source_ip='192.168.1.195', target_ip='71.61.66.148', target_port=80,
    start=1545475806.96806, end=1545475828.998385,
    flow_rows=133, packet_metadata_sum=40568)
BENIGN_SCENARIOS = {'CTU-Honeypot-Capture-4-1', 'CTU-Honeypot-Capture-5-1', 'CTU-Honeypot-Capture-7-1'}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic_json(path, value):
    temp = path.with_name(path.name+'.part')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def benign_count(spec):
    return sum(n for label,n in spec['native_labels'].items() if label.split('/',1)[0].casefold() == 'benign')


def reviewed_syn(row, detail, identity):
    if identity != SYN_REVIEW['capture_id'] or row['label'].casefold() != 'malicious' or row[detail] != 'DDoS' or row['proto'] != 'tcp':
        return False
    if row['id.orig_h'] != SYN_REVIEW['source_ip'] or row['id.resp_h'] != SYN_REVIEW['target_ip'] or int(row['id.resp_p']) != SYN_REVIEW['target_port'] or row.get('history') != 'S':
        return False
    start = float(row['ts'])
    duration = 0. if row['duration'] in ('-', '(empty)') else float(row['duration'])
    return (math.isfinite(start) and math.isfinite(duration) and duration >= 0 and
            SYN_REVIEW['start']-.001 <= start <= start+duration <= SYN_REVIEW['end']+.001)


def syn_signature(row):
    return [float(row['ts']).hex(), float(0 if row['duration'] in ('-', '(empty)') else row['duration']).hex(),
            row['id.orig_h'], int(row['id.orig_p']), row['id.resp_h'], int(row['id.resp_p']),
            int(row['orig_pkts']), int(row['resp_pkts']), row['history']]


def export_log(stream, spec, output, builder=None):
    fields = None; detail = None; counts = Counter(); digest = hashlib.sha256()
    size = 0; writers = {}; paths = {}; signatures = []; tick = time.monotonic()
    identity = spec['capture_id']; stem = identity.replace('/', '__')
    try:
        for line in stream:
            size += len(line); digest.update(line)
            if line.startswith(b'#fields'):
                if fields is not None:
                    raise ValueError('Multiple native log headers')
                fields = line.decode().split()[1:]
                aliases = DETAILS.intersection(fields)
                required = {'ts','duration','id.orig_h','id.orig_p','id.resp_h','id.resp_p','proto','label'}
                if len(set(fields)) != len(fields) or not required <= set(fields) or len(aliases) != 1 or 'loai_da_loc' in fields:
                    raise ValueError('Unsupported native log header')
                detail = next(iter(aliases)); continue
            if line.startswith(b'#') or not line.strip():
                continue
            values = line.decode().split()
            if fields is None or len(values) != len(fields):
                raise ValueError('Native log row/header mismatch')
            row = dict(zip(fields, values)); counts['source_flow_rows'] += 1
            if builder is not None:
                builder.observe(row)
            label = None
            if row['label'].casefold() == 'benign':
                label = 'binh_thuong'
            elif reviewed_syn(row, detail, identity):
                label = 'syn_flood'; signatures.append(syn_signature(row))
            if label:
                if label not in writers:
                    path = output/label/'csv'/(stem+'.csv.gz.part')
                    compressed = Compressed(path)
                    text = io.TextIOWrapper(compressed.gz, encoding='utf-8', newline='')
                    writer = csv.writer(text); writer.writerow(fields+['loai_da_loc'])
                    writers[label] = (compressed, text, writer); paths[label] = path
                writers[label][2].writerow(values+[label]); counts[label] += 1
            if time.monotonic()-tick >= 10:
                if shutil.disk_usage(output).free < 512*MIB:
                    raise ValueError('Low disk space; completed sources can be resumed')
                print(f'CSV {identity}: {size/1e6:.0f}/{spec["source_bytes"]/1e6:.0f} MB; Normal {counts["binh_thuong"]:,}; SYN {counts["syn_flood"]:,}', flush=True)
                tick = time.monotonic()
        if fields is None or size != spec['source_bytes'] or digest.hexdigest() != spec['source_sha256']:
            raise ValueError('Full native log differs from saved screening: '+identity)
        if counts['source_flow_rows'] != spec['connection_records'] or counts['binh_thuong'] != benign_count(spec):
            raise ValueError('Native/Benign counts differ from saved screening')
        if identity == SYN_REVIEW['capture_id']:
            signature = hashlib.sha256(json.dumps(sorted(signatures), separators=(',',':')).encode()).hexdigest()
            if signature != SYN_REVIEW['selected_flow_signature']:
                raise ValueError('Reviewed SYN flow contents changed; no SYN CSV published')
    finally:
        for compressed, text, _ in writers.values():
            try:
                text.close()
            finally:
                compressed.close()
    files = {label:dict(path=str(path.with_suffix('').relative_to(output)), sha256=sha(path), rows=counts[label])
             for label,path in paths.items()}
    return dict(capture_id=identity, source_sha256=digest.hexdigest(), source_flow_rows=counts['source_flow_rows'],
                normal_rows=counts['binh_thuong'], reviewed_syn_flood_rows=counts['syn_flood'],
                excluded_rows=counts['source_flow_rows']-counts['binh_thuong']-counts['syn_flood'], files=files)


class Progress:
    def __init__(self, source, total, phase):
        self.source, self.total, self.phase = source, total, phase
        self.hash = hashlib.sha256(); self.tick = time.monotonic()
    def read(self, size=-1):
        data = self.source.read(size); self.hash.update(data)
        if time.monotonic()-self.tick >= 10:
            print(f'Archive pass {self.phase}/2: {self.source.tell()/1e9:.2f}/{self.total/1e9:.2f} GB', flush=True)
            self.tick = time.monotonic()
        return data


def safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name:
        raise ValueError('Unsafe selected member path')
    return str(path)


def load_inputs(screen_path, inventory):
    parent = json.loads(screen_path.read_text())
    if parent.get('status') != 'complete' or parent.get('kind') != 'native_source_screening_not_training_dataset':
        raise ValueError('Need the completed iot23_sang_loc_01/BAO_CAO_LOC.json')
    if parent.get('inventory_sha256') != sha(inventory):
        raise ValueError('Inventory differs from saved screening')
    logs = {}; by_scenario = {}
    for spec in parent['sources']:
        member = safe_name(spec['archive_member'])
        identity = spec['capture_id']
        if not re.fullmatch(r'CTU-(?:IoT-Malware|Honeypot)-Capture-\d+-1(?:/[A-Za-z0-9_-]+)*', identity):
            raise ValueError('Unexpected source identity')
        scenario = identity.split('/')[0]
        if member in logs or scenario in by_scenario:
            raise ValueError('Multiple logs in one scenario require an explicit association rule')
        if scenario not in PurePosixPath(member).parts:
            raise ValueError('Source identity/member mismatch')
        logs[member] = spec; by_scenario[scenario] = spec
    pcaps = {}; inventory_logs = set()
    with inventory.open(newline='', encoding='utf-8-sig') as stream:
        for row in csv.DictReader(stream):
            name = PurePosixPath(row['archive_path'])
            if name.name == 'conn.log.labeled':
                member = safe_name(str(name)); inventory_logs.add(member)
                if member not in logs or row['type'] != 'file' or int(row['bytes']) != logs[member]['source_bytes']:
                    raise ValueError('Screened log differs from inventory')
            if name.suffix.lower() != '.pcap':
                continue
            member = safe_name(str(name))
            scenarios = set(name.parts).intersection(by_scenario)
            if len(scenarios) != 1 or row['type'] != 'file' or member in pcaps:
                raise ValueError('Ambiguous/nonregular/duplicate PCAP inventory member')
            scenario = next(iter(scenarios)); spec = by_scenario[scenario]
            remainder = name.parts[name.parts.index(scenario)+1:]
            stem = scenario+'__'+'__'.join(remainder)
            stem = stem[:-5]  # Drop only the final .pcap.
            pcaps[member] = dict(bytes=int(row['bytes']), capture_id=spec['capture_id'], stem=stem,
                                 pure_normal=scenario in BENIGN_SCENARIOS and benign_count(spec) == spec['connection_records'],
                                 reviewed_syn=spec['capture_id'] == SYN_REVIEW['capture_id'] and name.name == SYN_REVIEW['pcap_name'])
    if inventory_logs != set(logs):
        raise ValueError('Screening does not cover every inventoried native log')
    if not pcaps:
        raise ValueError('No PCAPs in inventory')
    return parent, logs, pcaps


def publish(output, result):
    # The manifest is saved before renaming .part files, allowing recovery even
    # if interrupted between two class outputs from the same source.
    for item in result['files'].values():
        final = output/item['path']; part = Path(str(final)+'.part')
        if final.is_file() and sha(final) == item['sha256']:
            continue
        if not part.is_file() or sha(part) != item['sha256']:
            raise ValueError('Completed output missing/changed: '+str(final))
        part.replace(final)


def disposition(result):
    labels = set(result['files'])
    return 'both' if len(labels) == 2 else next(iter(labels), 'skipped_no_matching_data')


def check_index(output, result):
    for relative, checksum in result.get('index_sha256', {}).items():
        path = output/relative
        if not path.is_file() or sha(path) != checksum:
            raise ValueError('Resume index missing/changed: '+str(path))


def write_reports(output, report):
    atomic_json(output/'BAO_CAO_XUAT.json', report)
    with (output/'DANH_SACH_TEP.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['capture_id','format','class','flow_rows','packets','file','sha256'])
        for kind, format_name in [('sources','CSV'),('pcaps','PCAP')]:
            for result in report[kind].values():
                for label, item in result['files'].items():
                    writer.writerow([result['capture_id'],format_name,label,item.get('rows',''),item.get('packets',''),item['path'],item['sha256']])
    page = '<!doctype html><html lang="vi"><meta charset="utf-8"><title>IoT-23 đã lọc</title><style>body{font:17px system-ui;max-width:1200px;margin:30px auto;line-height:1.6}table{border-collapse:collapse}td,th{border:1px solid #ccd;padding:7px}</style>'
    page += '<h1>'+('Đã xuất CSV và PCAP' if report['status'] == 'complete' else 'Xuất dữ liệu chưa hoàn tất')+'</h1>'
    if report.get('error'):
        page += '<p>'+html.escape(report['error'])+'</p>'
    page += '<p>Bình thường: nhãn Benign gốc. SYN flood: đoạn capture 34 đã kiểm chứng; không đổi mọi DDoS hoặc SYN đơn lẻ thành SYN flood. Nguồn có loại nào thì xuất loại đó, không có thì bỏ qua. Không tạo tệp rỗng.</p>'
    page += '<p>CSV nén giữ các cột flow gốc và thêm loai_da_loc. PCAP nén giữ nguyên byte gói tin và header gốc. Số flow và số gói là hai đơn vị khác nhau; CSV này không phải bộ sáu đặc trưng mỗi giây.</p>'
    page += '<p>Trong capture malware, PCAP bình thường chỉ giữ gói IPv4 TCP/UDP/ICMP khớp tuple hai chiều và thời gian của Benign, dung sai 1 ms; loại các khoảng nhãn xung đột. Gói không khớp, IPv6, phân mảnh hoặc lỗi không được tự gán bình thường. Các PCAP thuộc ba kịch bản honeypot bình thường được giữ toàn bộ. Tệp phụ có thể trùng gói với tệp chính; không cộng chúng thành các mẫu độc lập.</p>'
    page += '<table><tr><th>Nguồn</th><th>Dạng</th><th>Loại</th><th>Số dòng/gói</th><th>Tệp</th></tr>'
    for kind, format_name in [('sources','CSV'),('pcaps','PCAP')]:
        for result in report[kind].values():
            for label, item in result['files'].items():
                page += '<tr><td>'+html.escape(result['capture_id'])+'</td><td>'+format_name+'</td><td>'+label+'</td><td>'+str(item.get('rows',item.get('packets')))+'</td><td><a href="'+html.escape(item['path'],quote=True)+'">'+html.escape(Path(item['path']).name)+'</a></td></tr>'
    page += '</table><p><a href="DANH_SACH_TEP.csv">Danh sách tệp</a> | <a href="BAO_CAO_XUAT.json">Báo cáo và phần bị loại</a></p>'
    (output/'MO_DU_LIEU_DA_LOC.html').write_text(page, encoding='utf-8')


def run(archive, screen_output, inventory, output, resume=False, minimum_free_gib=24):
    archive, screen_output, inventory, output = [Path(p).expanduser().resolve() for p in (archive,screen_output,inventory,output)]
    parent_path = screen_output/'BAO_CAO_LOC.json'
    parent, logs, pcaps = load_inputs(parent_path, inventory)
    if not archive.is_file():
        raise ValueError('Archive not found: '+str(archive))
    code = {name:sha(Path(__file__).with_name(name)) for name in ('export_iot23_normal_syn.py','iot23_label_index.py','iot23_pcap_filter.py')}
    fingerprint = dict(screen_sha256=sha(parent_path), inventory_sha256=sha(inventory),
                       archive_sha256=parent['archive_sha256'], archive_bytes=archive.stat().st_size, code=code)
    state = output/'BAO_CAO_XUAT.json'
    if output.exists():
        if not resume or not state.is_file():
            raise ValueError('Output exists; use --resume for this job or choose a new folder')
        report = json.loads(state.read_text())
        if report.get('fingerprint') != fingerprint:
            raise ValueError('Resume inputs/tool differ from the saved job')
        for result in report['sources'].values():
            check_index(output, result); publish(output, result)
        for result in report['pcaps'].values():
            publish(output, result)
        if report['status'] == 'complete':
            print('Already complete:', output, flush=True)
            return report
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(output.parent).free < minimum_free_gib*GIB:
            raise ValueError(f'Need {minimum_free_gib:g} GiB free on the Ubuntu output drive')
        output.mkdir()
        report = dict(status='in_progress', kind='filtered_normal_syn_csv_and_pcap', fingerprint=fingerprint,
                      sources={}, pcaps={}, passes_complete=[], syn_review=SYN_REVIEW,
                      original_labels_preserved=True, native_flow_csv_not_six_features=True,
                      source_pcap_records_byte_preserved=True, model_changed=False)
        write_reports(output, report)
    report.update(status='in_progress'); report.pop('error',None)
    try:
        for phase in (1,2):
            if phase in report['passes_complete']:
                continue
            wanted = logs if phase == 1 else pcaps
            results = report['sources'] if phase == 1 else report['pcaps']
            found = set()
            print(f'PASS {phase}/2: '+('exporting flow CSV and indexing native labels' if phase == 1 else 'exporting packet PCAP files'), flush=True)
            with archive.open('rb') as raw:
                meter = Progress(raw, archive.stat().st_size, phase)
                with tarfile.open(fileobj=meter, mode='r|gz') as tar:
                    for member in tar:
                        name = str(PurePosixPath(member.name))
                        if name not in wanted:
                            continue
                        spec = wanted[name]
                        expected_size = spec['source_bytes'] if phase == 1 else spec['bytes']
                        if name in found or not member.isfile() or member.size != expected_size:
                            raise ValueError('Duplicate, nonregular or changed selected source: '+name)
                        found.add(name)
                        if name in results:
                            print('Reusing completed:', name, flush=True)
                            continue
                        with tar.extractfile(member) as source:
                            if phase == 1:
                                folder = output/'.tam'/spec['capture_id'].replace('/','__')
                                scenario = spec['capture_id'].split('/')[0]
                                pure = scenario in BENIGN_SCENARIOS and benign_count(spec) == spec['connection_records']
                                builder = None if pure else Builder(folder)
                                try:
                                    result = export_log(source, spec, output, builder)
                                    if builder is not None:
                                        result['index_counts'] = builder.finish()
                                        result['index_folder'] = str(folder.relative_to(output))
                                        result['index_sha256'] = {str(p.relative_to(output)):sha(p) for p in (folder/'keys.bin',folder/'hashes.bin',folder/'spans.bin')}
                                finally:
                                    if builder is not None:
                                        builder.close()
                            else:
                                log_result = next(r for r in report['sources'].values() if r['capture_id'] == spec['capture_id'])
                                index = None if spec['pure_normal'] else Index(output/log_result['index_folder'])
                                try:
                                    result = filter_pcap(source, spec['bytes'], index, output, spec['stem'], spec['pure_normal'], SYN_REVIEW if spec['reviewed_syn'] else None)
                                finally:
                                    del index
                                result.update(capture_id=spec['capture_id'], archive_member=name)
                        result['disposition'] = disposition(result)
                        results[name] = result
                        atomic_json(state, report)
                        publish(output, result)
                        write_reports(output, report)
                        print('EXPORTED:', spec['capture_id'], 'files:', len(result['files']), flush=True)
                    if found != set(wanted):
                        raise ValueError('Selected inventory members missing from archive')
                while meter.read(MIB):
                    pass
                if meter.hash.hexdigest() != parent['archive_sha256']:
                    raise ValueError('Full archive SHA differs from saved screening; outputs need review')
            report['passes_complete'].append(phase)
            write_reports(output, report)
        # A successful job must actually contain both requested formats.
        report.update(status='complete',
                      normal_flow_rows=sum(r['normal_rows'] for r in report['sources'].values()),
                      syn_flood_flow_rows=sum(r['reviewed_syn_flood_rows'] for r in report['sources'].values()),
                      normal_pcap_packets=sum(r['normal_packets'] for r in report['pcaps'].values()),
                      syn_flood_pcap_packets=sum(r['reviewed_syn_flood_packets'] for r in report['pcaps'].values()))
    except BaseException as error:
        report.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed', error=str(error) or 'Interrupted; run again with --resume')
        raise
    finally:
        write_reports(output, report)
    print('DONE. Open:', output/'MO_DU_LIEU_DA_LOC.html', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--screen-output', required=True)
    parser.add_argument('--inventory', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    try:
        run(args.archive, args.screen_output, args.inventory, args.output, args.resume)
    except (ValueError,OSError,tarfile.TarError,EOFError,KeyError,UnicodeError) as error:
        parser.exit(1, 'ERROR: '+str(error)+'\n')
