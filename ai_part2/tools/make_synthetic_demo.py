"""Artificial PCAPs only: validate the pipeline, never report these metrics as network accuracy."""
import argparse,csv,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scapy.all import Ether,IP,TCP,UDP,Raw,PcapWriter
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
out=Path(a.output)
if out.exists():p.error('Output exists; choose new output')
out.mkdir(parents=True)
rng=np.random.default_rng(51);entries=[]
for split in ('train','val','test'):
    for label in (0,1,2):
        for repetition in range(2):
            capture_id=f'{split}_{label}_{repetition}'
            path=out/(capture_id+'.pcap')
            base=1700000000+len(entries)*1000
            with PcapWriter(str(path),sync=True) as writer:
                for window in range(20):
                    n=int(rng.integers(20,65) if label==0 else rng.integers(220,400) if label==1 else rng.integers(50,120))
                    for i in range(n):
                        if label==0:
                            pkt=Ether(src="02:00:00:00:00:02",dst="02:00:00:00:00:01")/IP(src='198.18.0.2',dst='198.18.0.1')/TCP(sport=45000+i,dport=1883,flags='PA')/Raw(b'x'*int(rng.integers(50,150)))
                        else:
                            pkt=Ether(src="02:00:00:00:00:02",dst="02:00:00:00:00:01")/IP(src='198.18.0.3',dst='198.18.0.1')/TCP(sport=30000+i,dport=1883 if label==1 else 20+i,flags='S')
                        pkt.time=base+window+(i+.1)/n
                        writer.write(pkt)
            entries.append(dict(capture_id=capture_id,pcap=path.name,split=split,label=label,
                                start=base,end=base+20,source_kind='synthetic',target_net='198.18.0.1/32'))
with (out/'manifest.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(entries[0]));w.writeheader();w.writerows(entries)
print('SYNTHETIC ONLY:',out/'manifest.csv')
