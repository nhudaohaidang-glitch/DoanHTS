"""Local-only minimal dashboard; never changes firewall. Log source is explicitly displayed."""
import argparse,json,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from part2.logs import decode
p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
g.add_argument('--log');g.add_argument('--serial')
p.add_argument('--sensor-log');p.add_argument('--received-log')
p.add_argument('--baud',type=int,default=115200);p.add_argument('--port',type=int,default=8765);a=p.parse_args()
state={'source':('FILE REPLAY: '+a.log) if a.log else ('SERIAL: '+a.serial),'events':[],'bad_checksum_or_format':0,'sensor':[]}
lock=threading.Lock()
if a.serial:
    import serial
    stream=serial.Serial(a.serial,a.baud,timeout=1)
else:
    if not Path(a.log).is_file():p.error('Log file does not exist')
    stream=open(a.log,'rb')
def consume():
    with stream:
        while True:
            line=stream.readline()
            if not line:
                if not a.serial:return
                continue
            try:event=decode(line.decode('ascii'))
            except (UnicodeDecodeError,ValueError):
                with lock:state['bad_checksum_or_format']+=1
                continue
            with lock:
                state['events'].append(dict(event,received_at=time.time()))
                state['events']=state['events'][-100:]
            if not a.serial:time.sleep(.3)
def json_rows(path):
    if not path:return []
    rows=[]
    try:
        with open(path) as f:
            for line in f:
                try:rows.append(json.loads(line))
                except ValueError:continue
                if len(rows)>200:rows=rows[-100:]
    except OSError:return []
    return rows
HTML='''<!doctype html><meta charset="utf-8"><title>Part 2 lab</title>
<style>body{font:16px system-ui;max-width:1000px;margin:30px auto;background:#f4f7fb;color:#18293d}pre{background:white;padding:20px;border-radius:8px;white-space:pre-wrap}b{color:#b33}</style>
<h1>Lab MQTT và AI / FPGA</h1><p id="source"></p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px"><section><h2>Cảm biến MQTT</h2><p id="sensor-source"></p><pre id="sensor"></pre><canvas id="plot" width="450" height="160" style="background:white"></canvas></section><section><h2>Nhật ký FPGA</h2><b id="errors"></b><pre id="events"></pre></section></div>
<p>Đây là bản dashboard tối thiểu. Dữ liệu FILE REPLAY không chứng minh đã chặn trên kit. Không thay đổi firewall.</p>
<script>async function refresh(){let s=await(await fetch('/state')).json();document.getElementById('source').textContent=s.source;document.getElementById('errors').textContent='Dòng lỗi định dạng/checksum: '+s.bad_checksum_or_format;document.getElementById('events').textContent=s.events.map(x=>x.raw).join('\\n');document.getElementById('sensor-source').textContent=s.sensor_source;let ok=s.sensor.filter(x=>x.ok===true).length;let temperatures=s.received.filter(x=>x.payload&&typeof x.payload.temperature==='number');let last=temperatures.at(-1);document.getElementById('sensor').textContent=JSON.stringify({attempts:s.sensor.length,success:ok,failed:s.sensor.filter(x=>x.ok===false).length,last_temperature:last?last.payload.temperature:null,seconds_since_last_received:last?Math.round(Date.now()/1000-last.received_at):null},null,2);let ctx=document.getElementById('plot').getContext('2d');ctx.clearRect(0,0,450,160);ctx.strokeStyle='#1769aa';ctx.beginPath();temperatures.slice(-50).forEach((r,i)=>{let x=10+i*8,y=140-(r.payload.temperature-25)*20;i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke()}setInterval(refresh,500);refresh()</script>'''
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
    if self.path=='/state':
        with lock: snapshot=dict(state)
        snapshot['sensor']=json_rows(a.sensor_log)
        snapshot['received']=json_rows(a.received_log)
        snapshot['sensor_source']='Sensor: '+str(a.sensor_log or 'not connected')+' | Received: '+str(a.received_log or 'not connected')
        content=json.dumps(snapshot).encode()
        kind='application/json'
    elif self.path=='/':content=HTML.encode();kind='text/html; charset=utf-8'
    else:self.send_error(404);return
    self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
 def log_message(self,*args):pass
threading.Thread(target=consume,daemon=True).start()
print(f'Local dashboard port {a.port}; source: {state["source"]}',flush=True)
ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
