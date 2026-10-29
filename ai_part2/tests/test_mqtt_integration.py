"""Optional real loopback integration; no external network or privileged namespace."""
import json,os,socket,subprocess,sys,tempfile,time,unittest
from pathlib import Path

@unittest.skipUnless(os.environ.get('PART2_MOSQUITTO_BIN'),'Set PART2_MOSQUITTO_BIN for real MQTT integration')
class MQTTIntegration(unittest.TestCase):
 def exercise(self,prefixes,payload_bytes=0):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
   log=(root/'broker.log').open('w')
   broker=subprocess.Popen([os.environ['PART2_MOSQUITTO_BIN'],'-p',str(port)],stdout=log,stderr=log)
   observer=None;sensors=[];received=None
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
    for prefix in prefixes:
     sensors.append(subprocess.Popen([sys.executable,'lab/sensor_client.py','--host','127.0.0.1','--port',str(port),'--count','3','--interval','.2','--client-prefix',prefix,'--payload-bytes',str(payload_bytes)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE))
    for sensor in sensors:
     stdout,stderr=sensor.communicate(timeout=20)
     self.assertEqual(sensor.returncode,0,stderr)
     rows=[json.loads(x) for x in stdout.splitlines()]
     self.assertEqual(len(rows),3)
     self.assertTrue(all(r['ok'] for r in rows),rows)
    time.sleep(.2);observer.terminate();observer.wait(timeout=3);observer=None;received.close();received=None
    messages=[json.loads(x) for x in (root/'received.jsonl').read_text().splitlines()]
    if payload_bytes:self.assertTrue(all(len(r['payload'].get('padding',''))==payload_bytes for r in messages))
    actual={(r['payload']['sensor_id'],r['payload']['seq']) for r in messages}
    expected={(prefix,seq) for prefix in prefixes for seq in range(3)}
    self.assertEqual(actual,expected)
   finally:
    for sensor in sensors:
     if sensor.poll() is None:sensor.terminate();sensor.wait(timeout=3)
    if observer:observer.terminate();observer.wait(timeout=3)
    if received:received.close()
    broker.terminate();broker.wait(timeout=3);log.close()
 def test_real_publish_and_receive(self):self.exercise(['one'])
 def test_large_payload_publish(self):self.exercise(['large'],1024)
 def test_two_legitimate_clients_no_id_collision(self):self.exercise(['primary','secondary'])
