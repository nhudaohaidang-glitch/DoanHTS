"""Package the completed full-user-cache V5 and its reproducible inputs."""
import hashlib
import json
from pathlib import Path
import zipfile

KIT=Path(__file__).resolve().parents[1]
ROOT=KIT.parent
RESULT=KIT/'examples/user_v5_from_full_cache'
STEM='model_v5_cung_du_lieu'


def package():
    files={}
    def tree(source,prefix):
        for path in sorted(source.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc','.elf','.vvp'):
                files[str(Path(prefix)/path.relative_to(source))]=path.read_bytes()
    tree(RESULT,'')
    tree(KIT/'part2','code/part2')
    tree(KIT/'examples/scan_time_variants_v5','code/examples/scan_time_variants_v5')
    tree(KIT/'examples/public_vertical_scan','code/examples/public_vertical_scan')
    for name in ('train_from_v4_cache.py','train_filtered_three_classes.py','prepare_gowin.py',
                 'check_edge_cases.py','review_trained_v4.py','prepare_scan_time_variants.py','verify_v5_candidate.py'):
        files['code/tools/'+name]=(KIT/'tools'/name).read_bytes()
    for name in ('rtl/ai_core.v','sim/tb_ai_core.v','spec/FEATURES_V0.md','requirements.txt'):
        files['code/'+name]=(KIT/name).read_bytes()
    files['KIEM_TRA_GOI.py']=b'''"""Read-only verification of package files; no extra dependencies."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent
checks=json.loads((root/'FILE_SHA256.json').read_text())
bad=[]
for name,expected in checks.items():
    path=root/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        bad.append(name)
if bad:raise SystemExit('CHANGED/MISSING: '+', '.join(bad))
print('OK:',len(checks),'files match. Model weights and original V4 cache preserved.')
'''
    files['FILE_SHA256.json']=json.dumps({n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())},indent=2).encode()
    output=ROOT/(STEM+'.zip')
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,content in sorted(files.items()):
            entry=zipfile.ZipInfo(STEM+'/'+name,date_time=(2000,1,1,0,0,0))
            entry.external_attr=0o100644<<16;entry.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(entry,content)
    print(json.dumps(dict(zip=str(output),bytes=output.stat().st_size,files=len(files),
                          sha256=hashlib.sha256(output.read_bytes()).hexdigest()),indent=2))


if __name__=='__main__':package()
