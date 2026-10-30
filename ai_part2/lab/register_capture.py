import argparse,csv,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--id',required=True)
p.add_argument('--split',choices=['train','val','test','challenge'],required=True);p.add_argument('--label',type=int,choices=[0,1,2],required=True)
p.add_argument('--start',type=float,required=True);p.add_argument('--end',type=float,required=True);a=p.parse_args()
directory=Path(a.directory);manifest=directory/'manifest.csv'
rows=[]
if manifest.exists():
 with manifest.open() as f:rows=list(csv.DictReader(f))
if any(r['capture_id']==a.id for r in rows):p.error('Duplicate capture ID')
row=dict(capture_id=a.id,pcap=f'{a.id}/traffic.pcap',split=a.split,label=a.label,
         start=a.start,end=a.end,source_kind='lab',target_net='198.18.0.1/32')
with manifest.open('a',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=list(row))
 if not rows:writer.writeheader()
 writer.writerow(row)
print('Registered',row)
