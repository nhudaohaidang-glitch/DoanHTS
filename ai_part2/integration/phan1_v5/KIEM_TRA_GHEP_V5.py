"""Check package identity and execute V5 bus/CPU/reference-feature simulations."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
checks=json.loads((root/'FILE_SHA256.json').read_text())
for name,expected in checks.items():
    path=root/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise SystemExit('Changed/missing package file: '+name+'; preserve the original project to compare.')
print('V5 package identity OK. No model training or board programming.',flush=True)
for test in ('ai_v5','ai_cpu','features'):
    result=subprocess.run([sys.executable,str(root/'tools/run_sim.py'),test],cwd=root)
    if result.returncode:raise SystemExit(result.returncode)
print('PASS: V5 numeric integration and reference header-feature cases.\nRead MO_KET_QUA_GHEP_V5.html for the remaining SYN demo misses and MAC overflow.\nNo independent detection accuracy or physical-board PASS is claimed.')
