"""Read-only monitoring with cumulative counters and explicitly labeled data sources."""
import collections,json,math,os,statistics,threading,time
from pathlib import Path
from part2.logs import decode

class JsonlTail:
    def __init__(self,path):self.path=Path(path);self.position=0;self.identity=None;self.pending=b''
    def poll(self):
        try:
            stat=self.path.stat();identity=(stat.st_dev,stat.st_ino)
            reset=self.identity is not None and (identity!=self.identity or stat.st_size<self.position)
            if reset:self.position=0;self.pending=b''
            self.identity=identity
            with self.path.open('rb') as f:
                f.seek(self.position);data=f.read(1024*1024);self.position=f.tell()
            data=self.pending+data
            if len(data)>2*1024*1024 and b'\n' not in data:
                self.pending=b'';return [],1,reset,'JSON line exceeds 2 MiB'
            parts=data.split(b'\n');self.pending=parts.pop()
            rows=[];bad=0
            for line in parts:
                if not line.strip():continue
                try:row=json.loads(line)
                except (ValueError,UnicodeDecodeError):bad+=1;continue
                if isinstance(row,dict):rows.append(row)
                else:bad+=1
            return rows,bad,reset,None
        except OSError as e:return [],0,False,str(e)

class Monitor:
    def __init__(self,sensor_paths=(),received_path=None,source_mode='NO_FPGA',source_name='',live_mqtt=False,ids_schema='opaque'):
        self.lock=threading.RLock();self.live_mqtt=live_mqtt;self.ids_schema=ids_schema
        self.sensor_paths=[Path(p) for p in sensor_paths]
        self.received_path=Path(received_path) if received_path else None
        self.tails={str(p):JsonlTail(p) for p in self.sensor_paths+([self.received_path] if self.received_path else [])}
        self.sensor={};self.receiver={};self.file_errors={}
        self.source={'mode':source_mode,'name':source_name,'status':'not_connected' if source_mode=='NO_FPGA' else 'starting',
                     'serial_port_selected':source_mode=='SERIAL','error':None}
        self.fpga={'mode':None,'counters':None,'blocked':{},'events':collections.deque(maxlen=200),
                   'bad_frames':0,'ignored_plain_lines':0,'valid_frames':0,'latest_ids_raw':None,'latest_classification':None,'ids_schema':ids_schema}
    def set_source_status(self,status,error=None):
        with self.lock:self.source.update(status=status,error=error)
    def ingest_fpga(self,line,now=None):
        now=time.time() if now is None else now
        with self.lock:
            if not line.lstrip().startswith('$'):
                self.fpga['ignored_plain_lines']+=1;return
            try:event=decode(line)
            except (ValueError,UnicodeError):self.fpga['bad_frames']+=1;return
            kind,fields=event['kind'],event['fields']
            # Semantic validation is separate from checksum validity.
            try:
                if kind=='MODE':
                    if fields[0] not in ('DETECT','BLOCK'):raise ValueError('mode')
                    self.fpga['mode']=fields[0]
                elif kind=='CNT':
                    values=[int(v) for v in fields]
                    if any(v<0 or v>0xffffffff for v in values):raise ValueError('counter')
                    self.fpga['counters']=dict(zip(('forwarded','drop_blacklist','drop_syn_limit','crc_errors','overflow'),values))
                elif kind in ('BLK','UNB'):
                    import ipaddress
                    ip=str(ipaddress.IPv4Address(fields[0]))
                    if kind=='UNB':self.fpga['blocked'].pop(ip,None)
                    else:
                        ttl=int(fields[2])
                        if fields[1] not in ('DOS','SCAN') or not 1<=ttl<=86400:raise ValueError('block data')
                        self.fpga['blocked'][ip]={'ip':ip,'reason':fields[1],'ttl_seconds':ttl,'logged_at':now,'expires_at':now+ttl}
                elif kind=='IDS':
                    if self.ids_schema=='pdf-v1':
                        if len(fields)!=11:raise ValueError('IDS schema field count')
                        vals=[int(v) for v in fields]
                        if any(v<0 for v in vals) or vals[1] not in (0,1,2) or vals[2] not in (0,1,2):raise ValueError('IDS values')
                        self.fpga['latest_classification']=dict(zip(('window_id','raw_class','filtered_class','packet_count','mean_ip_bytes','syn_value_reported','src_count','dst_count','dst_port_count','flags','ai_cycles'),vals))
                    self.fpga['latest_ids_raw']=event['raw']
            except (ValueError,IndexError):self.fpga['bad_frames']+=1;return
            self.fpga['valid_frames']+=1
            self.fpga['events'].append(dict(event,received_at=now))
    def poll_files(self):
        with self.lock:
            for path,tail in self.tails.items():
                rows,bad,reset,error=tail.poll()
                if error:
                    if Path(path).name=='sensor_extra.jsonl' and not Path(path).exists():self.file_errors.pop(path,None)
                    else:self.file_errors[path]=error
                    continue
                self.file_errors.pop(path,None)
                if any(str(p)==path for p in self.sensor_paths):
                    if reset or path not in self.sensor:
                        self.sensor[path]={'attempts':0,'success':0,'failures':0,'invalid':0,'recent_elapsed':collections.deque(maxlen=2000),'recent':collections.deque(maxlen=200)}
                    store=self.sensor[path];store['invalid']+=bad
                    for r in rows:
                        elapsed=r.get('elapsed_ms')
                        if type(r.get('ok')) is not bool or not isinstance(elapsed,(int,float)) or not math.isfinite(elapsed) or elapsed<0:
                            store['invalid']+=1;continue
                        store['attempts']+=1;store['success']+=int(r['ok']);store['failures']+=int(not r['ok'])
                        store['recent_elapsed'].append(float(elapsed));store['recent'].append(r)
                else:
                    if reset or not self.receiver:
                        self.receiver={'total':0,'invalid':0,'samples':collections.deque(maxlen=512),'last_at':None}
                    self.receiver['invalid']+=bad
                    for r in rows:
                        t=r.get('received_at');payload=r.get('payload')
                        if not isinstance(t,(int,float)) or not math.isfinite(t) or not isinstance(payload,dict):
                            self.receiver['invalid']+=1;continue
                        self.receiver['total']+=1;self.receiver['last_at']=t
                        temperature=payload.get('temperature')
                        if isinstance(temperature,(int,float)) and math.isfinite(temperature):
                            self.receiver['samples'].append({'timestamp':t,'temperature':temperature,'sensor_id':str(payload.get('sensor_id','legacy')),'seq':payload.get('seq')})
    def snapshot(self,now=None):
        self.poll_files();now=time.time() if now is None else now
        with self.lock:
            attempts=sum(s['attempts'] for s in self.sensor.values());success=sum(s['success'] for s in self.sensor.values())
            elapsed=sorted(v for s in self.sensor.values() for v in s['recent_elapsed'])
            p95=elapsed[min(len(elapsed)-1,math.ceil(.95*len(elapsed))-1)] if elapsed else None
            last=self.receiver.get('last_at')
            blocked=[dict(v,ttl_elapsed_unconfirmed=now>=v['expires_at']) for v in self.fpga['blocked'].values()]
            return {'source':dict(self.source),'mqtt':{'mode':'LIVE_FILES' if self.live_mqtt else 'FILE_HISTORY',
                    'completed_attempts':attempts,'success':success,'failures':attempts-success,
                    'failure_rate':(attempts-success)/attempts if attempts else None,'p95_recent_elapsed_ms':p95,
                    'p95_scope':'last <=2000 completed attempts per sender file',
                    'received_records':self.receiver.get('total',0),'last_received_at':last,
                    'seconds_since_received':max(0,now-last) if self.live_mqtt and last is not None else None,
                    'samples':list(self.receiver.get('samples',[])),
                    'per_file':[{'path':p,**{k:v for k,v in s.items() if k not in ('recent','recent_elapsed')}} for p,s in self.sensor.items()],
                    'invalid_records':sum(s['invalid'] for s in self.sensor.values())+self.receiver.get('invalid',0)},
                    'fpga':{k:v for k,v in self.fpga.items() if k not in ('events','blocked')},
                    'events':list(self.fpga['events']),'blocked':blocked,'file_errors':dict(self.file_errors),
                    'notes':['Source badge identifies replay versus a connected serial device.',
                             'Serial logs report device actions; they do not independently prove traffic was blocked.',
                             'MQTT counters include completed logged operations only.']}
