import json
from pathlib import Path
import numpy as np

def infer(x, m):
    x=np.asarray(x,dtype=np.int64).reshape(-1,6)
    w1=np.asarray(m['w1'],dtype=np.int64);b1=np.asarray(m['b1'],dtype=np.int64)
    w2=np.asarray(m['w2'],dtype=np.int64);b2=np.asarray(m['b2'],dtype=np.int64)
    h=np.clip((x@w1.T+b1)>>m['shift1'],0,127)
    return np.clip((h@w2.T+b2)>>m['shift2'],-32768,32767).astype(np.int64)

def signed_hex(v,bits): return format(int(v)&((1<<bits)-1),f'0{bits//4}x')

def export_model(model, out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'model.json').write_text(json.dumps(model,indent=2))
    for key,bits in [('w1',8),('w2',8),('b1',32),('b2',32)]:
        data=np.asarray(model[key]).reshape(-1)
        (out/(key+'.hex')).write_text('\n'.join(signed_hex(x,bits) for x in data)+'\n')
    (out/'quant_params.vh').write_text(f"`define SHIFT1 {model['shift1']}\n`define SHIFT2 {model['shift2']}\n")

def write_vectors(x, model, path):
    x=np.asarray(x,dtype=np.int64).reshape(-1,6)
    scores=infer(x,model)
    with Path(path).open('w') as f:
        for sample,score in zip(x,scores):
            feat=sum(int(v)<<(8*i) for i,v in enumerate(sample))
            packed=sum((int(v)&65535)<<(16*i) for i,v in enumerate(score))
            f.write(f'{feat:012x} {packed:012x} {int(np.argmax(score))}\n')
    return len(x)
