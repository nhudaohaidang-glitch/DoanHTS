"""Collect separate development or post-freeze holdout sessions in the owned lab."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))
from part2.development import verify_freeze


def plan(phase, prefix):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', prefix):
        raise ValueError('Use an alphanumeric prefix with underscores/hyphens')
    # Name, mode, PPS, legitimate interval, sources, padding bytes.
    settings = {
        'train': [('normal_small','normal',200,.5,1,0),
                  ('normal_large','normal',200,.5,1,1024),
                  ('normal_two','normal',200,.2,2,512),
                  ('retry_low','normal_probe',4,1,1,0),
                  ('retry_high','normal_probe',10,1,1,0),
                  ('syn_low','syn',20,1,1,0), ('syn_mid','syn',80,1,1,0),
                  ('syn_high','syn',300,1,1,0),
                  ('scan_slow','scan',5,1,1,0), ('scan_fast','scan',80,1,1,0)],
        'val': [('normal_small','normal',200,.7,1,0),
                ('normal_large','normal',200,.5,1,768),
                ('normal_two','normal',200,.3,2,768),
                ('retry_low','normal_probe',6,1,1,0),
                ('retry_high','normal_probe',9,1,1,0),
                ('syn_low','syn',25,1,1,0), ('syn_mid','syn',100,1,1,0),
                ('syn_high','syn',250,1,1,0),
                ('scan_slow','scan',7,1,1,0), ('scan_fast','scan',60,1,1,0)],
        'challenge': [('normal_small','normal',200,.6,1,0),
                      ('normal_large','normal',200,.4,1,896),
                      ('normal_two','normal',200,.25,2,640),
                      ('retry_low','normal_probe',5,1,1,0),
                      ('retry_high','normal_probe',8,1,1,0),
                      ('syn_low','syn',30,1,1,0), ('syn_mid','syn',60,1,1,0),
                      ('syn_high','syn',200,1,1,0),
                      ('scan_slow','scan',6,1,1,0), ('scan_fast','scan',100,1,1,0)]}
    if phase not in ('dev', 'holdout'):
        raise ValueError('Phase must be dev or holdout')
    root = f'v2_{"development" if phase == "dev" else "holdout"}/{prefix}'
    commands = []
    for split in (('train', 'val') if phase == 'dev' else ('challenge',)):
        for name, mode, pps, interval, sources, padding in settings[split]:
            capture_id = f'{prefix}_{split}_{name}'
            args = ['bash', 'lab/run_capture.sh', mode, split, capture_id,
                    '20' if phase == 'dev' else '25', str(pps), str(interval),
                    str(sources), str(padding), root]
            commands.append(dict(capture_id=capture_id, command=args))
    return root, commands


def collect(phase, prefix, model_dir, dry_run=False):
    relative_root, commands = plan(phase, prefix)
    root = KIT / 'data' / relative_root
    if dry_run:
        return dict(root=str(root), sessions=commands, resets_owned_lab_before_every_session=True)
    if os.geteuid() != 0:
        raise ValueError('Use sudo bash lab/collect_v2.sh dev|holdout PREFIX')
    if root.exists():
        raise ValueError('Collection directory exists. Preserve it and use a new prefix')
    # Read/verify the model BEFORE any lab mutation or holdout packet generation.
    record = dict(format=1, phase=phase, capture_ids=[r['capture_id'] for r in commands],
                  collection_started_at=time.time(), plan=commands,
                  reset_owned_lab_each_session=True)
    if phase == 'holdout':
        record['selection'] = verify_freeze(model_dir)
    marker = KIT / 'build/lab.created'
    if marker.exists() and marker.read_text().strip() != 'Created by ai_part2 lab/setup_lab.sh':
        raise ValueError('Unexpected lab ownership marker; refusing reset')
    root.mkdir(parents=True)
    (root / 'COLLECTION.json').write_text(json.dumps(record, indent=2))
    try:
        for number, row in enumerate(commands, 1):
            print(f'[{number}/{len(commands)}] {row["capture_id"]}', flush=True)
            # Previous half-open TCP state and SYN-cookie counters must not leak
            # from one scenario to the next. Only reset this kit's owned lab.
            if marker.exists():
                subprocess.run(['bash', 'lab/setup_lab.sh', 'down'], cwd=KIT, check=True)
            subprocess.run(['bash', 'lab/setup_lab.sh', 'up'], cwd=KIT, check=True)
            subprocess.run(row['command'], cwd=KIT, check=True)
            log = (root / row['capture_id'] / 'capture.log').read_text()
            match = re.search(r'(\d+) packets dropped by kernel', log)
            if not match or int(match.group(1)) != 0:
                raise ValueError('Missing capture statistics or kernel drops; inspect this session before evaluation')
        (root / 'COMPLETE.json').write_text(json.dumps({'sessions': len(commands), 'finished_at': time.time()}, indent=2))
    finally:
        if 'SUDO_UID' in os.environ:
            uid = int(os.environ['SUDO_UID'])
            gid = int(os.environ.get('SUDO_GID', uid))
            for path in [root, *root.rglob('*')]:
                if not path.is_symlink():
                    os.chown(path, uid, gid)
    return dict(saved=str(root), sessions=len(commands),
                note='Development validation is not a final test. No FPGA blocking measured.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=['dev', 'holdout'])
    p.add_argument('prefix')
    p.add_argument('--model-dir', default=str(KIT / 'build/lab_model_v2'))
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    try:
        print(json.dumps(collect(a.phase, a.prefix, a.model_dir, a.dry_run), indent=2))
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as e:
        raise SystemExit('ERROR: ' + str(e))
