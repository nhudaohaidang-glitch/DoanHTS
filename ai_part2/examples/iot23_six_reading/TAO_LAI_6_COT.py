"""Reproduce the six-feature tables from the PCAPs bundled with this reading set."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MODULE_ROOT = HERE if (HERE/'part2/features.py').is_file() else HERE.parents[1]
sys.path.insert(0, str(MODULE_ROOT))
try:
    from part2.features import NAMES, extract, values, quantize
except ImportError:
    raise SystemExit('Use the existing AI environment: ~/ai_part2/.venv/bin/python TAO_LAI_6_COT.py')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while b := f.read(1024*1024): h.update(b)
    return h.hexdigest()


def write(path, names, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(names); w.writerows(rows)


def run(output, data_dir=HERE):
    output = Path(output)
    data_dir = Path(data_dir)
    if output.exists(): raise ValueError('Output exists; choose a new folder')
    sources = json.loads((data_dir/'SOURCES.json').read_text())
    raw_rows, labels, provenance = [], [], []
    for source in sources:
        pcap = data_dir/source['included_pcap']
        if digest(pcap) != source['included_sha256']: raise ValueError('PCAP changed')
        print('Reading', source['capture_id'], flush=True)
        windows, stats = extract(pcap, source['protected_ip']+'/32', 1., 'exact')
        selected = [(slot, values(w, 'exact')) for slot, w in sorted(windows.items())
                    if math.ceil(source['start']) <= slot < math.floor(source['end'])]
        selected = [(slot, raw) for slot, raw in selected if raw[0] > 0]
        if len(selected) != source['expected_windows']: raise ValueError('Unexpected window count')
        for slot, raw in selected:
            raw_rows.append(raw); labels.append([source['label']])
            provenance.append([len(raw_rows), source['capture_id'], slot])
    q = quantize(raw_rows, [8,2,1,1,1,1]).tolist()
    output.mkdir(parents=True)
    write(output/'X_6_raw.csv', NAMES, raw_rows)
    write(output/'X_6_fpga.csv', ['q0','q1','q2','q3','q4','q5'], q)
    write(output/'y.csv', ['class'], labels)
    write(output/'THONG_TIN_DONG.csv', ['row_number','capture_id','window_start'], provenance)
    print('DONE:', len(raw_rows), 'rows; each X file has exactly six columns')
    return raw_rows, labels, provenance


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', default='ket_qua_tao_lai')
    p.add_argument('--data-dir', default=str(HERE))
    a = p.parse_args()
    run(a.output, a.data_dir)
