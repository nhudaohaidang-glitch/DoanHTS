import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from part2.assessment import compare_sessions
p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--during',required=True)
p.add_argument('--output',required=True);p.add_argument('--shared-clock',action='store_true')
a=p.parse_args();out=Path(a.output)
if out.exists():p.error('Output exists; preserve prior report')
report=compare_sessions(a.baseline,a.during,a.shared_clock)
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
