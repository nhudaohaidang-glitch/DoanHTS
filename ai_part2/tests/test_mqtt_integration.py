"""Optional real loopback integration; no external network or privileged namespace."""
import json,os,socket,subprocess,sys,tempfile,time,unittest
from pathlib import Path

@unittest.skipUnless(os.environ.get('PART2_MOSQUITTO_BIN'),'Set PART2_MOSQUITTO_BIN for real MQTT integration')
class MQTTIntegration(unittest.TestCase):
 def test_real_publish_and_receive(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
   # Mosquitto 2.x without a config starts in local-only mode. Avoid custom
   # config paths that Ubuntu AppArmor may deny (especially temporary dirs).
   log=(root/'broker.log').open('w')
   broker=subprocess.Popen([os.environ['PART2_MOSQUITTO_BIN'],'-p',str(port)],stdout=log,stderr=log)
   observer=None
   try:
    for _ in range(40):
     if broker.poll() is not None:raise RuntimeError('broker failed: '+(root/'broker.log').read_text())
     try:
      with socket.create_connection(('127.0.0.1',port),timeout=.2):break
     except OSError:time.sleep(.05)
    else:raise RuntimeError('broker did not become ready: '+(root/'broker.log').read_text())
    received=(root/'received.jsonl').open('w')
    observer=subprocess.Popen([sys.executable,'-u','lab/broker_observer.py','--host','127.0.0.1','--port',str(port)],stdout=received,stderr=subprocess.STDOUT)
    time.sleep(.5)
    sensor=subprocess.run([sys.executable,'lab/sensor_client.py','--host','127.0.0.1','--port',str(port),'--count','3','--interval','.2'],text=True,capture_output=True,timeout=20)
    self.assertEqual(sensor.returncode,0,sensor.stderr)
    rows=[json.loads(x) for x in sensor.stdout.splitlines()]
    self.assertEqual(len(rows),3)
    self.assertTrue(all(r['ok'] for r in rows),rows)
    time.sleep(.2);observer.terminate();observer.wait(timeout=3);observer=None;received.close()
    messages=[json.loads(x) for x in (root/'received.jsonl').read_text().splitlines()]
    self.assertEqual([r['payload']['seq'] for r in messages],[0,1,2])
   finally:
    if observer:observer.terminate();observer.wait(timeout=3)
    broker.terminate();broker.wait(timeout=3);log.close()
