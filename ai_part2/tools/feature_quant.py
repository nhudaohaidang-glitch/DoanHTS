import argparse, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from part2.features import build_dataset
p=argparse.ArgumentParser()
p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
p.add_argument('--window',type=float,default=1.0)
p.add_argument('--distinct',choices=['exact','bitmap256'],default='exact')
a=p.parse_args()
print(json.dumps(build_dataset(a.manifest,a.output,a.window,a.distinct),indent=2))
