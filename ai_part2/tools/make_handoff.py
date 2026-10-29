import argparse,hashlib,json,sys
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
kit=Path(__file__).resolve().parents[1];out=Path(a.output)
if out.exists():p.error('Output exists; preserve prior handoff')
paths=[kit/'gowin/lab_model_v1',kit/'handoff',kit/'spec/FEATURES_V0.md',kit/'spec/AI_INTERFACE.md',kit/'spec/LOG_SCHEMA_PDF_V1.md']
files=[]
for path in paths:
 for file in (path.rglob('*') if path.is_dir() else [path]):
  if file.is_file() and not any(p in ('build','__pycache__') for p in file.relative_to(kit).parts):files.append(file)
manifest={str(f.relative_to(kit)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
out.parent.mkdir(parents=True,exist_ok=True)
with ZipFile(out,'w',ZIP_DEFLATED) as z:
 for f in files:z.write(f,Path('ai_v1_handoff')/f.relative_to(kit))
 z.writestr('ai_v1_handoff/FILE_SHA256.json',json.dumps(manifest,indent=2))
with ZipFile(out) as z:
 if z.testzip():raise ValueError('ZIP CRC check failed')
print('Handoff saved:',out,'files:',len(files))
