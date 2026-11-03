"""Package ready-to-use public vertical-scan PCAP/CSV and a copy-only helper."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED


def build():
    tools=Path(__file__).resolve().parent;kit=tools.parent;repo=kit.parent
    root='vertical_scan_pcap_csv'
    dataset=kit/'examples/public_vertical_scan'
    files={str(path.relative_to(dataset)):path for path in (dataset/'vertical_scan').rglob('*') if path.is_file()}
    files.update({'THEM_VERTICAL_SCAN.py':tools/'install_public_vertical_scan.py',
                  'HUONG_DAN.md':kit/'handoff/VERTICAL_SCAN_PUBLIC_PCAP_CSV_VI.md'})
    checksums={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()}
    target=repo/(root+'.zip')
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for name,path in sorted(files.items()):
            archive.write(path,root+'/'+name)
        archive.writestr(root+'/FILE_SHA256.json',json.dumps(checksums,indent=2)+'\n')
    with ZipFile(target) as archive:
        if archive.testzip():raise ValueError('ZIP CRC differs')
        for name,checksum in checksums.items():
            if hashlib.sha256(archive.read(root+'/'+name)).hexdigest()!=checksum:
                raise ValueError('Packaged checksum differs: '+name)
    print(target,'bytes:',target.stat().st_size)
    return target


if __name__=='__main__':
    build()
