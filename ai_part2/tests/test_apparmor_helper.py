import importlib.util
from pathlib import Path
import subprocess,tempfile,unittest

spec=importlib.util.spec_from_file_location('apparmor_helper',Path(__file__).resolve().parents[1]/'scripts'/'allow_lab_apparmor.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

class AppArmorHelperTest(unittest.TestCase):
 def fixture(self,root,name='mosquitto',syntax='include if exists <local/mosquitto>'):
  (root/name).write_text('profile mosquitto /usr/sbin/mosquitto {\n'+syntax+'\n}\n')
 def test_modern_and_legacy_include(self):
  for name,syntax in [('mosquitto','include if exists <local/mosquitto>'),('usr.sbin.mosquitto','#include <local/usr.sbin.mosquitto>')]:
   with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
    root=Path(d);self.fixture(root,name,syntax)
    plan=helper.discover(root)
    self.assertEqual(plan['profile'].name,name)
    self.assertEqual(plan['local'].parent,root/'local')
 def test_ambiguous_or_missing_profiles_refused(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   with self.assertRaises(ValueError):helper.discover(root)
   self.fixture(root);self.fixture(root,'usr.sbin.mosquitto')
   with self.assertRaises(ValueError):helper.discover(root)
 def test_rule_is_additive_and_idempotent(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.fixture(root);plan=helper.discover(root)
   plan['local'].parent.mkdir();plan['local'].write_text('# user settings\n/etc/example r,\n')
   calls=[]
   def runner(args,**kwargs):calls.append(args)
   backup=helper.apply(plan,'parser',runner)
   text=plan['local'].read_text()
   self.assertIn('/etc/example r,',text)
   self.assertEqual(backup.read_text(),'# user settings\n/etc/example r,\n')
   helper.apply(plan,'parser',runner)
   self.assertEqual(plan['local'].read_text(),text)
   self.assertEqual(text.count(helper.RULE),1)
   self.assertEqual(calls[0][1:3],['-Q','-T'])
   self.assertEqual(calls[1][1:3],['-r','-T'])
 def test_syntax_failure_restores_file(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.fixture(root);plan=helper.discover(root)
   plan['local'].parent.mkdir();plan['local'].write_text('# original\n')
   def fail(args,**kwargs):raise subprocess.CalledProcessError(1,args,stderr='parse failed')
   with self.assertRaises(subprocess.CalledProcessError):helper.apply(plan,'parser',fail)
   self.assertEqual(plan['local'].read_text(),'# original\n')
 def test_failure_removes_only_new_file(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.fixture(root);plan=helper.discover(root)
   def fail(args,**kwargs):raise subprocess.CalledProcessError(1,args)
   with self.assertRaises(subprocess.CalledProcessError):helper.apply(plan,'parser',fail)
   self.assertFalse(plan['local'].exists())
   self.assertTrue(plan['profile'].exists())
 def test_symlink_escape_refused(self):
  with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as outside:
   root=Path(d);self.fixture(root);(root/'local').mkdir()
   (root/'local'/'mosquitto').symlink_to(Path(outside)/'secret')
   with self.assertRaises(ValueError):helper.discover(root)

if __name__=='__main__':unittest.main()
