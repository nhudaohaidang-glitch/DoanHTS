import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from part2.logs import encode
for payload in ['MODE,DETECT','CNT,1520,0,0,0,0','IDS,5,1,1,7065,62,99,253,1,2,0,42',
                'MODE,BLOCK','BLK,198.18.0.3,DOS,60','CNT,1520,3812,0,0,0','UNB,198.18.0.3']:
 print(encode(payload))
