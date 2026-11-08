import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
KIT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('updater',KIT/'tools/apply_update.py')
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
class UpdaterTest(unittest.TestCase):
 def fixture(self,d):
  root=Path(d);target=root/'existing';(target/'part2').mkdir(parents=True);(target/'scripts').mkdir()
  (target/'data').mkdir();(target/'data/keep.pcap').write_bytes(b'unchanged')
  (target/'build/lab_model_v1').mkdir(parents=True);(target/'build/lab_model_v1/model.json').write_text('frozen')
  (target/'tools').mkdir();(target/'tools/a.py').write_text('old')
  bundle=root/'bundle';(bundle/'payload/tools').mkdir(parents=True)
  (bundle/'payload/tools/a.py').write_text('new');(bundle/'payload/tools/b.py').write_text('second')
  files={str(p.relative_to(bundle/'payload')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (bundle/'payload').rglob('*') if p.is_file()}
  (bundle/'UPDATE_MANIFEST.json').write_text(json.dumps({'format':1,'files':files}));return bundle,target
 def test_backup_preserve_data_and_repeat(self):
  with tempfile.TemporaryDirectory() as d:
   bundle,target=self.fixture(d)
   self.assertEqual(u.apply_update(bundle,target)['status'],'preview');self.assertEqual((target/'tools/a.py').read_text(),'old')
   r=u.apply_update(bundle,target,True)
   self.assertEqual((Path(r['backup'])/'tools/a.py').read_text(),'old')
   self.assertEqual((target/'data/keep.pcap').read_bytes(),b'unchanged')
   self.assertEqual((target/'build/lab_model_v1/model.json').read_text(),'frozen')
   self.assertEqual(u.apply_update(bundle,target,True)['status'],'already_current')
 def test_gitignore_is_additive(self):
  with tempfile.TemporaryDirectory() as d:
   bundle,target=self.fixture(d);(target/'.gitignore').write_text('custom-user-rule/\n')
   (bundle/'payload/.gitignore').write_text('data/challenge/\n')
   path=bundle/'UPDATE_MANIFEST.json';m=json.loads(path.read_text())
   m['files']['.gitignore']=hashlib.sha256((bundle/'payload/.gitignore').read_bytes()).hexdigest();path.write_text(json.dumps(m))
   u.apply_update(bundle,target,True)
   self.assertEqual((target/'.gitignore').read_text(),'custom-user-rule/\ndata/challenge/\n')
 def test_corrupt_payload_refused(self):
  with tempfile.TemporaryDirectory() as d:
   bundle,target=self.fixture(d);(bundle/'payload/tools/a.py').write_text('corrupt')
   with self.assertRaises(ValueError):u.apply_update(bundle,target,True)
   self.assertEqual((target/'tools/a.py').read_text(),'old')
 def test_partial_failure_rolls_back(self):
  with tempfile.TemporaryDirectory() as d:
   bundle,target=self.fixture(d);replace=u.os.replace;count=0
   def fail_second(a,b):
    nonlocal count
    count+=1
    if count==2:raise OSError('simulated disk failure')
    return replace(a,b)
   with patch.object(u.os,'replace',side_effect=fail_second):
    with self.assertRaises(OSError):u.apply_update(bundle,target,True)
   self.assertEqual((target/'tools/a.py').read_text(),'old');self.assertFalse((target/'tools/b.py').exists())
 def test_protected_paths_refused(self):
  with tempfile.TemporaryDirectory() as d:
   bundle,target=self.fixture(d)
   (bundle/'UPDATE_MANIFEST.json').write_text(json.dumps({'format':1,'files':{'data/keep.pcap':'bad'}}))
   with self.assertRaises(ValueError):u.apply_update(bundle,target,True)
   self.assertEqual((target/'data/keep.pcap').read_bytes(),b'unchanged')
if __name__=='__main__':unittest.main()
