"""Collect separate development or post-freeze holdout sessions in the owned lab."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import math

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


def completed_sessions(root, commands):
    """Validate registered finished sessions before skipping them on resume."""
    manifest = root / 'manifest.csv'
    if not manifest.exists():
        return set()
    with manifest.open() as f:
        rows = list(csv.DictReader(f))
    planned = {r['capture_id']: r['command'] for r in commands}
    completed = set()
    for row in rows:
        cid = row['capture_id']
        if cid not in planned or cid in completed:
            raise ValueError('Unknown/duplicate registered capture: ' + cid)
        args = planned[cid]
        label = {'normal': '0', 'normal_probe': '0', 'syn': '1', 'scan': '2'}[args[2]]
        if (row['split'] != args[3] or row['label'] != label or row['pcap'] != f'{cid}/traffic.pcap'
                or row['source_kind'] != 'lab' or row['target_net'] != '198.18.0.1/32'
                or not all(math.isfinite(float(row[k])) for k in ('start', 'end'))
                or float(row['end']) <= float(row['start'])):
            raise ValueError('Registered capture differs from the collection plan: ' + cid)
        folder = root / cid
        pcap = folder / 'traffic.pcap'
        if not pcap.is_file() or pcap.stat().st_size <= 24:
            raise ValueError('Missing/empty PCAP in registered session: ' + cid)
        log = (folder / 'capture.log').read_text()
        match = re.search(r'(\d+) packets dropped by kernel', log)
        if not match or int(match.group(1)) != 0:
            raise ValueError('Registered session has missing capture statistics or drops: ' + cid)
        scenario = dict(line.split('=', 1) for line in (folder / 'scenario.txt').read_text().splitlines() if '=' in line)
        expected = dict(mode=args[2], split=args[3], seconds=args[5], requested_pps=args[6],
                        sensor_interval=args[7], normal_clients=args[8], payload_bytes=args[9])
        if any(scenario.get(k) != v for k, v in expected.items()):
            raise ValueError('Scenario parameters differ from the collection plan: ' + cid)
        completed.add(cid)
    return completed


def collect(phase, prefix, model_dir, dry_run=False, resume=False):
    relative_root, commands = plan(phase, prefix)
    root = KIT / 'data' / relative_root
    if dry_run:
        return dict(root=str(root), sessions=commands, resets_owned_lab_before_every_session=True)
    if os.geteuid() != 0:
        raise ValueError('Use sudo bash lab/collect_v2.sh dev|holdout PREFIX')
    if root.exists() and not resume:
        raise ValueError('Collection directory exists. Preserve it and use a new prefix')
    if resume and not root.is_dir():
        raise ValueError('No existing collection to resume')
    # Read/verify the model BEFORE any lab mutation or holdout packet generation.
    record = dict(format=1, phase=phase, capture_ids=[r['capture_id'] for r in commands],
                  collection_started_at=time.time(), plan=commands,
                  reset_owned_lab_each_session=True)
    if phase == 'holdout':
        record['selection'] = verify_freeze(model_dir)
    marker = KIT / 'build/lab.created'
    if marker.exists() and marker.read_text().strip() != 'Created by ai_part2 lab/setup_lab.sh':
        raise ValueError('Unexpected lab ownership marker; refusing reset')
    if resume:
        original = json.loads((root / 'COLLECTION.json').read_text())
        for key in ('format', 'phase', 'capture_ids', 'plan', 'reset_owned_lab_each_session'):
            if original.get(key) != record.get(key):
                raise ValueError('Existing collection plan differs; cannot resume')
        if phase == 'holdout' and original.get('selection') != record['selection']:
            raise ValueError('Frozen model changed; cannot resume this holdout')
        completed = completed_sessions(root, commands)
        # Refuse to overwrite an unregistered partial capture. Preserve it for inspection.
        for row in commands:
            if row['capture_id'] not in completed and (root / row['capture_id']).exists():
                raise ValueError('Unregistered partial session exists; preserve and inspect it: ' + row['capture_id'])
    else:
        completed = set()
        root.mkdir(parents=True)
        (root / 'COLLECTION.json').write_text(json.dumps(record, indent=2))
    if len(completed) == len(commands) and (root / 'COMPLETE.json').exists():
        return dict(saved=str(root), sessions=len(commands), status='already_complete')
    try:
        if resume and len(completed) < len(commands) and not marker.exists():
            from lab.recover_lab import recover_orphans
            removed = recover_orphans(KIT, root / 'COLLECTION.json')
            print('Orphan lab endpoints recovered:', ', '.join(removed) or 'none', flush=True)
        for number, row in enumerate(commands, 1):
            if row['capture_id'] in completed:
                print(f'[{number}/{len(commands)}] KEEP {row["capture_id"]}', flush=True)
                continue
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
    p.add_argument('--resume', action='store_true', help='Keep validated registered sessions and collect only missing ones')
    a = p.parse_args()
    try:
        print(json.dumps(collect(a.phase, a.prefix, a.model_dir, a.dry_run, a.resume), indent=2))
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as e:
        raise SystemExit('ERROR: ' + str(e))
