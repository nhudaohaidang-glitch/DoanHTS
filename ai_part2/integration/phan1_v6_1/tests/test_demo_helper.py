"""Ensure the standalone demo is portable and cannot replace the MAC project."""
from pathlib import Path
import json,shutil,subprocess,sys,tempfile,unittest,xml.etree.ElementTree as ET,zipfile
ROOT=Path(__file__).resolve().parents[1]

class DemoProjectChecks(unittest.TestCase):
 def test_demo_uses_its_own_wrapper_and_twelve_matching_pin_constraints(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'project with spaces';root.mkdir()
   files=['CHUAN_BI_DEMO_GOWIN.py','THU_BAO_CAO_DEMO.py','sources.f','fw/firmware.hex','rtl/part2_ai/model.json','rtl/board/tangnano9k_top.v','board/tangnano9k_demo.cst','board/tangnano9k_demo.sdc']
   files += [line.strip() for line in (ROOT/'sources.f').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
   for name in files:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
   (root/'build/gowin').mkdir(parents=True);(root/'build/gowin/gowin_top.v').write_text('MAC wrapper must stay unchanged')
   (root/'gateway_phan1_v6_1.gprj').write_text('MAC project must stay unchanged')
   p=subprocess.run([sys.executable,str(root/'CHUAN_BI_DEMO_GOWIN.py')],capture_output=True,text=True)
   self.assertEqual(p.returncode,0,p.stderr)
   self.assertEqual((root/'gateway_phan1_v6_1.gprj').read_text(),'MAC project must stay unchanged')
   self.assertEqual((root/'build/gowin/gowin_top.v').read_text(),'MAC wrapper must stay unchanged')
   wrapper=(root/'build/gowin_demo/gowin_demo_top.v').read_text()
   self.assertIn('.SELFTEST(1)',wrapper);self.assertIn('.a_ref_clk(1\'b0)',wrapper)
   ports=wrapper.split(')(')[1].split(');')[0]
   self.assertNotIn('a_ref_clk',ports);self.assertNotIn('b_ref_clk',ports)
   project=ET.parse(root/'gateway_phan1_v6_1_demo.gprj')
   for f in project.findall('.//File'):self.assertTrue((root/f.attrib['path']).is_file(),f.attrib['path'])
   self.assertEqual((root/'board/tangnano9k_demo.cst').read_text().count('IO_LOC'),12)
   sdc=(root/'board/tangnano9k_demo.sdc').read_text();self.assertEqual(sdc.count('create_clock'),1);self.assertNotIn('a_ref_clk',sdc)
   # A MAC report alone must never be accepted as a demo report.
   impl=root/'impl/pnr';impl.mkdir(parents=True);(impl/'gateway_phan1_v6_1.rpt.html').write_text('MAC fixture')
   p=subprocess.run([sys.executable,str(root/'THU_BAO_CAO_DEMO.py')],capture_output=True,text=True)
   self.assertNotEqual(p.returncode,0);self.assertIn('No demo reports',p.stderr)
   (impl/'gateway_phan1_v6_1_demo.rpt.html').write_text('Demo fixture, no hardware claim')
   p=subprocess.run([sys.executable,str(root/'THU_BAO_CAO_DEMO.py')],capture_output=True,text=True)
   self.assertEqual(p.returncode,0,p.stderr)
   with zipfile.ZipFile(root/'BAO_CAO_DEMO_V6_1.zip') as z:
    self.assertNotIn('impl/pnr/gateway_phan1_v6_1.rpt.html',z.namelist())
    meta=json.loads(z.read('COLLECTION.json'));self.assertFalse(meta['board_pass_claimed']);self.assertFalse(meta['physical_ethernet_tested'])

if __name__=='__main__':unittest.main()
