"""Download a small, explicitly partial IoT-23 reading collection from its publisher.

Python standard library only. Does not train a model or replay any traffic.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
import lzma
from pathlib import Path
import urllib.request

BASE = 'https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/IndividualScenarios/'
OFFICIAL = 'https://www.stratosphereips.org/datasets-iot23'
SOURCES = [
    ('CTU-Honeypot-Capture-4-1', 61653, 'aebe40ea0e03b120265a5c7bc140dd9b0d3fe2fce65559e84776b7dd5360e71e'),
    ('CTU-Honeypot-Capture-5-1', 182147, 'f36db06e7d6ba7364e932a5b003f75835e004b320d70019e8a2f0ba8685d9262'),
    ('CTU-IoT-Malware-Capture-34-1', 2926718, 'd69e49b2aae8c1bd33286936531658202dec47d989f0439bad3f8be180467a6e'),
    ('CTU-IoT-Malware-Capture-44-1', 31179, '12cd99bcda78140dd5f31cf3d786642f150e42e0ebc3599190f35314e406f71f'),
    ('CTU-IoT-Malware-Capture-3-1', 24383537, '9851009bbca03e15089fa1a356dd4b5eee4a98161a51703626058a0b507f50d0'),
]
PCAP_NAME = '2018-10-25-14-06-32-192.168.1.132.pcap'
PCAP_XZ_BYTES = 376840
PCAP_XZ_SHA = 'bc5a57306d9a5f614b09d9c0976f007667fee5b6de3427fbab094fa3084b9b64'
PCAP_BYTES = 4594492
PCAP_SHA = '3fb775c0391b6ad313a3f7845e634a277b07c3f6377346c2486ba63e1c22e90c'


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as f:
        while block := f.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def fetch(url, path, size, expected):
    path = Path(path)
    if path.exists():
        if path.stat().st_size != size or digest(path) != expected:
            raise ValueError(f'Existing file differs from expected source: {path}; use a new output folder')
        print('  Already downloaded and verified:', path.name, flush=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + '.part')
    count = 0
    req = urllib.request.Request(url, headers={'User-Agent': 'IoT23-reading-helper/1.0'})
    with urllib.request.urlopen(req, timeout=60) as response, partial.open('wb') as target:
        while block := response.read(1024 * 1024):
            count += len(block)
            if count > size:
                raise ValueError('Download exceeds pinned source size')
            target.write(block)
    if count != size or digest(partial) != expected:
        raise ValueError(f'Download checksum/size differs: {partial}')
    partial.replace(path)


def zeek_rows(path):
    fields = None
    with Path(path).open(encoding='utf-8') as f:
        for number, line in enumerate(f, 1):
            if line.startswith('#fields'):
                fields = line.split()[1:]
                fields = ['detailed_label' if k in ('det_label', 'detailed-label') else k for k in fields]
                if len(set(fields)) != len(fields):
                    raise ValueError('Duplicate Zeek column names')
                continue
            if line.startswith('#') or not line.strip():
                continue
            if fields is None:
                raise ValueError('Zeek #fields header is missing')
            values = line.split()
            if len(values) != len(fields):
                raise ValueError(f'Unexpected field count in {path}, line {number}')
            yield dict(zip(fields, values))


def convert(path, output, scenario):
    counts = Counter()
    selected = Counter()
    preview = []
    total = 0
    writer = None
    output.parent.mkdir(parents=True, exist_ok=True)
    # BOM allows Excel to recognize UTF-8; original Zeek log is left byte-identical.
    with output.open('w', encoding='utf-8-sig', newline='') as f:
        for row in zeek_rows(path):
            if writer is None:
                writer = csv.DictWriter(f, fieldnames=list(row))
                writer.writeheader()
            writer.writerow(row)
            total += 1
            key = (row['label'], row['detailed_label'])
            counts[key] += 1
            if selected[key] < 20:
                preview.append(dict(row, scenario=scenario))
                selected[key] += 1
    if not total:
        raise ValueError(f'No flows in {path}')
    return dict(scenario=scenario, flows=total,
                labels=[dict(label=k[0], detailed_label=k[1], flows=v) for k, v in sorted(counts.items())]), preview


PAGE = r'''<!doctype html><html lang="vi"><meta charset="utf-8">
<title>Đọc dữ liệu IoT-23</title>
<style>
body{font:16px system-ui,sans-serif;color:#172b44;background:#f1f5fa;margin:0;padding:24px}
main{max-width:1320px;margin:auto}section{background:white;border:1px solid #dbe3ec;border-radius:12px;padding:20px;margin:18px 0}
h1,h2{color:#103c68}p,li{line-height:1.6}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;border-bottom:1px solid #e1e7ef;text-align:left;vertical-align:top}th{background:#edf3fa}
.scroll{overflow:auto;max-height:600px}select,input{font:inherit;padding:8px;margin:6px;border:1px solid #acbacb;border-radius:6px}.good{color:#076d42}.bad{color:#ab2038}code{background:#edf3fa;padding:2px 5px}a{color:#155fa3}
</style><main>
<h1>Đọc dữ liệu IoT-23</h1>
<p>Đây là <strong>5 capture được chọn để học cách đọc</strong>, không phải toàn bộ 23 capture. Nguồn: <a href="https://www.stratosphereips.org/datasets-iot23">Stratosphere Laboratory / CTU</a>.</p>
<section><h2>1. Phân biệt ba loại dữ liệu</h2>
<ul><li><strong>PCAP:</strong> một bản ghi gồm các gói mạng, mở bằng Wireshark.</li>
<li><strong>conn.log.labeled / CSV ở đây:</strong> một dòng là một luồng kết nối được Zeek tóm tắt, có thể kéo dài nhiều giây.</li>
<li><strong>CSV của model v3:</strong> một dòng là sáu đặc trưng của một cửa sổ một giây. Không thay trực tiếp bằng một dòng Zeek.</li></ul>
<p>Bắt đầu với <a href="csv/CTU-Honeypot-Capture-4-1.csv">CSV Philips Hue bình thường</a>. Các bảng CSV giữ toàn bộ luồng của năm log đã tải; trang này chỉ xem trước tối đa 20 dòng cho mỗi cặp nhãn trong mỗi capture.</p></section>
<section><h2>2. Các tệp đã tải</h2><table><thead><tr><th>Capture</th><th>Số luồng</th><th>CSV đầy đủ của log này</th></tr></thead><tbody>__SUMMARY__</tbody></table>
<p>PCAP bình thường: <a href="raw/CTU-Honeypot-Capture-4-1/2018-10-25-14-06-32-192.168.1.132.pcap">Philips Hue — 4,6 MB</a>. Mở bằng Wireshark. Đây là capture gốc đầy đủ, không phải PCAP cắt mẫu.</p></section>
<section><h2>3. Xem các dòng thật</h2>
<label>Capture <select id="capture"><option value="">Tất cả</option></select></label>
<label>Nhãn chi tiết <select id="label"><option value="">Tất cả</option></select></label>
<input id="search" placeholder="Tìm IP, port hoặc nhãn..." aria-label="Tìm trong các dòng xem trước">
<p id="count"></p><div class="scroll"><table><thead><tr><th>Capture</th><th>Nguồn IP:port</th><th>Đích IP:port</th><th>Giao thức</th><th>Thời lượng (s)</th><th>Gói đi / về</th><th>label</th><th>detailed_label</th></tr></thead><tbody id="rows"></tbody></table></div></section>
<section><h2>4. Các cột nghĩa là gì?</h2><table>
<tr><th>Cột</th><th>Cách hiểu</th></tr>
<tr><td>ts / uid</td><td>Timestamp bắt đầu luồng / mã định danh luồng; không phải nhãn tấn công.</td></tr>
<tr><td>id.orig_h / id.orig_p</td><td>IP / port phía khởi tạo luồng. Không mặc định phía này là kẻ tấn công.</td></tr>
<tr><td>id.resp_h / id.resp_p</td><td>IP / port phía còn lại của luồng.</td></tr>
<tr><td>proto / duration</td><td>Giao thức TCP, UDP... / thời gian luồng kéo dài, tính bằng giây.</td></tr>
<tr><td>orig_pkts / resp_pkts</td><td>Số gói theo hai chiều trong cả luồng, không phải số gói của một cửa sổ một giây.</td></tr>
<tr><td>orig_bytes / orig_ip_bytes</td><td>Byte payload / byte IP theo định nghĩa Zeek; hai loại khác nhau.</td></tr>
<tr><td>label / detailed_label</td><td>Nhãn gốc tổng quát / chi tiết. Benign hoặc benign = bình thường. Malicious = độc hại theo nhãn nguồn.</td></tr>
<tr><td>conn_state=S0</td><td>Ghi nhận thử kết nối, không thấy phản hồi theo trạng thái Zeek. S0 tự nó không chứng minh tấn công.</td></tr>
<tr><td>-</td><td>Không có giá trị được ghi cho trường đó; không tự đổi mọi dấu - thành số 0.</td></tr>
</table><p>Chỉ chuẩn hóa tên cột <code>det_label</code>/<code>detailed-label</code> thành <code>detailed_label</code> trong CSV. Giá trị nhãn được giữ nguyên, kể cả khác chữ hoa/thường; log gốc không bị sửa.</p></section>
<section><h2>5. Liên hệ với model đang làm</h2>
<p><code>PartOfAHorizontalPortScan</code> là quét ngang, không tự đổi thành vertical scan. <code>DDoS</code> không mặc định là SYN flood; cần xem PCAP/TCP flags. Năm log này chứa nhãn gốc IoT-23, không phải bảng ba nhãn 0/1/2 của model.</p>
<p>Để tạo sáu đặc trưng một giây giống v3, cần quay về PCAP, đúng chiều ingress và cửa sổ; không thể lấy tỷ lệ SYN mỗi giây chính xác chỉ từ các trường tổng luồng ở đây.</p></section>
</main><script type="application/json" id="data">__DATA__</script>
<script>
const data=JSON.parse(document.getElementById('data').textContent);
const cap=document.getElementById('capture'),label=document.getElementById('label'),search=document.getElementById('search');
function options(el,values){for(const value of [...new Set(values)].sort()){const o=document.createElement('option');o.value=value;o.textContent=value;el.appendChild(o)}}
options(cap,data.map(x=>x.scenario));options(label,data.map(x=>x.detailed_label));
function render(){const q=search.value.toLowerCase();const chosen=data.filter(r=>(!cap.value||r.scenario===cap.value)&&(!label.value||r.detailed_label===label.value)&&(!q||Object.values(r).join(' ').toLowerCase().includes(q)));
document.getElementById('count').textContent=`Đang hiển thị ${chosen.length} dòng trong phần xem trước. Đọc tất cả các dòng bằng tệp CSV tương ứng.`;
const body=document.getElementById('rows');body.replaceChildren();for(const r of chosen){const tr=document.createElement('tr');const values=[r.scenario,r['id.orig_h']+':'+r['id.orig_p'],r['id.resp_h']+':'+r['id.resp_p'],r.proto,r.duration,r.orig_pkts+' / '+r.resp_pkts,r.label,r.detailed_label];for(const v of values){const td=document.createElement('td');td.textContent=v;tr.appendChild(td)}tr.children[6].className=r.label.toLowerCase()==='benign'?'good':'bad';body.appendChild(tr)}}
cap.addEventListener('change',render);label.addEventListener('change',render);search.addEventListener('input',render);render();
</script></html>'''


def run(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    metadata = []
    summaries = []
    preview = []
    for index, (scenario, size, expected) in enumerate(SOURCES, 1):
        print(f'[{index}/6] {scenario}: downloading labeled flow log', flush=True)
        relative = Path('raw') / scenario / 'bro/conn.log.labeled'
        url = BASE + scenario + '/bro/conn.log.labeled'
        fetch(url, output / relative, size, expected)
        summary, rows = convert(output / relative, output / 'csv' / (scenario + '.csv'), scenario)
        summaries.append(summary)
        preview.extend(rows)
        metadata.append(dict(url=url, path=relative.as_posix(), bytes=size, sha256=expected,
                             checksum_note='Local provenance SHA256; not a publisher checksum'))
        print('  Converted flows:', summary['flows'], flush=True)
    print('[6/6] Philips Hue original PCAP', flush=True)
    relative = Path('raw/CTU-Honeypot-Capture-4-1') / (PCAP_NAME + '.xz')
    url = BASE + 'CTU-Honeypot-Capture-4-1/' + PCAP_NAME + '.xz'
    fetch(url, output / relative, PCAP_XZ_BYTES, PCAP_XZ_SHA)
    pcap = (output / relative).with_suffix('')
    if not pcap.exists():
        partial = pcap.with_suffix('.pcap.part')
        size = 0
        with lzma.open(output / relative, 'rb') as source, partial.open('wb') as target:
            while block := source.read(1024 * 1024):
                size += len(block)
                if size > PCAP_BYTES:
                    raise ValueError('Expanded PCAP exceeds expected size')
                target.write(block)
        if size != PCAP_BYTES or digest(partial) != PCAP_SHA:
            raise ValueError('Expanded PCAP checksum differs')
        partial.replace(pcap)
    if pcap.stat().st_size != PCAP_BYTES or digest(pcap) != PCAP_SHA:
        raise ValueError('Existing PCAP differs from original source')
    metadata.append(dict(url=url, path=relative.as_posix(), bytes=PCAP_XZ_BYTES, sha256=PCAP_XZ_SHA,
                         expanded_path=pcap.relative_to(output).as_posix(), expanded_bytes=PCAP_BYTES,
                         expanded_sha256=PCAP_SHA))
    summary_html = ''.join('<tr><td>' + html.escape(s['scenario']) + '</td><td>' + str(s['flows'])
                           + '</td><td><a href="csv/' + html.escape(s['scenario']) + '.csv">Mở CSV</a></td></tr>' for s in summaries)
    encoded = json.dumps(preview, ensure_ascii=False).replace('<', chr(92) + 'u003c')
    page = PAGE.replace('__SUMMARY__', summary_html).replace('__DATA__', encoded)
    (output / 'MO_DE_DOC.html').write_text(page, encoding='utf-8')
    manifest = dict(official_page=OFFICIAL, subset_only=True, labels_unmodified=True,
                    downloaded_at_utc=datetime.now(timezone.utc).isoformat(),
                    files=metadata, captures=summaries, preview_rows=len(preview),
                    total_flows=sum(s['flows'] for s in summaries))
    (output / 'DOWNLOAD_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'README.txt').write_text('Open MO_DE_DOC.html in your browser. Each Zeek/CSV row is a FLOW, not a packet or a one-second model window.\n'
        'Only five selected IoT-23 labeled logs and one benign original PCAP are included. Native labels are not mapped to model classes.\n'
        'Original files are fetched over HTTPS from the publisher, preserved byte-identical and SHA256 checked.\n'
        'Full dataset and citation information: ' + OFFICIAL + '\n', encoding='utf-8')
    print('\nDONE. Open:', output / 'MO_DE_DOC.html', flush=True)
    print('Full labeled flows in this reading subset:', manifest['total_flows'], flush=True)
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', default='data/iot23_reading', help='New folder for original files, CSVs and offline reading page')
    a = p.parse_args()
    run(a.output)
