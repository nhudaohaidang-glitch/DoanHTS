"""Package only the frozen AI part, with no CPU, bus, MAC or board top."""
import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree

REPO = Path(__file__).resolve().parents[2]
MAIN = REPO / 'ai_part2/handoff/phan2_ai_v6_ban_giao'
MODEL_SHA = '3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515'
RTL_SHA = 'b4e99f801c7ac30fe3d7f61a2bc9818916d26dc16bb1ac231a763a6a8391261c'
SKIP = {'__pycache__', 'build', 'impl', '.pytest_cache'}


def files(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and not SKIP.intersection(p.relative_to(root).parts))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def index(root):
    write_json(root / 'FILE_SHA256.json', {p.relative_to(root).as_posix(): sha(p) for p in files(root) if p.name != 'FILE_SHA256.json'})


def archive(root):
    out = REPO / (root.name + '.zip')
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files(root):
            info = zipfile.ZipInfo(root.name + '/' + p.relative_to(root).as_posix(), (2000, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes())
    with zipfile.ZipFile(out) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC failure')
    out.with_suffix('.zip.sha256').write_text(sha(out) + '  ' + out.name + '\n')
    print(out.name, out.stat().st_size, 'bytes', sha(out))


def main_package():
    assert sha(MAIN / 'model/model.json') == MODEL_SHA
    assert sha(MAIN / 'rtl/ai_core_model_v6.v') == RTL_SHA
    rtl_files = list((MAIN / 'rtl').glob('*.v'))
    assert len(rtl_files) == 1
    assert re.findall(r'^module\s+(\w+)', rtl_files[0].read_text(), re.M) == ['ai_core']
    allowed_roots = {'rtl', 'firmware', 'model', 'verification', 'tools', 'gowin', 'spec', 'integration'}
    allowed_top = {'.gitignore', '.gitattributes', 'README.md', 'HOP_DONG_GHEP_AI_V6.md', 'GIOI_HAN_MODEL.md',
                   'KIEM_TRA_PHAN2.py', 'AI_ONLY_MANIFEST.json', 'FILE_SHA256.json'}
    forbidden = {'picorv32.v', 'wb_ai_regs.v', 'gateway_soc.v', 'tangnano9k_top.v', 'eth_mac.v',
                 'eth_stub.v', 'feat_core_stub.v', 'firmware.hex', 'firmware_sim.hex', 'main.c'}
    for p in files(MAIN):
        rel = p.relative_to(MAIN)
        assert (len(rel.parts) == 1 and p.name in allowed_top) or rel.parts[0] in allowed_roots, rel
        assert p.name not in forbidden and not p.name.startswith('rmii'), rel
        assert p.suffix not in {'.fs', '.bin', '.exe', '.vvp', '.o'}, rel
    project = MAIN / 'gowin/ai_core_v6.gprj'
    entries = ElementTree.parse(project).findall('.//File')
    assert len(entries) == 2
    for entry in entries:
        assert (project.parent / entry.attrib['path']).resolve().is_file()
    result_path = MAIN / 'verification/recorded/check_result.json'
    validation = json.loads(result_path.read_text()) if result_path.exists() else None
    if validation is not None:
        assert validation['c_packing_checked'] and validation['standalone_rtl_checked']
        assert validation['python_vectors'] == 3762 and validation['core_cycles_min'] == validation['core_cycles_max'] == 84
    write_json(MAIN / 'AI_ONLY_MANIFEST.json', {
        'scope': 'person2_AI_only', 'model_version': 'v6', 'model_sha256': MODEL_SHA,
        'rtl_sha256': RTL_SHA, 'rtl_module': 'ai_core', 'architecture': [6, 8, 3],
        'divisors': [8, 2, 1, 1, 1, 1], 'shift1': 5, 'shift2': 0,
        'core_cycles_start_accepted_to_done': 84, 'q_vectors': 3762, 'counter_cases': 41,
        'includes_other_members_implementation': False,
        'excluded': ['CPU', 'bus_adapter', 'system_firmware', 'MAC_PHY', 'P3_RTL', 'board_top', 'demo', 'bitstream'],
        'standalone_synthesis_and_physical_timing_run_for_this_package': False,
        'physical_board_tested': False, 'new_independent_traffic_test': False,
        'validation': validation,
    })
    index(MAIN)
    archive(MAIN)


def training_package(stage):
    root = stage / 'phan2_ai_v6_train_va_du_lieu'
    src = REPO / 'ai_part2/integration/phan1_v6_1/training'
    if root.exists():
        raise ValueError('Training stage already exists; use a new --training-stage directory')
    root.mkdir(parents=True)
    dirs = ('cache', 'data', 'frozen', 'runtime', 'sources')
    names = ('LIBRARY_VERSIONS.json', 'REPRODUCTION_CHECK.json', 'hybrid_v3_holdout_v3test01.csv',
             'hybrid_v3_holdout_v3test01.meta.json', 'historical_lab_regression.json', 'prepare_data.py',
             'requirements-reproduce.txt', 'test_data.py', 'train.py', 'training_summary.json', 'training_summary_extra.json')
    for name in dirs:
        shutil.copytree(src / name, root / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in names:
        shutil.copy2(src / name, root / name)
    shutil.copy2(MAIN / 'model/DATA_PROVENANCE.json', root / 'DATA_PROVENANCE.json')
    shutil.copy2(MAIN / 'GIOI_HAN_MODEL.md', root / 'GIOI_HAN_MODEL.md')
    (root / 'tools').mkdir()
    shutil.copy2(MAIN / 'tools/ai_reference.py', root / 'tools/ai_reference.py')
    for name in ('README.md', 'evaluate_historical_lab.py'):
        shutil.copy2(REPO / 'ai_part2/handoff/training_only_docs' / name, root / name)
    assert sha(root / 'frozen/model.json') == MODEL_SHA
    index(root)
    archive(root)
    print('Training stage:', root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training-stage', type=Path)
    args = parser.parse_args()
    main_package()
    if args.training_stage:
        training_package(args.training_stage)
