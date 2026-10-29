"""Read-only measurements of the current namespace's TCP stack, not a stress tool."""
import argparse,json,signal,time
p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=30);a=p.parse_args()
stop=False
def terminate(*args):
 global stop
 stop=True
signal.signal(signal.SIGTERM,terminate)
KEYS={'SyncookiesSent','ListenOverflows','ListenDrops','TCPReqQFullDoCookies','TCPReqQFullDrop','TCPSynRetrans'}
def snapshot():
 from pathlib import Path
 lines=Path('/proc/net/netstat').read_text().splitlines();counters={}
 for i in range(0,len(lines)-1,2):
  header,values=lines[i].split(),lines[i+1].split()
  if header and header[0]=='TcpExt:':counters={k:int(v) for k,v in zip(header[1:],values[1:]) if k in KEYS}
 states={}
 for line in Path('/proc/net/tcp').read_text().splitlines()[1:]:
  fields=line.split();state={'03':'SYN_RECV','01':'ESTABLISHED','0A':'LISTEN'}.get(fields[3])
  if state:states[state]=states.get(state,0)+1
 return {'timestamp':time.time(),'tcp_ext':counters,'tcp_states':states}
end=time.monotonic()+a.seconds
while True:
 print(json.dumps(snapshot()),flush=True)
 if stop or time.monotonic()>=end:break
 time.sleep(.5)
