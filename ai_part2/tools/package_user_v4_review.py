"""Bundle a read-only review of the user's actual V4, preserving its hash."""
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED,ZipFile


def build():
    tools=Path(__file__).resolve().parent;kit=tools.parent;repo=kit.parent
    source=kit/'examples/user_v4_review_51050d9c'
    files={str(p.relative_to(source)):p for p in source.rglob('*') if p.is_file()}
    files['HUONG_DAN.md']=kit/'handoff/KIEM_TRA_MODEL_V4_MAY_BAN_VI.md'
    checksums={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()}
    target=repo/'kiem_tra_model_v4.zip'
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for name,path in sorted(files.items()):archive.write(path,'kiem_tra_model_v4/'+name)
        archive.writestr('kiem_tra_model_v4/FILE_SHA256.json',json.dumps(checksums,indent=2)+'\n')
    with ZipFile(target) as archive:
        if archive.testzip():raise ValueError('ZIP CRC differs')
        for name,checksum in checksums.items():
            if hashlib.sha256(archive.read('kiem_tra_model_v4/'+name)).hexdigest()!=checksum:
                raise ValueError('Bundled file differs: '+name)
    print(target,'bytes:',target.stat().st_size)


if __name__=='__main__':build()
