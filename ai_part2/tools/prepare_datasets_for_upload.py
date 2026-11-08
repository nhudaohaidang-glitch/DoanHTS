"""Package a selected dataset folder into independently uploadable ZIP files.

Standard library only. Originals remain unchanged. Larger compressed archives
are carried as byte parts inside ordinary ZIP files, with hashes for reassembly.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

MIB = 1024 * 1024
SKIP_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules'}


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while block := f.read(MIB):
            h.update(block)
    return h.hexdigest()


def prepare(source, output, max_zip_bytes=20 * MIB, part_bytes=16 * MIB):
    source = Path(source).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f'Input folder not found: {source}')
    if source == output or source in output.parents:
        raise ValueError('Put output outside the input folder')
    if output.exists():
        raise ValueError('Output folder already exists; choose a new output folder')
    if not 0 < part_bytes < max_zip_bytes:
        raise ValueError('Part size must be smaller than ZIP limit')
    files = sorted(p for p in source.rglob('*')
                   if p.is_file() and not p.is_symlink()
                   and not set(p.relative_to(source).parts) & SKIP_DIRS)
    if not files:
        raise ValueError('Input folder has no files')
    output.parent.mkdir(parents=True, exist_ok=True)
    index = []
    # Complete archive lives in a temporary directory, not in the originals.
    with tempfile.TemporaryDirectory(prefix='dataset_pack_', dir=output.parent) as tmp:
        archive = Path(tmp) / 'all_datasets.zip'
        with ZipFile(archive, 'w', ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
            for n, path in enumerate(files, 1):
                relative = path.relative_to(source).as_posix()
                print(f'[{n}/{len(files)}] {relative}', flush=True)
                h = hashlib.sha256()
                size = 0
                with path.open('rb') as src, z.open('du_lieu/' + relative, 'w', force_zip64=True) as dst:
                    while block := src.read(MIB):
                        h.update(block)
                        size += len(block)
                        dst.write(block)
                index.append(dict(path=relative, bytes=size, sha256=h.hexdigest()))
            z.writestr('_FILE_INDEX.json', json.dumps(dict(format='dataset-files-1', files=index),
                                                       ensure_ascii=False, indent=2))
        archive_size = archive.stat().st_size
        archive_hash = sha256(archive)
        output.mkdir()
        generated = []
        if archive_size <= max_zip_bytes:
            destination = output / 'GUI_001.zip'
            shutil.move(archive, destination)
            generated.append(destination)
            mode = 'whole_archive'
        else:
            mode = 'archive_parts'
            total = (archive_size + part_bytes - 1) // part_bytes
            with archive.open('rb') as src:
                for number in range(1, total + 1):
                    data = src.read(part_bytes)
                    member = f'archive.part{number:05d}'
                    info = dict(format='dataset-transfer-1', archive_name='all_datasets.zip',
                                archive_bytes=archive_size, archive_sha256=archive_hash,
                                part_number=number, total_parts=total, member=member,
                                part_bytes=len(data), part_sha256=hashlib.sha256(data).hexdigest())
                    destination = output / f'GUI_{number:03d}.zip'
                    with ZipFile(destination, 'w', ZIP_STORED) as z:
                        z.writestr(member, data)
                        z.writestr('_PART_INFO.json', json.dumps(info, indent=2))
                    if destination.stat().st_size > max_zip_bytes:
                        raise ValueError('Unexpected ZIP overhead; transfer size exceeded')
                    generated.append(destination)
        summary = dict(mode=mode, original_files=len(files), original_bytes=sum(f['bytes'] for f in index),
                       archive_bytes=archive_size, archive_sha256=archive_hash,
                       upload_files=[dict(name=p.name, bytes=p.stat().st_size, sha256=sha256(p)) for p in generated])
        (output / 'THONG_TIN_GUI.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        print('\nDONE. Attach ALL these ZIP files to the chat:', flush=True)
        for p in generated:
            print(f'  {p.name}: {p.stat().st_size / MIB:.2f} MiB', flush=True)
        print('Folder:', output, flush=True)
        return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, help='Folder containing only the datasets and related notes/code you want to share')
    p.add_argument('--output', required=True, help='New folder outside the input folder')
    a = p.parse_args()
    prepare(a.input, a.output)
