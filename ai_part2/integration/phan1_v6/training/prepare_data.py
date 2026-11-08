"""Controlled packet-derived development profiles from the exact existing sources."""
import csv,gzip,hashlib,json,struct,sys,collections,math,io,argparse
from pathlib import Path
from scapy.utils import RawPcapReader
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP,TCP
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'runtime'))
from part2.features import NAMES,quantize
from part2.filtered_training_data import packet_fields
import sqlite3
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--syn-pcap',type=Path,default=ROOT/'sources/syn34.pcap.gz')
parser.add_argument('--normal-pcap',type=Path,default=ROOT/'sources/normal34.pcap.gz')
parser.add_argument('--scan-pcap',type=Path,default=ROOT/'sources/vertical_scan.pcap')
parser.add_argument('--native-cache',type=Path,default=ROOT/'cache/native_patterns.sqlite')
args=parser.parse_args()
SYN,NORMAL,SCAN,OUT=args.syn_pcap,args.normal_pcap,args.scan_pcap,args.output
DIV=[8,2,1,1,1,1]
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(path):
 with RawPcapReader(str(path)) as rd:
  assert rd.linktype==1 and not rd.nano
  return [(raw,m.sec*1000000+m.usec,m.wirelen,idx) for idx,(raw,m) in enumerate(rd)]
def load():
 assert sha(SYN)=='e9adf7269ba420ffa57c552e8d7b0dd1150fec50da8cb9bad1b9db831dcfd9d9'
 assert sha(NORMAL)=='c01e177831761294b5eacd8325e5ab646b2cbeda35f4956e16b4f0cdb590cb9d'
 assert sha(SCAN)=='dec17c51b1b9d464831edb6e1f0a5bbcbeabdc519bfb4a5a402803384adb257c'
 syn=read(SYN);normal=read(NORMAL);scan=read(SCAN)
 syns={};replies=set();acks=[]
 for raw,t,wire,idx in normal:
  if raw[12:14]!=b'\x08\x00' or raw[23]!=6:continue
  p=Ether(raw);ip=p[IP];tcp=p[TCP];flags=int(tcp.flags)
  if flags&0x12==2:syns[ip.src,int(tcp.sport),ip.dst,int(tcp.dport)]=(raw,t,wire,idx)
  if flags&0x12==0x12:replies.add((ip.dst,int(tcp.dport),ip.src,int(tcp.sport)))
  if flags&0x12==0x10 and 40<=int(ip.len)<=96:acks.append((raw,t,wire,idx))
 opens=[syns[k] for k in sorted(set(syns)&replies)]
 assert len(opens)>=8 and len(acks)>=64
 # Benign SYN templates are from recorded handshakes, excluding unresolved dense SYN-only flows.
 return syn,scan,opens,acks[:128]
normal_labels={}
if sha(args.native_cache)!='b76850743125c9b68c9d2419200515de9e7d53a326993532d768c6671d882e76':raise ValueError('Native cache checksum changed')
with sqlite3.connect(args.native_cache) as db:
 for label,packed,count in db.execute('SELECT label,packed,count FROM patterns'):
  normal_labels.setdefault(packed,set()).add(label)
transformed={}
def address(template,target,port,client):
 key=(template[3],target,port,client)
 if key not in transformed:
  p=Ether(template[0]);p[IP].src='198.18.0.'+str(2+client);p[IP].dst=target;p[TCP].dport=port
  del p[IP].chksum;del p[TCP].chksum
  transformed[key]=bytes(p)
 return transformed[key]
PROFILES=['none','one_syn','sensor7','sensor7_other','two_sensors14']
def backgrounds(start,end,target,service,profile,opens,acks):
 if profile=='none':return []
 clients=2 if profile=='two_sensors14' else 1
 per=1 if profile=='one_syn' else 7
 events=[];seq=0
 for slot in range(int((end-start)//1000000)+1):
  for client in range(clients):
   for j in range(per):
    timestamp=start+slot*1000000+(j+1)*1000000//(per+1)+client*1000
    if timestamp>end:continue
    template=opens[(seq//7)%len(opens)] if j==0 else acks[seq%len(acks)]
    port=1883 if profile=='sensor7_other' else service
    raw=address(template,target,port,client);events.append((timestamp,raw,len(raw),False,template[3]));seq+=1
 return events
specs=[]
def emit(name,attack,label,split,target,service,profile,opens,acks,rate=None,scale=None,phase=125000,duration=None,normal_per=None):
 origin=1800000000*1000000+phase
 if attack:
  first,last=attack[0][1],attack[-1][1]
  span=(len(attack)-1)*1000000/rate if rate else (last-first)*scale
  end=origin+int(round(span));events=[]
  for raw,t,wire,idx in attack:
   timestamp=origin+int(round((t-first)*span/(last-first)))
   events.append((timestamp,raw,wire,True,idx))
 else:
  end=origin+duration*1000000;events=[]
 events+=backgrounds(origin,end,target,service,profile,opens,acks)
 if not attack and normal_per:
  # Real normal packet templates scheduled at controlled rates, same receiver and 1-2 sources.
  events=[]
  for i in range(duration*normal_per):
   timestamp=origin+i*1000000//normal_per
   temp=opens[(i//7)%len(opens)] if i%7==0 else acks[i%len(acks)]
   client=(i%2) if profile=='two_sensors14' else 0
   port=1883 if profile=='sensor7_other' else service
   raw=address(temp,target,port,client);events.append((timestamp,raw,len(raw),False,temp[3]))
 events.sort(key=lambda e:(e[0],not e[3],e[4]));windows={}
 path=OUT/'pcap'/(name+'.pcap.gz')
 with path.open('wb') as file,gzip.GzipFile(filename='',fileobj=file,mode='wb',mtime=0) as stream:
  stream.write(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1))
  for t,raw,wire,isattack,index in events:
   sec,usec=divmod(t,1000000);stream.write(struct.pack('<IIII',sec,usec,len(raw),wire));stream.write(raw)
   fields=packet_fields(memoryview(raw),1);assert fields and fields[0]==int.from_bytes(bytes(map(int,target.split('.'))),'big')
   dst,src,size,port,syn=fields
   w=windows.setdefault(sec,dict(n=0,size=0,syn=0,src=set(),ports=set(),attack_n=0,attack_ports=set(),background_n=0))
   w['n']+=1;w['size']+=size;w['syn']+=int(syn);w['src'].add(src)
   if port!=65536:w['ports'].add(port)
   if isattack:w['attack_n']+=1;w['attack_ports'].add(port)
   else:w['background_n']+=1
 rows=[];reasons=collections.Counter()
 for sec,w in sorted(windows.items()):
  if sec*1000000<origin or (sec+1)*1000000>end:continue
  raw=[w['n'],w['size']//w['n'],127*w['syn']//w['n'],len(w['src']),1,len(w['ports'])]
  q=quantize(raw,DIV).tolist();packed=sum(v<<(8*i) for i,v in enumerate(q))
  reason='eligible'
  if label==1 and w['attack_n']<20:reason='sparse_attack_needs_context'
  if label==2 and len(w['attack_ports'])<3:reason='sparse_scan_needs_context'
  if reason=='eligible' and any(l!=label for l in normal_labels.get(packed,set())):reason='native_label_alias_ambiguous'
  reasons[reason]+=1
  rows.append([name,split,label,sec,reason,w['attack_n'],len(w['attack_ports']),w['background_n'],*raw,*q])
 csvpath=OUT/'features'/(name+'.csv.gz')
 with csvpath.open('wb') as cf,gzip.GzipFile(filename='',fileobj=cf,mode='wb',mtime=0) as gz,io.TextIOWrapper(gz,newline='') as f:
  writer=csv.writer(f,lineterminator='\n');writer.writerow(['profile','split','label','window_start','status','attack_count','attack_port_count','background_count',*NAMES,*['q'+str(i) for i in range(6)]]);writer.writerows(rows)
 specs.append(dict(id=name,split=split,label=label,target=target,rate=rate,time_scale=scale,normal_profile=profile,
  parent_group='IoT23/SYN34_one_episode' if label==1 else 'ChrisSanders/scan_one_episode' if label==2 else 'IoT23/Normal34',
  pcap=str(path.relative_to(OUT)),pcap_sha256=sha(path),features=str(csvpath.relative_to(OUT)),features_sha256=sha(csvpath),
  frames=len(events),attack_frames=len(attack),windows=len(rows),status_counts=dict(reasons),phase_microseconds=phase,
  original_attack_record_range=[attack[0][3],attack[-1][3]] if attack else None))
 print(name,dict(reasons),flush=True)
def run():
 if OUT.exists():raise ValueError('Output exists; preserve generated profiles')
 (OUT/'pcap').mkdir(parents=True);(OUT/'features').mkdir()
 syn,scan,opens,acks=load()
 target='64.13.134.52';scan=[p for p in scan if packet_fields(memoryview(p[0]),1) and packet_fields(memoryview(p[0]),1)[0]==0x400d8634]
 assert len(scan)==1994
 for split,rates,segment,phase in [('train',[32,64,128,256,512,1024,2048],syn[:12000],125000),('development',[48,96,192,384,768,1536],syn[12000:24000],625000)]:
  for rate in rates:
   for profile in PROFILES:emit(f'syn_{split}_{rate}_{profile}',segment,1,split,'71.61.66.148',80,profile,opens,acks,rate=rate,phase=phase)
  for scale in ([2,8,32,128] if split=='train' else [4,16,64]):
   for profile in PROFILES[1:]:emit(f'scan_{split}_{scale}_{profile}',scan,2,split,target,1883,profile,opens,acks,scale=scale,phase=phase)
  for rate in ([1,7,14,64,256] if split=='train' else [2,21,96,192]):
   for profile in ['sensor7','sensor7_other','two_sensors14']:
    emit(f'normal_{split}_{rate}_{profile}',[],0,split,'71.61.66.148',80,profile,opens,acks,duration=30,normal_per=rate,phase=phase)
 manifest=dict(kind='controlled_packet_derived_v6_development',sources={k:dict(path='sources/'+{'syn34':'syn34.pcap.gz','normal34':'normal34.pcap.gz','scan':'vertical_scan.pcap'}[k],sha256=sha(p)) for k,p in [('syn34',SYN),('normal34',NORMAL),('scan',SCAN)]},
  original_base_v5_model_sha256='688f1109f77da566c542c4903a0555be79cbf3e22ea08866187de20de68b7b8e',
  same_original_training_groups=True,new_independent_attack_episodes=0,profiles=specs,source_templates=dict(normal_syn_record_ids=[x[3] for x in opens],normal_ack_record_ids=[x[3] for x in acks]),
  transforms=['Attack frame bytes preserved; only timestamp spacings scaled to requested rates.',
   'Background packet templates are from original Native Benign normal34; SYN templates have recorded SYN-ACK replies.',
   'Background source/destination IP and TCP destination port remapped to combine traffic at one protected receiver; IP/TCP checksums recomputed.',
   'Derived labels are controlled scenario annotations, not new publisher-provided labels.',
   'Keep all original cache labels. Derived windows aliasing another original native label are retained as ambiguous and excluded from fit/selection; report them separately.',
   'Development rates and timestamps differ from training profiles but share the same parent captures; not an independent test.'])
 (OUT/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('DONE',len(specs),'profiles',flush=True)
if __name__=='__main__':run()
