"""Add integration instructions/tools to the existing, unchanged V5 release."""
import hashlib
import json
from pathlib import Path
import zipfile

KIT=Path(__file__).resolve().parents[1]
ROOT=KIT.parent
STEM='v5_san_sang_ghep'

START='''"""Verify the bundle, then prepare the already trained V5; never fit."""
import argparse,hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data',default=str(Path.home()/'iot23_da_loc_01'))
parser.add_argument('--output',default=str(Path.home()/'iot23_v5_ghep_01'))
parser.add_argument('--verify-pcaps',action='store_true')
parser.add_argument('--skip-local-data-check',action='store_true',help='Only verify the supplied cache; do not claim the local PCAP files were checked')
args=parser.parse_args()
checks=json.loads((root/'FILE_SHA256.json').read_text())
for name,expected in checks.items():
    path=root/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise SystemExit('Package file changed/missing: '+name)
sys.path[:0]=[str(root/'code'),str(root/'code/tools')]
try:
    from prepare_v5_handoff import prepare
    prepare(root,args.output,None if args.skip_local_data_check else args.data,args.verify_pcaps)
except ImportError as error:
    raise SystemExit('Use the existing ~/ai_part2/.venv/bin/python for this script. Missing dependency: '+str(error))
except (ValueError,OSError,KeyError) as error:
    raise SystemExit('ERROR: '+str(error))
'''


def package():
    files={}
    with zipfile.ZipFile(ROOT/'model_v5_cung_du_lieu.zip') as source:
        for entry in source.infolist():
            name=str(Path(*Path(entry.filename).parts[1:]))
            if name!='FILE_SHA256.json':files[name]=source.read(entry)
    files['BAT_DAU_V5.py']=START.encode()
    files['code/tools/prepare_v5_handoff.py']=(KIT/'tools/prepare_v5_handoff.py').read_bytes()
    for name in ('LO_TRINH_V5.md','FEATURES_V5.md'):
        content=(KIT/'handoff'/name).read_bytes()
        files[name]=content;files['code/handoff/'+name]=content
    for path in sorted((KIT/'handoff/v5').iterdir()):
        if path.is_file():files[path.name]=path.read_bytes()
    files['HANDOFF_PREPARATION_CHECK.json']=(ROOT/'reports/V5_HANDOFF_PREPARATION.json').read_bytes()
    files['MO_BAT_DAU_V5.html']=('''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Bắt đầu dùng V5</title>
<style>body{font:19px system-ui;max-width:1050px;margin:35px auto;line-height:1.7}pre{background:#eef;padding:16px;overflow:auto}</style>
<h1>V5 đã train từ đúng ba nhóm dữ liệu của bạn</h1>
<p>Gói này giữ nguyên model V5. Dữ liệu học vẫn là Normal/SYN của IoT-23 và vertical scan Chris Sanders, cùng các biến thể timestamp của scan đã tạo. Lab MQTT dùng để kiểm ghép hệ thống.</p>
<p>Trong Ubuntu, giải nén vào Downloads rồi chạy không sudo:</p>
<pre>~/ai_part2/.venv/bin/python ~/Downloads/v5_san_sang_ghep/BAT_DAU_V5.py</pre>
<p>Chương trình kiểm model/cache và vị trí 30 PCAP gốc, tạo thư mục ~/iot23_v5_ghep_01. Mở MO_BAN_GIAO_V5.html trong thư mục đó.</p>
<p><a href="LO_TRINH_V5.md">Các bước từ train đến ghép</a> | <a href="MO_KET_QUA_V5.html">Kết quả model</a> | <a href="FEATURES_V5.md">Hợp đồng sáu đặc trưng</a> | <a href="INTEGRATION_V5.json">Vector bàn giao đã tạo sẵn</a></p>
<p>Trên Windows: tải cùng ZIP, giải nén và mở candidate_v5/gowin/ai_core_v5.gprj để chạy Synthesize. Core riêng chưa phải firewall hoàn chỉnh; cần source top, CPU và feat_core mới nhất để kiểm ghép thực tế.</p></html>''').encode()
    files['FILE_SHA256.json']=json.dumps({n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())},indent=2).encode()
    output=ROOT/(STEM+'.zip')
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,content in sorted(files.items()):
            entry=zipfile.ZipInfo(STEM+'/'+name,date_time=(2000,1,1,0,0,0))
            entry.external_attr=0o100644<<16;entry.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(entry,content)
    print(json.dumps(dict(zip=str(output),files=len(files),bytes=output.stat().st_size,
                          sha256=hashlib.sha256(output.read_bytes()).hexdigest()),indent=2))
    return output


if __name__=='__main__':package()
