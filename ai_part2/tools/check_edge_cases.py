"""Offline feature probes for the integration feedback; never training data.

Expected labels describe the explicitly constructed control/scanning scenarios,
not ground truth inferred from anonymous traffic. No packets are sent.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from part2.features import NAMES, quantize
from part2.integer import infer, write_vectors


def probes():
    cases = [
        ('sensor_feedback', 'normal_control', [7, 61, 18, 1, 1, 1], 0, 1),
        ('single_legitimate_syn', 'normal_control', [1, 40, 127, 1, 1, 1], 0, 1),
    ]
    cases += [(f'ack52_{n}', 'normal_control', [n, 52, 0, 1, 1, 1], 0, 0)
              for n in (1, 7, 8, 30, 100, 1000)]
    cases += [(f'pure_vertical_scan_{n}', 'vertical_scan', [n, 40, 127, 1, 1, n], 2, n)
              for n in range(3, 31)]
    return cases


def check(model_dir, output):
    model_dir, output = Path(model_dir), Path(output)
    if output.exists():
        raise ValueError('Output exists; choose another path to preserve evidence')
    data = (model_dir / 'model.json').read_bytes()
    model = json.loads(data)
    version = model.get('model_version')
    if version not in ('v2', 'v3', 'v4') or model['architecture'] != [6, 8, 3]:
        raise ValueError('Expected a v2/v3/v4 6-8-3 model')
    cases = probes()
    raw = np.asarray([c[2] for c in cases], dtype=np.int64)
    q = quantize(raw, model['divisors'])
    scores = infer(q, model)
    predictions = scores.argmax(axis=1)
    rows = []
    c_lines = ['#include <stdint.h>', '#include <stdio.h>',
               f'#include "ai_quant_{version}.h"', 'int main(void) {',
               '    unsigned failures = 0;']
    for i, (name, scenario, features, expected, syn_count) in enumerate(cases):
        packed = sum(int(v) << (8 * j) for j, v in enumerate(q[i]))
        rows.append(dict(case=name, scenario=scenario, raw=dict(zip(NAMES, features)),
                         quantized=q[i].tolist(), feat_hex=f'{packed:012x}',
                         scores=scores[i].tolist(), prediction=int(predictions[i]),
                         expected_scenario_class=expected,
                         scenario_expectation_met=bool(predictions[i] == expected)))
        n, mean, ratio, src, dst, ports = features
        assert 127 * syn_count // n == ratio
        # mean*n is ONE aggregate consistent with floor(sum_ip_bytes/n),
        # not a reconstruction of an original sensor trace.
        c_lines += [f'    /* {name}: aggregate consistent with this raw probe. */',
                    f'    if (ai_{version}_pack({n}u, UINT64_C({mean*n}), {syn_count}u, {src}u, {dst}u, {ports}u)',
                    f'        != UINT64_C(0x{packed:012x})) {{ puts("PACK MISMATCH {name}"); ++failures; }}']
    c_lines += [f'    printf("C packing: %u failures / {len(cases)} probes\\n", failures);',
                '    return failures ? 1 : 0;', '}', '']
    failed = [r['case'] for r in rows if not r['scenario_expectation_met']]
    result = dict(kind='offline_engineered_feature_probes_not_pcaps_not_training',
                  model_version=version, model_sha256=hashlib.sha256(data).hexdigest(),
                  model_modified=False, divisors=model['divisors'], cases=rows,
                  total=len(rows), failed_scenario_expectations=failed,
                  limitations=[
                      'No independent traffic collection or real FPGA run here.',
                      'RTL vectors reproduce MODEL scores, including semantic errors; RTL PASS is not detection accuracy.',
                      'A single SYN cannot establish SYN flood; these benign control scenarios must not cause automatic blocking.',
                      'Port count is global per window; multiport traffic alone does not prove one source vertically scanned one target.',
                  ])
    output.mkdir(parents=True)
    (output / 'report.json').write_text(json.dumps(result, indent=2))
    (output / 'check_pack.c').write_text('\n'.join(c_lines))
    write_vectors(q, model, output / 'vectors.txt')
    with (output / 'cases.csv').open('w', newline='') as f:
        w = csv.writer(f,lineterminator='\n')
        w.writerow(['case', *NAMES, 'quantized', 'feat_hex', 'score_normal', 'score_syn', 'score_scan', 'prediction', 'expected_scenario_class'])
        for row in rows:
            w.writerow([row['case'], *row['raw'].values(), json.dumps(row['quantized']), row['feat_hex'],
                        *row['scores'], row['prediction'], row['expected_scenario_class']])
    print(json.dumps(dict(model_version=version, model_sha256=result['model_sha256'],
                         probes=len(rows), unmet_scenario_expectations=len(failed),
                         failed_cases=failed, output=str(output)), indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', default='gowin/hybrid_v3/model')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    check(a.model, a.output)
