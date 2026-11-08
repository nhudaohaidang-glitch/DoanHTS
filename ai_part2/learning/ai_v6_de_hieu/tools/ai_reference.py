"""Integer-only reference for the frozen part2 6-8-3 interface."""
def infer(q, model):
    if len(q)!=6 or any(type(v) is not int or not 0<=v<=127 for v in q):
        raise ValueError('Six integer q values in 0..127 required')
    hidden=[max(0,min(127,(sum(v*w for v,w in zip(q,row))+bias)>>model['shift1']))
            for row,bias in zip(model['w1'],model['b1'])]
    return [max(-32768,min(32767,(sum(v*w for v,w in zip(hidden,row))+bias)>>model['shift2']))
            for row,bias in zip(model['w2'],model['b2'])]

def prepare(counters, model):
    if len(counters)!=6 or any(type(v) is not int or v<0 for v in counters):
        raise ValueError('Six nonnegative integer counters required')
    n,total,syn,ns,nd,np=counters
    if total>=2**64 or any(v>=2**32 for v in (n,syn,ns,nd,np)) or syn>n:
        raise ValueError('Counter outside C interface bounds or SYN count exceeds N')
    if n==0:return False,0
    raw=[n,total//n,127*syn//n,ns,nd,np]
    q=[min(127,v//d) for v,d in zip(raw,model['divisors'])]
    return True,sum(v<<(8*i) for i,v in enumerate(q))

def unpack(packed):
    return [(packed>>(8*i))&255 for i in range(6)]
