"""Collect local Gowin reports for review; does not declare hardware PASS."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--uart',type=Path,help='Optional serial log from the real board')
args=parser.parse_args();output=ROOT/'BAO_CAO_GOWIN_V6.zip'
if output.exists():raise SystemExit('Output exists; rename the previous BAO_CAO_GOWIN_V6.zip before collecting another run.')
files=[]
for folder in ('impl','build'):
    if (ROOT/folder).is_dir():
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and (p.suffix.lower() in ('.html','.htm','.rpt','.log') or p.name.lower()=='result.log'))
if not files:raise SystemExit('No Gowin reports found yet. Run Synthesize and Place & Route for gateway_phan1_v6.gprj first.')
entries={p.relative_to(ROOT).as_posix():p.read_bytes() for p in sorted(files)}
for name in ('gateway_phan1_v6.gprj','board/tangnano9k.sdc','board/tangnano9k.cst'):
    p=ROOT/name
    if p.is_file():entries[name]=p.read_bytes()
if args.uart:entries['board_uart.log']=args.uart.read_bytes()
metadata={'kind':'unreviewed_local_gowin_reports_v6','model_sha256':hashlib.sha256((ROOT/'rtl/part2_ai/model.json').read_bytes()).hexdigest(),
          'firmware_sha256':hashlib.sha256((ROOT/'fw/firmware.hex').read_bytes()).hexdigest(),
          'files':{n:hashlib.sha256(data).hexdigest() for n,data in entries.items()},'board_pass_claimed':False}
entries['COLLECTION.json']=(json.dumps(metadata,indent=2)+'\n').encode()
with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
    for name,data in entries.items():archive.writestr(name,data)
print('Created:',output)
print('Reports collected for review. Timing, wiring and board operation still require assessment.')
