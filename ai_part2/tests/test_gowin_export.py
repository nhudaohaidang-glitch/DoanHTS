import importlib.util,shutil,tempfile,unittest
from pathlib import Path
KIT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prepare_gowin',KIT/'tools/prepare_gowin.py')
exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)
class GowinExportTest(unittest.TestCase):
 def fixture(self,root):
  model=root/'model';shutil.copytree(KIT/'examples/synthetic_model',model);return model
 def test_export_self_contained_and_no_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);model=self.fixture(root);out=root/'project'
   report=exporter.prepare(model,out,KIT)
   rtl=(out/'src/ai_core_model_v1.v').read_text()
   self.assertNotIn('$readmemh',rtl);self.assertNotIn('`include',rtl)
   self.assertIn('module ai_core (',rtl);self.assertIn('rom_w1(neuron*6+idx)',rtl)
   self.assertEqual(report['vector_count'],384)
   self.assertEqual((out/'verification/vectors.txt').read_bytes(),(model/'vectors.txt').read_bytes())
   import xml.etree.ElementTree as E
   project=E.parse(out/'ai_core_v1.gprj')
   self.assertEqual(project.find('Device').attrib['pn'],'GW1NR-LV9QN88PC6/I5')
   for f in project.findall('.//File'):self.assertTrue((out/f.attrib['path']).is_file())
   with self.assertRaises(ValueError):exporter.prepare(model,out,KIT)
 def test_stale_hex_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   model=self.fixture(Path(d));path=model/'w1.hex';lines=path.read_text().splitlines()
   lines[0]='00' if lines[0]!='00' else 'ff';path.write_text('\n'.join(lines)+'\n')
   with self.assertRaisesRegex(ValueError,'w1.hex differs'):exporter.validate(model)
 def test_v2_project_has_distinct_filenames_and_firmware_symbols(self):
  import json
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);model=self.fixture(root);path=model/'model.json'
   m=json.loads(path.read_text());m['model_version']='v2';path.write_text(json.dumps(m))
   out=root/'v2';exporter.prepare(model,out,KIT)
   self.assertTrue((out/'src/ai_core_model_v2.v').is_file())
   self.assertTrue((out/'ai_core_v2.gprj').is_file())
   self.assertIn('ai_v2_pack',(out/'firmware/ai_quant_v2.h').read_text())
   self.assertIn('src/ai_core_model_v2.v',(out/'verification/run_sim.sh').read_text())
   self.assertFalse((out/'src/ai_core_model_v1.v').exists())
 def test_wrong_vector_class_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   model=self.fixture(Path(d));path=model/'vectors.txt';lines=path.read_text().splitlines()
   a,b,c=lines[0].split();lines[0]=f'{a} {b} {(int(c)+1)%3}';path.write_text('\n'.join(lines)+'\n')
   with self.assertRaisesRegex(ValueError,'Vectors do not match'):exporter.validate(model)
if __name__=='__main__':unittest.main()
