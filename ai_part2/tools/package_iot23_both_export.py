"""Build the standalone CSV+PCAP filtering helper, with file checksums."""
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def build():
    tools = Path(__file__).resolve().parent
    repo = tools.parents[1]
    for folder, launcher, guide in [('loc_iot23_csv_pcap','LOC_CSV_PCAP.py','LOC_IOT23_CSV_PCAP_VI.md'),
                                    ('sua_loi_loc_iot23','LOC_TIEP.py','SUA_LOI_LOC_IOT23_CUOI_PCAP_VI.md')]:
        files = {launcher:tools/'run_iot23_both_export.py', 'HUONG_DAN.md':tools.parent/'handoff'/guide}
        files['SUA_LOI_LOC_IOT23_CUOI_PCAP_VI.md'] = tools.parent/'handoff/SUA_LOI_LOC_IOT23_CUOI_PCAP_VI.md'
        for name in ('export_iot23_normal_syn.py','iot23_label_index.py','iot23_pcap_filter.py'):
            files[name] = tools/name
        checksums = {name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()}
        target = repo/(folder+'.zip')
        with ZipFile(target,'w',ZIP_DEFLATED) as archive:
            for name,path in files.items():
                archive.write(path,folder+'/'+name)
            archive.writestr(folder+'/FILE_SHA256.json',json.dumps(checksums,indent=2))
        with ZipFile(target) as archive:
            assert archive.testzip() is None
            for name, checksum in checksums.items():
                assert hashlib.sha256(archive.read(folder+'/'+name)).hexdigest() == checksum
        print(target)


if __name__ == '__main__':
    build()
