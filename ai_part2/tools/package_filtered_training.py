"""Bundle the three-folder trainer and the explicitly scoped trained reference."""
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED,ZipFile


def build():
    tools=Path(__file__).resolve().parent;kit=tools.parent;repo=kit.parent
    files={'TRAIN_BA_NHOM.py':tools/'train_filtered_three_classes.py',
           'prepare_gowin.py':tools/'prepare_gowin.py',
           'HUONG_DAN.md':kit/'handoff/TRAIN_BA_NHOM_V4_VI.md',
           'rtl/ai_core.v':kit/'rtl/ai_core.v','sim/tb_ai_core.v':kit/'sim/tb_ai_core.v'}
    for name in ('__init__.py','features.py','integer.py','assessment.py','development.py',
                 'filtered_training.py','filtered_training_data.py'):
        files['part2/'+name]=kit/'part2'/name
    reference=kit/'examples/filtered_v4_reference'
    for path in reference.rglob('*'):
        if path.is_file():files['MODEL_THAM_CHIEU/'+str(path.relative_to(reference))]=path
    checksums={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()}
    target=repo/'train_ba_nhom_v4.zip'
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for name,path in sorted(files.items()):archive.write(path,'train_ba_nhom_v4/'+name)
        archive.writestr('train_ba_nhom_v4/FILE_SHA256.json',json.dumps(checksums,indent=2)+'\n')
    with ZipFile(target) as archive:
        if archive.testzip():raise ValueError('ZIP CRC differs')
        for name,checksum in checksums.items():
            if hashlib.sha256(archive.read('train_ba_nhom_v4/'+name)).hexdigest()!=checksum:
                raise ValueError('Bundle file differs: '+name)
    print(target,'bytes:',target.stat().st_size,'files:',len(files))
    return target


if __name__=='__main__':build()
