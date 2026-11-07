"""Artificial rows check prediction/report plumbing, not model accuracy."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

KIT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(KIT/'tools'))
import run_iot23_six_v3 as runner
from part2.features import NAMES


def write(path,header,rows):
    with path.open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(header);writer.writerows(rows)


class PredictionChecks(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name)
        self.data=self.root/'data';self.folder=self.data/'du_lieu_6_cot';self.folder.mkdir(parents=True)
        self.raw=[[1,40,0,1,1,1]]*2880+[[2000,40,127,1,1,1]]*21
        self.q=[[0,20,0,1,1,1]]*2880+[[127,20,127,1,1,1]]*21
        write(self.folder/'X_6_raw.csv',NAMES,self.raw)
        write(self.folder/'X_6_fpga.csv',['q0','q1','q2','q3','q4','q5'],self.q)
        write(self.folder/'y.csv',['class'],[[0]]*2880+[[1]]*21)
        write(self.folder/'THONG_TIN_DONG.csv',['row_number','capture_id','window_start'],
              [[i+1,'iot23_hue4' if i<2880 else 'iot23_syn34',10000+i] for i in range(2901)])
        (self.data/'BAO_CAO.json').write_text(json.dumps(dict(status='complete',feature_names=NAMES,windows={'iot23_hue4':2880,'iot23_syn34':21})))
        self.output=self.root/'output'

    def tearDown(self):self.temporary.cleanup()

    def test_complete_rows_including_zero_q0_and_explicit_development_status(self):
        before={p.name:runner.sha(p) for p in self.folder.iterdir()}
        report=runner.run(self.data,self.output)
        self.assertEqual(report['total_rows'],2901)
        self.assertFalse(report['independent_test'])
        self.assertEqual(report['missing_true_classes'],[2])
        self.assertEqual(report['model_sha256'],runner.MODEL_SHA)
        self.assertEqual(before,{p.name:runner.sha(p) for p in self.folder.iterdir()})
        with (self.output/'DU_DOAN.csv').open() as stream:rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),2901)
        self.assertEqual(rows[0]['row_number'],'1')
        page=(self.output/'XEM_DU_DOAN.html').read_text()
        self.assertIn('không phải test độc lập',page)
        self.assertIn('iot23_syn34',page)

    def test_changed_quantized_input_fails_instead_of_double_quantizing(self):
        changed=[row[:] for row in self.q];changed[0][0]=1
        write(self.folder/'X_6_fpga.csv',['q0','q1','q2','q3','q4','q5'],changed)
        with self.assertRaisesRegex(ValueError,'q CSV differs'):runner.run(self.data,self.output)
        self.assertFalse(self.output.exists())

    def test_missing_row_and_wrong_source_labels_are_rejected(self):
        write(self.folder/'y.csv',['class'],[[0]]*2880+[[1]]*20)
        with self.assertRaisesRegex(ValueError,'aligned rows'):runner.run(self.data,self.output)
        write(self.folder/'y.csv',['class'],[[0]]*2880+[[2]]*21)
        with self.assertRaisesRegex(ValueError,'source label'):runner.run(self.data,self.output)
        self.assertFalse(self.output.exists())

    def test_changed_model_is_rejected_before_output(self):
        model=self.root/'wrong_model.json';model.write_text('{}')
        with self.assertRaisesRegex(ValueError,'frozen V3'):runner.run(self.data,self.output,model)
        self.assertFalse(self.output.exists())


if __name__=='__main__':unittest.main()
