#!/usr/bin/env python3
"""Grant only read access to this lab's Mosquitto session configs, via a local profile include."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

RULE = '/etc/mosquitto/part2-lab/session.*.conf r,'
INCLUDE = re.compile(r'^\s*(?:#\s*)?include(?:\s+if\s+exists)?\s+[<"]local/([^>"\s]+)[>"]', re.MULTILINE)

def discover(base=Path('/etc/apparmor.d')):
    base=Path(base)
    found=[]
    for name in ('usr.sbin.mosquitto','mosquitto'):
        path=base/name
        if not path.is_file():continue
        text=path.read_text()
        includes=INCLUDE.findall(text)
        if len(includes)!=1:
            raise ValueError(f'{path}: expected exactly one supported local include; will not edit the main profile')
        relative=Path(includes[0])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe local include path')
        local=base/'local'/relative
        if not local.resolve().is_relative_to((base/'local').resolve()):
            raise ValueError('Local include escapes local directory')
        if local.is_symlink():raise ValueError('Refusing to modify a symlink')
        found.append({'profile':path,'local':local})
    if len(found)!=1:
        raise ValueError(f'Found {len(found)} supported Mosquitto profiles; refusing to guess. Send the output of: ls /etc/apparmor.d/*mosquitto*')
    return found[0]

def append_rule(text):
    if RULE in [line.strip() for line in text.splitlines()]:return text
    return text.rstrip()+'\n\n# ai_part2: read-only runtime configuration for isolated namespace lab\n'+RULE+'\n'

def apply(plan,parser,runner=subprocess.run):
    local,profile=plan['local'],plan['profile']
    existed=local.exists()
    original=local.read_bytes() if existed else b''
    updated=append_rule(original.decode('utf-8')).encode('utf-8')
    backup=None
    if existed and updated!=original:
        backup=local.with_name('.'+local.name+'.ai-part2-backup-'+str(time.time_ns()))
        shutil.copy2(local,backup)
    local.parent.mkdir(parents=True,exist_ok=True)
    if updated!=original:local.write_bytes(updated)
    loaded=False
    try:
        # Validate with no kernel load, then reload only this profile; retain enforcement.
        runner([parser,'-Q','-T',str(profile)],check=True,capture_output=True,text=True)
        loaded=True
        runner([parser,'-r','-T',str(profile)],check=True,capture_output=True,text=True)
    except Exception:
        if existed:local.write_bytes(original)
        elif local.exists():local.unlink()
        if loaded:
            try:runner([parser,'-r','-T',str(profile)],check=True,capture_output=True,text=True)
            except Exception:print('WARNING: original file restored, but kernel profile reload could not be confirmed.',file=sys.stderr)
        raise
    return backup

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply',action='store_true',help='Apply the single read rule and reload only Mosquitto; requires sudo')
    a=p.parse_args()
    try:
        plan=discover()
        print('Profile:',plan['profile'])
        print('Local include:',plan['local'])
        print('Single permission:',RULE)
        if not a.apply:
            print('Preview only. To apply: sudo python3 allow_lab_apparmor.py --apply')
            return 0
        if os.geteuid()!=0:p.error('--apply requires sudo')
        parser=shutil.which('apparmor_parser')
        if not parser:raise RuntimeError('apparmor_parser is missing; no policy file changed')
        backup=apply(plan,parser)
        print('OK: validated and reloaded Mosquitto profile. AppArmor remains enforced.')
        if backup:print('Previous local include backup:',backup)
        print('Retry capture with a NEW run ID; existing failed captures are preserved.')
        return 0
    except subprocess.CalledProcessError as e:
        print('ERROR: '+(e.stderr or str(e)),file=sys.stderr)
        return 1
    except (OSError,ValueError,RuntimeError) as e:
        print('ERROR: '+str(e),file=sys.stderr)
        return 1

if __name__=='__main__':raise SystemExit(main())
