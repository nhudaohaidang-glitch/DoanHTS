"""Read-only local MQTT/FPGA dashboard. Defaults to NO FPGA, never fabricates device logs."""
import argparse,json,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from part2.monitor import Monitor


def handler_for(monitor,html,evaluation_note=''):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=='/state':
                value=monitor.snapshot();value['evaluation_note']=evaluation_note
                content=json.dumps(value,allow_nan=False).encode();kind='application/json'
            elif self.path=='/':content=html;kind='text/html; charset=utf-8'
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
        def log_message(self,*args):pass
    return Handler


def main():
    p=argparse.ArgumentParser(description=__doc__);source=p.add_mutually_exclusive_group()
    source.add_argument('--log');source.add_argument('--follow-log');source.add_argument('--serial')
    p.add_argument('--session');p.add_argument('--sensor-log',action='append',default=[]);p.add_argument('--received-log')
    p.add_argument('--live-mqtt',action='store_true');p.add_argument('--baud',type=int,default=115200)
    p.add_argument('--ids-schema',choices=['opaque','pdf-v1'],default='opaque')
    p.add_argument('--port',type=int,default=8765);p.add_argument('--evaluation')
    a=p.parse_args();sensor_paths=a.sensor_log;received=a.received_log
    if a.session:
        if sensor_paths or received:p.error('Use --session OR explicit sensor/received files')
        root=Path(a.session)
        if not a.live_mqtt and not root.is_dir():p.error('Session does not exist; for a new live capture add --live-mqtt')
        sensor_paths=[str(root/'sensor.jsonl')]
        if a.live_mqtt or (root/'sensor_extra.jsonl').exists():sensor_paths.append(str(root/'sensor_extra.jsonl'))
        received=str(root/'received.jsonl')
    mode='SERIAL' if a.serial else 'FILE_FOLLOW' if a.follow_log else 'FILE_REPLAY' if a.log else 'NO_FPGA'
    name=a.serial or a.follow_log or a.log or 'No hardware log source selected'
    monitor=Monitor(sensor_paths,received,mode,name,a.live_mqtt,a.ids_schema);stop=threading.Event()
    note=''
    if a.evaluation:
        report=json.loads(Path(a.evaluation).read_text())
        if report.get('kind')!='frozen_challenge_evaluation':p.error('Expected a frozen challenge metrics.json')
        note=f"ĐÁNH GIÁ NGOẠI TUYẾN: {report['ai']['windows']} cửa sổ; AI accuracy={report['ai']['accuracy']:.4f}; baseline={report['baseline']['accuracy']:.4f}. Không phải đánh giá chặn trên kit."
    stream=None
    if a.serial:
        import serial
        stream=serial.Serial(a.serial,a.baud,timeout=1)
    elif a.log:
        if not Path(a.log).is_file():p.error('Log file does not exist')
        stream=open(a.log,'rb')
    def reader():
        monitor.set_source_status('reading')
        try:
            if a.follow_log:
                position=0;identity=None;pending=b''
                while not stop.is_set():
                    try:
                        path=Path(a.follow_log);stat=path.stat();newid=(stat.st_dev,stat.st_ino)
                        if identity is not None and (newid!=identity or stat.st_size<position):position=0;pending=b''
                        identity=newid
                        with path.open('rb') as f:f.seek(position);data=f.read(65536);position=f.tell()
                        parts=(pending+data).split(b'\n');pending=parts.pop()
                        for line in parts:monitor.ingest_fpga(line.decode('ascii',errors='replace'))
                        monitor.set_source_status('following')
                    except FileNotFoundError:monitor.set_source_status('waiting_for_file')
                    stop.wait(.2)
            else:
                with stream:
                    while not stop.is_set():
                        line=stream.readline(8192)
                        if not line:
                            if not a.serial:break
                            continue
                        monitor.ingest_fpga(line.decode('ascii',errors='replace'))
                        if not a.serial:stop.wait(.1)
                monitor.set_source_status('stopped' if a.serial else 'replay_complete')
        except Exception as e:monitor.set_source_status('error',str(e))
    worker=None
    if mode!='NO_FPGA':worker=threading.Thread(target=reader,daemon=True);worker.start()
    html=(Path(__file__).resolve().parents[1]/'ui/dashboard.html').read_bytes()
    server=ThreadingHTTPServer(('127.0.0.1',a.port),handler_for(monitor,html,note))
    print(f'Dashboard local port {server.server_port}; source={mode}; Ctrl+C to stop',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        stop.set();server.server_close()
        if worker:worker.join(timeout=2)

if __name__=='__main__':main()
