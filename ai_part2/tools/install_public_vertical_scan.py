"""Copy the bundled reviewed vertical-scan files alongside Normal/SYN data."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def install(bundle, output):
    bundle,output=Path(bundle).resolve(),Path(output).expanduser().resolve()
    manifest=json.loads((bundle/'FILE_SHA256.json').read_text())
    if not isinstance(manifest,dict) or not manifest:
        raise ValueError('Missing bundle checksums')
    selected={}
    for name,checksum in manifest.items():
        path=PurePosixPath(name)
        if not path.parts or path.is_absolute() or '..' in path.parts or '\\' in name:
            raise ValueError('Unsafe bundle member')
        source=bundle.joinpath(*path.parts)
        if not source.resolve().is_relative_to(bundle) or not source.is_file() or sha(source)!=checksum:
            raise ValueError('Bundled file missing/changed: '+name)
        if path.parts[0]=='vertical_scan':
            selected[PurePosixPath(*path.parts[1:])]=(source,checksum)
    required={'pcap/chris_sanders_synscan_vertical.pcap','csv/chris_sanders_synscan_vertical.csv',
              'BAO_CAO_VERTICAL_SCAN.json','MO_DU_LIEU_SCAN.html'}
    if not required <= {str(name) for name in selected}:
        raise ValueError('Missing reviewed dataset files')
    report=json.loads((bundle/'vertical_scan/BAO_CAO_VERTICAL_SCAN.json').read_text())
    if report.get('status')!='complete' or report.get('evidence',{}).get('distinct_target_ports')!=1000:
        raise ValueError('Expected the reviewed 1000-port scan sample')
    if not output.is_dir():
        raise ValueError('Dataset folder not found: '+str(output)+'; use --output with the correct existing folder')
    target=output/'vertical_scan'
    if target.exists():
        for name,(_,checksum) in selected.items():
            path=target.joinpath(*name.parts)
            if not path.is_file() or sha(path)!=checksum:
                raise ValueError('Existing vertical_scan differs; preserved existing files: '+str(path))
        print('Vertical scan already installed and checksums match:',target)
    else:
        with tempfile.TemporaryDirectory(prefix='.vertical_scan_install_',dir=output) as temp:
            stage=Path(temp)/'vertical_scan';stage.mkdir()
            for name,(source,checksum) in selected.items():
                path=stage.joinpath(*name.parts);path.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,path)
                if sha(path)!=checksum:
                    raise ValueError('Copied file checksum differs: '+str(name))
            stage.rename(target)
        print('ADDED:',target)
    page='''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Ba nhóm dữ liệu</title>
<style>body{font:18px system-ui;max-width:1050px;margin:35px auto;line-height:1.6}td,th{border:1px solid #ccd;padding:10px}table{border-collapse:collapse}</style>
<h1>Ba nhóm dữ liệu PCAP và CSV</h1>
<table><tr><th>Nhóm</th><th>PCAP</th><th>CSV</th><th>Nguồn</th></tr>
<tr><td>Bình thường</td><td><a href="binh_thuong/pcap/">pcap/</a></td><td><a href="binh_thuong/csv/">csv/</a></td><td>Benign gốc từ IoT-23</td></tr>
<tr><td>SYN flood</td><td><a href="syn_flood/pcap/">pcap/</a></td><td><a href="syn_flood/csv/">csv/</a></td><td>Đoạn capture 34 IoT-23 đã kiểm chứng</td></tr>
<tr><td>Vertical scan</td><td><a href="vertical_scan/pcap/">pcap/</a></td><td><a href="vertical_scan/csv/">csv/</a></td><td>PCAP mẫu công khai Chris Sanders, 1 IP nguồn quét 1.000 cổng trên 1 IP đích</td></tr></table>
<p><a href="MO_DU_LIEU_DA_LOC.html">Báo cáo lọc IoT-23</a> | <a href="vertical_scan/MO_DU_LIEU_SCAN.html">Báo cáo vertical scan và nguồn</a></p>
<p>Vertical scan là nguồn bên ngoài IoT-23. CSV scan được tạo từ PCAP và gán nhãn sau khi kiểm tra hành vi; CSV Normal/SYN giữ các cột nhãn flow gốc. Mỗi dòng CSV là flow; các bảng này chưa phải sáu đặc trưng model theo giây.</p>
<p>Đây là các nguồn dữ liệu đã lọc, chưa phải bộ train/validation/test độc lập. Mẫu scan là một lần quét; không chia các flow của cùng lần quét thành các phiên độc lập.</p></html>'''
    index=output/'MO_BA_LOAI_DU_LIEU.html'
    if not index.exists():
        index.write_text(page,encoding='utf-8')
    elif index.read_text(encoding='utf-8')!=page:
        print('Existing overview page preserved:',index)
    print('DONE. Open:',target/'MO_DU_LIEU_SCAN.html')
    return target


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default=str(Path.home()/'iot23_da_loc_01'))
    args=parser.parse_args()
    try:
        install(Path(__file__).resolve().parent,args.output)
    except (ValueError,OSError,KeyError) as error:
        parser.exit(1,'ERROR: '+str(error)+'\n')


if __name__=='__main__':
    main()
