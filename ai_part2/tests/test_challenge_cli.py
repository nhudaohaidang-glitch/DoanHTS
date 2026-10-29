"""CLI regression using temporary artificial PCAP fixtures, not a measured challenge result."""
import csv,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from scapy.all import Ether,IP,TCP,wrpcap
from part2.features import build_dataset
KIT=Path(__file__).resolve().parents[1]
class ChallengeCLITest(unittest.TestCase):
 def test_cli_exports_report_and_rejects_original_capture_reuse(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);packets=[]
   for t in (100.1,100.4,101.1,101.4):
    pkt=Ether(src='02:00:00:00:00:02',dst='02:00:00:00:00:01')/IP(src='198.18.0.2',dst='198.18.0.1')/TCP(dport=1883,flags='A')
    pkt.time=t;packets.append(pkt)
   wrpcap(str(root/'fixture.pcap'),packets)
   row=dict(capture_id='unit_fixture',pcap='fixture.pcap',split='challenge',label=0,start=100,end=102,source_kind='lab')
   with (root/'manifest.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
   build_dataset(root/'manifest.csv',root/'features.csv')
   original=root/'old.json';original.write_text(json.dumps({'captures':[{'sha256':'0'*64}]}))
   command=[sys.executable,str(KIT/'tools/evaluate_frozen.py'),'--dataset',str(root/'features.csv'),'--model',str(KIT/'gowin/lab_model_v1/reference/model.json'),'--original-meta',str(original)]
   result=subprocess.run(command+['--output',str(root/'report')],capture_output=True,text=True,timeout=20)
   self.assertEqual(result.returncode,0,result.stderr)
   report=json.loads((root/'report/metrics.json').read_text())
   self.assertEqual(report['kind'],'frozen_challenge_evaluation');self.assertFalse(report['model_retrained'])
   self.assertEqual(report['missing_classes'],[1,2]);self.assertTrue((root/'report/report.html').exists())
   original.write_text(json.dumps({'captures':[{'sha256':hashlib.sha256((root/'fixture.pcap').read_bytes()).hexdigest()}]}))
   result=subprocess.run(command+['--output',str(root/'reused')],capture_output=True,text=True,timeout=20)
   self.assertNotEqual(result.returncode,0);self.assertIn('reuses an original capture',result.stderr)
   self.assertFalse((root/'reused').exists())
if __name__=='__main__':unittest.main()
