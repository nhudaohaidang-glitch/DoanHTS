"""Collect only the independent onboard-demo project reports for review."""
import argparse,hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--uart',type=Path);a=p.parse_args()
output=root/'BAO_CAO_DEMO_V6_1.zip'
if output.exists():raise SystemExit('Output exists; rename the previous BAO_CAO_DEMO_V6_1.zip first.')
stem='gateway_phan1_v6_1_demo'
reports=[p for p in (root/'impl').rglob('*') if p.is_file() and p.name.startswith(stem) and p.suffix.lower() in ('.log','.html','.htm','.rpt','.txt')]
if not reports:raise SystemExit('No demo reports. Run Synthesize and Place & Route for '+stem+'.gprj first.')
entries={p.relative_to(root).as_posix():p.read_bytes() for p in sorted(reports)}
for name in (stem+'.gprj','board/tangnano9k_demo.cst','board/tangnano9k_demo.sdc','build/gowin_demo/gowin_demo_top.v','sources.f','rtl/board/tangnano9k_top.v','rtl/stubs/eth_stub.v','rtl/part2_ai/ai_core_model_v6.v'):
 path=root/name
 if path.is_file():entries[name]=path.read_bytes()
if a.uart:entries['board_demo_uart.log']=a.uart.read_bytes()
meta={'kind':'unreviewed_cpu_ai_onboard_demo','mode':1,'top':'gowin_demo_top','clock_mhz':27,
      'model_sha256':hashlib.sha256((root/'rtl/part2_ai/model.json').read_bytes()).hexdigest(),
      'firmware_sha256':hashlib.sha256((root/'fw/firmware.hex').read_bytes()).hexdigest(),
      'files':{n:hashlib.sha256(data).hexdigest() for n,data in entries.items()},
      'physical_ethernet_tested':False,'board_pass_claimed':False}
entries['COLLECTION.json']=(json.dumps(meta,indent=2)+'\n').encode()
with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for name,data in entries.items():z.writestr(name,data)
print('Created:',output)
print('Independent demo reports collected; no physical Ethernet or board PASS inferred.')
