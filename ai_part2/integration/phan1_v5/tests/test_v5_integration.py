"""Migration integrity and negative checks; no network accuracy claim."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('trace_checker',ROOT/'tools/check_v5_trace.py')
trace=importlib.util.module_from_spec(spec);spec.loader.exec_module(trace)
spec_runner=importlib.util.spec_from_file_location('simulation_runner',ROOT/'tools/run_sim.py')
runner=importlib.util.module_from_spec(spec_runner);spec_runner.loader.exec_module(runner)


class V5MigrationChecks(unittest.TestCase):
    def test_testbench_fail_cannot_be_reported_as_success_with_zero_exit(self):
        # The legacy testbench uses $finish, which returns 0 even on FAIL.
        responses=[subprocess.CompletedProcess([],0,'',''),
                   subprocess.CompletedProcess([],0,'[tb] FAIL: 1 loi\n','')]
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'ROOT',Path(d)),patch.object(runner.shutil,'which',return_value='/tool'),patch.object(runner.subprocess,'run',side_effect=responses):
            with self.assertRaisesRegex(ValueError,'Test failed'):runner.run('system')

    def test_active_model_and_firmware_reference_match_frozen_v5(self):
        model=ROOT/'rtl/part2_ai/model.json'
        self.assertEqual(hashlib.sha256(model.read_bytes()).hexdigest(),trace.MODEL_SHA)
        active=(ROOT/'sources.f').read_text()
        self.assertIn('rtl/part2_ai/ai_core_model_v5.v',active)
        self.assertNotIn('ai_core_model_v2.v',active)
        refs=json.loads((ROOT/'fw/part2/INTEGRATION_VECTORS.json').read_text())
        self.assertEqual(refs['model_sha256'],trace.MODEL_SHA)
        self.assertEqual(len(refs['examples']),37)
        self.assertEqual(sum(e['decision_valid'] for e in refs['examples']),36)
        self.assertFalse((ROOT/'board/prebuilt/tangnano9k_noeth.fs').exists())

    def test_legacy_vector_generation_is_rejected_before_files_change(self):
        before=[(ROOT/n).read_bytes() for n in ('fw/font5x7.c','sim/font5x7.hex','fw/ai_vectors.h')]
        with tempfile.TemporaryDirectory() as d:
            bad=Path(d)/'old.json'
            with zipfile.ZipFile(ROOT/'reference/original_v2_ai.zip') as z:
                bad.write_bytes(z.read('fw/part2/INTEGRATION_VECTORS.json'))
            result=subprocess.run([sys.executable,'tools/gen_tables.py','tools/vendor/glcdfont.c',str(bad)],cwd=ROOT,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('do not match',result.stderr)
        self.assertEqual(before,[(ROOT/n).read_bytes() for n in ('fw/font5x7.c','sim/font5x7.hex','fw/ai_vectors.h')])

    def test_actual_runtime_trace_matches_and_changed_score_is_detected(self):
        path=ROOT/'verification/recorded/runtime_feature_trace.csv'
        self.assertEqual(trace.check(path)['runtime_windows'],37)
        with path.open() as f:reader=csv.DictReader(f);rows=list(reader);fields=reader.fieldnames
        rows[0]['score0']=str(int(rows[0]['score0'])+1)
        with tempfile.TemporaryDirectory() as d:
            bad=Path(d)/'bad.csv'
            with bad.open('w',newline='') as f:
                writer=csv.DictWriter(f,fields);writer.writeheader();writer.writerows(rows)
            with self.assertRaisesRegex(ValueError,'mismatch'):trace.check(bad)


if __name__=='__main__':unittest.main()
