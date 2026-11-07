"""Install this code-only update with backups; never touches data, .venv or frozen build models."""
import argparse,hashlib,json,os,shutil,stat,tempfile,time
from pathlib import Path

ALLOWED={'part2','tools','lab','scripts','tests','ui','gowin','spec','handoff'}

def apply_update(bundle,target,do_apply=False):
    bundle,target=Path(bundle).resolve(),Path(target).resolve()
    if not (target/'part2').is_dir() or not (target/'scripts').is_dir():raise ValueError('Target is not the existing ai_part2 folder')
    manifest=json.loads((bundle/'UPDATE_MANIFEST.json').read_text())
    if manifest.get('format')!=1:raise ValueError('Unsupported update format')
    changes=[]
    for name,digest in manifest['files'].items():
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:raise ValueError('Unsafe path')
        if relative.parts[0] not in ALLOWED and name not in ('README_NEXT_STEPS_VI.md','.gitignore'):raise ValueError('Update attempts a protected path: '+name)
        source=bundle/'payload'/relative;dest=target/relative
        if source.is_symlink() or not source.resolve().is_relative_to((bundle/'payload').resolve()):raise ValueError('Unsafe source symlink')
        if dest.is_symlink():raise ValueError('Refusing destination symlink')
        for parent in dest.parents:
            if parent==target:break
            if parent.is_symlink():raise ValueError('Destination parent is a symlink')
        if dest.exists() and not dest.is_file():raise ValueError('Destination is not a file')
        if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise ValueError('Payload checksum mismatch: '+name)
        content=source.read_bytes()
        if name=='.gitignore':
            old=dest.read_text() if dest.exists() else ''
            missing=[line for line in content.decode().splitlines() if line and line not in old.splitlines()]
            content=(old+('\n' if old and not old.endswith('\n') else '')+''.join(line+'\n' for line in missing)).encode()
        if not dest.exists() or dest.read_bytes()!=content:changes.append((relative,content,dest))
    if not do_apply:return {'status':'preview','files':[str(p) for p,_,_ in changes]}
    if not changes:return {'status':'already_current','changed':0}
    backup=target/'build'/'update_backups'/str(time.time_ns())
    if not backup.resolve().is_relative_to(target):raise ValueError('Backup folder escapes project')
    backup.mkdir(parents=True)
    existing=[]
    for rel,content,dest in changes:
        existed=dest.exists();existing.append((rel,existed))
        if existed:
            saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,saved)
    (backup/'RESTORE_MANIFEST.json').write_text(json.dumps({'files':[{'path':str(p),'existed':e} for p,e in existing]},indent=2))
    written=[]
    try:
        for rel,content,dest in changes:
            dest.parent.mkdir(parents=True,exist_ok=True)
            mode=stat.S_IMODE(dest.stat().st_mode) if dest.exists() else 0o644
            tmp=None
            try:
                with tempfile.NamedTemporaryFile(dir=dest.parent,delete=False) as f:
                    tmp=Path(f.name);f.write(content);f.flush();os.fsync(f.fileno())
                os.chmod(tmp,mode);os.replace(tmp,dest);written.append(rel)
            finally:
                if tmp and tmp.exists():tmp.unlink()
    except Exception:
        old=dict(existing)
        for rel in reversed(written):
            if old[rel]:shutil.copy2(backup/rel,target/rel)
            else:(target/rel).unlink(missing_ok=True)
        raise
    return {'status':'updated','changed':len(changes),'backup':str(backup),
            'preserved':['data/','.venv/','build/lab_model_v1/','build/lab_features_v1.*']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',required=True);p.add_argument('--apply',action='store_true')
    a=p.parse_args()
    if os.geteuid()==0:p.error('Run as your normal user, without sudo')
    try:print(json.dumps(apply_update(Path(__file__).resolve().parent,a.target,a.apply),indent=2))
    except (ValueError,OSError,KeyError) as e:raise SystemExit('ERROR: '+str(e))
