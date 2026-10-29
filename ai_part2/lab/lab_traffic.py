"""Bounded traffic for the fixed, isolated namespace lab; no arbitrary target parameter."""
import argparse,random,time,subprocess,signal,socket
from scapy.all import IP,TCP,conf
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['syn','scan','probe'],required=True)
p.add_argument('--seed',type=int,default=29)
p.add_argument('--seconds',type=int,default=20);p.add_argument('--pps',type=int,default=200);a=p.parse_args()
if not 1<=a.seconds<=60 or not 1<=a.pps<=500:p.error('seconds 1..60, pps 1..500')
if a.mode=='probe' and a.pps>10:p.error('benign probe control is limited to 10 attempts/s')
ns=subprocess.check_output(['ip','netns','identify'],text=True).strip()
if ns!='p2source':p.error('Run only inside p2source created by setup_lab.sh')
routes=subprocess.check_output(['ip','route','show','default'],text=True).strip()
if routes:p.error('Lab source must not have a default route')
stopping=False
def stop(signum,frame):
    global stopping
    stopping=True
signal.signal(signal.SIGTERM,stop)
sock=conf.L3socket(iface='eth0') if a.mode!='probe' else None
rng=random.Random(a.seed);began=time.monotonic();i=0
while not stopping and time.monotonic()-began<a.seconds:
    if a.mode=='probe':
        # Explicit normal control: legitimate failed reconnect to one unavailable service.
        try:
            with socket.create_connection(('198.18.0.1',1884),timeout=.3):pass
        except OSError:pass
    else:
        dport=1883 if a.mode=='syn' else 20+i%2000
        pkt=IP(src='198.18.0.3',dst='198.18.0.1')/TCP(sport=rng.randrange(20000,60000),dport=dport,flags='S',seq=rng.randrange(2**31))
        sock.send(pkt)
    i+=1
    deadline=began+i/a.pps
    time.sleep(max(0,deadline-time.monotonic()))
if sock:sock.close()
unit='attempts' if a.mode=='probe' else 'packets'
print(f'mode={a.mode} {unit}={i} elapsed={time.monotonic()-began:.3f}s',flush=True)
