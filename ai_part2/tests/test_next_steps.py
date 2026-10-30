"""Artificial unit fixtures, not real attack evaluation results."""
import importlib.util,json,tempfile,threading,unittest
from pathlib import Path
from urllib.request import urlopen
import numpy as np
from part2.assessment import evaluate_frozen,compare_sessions
from part2.monitor import Monitor
KIT=Path(__file__).resolve().parents[1]

def model():
 w1=np.zeros((8,6),dtype=int);w1[0,0]=1;w1[1,5]=2
 w2=np.zeros((3,8),dtype=int);w2[1,0]=1;w2[2,1]=1
 return dict(w1=w1.tolist(),b1=[0]*8,w2=w2.tolist(),b2=[5,0,0],shift1=0,shift2=0,divisors=[1]*6)

def row(name,label,values):
 names=['packet_count','mean_ip_bytes','syn_ratio_q127','src_count','dst_count','dst_port_count']
 return dict(capture_id=name,label=str(label),split='challenge',source_kind='lab',window_start=100,**dict(zip(names,values)))

class AssessmentTest(unittest.TestCase):
 def test_frozen_results_and_saturation(self):
  rows=[row('normal',0,[1,40,0,2,1,1]),row('syn',1,[20,40,100,2,1,1]),row('scan',2,[3,40,100,2,1,10])]
  m=model();before=json.dumps(m,sort_keys=True)
  baseline=dict(packet_threshold=10,port_threshold=5,syn_ratio_q127_threshold=32)
  report,details=evaluate_frozen(rows,m,baseline)
  self.assertEqual(report['ai']['confusion_matrix'],[[1,0,0],[0,1,0],[0,0,1]])
  self.assertEqual(report['baseline']['accuracy'],1)
  self.assertFalse(report['model_retrained']);self.assertEqual(json.dumps(m,sort_keys=True),before)
  rows[1]['packet_count']=10000
  report,_=evaluate_frozen(rows,m,baseline)
  self.assertEqual(report['input_saturation'][0]['clipped_windows'],1)
 def test_old_split_and_synthetic_refused(self):
  sample=row('old',0,[1,40,0,1,1,1]);sample['split']='test'
  with self.assertRaises(ValueError):evaluate_frozen([sample],model(),{})
  sample['split']='challenge';sample['source_kind']='synthetic'
  with self.assertRaises(ValueError):evaluate_frozen([sample],model(),{})
 def session(self,path,fail=False):
  path.mkdir()
  rows=[dict(timestamp=100+i,seq=i,ok=not(fail and i==1),elapsed_ms=10*(i+1)) for i in range(3)]
  (path/'sensor.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
  received=[dict(received_at=100+i+.01,payload=dict(seq=i,sent_at=100+i,temperature=28)) for i in (0,2)]
  (path/'received.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in received))
  (path/'scenario.txt').write_text('sensor_interval=1\n')
 def test_comparison_reports_failure_and_limits(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.session(root/'before');self.session(root/'during',True)
   r=compare_sessions(root/'before',root/'during',True)
   self.assertEqual(r['during']['failures'],1);self.assertEqual(r['during']['received_unique_messages'],2)
   self.assertAlmostEqual(r['during']['send_to_receive_ms_p95'],10)
   self.assertFalse(r['hardware_blocking_verified']);self.assertTrue(r['legitimate_load_comparable'])
   r=compare_sessions(root/'before',root/'before')
   self.assertIn('NOT demonstrated',r['notes'][0]);self.assertIsNone(r['during']['send_to_receive_ms_p95'])

class MonitorTest(unittest.TestCase):
 def test_partial_lines_cumulative_counts_and_truncation(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'sensor.jsonl';path.write_text('{"ok":true')
   m=Monitor([path]);self.assertEqual(m.snapshot()['mqtt']['completed_attempts'],0)
   with path.open('a') as f:
    f.write(',"elapsed_ms":1}\n')
    for _ in range(249):f.write('{"ok":true,"elapsed_ms":2}\n')
   self.assertEqual(m.snapshot()['mqtt']['completed_attempts'],250)
   self.assertEqual(m.snapshot()['mqtt']['success'],250)
   path.write_text('{"ok":false,"elapsed_ms":3}\n')
   self.assertEqual(m.snapshot()['mqtt']['completed_attempts'],1)
 def test_checksum_semantics_source_and_unblock(self):
  from part2.logs import encode
  m=Monitor(source_mode='FILE_REPLAY',source_name='sample')
  for line in ['MODE,BLOCK','CNT,10,2,1,0,0','BLK,198.18.0.3,DOS,60']:m.ingest_fpga(encode(line),100)
  m.ingest_fpga('$CNT,1,2,3,4,5*00',100)
  s=m.snapshot(200)
  self.assertFalse(s['source']['serial_port_selected']);self.assertEqual(s['source']['mode'],'FILE_REPLAY')
  self.assertTrue(s['blocked'][0]['ttl_elapsed_unconfirmed']);self.assertEqual(s['fpga']['counters']['forwarded'],10)
  self.assertEqual(s['fpga']['bad_frames'],1)
  m.ingest_fpga(encode('UNB,198.18.0.3'),201);self.assertFalse(m.snapshot(201)['blocked'])
  m.ingest_fpga(encode('CNT,-1,0,0,0,0'),201);self.assertEqual(m.snapshot()['fpga']['bad_frames'],2)
 def test_ids_schema_is_opt_in(self):
  from part2.logs import encode
  line=encode('IDS,5,1,1,7065,62,99,253,1,2,0,84')
  opaque=Monitor();opaque.ingest_fpga(line)
  self.assertIsNone(opaque.snapshot()['fpga']['latest_classification'])
  parsed=Monitor(ids_schema='pdf-v1');parsed.ingest_fpga(line)
  self.assertEqual(parsed.snapshot()['fpga']['latest_classification']['raw_class'],1)
 def test_history_no_live_age_and_http(self):
  spec=importlib.util.spec_from_file_location('dashboard',KIT/'tools/dashboard.py')
  dash=importlib.util.module_from_spec(spec);spec.loader.exec_module(dash)
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'received.jsonl';path.write_text(json.dumps(dict(received_at=100,payload=dict(temperature=28,sensor_id='one')))+'\n')
   m=Monitor(received_path=path);self.assertIsNone(m.snapshot(1000)['mqtt']['seconds_since_received'])
   server=dash.ThreadingHTTPServer(('127.0.0.1',0),dash.handler_for(m,b'<html>dashboard</html>'))
   t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
   try:
    with urlopen(f'http://127.0.0.1:{server.server_port}/state',timeout=2) as response:s=json.load(response)
    self.assertEqual(s['source']['mode'],'NO_FPGA');self.assertEqual(s['mqtt']['received_records'],1)
   finally:server.shutdown();server.server_close();t.join()

if __name__=='__main__':unittest.main()
