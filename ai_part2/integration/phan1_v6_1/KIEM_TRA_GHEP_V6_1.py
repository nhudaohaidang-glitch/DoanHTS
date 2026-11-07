"""Verify the delivered package and rerun V6 integration checks; no retraining."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--verify-only', action='store_true', help='Check file hashes without Icarus')
parser.add_argument('--full', action='store_true', help='Also run gateway and prototype RMII/MAC scenarios')
args = parser.parse_args()
checks = json.loads((root/'FILE_SHA256.json').read_text())
for name, expected in checks.items():
    path = root/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit('Changed/missing package file: '+name+'; compare with a fresh extracted copy.')
print('V6.1 package identity OK: '+str(len(checks))+' files.', flush=True)
if args.verify_only:
    raise SystemExit(0)
for test in ('ai_v6', 'ai_cpu', 'features', 'rmii_rx', 'mac') + (('full', 'system') if args.full else ()):
    result = subprocess.run([sys.executable, str(root/'tools/run_sim.py'), test], cwd=root)
    if result.returncode:
        raise SystemExit(result.returncode)
if args.full:
    result = subprocess.run([sys.executable, str(root/'tools/check_v6_trace.py')], cwd=root)
    if result.returncode:
        raise SystemExit(result.returncode)
print('PASS: requested V6 integration checks. Read MO_KET_QUA_GHEP_V6_1.html for measured results and remaining board/P3/MAC work.')
