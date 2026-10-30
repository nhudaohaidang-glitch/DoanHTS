"""Checksum-aware parser. Field meanings of IDS remain opaque until group firmware agrees."""
def encode(payload):
    checksum=0
    for b in payload.encode('ascii'):checksum^=b
    return f'${payload}*{checksum:02X}'

def decode(line):
    line=line.strip()
    if not line.startswith('$') or '*' not in line:raise ValueError('not a framed log')
    payload,checksum=line[1:].rsplit('*',1)
    if len(checksum)!=2:raise ValueError('checksum must contain two hex digits')
    expected=encode(payload).rsplit('*',1)[1]
    if checksum.upper()!=expected:raise ValueError('checksum mismatch')
    fields=payload.split(',')
    if fields[0] not in ('IDS','BLK','UNB','CNT','MODE'):raise ValueError('unknown log kind')
    required={'BLK':4,'UNB':2,'CNT':6,'MODE':2}
    if fields[0] in required and len(fields)!=required[fields[0]]:raise ValueError('wrong field count')
    return {'kind':fields[0],'fields':fields[1:],'raw':line}
