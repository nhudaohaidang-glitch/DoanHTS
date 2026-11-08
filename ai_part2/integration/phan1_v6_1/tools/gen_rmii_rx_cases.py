"""Generate reproducible offline RMII regression fixtures in a new directory."""
from pathlib import Path
import argparse,zlib,random,json
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
sim=a.output
if sim.exists():raise SystemExit('Output exists; use a new folder')
sim.mkdir(parents=True)
rng=random.Random(6112026);cases=[];data=[]
lengths=[60,64,70,127,256,512,1514,1518]
for phase in (2,8,14):
 for n in lengths:
  payload=bytes(rng.randrange(256) for _ in range(n));good=len(cases)%4!=3
  fcs=bytearray(zlib.crc32(payload).to_bytes(4,'little'))
  if not good:fcs[0]^=0x80
  packet=payload+fcs;cases.append(dict(payload_bytes=n,received_bytes=len(packet),good_crc=good,phase_ns=phase));data.extend(packet)
for i in range(16):
 n=rng.randrange(60,1519);payload=bytes(rng.randrange(256) for _ in range(n));good=i%4!=3
 fcs=bytearray(zlib.crc32(payload).to_bytes(4,'little'))
 if not good:fcs[-1]^=1
 packet=payload+fcs;cases.append(dict(payload_bytes=n,received_bytes=len(packet),good_crc=good,phase_ns=(lambda p: 9 if p==10 else p)(rng.randrange(1,19))));data.extend(packet)
(sim/'rmii_rx_packets.hex').write_text(''.join(f'{v:02x}\n' for v in data))
(sim/'rmii_rx_cases.json').write_text(json.dumps(dict(kind='offline_rmii_waveforms_not_training_data',generator_seed=6112026,crc_reference='Python zlib.crc32',cases=cases,total_received_bytes=len(data)),indent=2)+'\n')
lines=[f'localparam integer CASES={len(cases)}, TOTAL_BYTES={len(data)};', 'integer frame_len[0:CASES-1], phase[0:CASES-1];','reg good[0:CASES-1];','initial begin']
for i,c in enumerate(cases):lines.append(f" frame_len[{i}]={c['received_bytes']}; phase[{i}]={c['phase_ns']}; good[{i}]=1'b{int(c['good_crc'])};")
lines+=['end',''];(sim/'rmii_rx_cases.vh').write_text('\n'.join(lines))
print(len(cases),len(data),'fixture bytes')
