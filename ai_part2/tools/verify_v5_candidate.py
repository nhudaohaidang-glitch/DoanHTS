"""Extra scalar/NumPy/RTL parity checks; no training or traffic benchmark."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

KIT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(KIT))
from part2.features import quantize
from part2.filtered_training_data import sha
from part2.integer import infer,write_vectors
from prepare_gowin import validate
from review_trained_v4 import scalar_scores
from check_edge_cases import probes
from train_filtered_three_classes import verify_files


def verify(candidate,output):
    candidate,output=Path(candidate),Path(output)
    complete=json.loads((candidate/'CANDIDATE_COMPLETE.json').read_text())
    verify_files(candidate,complete['files'])
    model,_=validate(candidate/'model')
    if model.get('model_version')!='v5':raise ValueError('Requires V5')
    if output.exists():raise ValueError('Output exists; preserve previous verification')
    output.mkdir(parents=True)
    controls=quantize([p[2] for p in probes()],model['divisors'])
    points=np.vstack([controls,np.random.default_rng(470).integers(0,128,(1024,6)),
                      np.zeros((1,6),dtype=int),np.full((1,6),127),np.eye(6,dtype=int)*127,
                      [127,20,127,1,1,1]])
    scores=infer(points,model)
    if not np.array_equal(scores,np.asarray([scalar_scores(p.tolist(),model) for p in points])):
        raise ValueError('Scalar arithmetic disagrees with NumPy')
    count=write_vectors(points,model,output/'vectors.txt')
    expected=[p[3] for p in probes()]
    failed=[p[0] for p,v in zip(probes(),scores[:len(expected)].argmax(1)) if p[3]!=int(v)]
    report=dict(kind='v5_additional_arithmetic_verification',model_sha256=sha(candidate/'model/model.json'),
                scalar_numpy_scores_match=True,additional_vector_count=count,
                known_development_probe_count=len(expected),unmet_probe_expectations=failed,
                probes_used_for_fit_or_calibration=False,independent_traffic_test=False,
                automatic_blocking_ready=False,gowin_synthesis_executed=False,board_timing_measured=False)
    if shutil.which('iverilog') and shutil.which('vvp'):
        with tempfile.TemporaryDirectory(dir=output) as temp:
            executable=str(Path(temp)/'sim.vvp');log=[]
            commands=[['iverilog','-g2012','-Wall','-s','tb_ai_core','-o',executable,
                       str(candidate/'gowin/src/ai_core_model_v5.v'),str(candidate/'gowin/verification/tb_ai_core.v')],
                      ['vvp',executable,'+vectors='+str((output/'vectors.txt').resolve())]]
            for cmd in commands:
                result=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
                log.append(result.stdout+result.stderr)
                if result.returncode:raise ValueError('RTL failed: '+log[-1])
            if 'PASS vectors=' not in log[-1]:raise ValueError('RTL did not report PASS')
            (output/'RTL_RESULT.txt').write_text('\n'.join(log))
            report['rtl']=log[-1].strip()
    else:report['rtl']='not run: Icarus tools unavailable'
    report['int32_accumulator_bounds']={wk:max(127*sum(abs(w) for w in row)+abs(b) for row,b in zip(model[wk],model[bk]))
                                       for wk,bk in [('w1','b1'),('w2','b2')]}
    (output/'RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();verify(args.candidate,args.output)
