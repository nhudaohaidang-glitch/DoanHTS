"""Package V6.1 handoff with reviewed MAC timing and a separate USB demo project."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'ai_part2/integration/phan1_v6_1'
STEM='ban_giao_ai_v6_1'

def files():
    for path in sorted(SOURCE.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(SOURCE)
        if any(p in ('__pycache__','out','build','impl') for p in relative.parts):continue
        if path.suffix in ('.pyc','.elf','.bin','.map','.lst','.vvp','.fs'):continue
        if str(relative) in ('FILE_SHA256.json','gateway_phan1_v6_1.gprj','gateway_phan1_v6_1_demo.gprj'):continue
        yield path,relative.as_posix()

def package():
    entries={name:path.read_bytes() for path,name in files()}
    checks={n:hashlib.sha256(data).hexdigest() for n,data in entries.items()}
    manifest=SOURCE/'FILE_SHA256.json';manifest.write_text(json.dumps(checks,indent=2)+'\n')
    entries['FILE_SHA256.json']=manifest.read_bytes();output=ROOT/(STEM+'.zip')
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(entries.items()):
            entry=zipfile.ZipInfo(STEM+'/'+name,date_time=(2000,1,1,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED;entry.external_attr=0o100644<<16
            archive.writestr(entry,data,compresslevel=9)
    print(json.dumps(dict(zip=str(output),files=len(entries),bytes=output.stat().st_size,
                         sha256=hashlib.sha256(output.read_bytes()).hexdigest()),indent=2))
    return output

if __name__=='__main__':package()
