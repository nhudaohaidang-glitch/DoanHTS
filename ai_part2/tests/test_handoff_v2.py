"""Handoff consistency checks using artificial feature fixtures, not network results."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from test_v2_development import fixture
from part2.development import evaluate_v2, train_v2, verify_freeze
from tools.make_handoff_v2 import package, integration_guard_header
from tools.prepare_gowin import prepare, firmware_header

KIT = Path(__file__).resolve().parents[1]


def inputs(root):
    dev = fixture(root / 'dev')
    model = root / 'model'
    train_v2(dev, model)
    project = root / 'gowin'
    manifest = prepare(model, project, KIT)
    # A fixture log exercises the packaging guard; no hardware run is claimed.
    (project / 'verification/build').mkdir()
    (project / 'verification/build/result.log').write_text(
        f'PASS vectors={manifest["vector_count"]} cycles_min=84 cycles_max=84 (fixture)\n')
    dataset = fixture(root / 'holdout', ('challenge',), offset=1000)
    meta = json.loads(dataset.with_suffix('.meta.json').read_text())
    record = root / 'COLLECTION.json'
    record.write_text(json.dumps(dict(selection=verify_freeze(model),
        capture_ids=[r['capture_id'] for r in meta['captures']], collection_started_at=900)))
    report, _ = evaluate_v2(dataset, model, record)
    evaluation = root / 'evaluation'
    evaluation.mkdir()
    (evaluation / 'metrics.json').write_text(json.dumps(report, indent=2))
    (evaluation / 'per_capture.csv').write_text('capture_id\n')
    (evaluation / 'report.html').write_text('<title>Artificial test fixture</title>')
    return model, project, dataset, evaluation, record


class HandoffV2Test(unittest.TestCase):
    @unittest.skipUnless(shutil.which('gcc'), 'host C compiler unavailable')
    def test_guard_skips_raw_zero_but_accepts_small_nonempty_windows(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            model=json.loads((KIT/'examples/synthetic_model/model.json').read_text())
            model.update(model_version='v2',divisors=[8,2,1,1,1,1])
            (root/'ai_quant_v2.h').write_text(firmware_header(model))
            (root/'ai_v2_integration.h').write_text(integration_guard_header())
            source=root/'guard_test.c'
            source.write_text('''#include "ai_v2_integration.h"
int main(void) {
    uint64_t feat = 123;
    if (ai_v2_prepare_window(0,0,0,0,0,0,&feat) || feat != 0) return 1;
    if (!ai_v2_prepare_window(1,60,1,1,1,1,&feat) || (feat & 255) != 0 || feat == 0) return 2;
    if (!ai_v2_prepare_window(7,280,5,1,1,5,&feat) || (feat & 255) != 0 || feat == 0) return 3;
    if (!ai_v2_prepare_window(8,320,6,1,1,6,&feat) || (feat & 255) != 1) return 4;
    if (ai_v2_prepare_window(1,60,1,1,1,1,0)) return 5;
    return 0;
}
''')
            result=subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-I',str(root),str(source),'-o',str(root/'guard_test')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(subprocess.run([str(root/'guard_test')]).returncode,0)

    def test_consistent_bundle_checksum_and_no_overwrite(self):
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            args = inputs(root)
            out = root / 'handoff.zip'
            result = package(*args, out)
            self.assertFalse(result['hardware_blocking_verified'])
            with ZipFile(out) as archive:
                self.assertIsNone(archive.testzip())
                checksums = json.loads(archive.read('ai_v2_handoff/FILE_SHA256.json'))
                for name, digest in checksums.items():
                    self.assertEqual(hashlib.sha256(archive.read('ai_v2_handoff/'+name)).hexdigest(),digest)
                examples = json.loads(archive.read('ai_v2_handoff/INTEGRATION_VECTORS.json'))
                self.assertEqual(examples['examples'][2]['quantized'][5],2)
                self.assertEqual(examples['examples'][3]['quantized'][5],6)
                self.assertFalse(examples['examples'][0]['decision_valid'])
                self.assertTrue(examples['examples'][1]['decision_valid'])
                self.assertIn('ai_v2_handoff/gowin_ai_v2/firmware/ai_quant_v2.h',archive.namelist())
                self.assertEqual(archive.read('ai_v2_handoff/gowin_ai_v2/firmware/ai_v2_integration.h').decode(),integration_guard_header())
                self.assertIn('ai_v2_handoff/holdout/features.csv',archive.namelist())
                self.assertIn('ai_v2_handoff/holdout/features.meta.json',archive.namelist())
                self.assertFalse(any(name.endswith('.vvp') or name.endswith('.pcap') for name in archive.namelist()))
                evidence = json.loads(archive.read('ai_v2_handoff/evidence/GOWIN_USER_REPORTED.json'))
                self.assertFalse(evidence['routed_timing_verified'])
            with self.assertRaisesRegex(ValueError,'Output exists'):
                package(*args,out)

    def test_stale_export_and_changed_holdout_report_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);args=inputs(root);model,project,dataset,evaluation,record=args
            path=project/'src/ai_core_model_v2.v';old=path.read_text();path.write_text(old+'// different\n')
            with self.assertRaisesRegex(ValueError,'Verilog differs'):
                package(*args,root/'bad.zip')
            self.assertFalse((root/'bad.zip').exists())
            path.write_text(old)
            path=evaluation/'metrics.json';data=json.loads(path.read_text());data['ai']['accuracy']=.12345;path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'metrics differ'):
                package(*args,root/'bad.zip')

    def test_missing_or_wrong_simulation_log_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);args=inputs(root)
            log=args[1]/'verification/build/result.log';log.write_text('PASS vectors=1 cycles_min=84 cycles_max=84\n')
            with self.assertRaisesRegex(ValueError,'simulation log'):
                package(*args,root/'bad.zip')


if __name__=='__main__':unittest.main()
