"""Package the reviewed Person 1 / frozen V5 integration, including failed tests."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'ai_part2/integration/phan1_v5'
STEM='ghep_phan1_ai_v5'


def files():
    for path in sorted(SOURCE.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(SOURCE)
        if any(p in ('__pycache__','out','build') for p in relative.parts):continue
        if path.suffix in ('.pyc','.elf','.bin','.map','.lst','.vvp','.fs'):continue
        if path.name in ('FILE_SHA256.json','gateway_phan1_v5.gprj'):continue
        yield path,str(relative)


def package():
    entries={name:path.read_bytes() for path,name in files()}
    checks={n:hashlib.sha256(data).hexdigest() for n,data in entries.items()}
    (SOURCE/'FILE_SHA256.json').write_text(json.dumps(checks,indent=2)+'\n')
    entries['FILE_SHA256.json']=(SOURCE/'FILE_SHA256.json').read_bytes()
    output=ROOT/(STEM+'.zip')
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(entries.items()):
            entry=zipfile.ZipInfo(STEM+'/'+name,date_time=(2000,1,1,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED;entry.external_attr=0o100644<<16
            archive.writestr(entry,data)
    print(json.dumps(dict(zip=str(output),files=len(entries),bytes=output.stat().st_size,
                          sha256=hashlib.sha256(output.read_bytes()).hexdigest()),indent=2))
    return output


if __name__=='__main__':package()
