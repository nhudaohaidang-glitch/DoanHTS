import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from part2.features import quantize
from part2.integer import infer
p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--features',nargs=6,type=int,required=True);a=p.parse_args()
m=json.loads(Path(a.model).read_text());x=quantize([a.features],m['divisors']);scores=infer(x,m)[0]
print(json.dumps({'quantized':x[0].tolist(),'feat_hex':f"{sum(int(v)<<(8*i) for i,v in enumerate(x[0])):012x}",
 'scores':scores.tolist(),'class_id':int(scores.argmax()),'model_source_kind':m['source_kind']},indent=2))
