"""Verify the AI-only package; optional C and RTL checks, without a CPU/SoC."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from ai_reference import infer,prepare,unpack
EXPECTED_MODEL='3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515'

def check(run_c=False,run_rtl=False):
    for name,expected in json.loads((ROOT/'FILE_SHA256.json').read_text()).items():
        p=ROOT/name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
            raise ValueError('Changed/missing file: '+name)
    mp=ROOT/'model/model.json'
    if hashlib.sha256(mp.read_bytes()).hexdigest()!=EXPECTED_MODEL:raise ValueError('Wrong model version/hash')
    m=json.loads(mp.read_text())
    if m['architecture']!=[6,8,3] or m['divisors']!=[8,2,1,1,1,1]:raise ValueError('Unexpected model interface')
    count=0
    for line in (ROOT/'verification/vectors.txt').read_text().splitlines():
        a,b,c=line.split();packed=int(a,16);q=unpack(packed);scores=infer(q,m)
        word=sum((s&65535)<<(16*i) for i,s in enumerate(scores))
        if word!=int(b,16) or max(range(3),key=lambda i:scores[i])!=int(c):raise ValueError('Numeric vector mismatch: '+str(count))
        count+=1
    if count!=3762:raise ValueError('Expected all 3762 frozen vectors')
    refs=json.loads((ROOT/'verification/counter_vectors.json').read_text());valid_count=0
    for e in refs['cases']:
        valid,packed=prepare(e['counter_inputs'],m)
        if valid!=e['decision_valid'] or packed!=int(e['feat_hex'],16):raise ValueError('Packing/validity mismatch: '+e['name'])
        if valid:
            valid_count+=1;scores=infer(unpack(packed),m)
            if scores!=e['scores'] or max(range(3),key=lambda i:scores[i])!=e['class_id']:raise ValueError('Counter score mismatch: '+e['name'])
        elif e['scores'] is not None or e['class_id'] is not None:raise ValueError('Empty input must have no decision')
    if len(refs['cases'])!=41 or valid_count!=40:raise ValueError('Incomplete counter references')
    print('PASS AI_ONLY identity and Python integer reference: vectors=3762 counters=41 valid=40 empty_skip=1',flush=True)
    result={'kind':'part2_only_numeric_interface_validation_not_detection_accuracy','model_sha256':EXPECTED_MODEL,
            'python_vectors':count,'counter_cases':41,'valid_counter_cases':40,'empty_skipped':1,
            'c_packing_checked':False,'standalone_rtl_checked':False,'cpu_bus_or_mac_tested_by_this_script':False}
    build=ROOT/'verification/build';build.mkdir(parents=True,exist_ok=True)
    if run_c:
        cc=shutil.which('gcc') or shutil.which('cc')
        if not cc:raise ValueError('C compiler required for --c (gcc or cc)')
        exe=build/('test_pack.exe' if sys.platform=='win32' else 'test_pack')
        p=subprocess.run([cc,'-std=c99','-Wall','-Wextra','-Werror','-I',str(ROOT/'firmware'),str(ROOT/'verification/test_pack.c'),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        if p.returncode:raise ValueError(p.stdout+p.stderr)
        p=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,text=True)
        (build/'c_result.log').write_text(p.stdout+p.stderr)
        if p.returncode or 'PASS C_PACK cases=41 valid=40 empty_skipped=1' not in p.stdout:raise ValueError('C test failed: '+p.stdout+p.stderr)
        print(p.stdout.strip(),flush=True);result['c_packing_checked']=True
    if run_rtl:
        if not shutil.which('iverilog') or not shutil.which('vvp'):raise ValueError('Icarus Verilog required for --rtl')
        exe=build/'ai_core.vvp'
        p=subprocess.run(['iverilog','-g2012','-Wall','-s','tb_ai_core','-o',str(exe),'rtl/ai_core_model_v6.v','verification/tb_ai_core.v'],cwd=ROOT,capture_output=True,text=True)
        (build/'rtl_compile.log').write_text(p.stdout+p.stderr)
        if p.returncode:raise ValueError(p.stdout+p.stderr)
        p=subprocess.run(['vvp','-n',str(exe),'+vectors=verification/vectors.txt'],cwd=ROOT,capture_output=True,text=True,timeout=120)
        log=p.stdout+p.stderr;(build/'rtl_result.log').write_text(log)
        if p.returncode or 'FATAL' in log or not re.search(r'^PASS vectors=3762 cycles_min=84 cycles_max=84',log,re.M):raise ValueError('RTL test failed: '+log)
        print(log.strip(),flush=True);result.update(standalone_rtl_checked=True,core_cycles_min=84,core_cycles_max=84)
    (build/'check_result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--c',action='store_true',help='Compile/test the standalone C packing helpers');p.add_argument('--rtl',action='store_true',help='Run only ai_core with Icarus, no bus/CPU/system')
    a=p.parse_args()
    try:check(a.c,a.rtl)
    except (ValueError,OSError,subprocess.TimeoutExpired) as e:p.exit(1,'ERROR: '+str(e)+'\n')
