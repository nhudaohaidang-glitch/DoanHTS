"""Portable reproduction from cached original features and disclosed packet-derived profiles."""
import sys,json,sqlite3,gzip,csv,warnings,hashlib,argparse,platform
from pathlib import Path
from collections import Counter
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'runtime'))
from part2.filtered_training import unpack,weighted_metrics
from part2.filtered_calibration import calibrate_integer_model
from part2.integer import infer,export_model,write_vectors
parser=argparse.ArgumentParser(description='Train a separate V6 candidate; never overwrite the integrated model or call development a test.')
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--data',type=Path,default=ROOT/'data')
parser.add_argument('--search',action='store_true',help='Repeat all 27 development candidates; default reproduces selected alpha=.01 seed=5 only')
a=parser.parse_args();OUT=a.output
if OUT.exists():raise SystemExit('Output already exists; use a new candidate directory')
OUT.mkdir(parents=True)
BASE=ROOT/'cache'

if hashlib.sha256((BASE/'v5_patterns.sqlite').read_bytes()).hexdigest()!='e654b42ea80583630bfdc7a869e3234b0252d1f84ebaa7efc6a1d07a6e7c55bf':raise ValueError('Base cache checksum changed')
with sqlite3.connect(BASE/'v5_patterns.sqlite') as db:base_rows=list(db.execute('SELECT label,packed,count FROM patterns ORDER BY label,packed'))
if hashlib.sha256((BASE/'native_patterns.sqlite').read_bytes()).hexdigest()!='b76850743125c9b68c9d2419200515de9e7d53a326993532d768c6671d882e76':raise ValueError('Base cache checksum changed')
with sqlite3.connect(BASE/'native_patterns.sqlite') as db:orig_rows=list(db.execute('SELECT label,packed,count FROM patterns ORDER BY label,packed'))
counts=Counter({(l,p):n for l,p,n in base_rows});dev=Counter();all_aug=Counter();ambiguities=Counter();status=Counter()
manifest=json.loads((a.data/'MANIFEST.json').read_text())
for spec in manifest['profiles']:
 if hashlib.sha256((a.data/spec['features']).read_bytes()).hexdigest()!=spec['features_sha256']:raise ValueError('Changed features: '+spec['features'])
 with gzip.open(a.data/spec['features'],'rt') as f:
  for row in csv.DictReader(f):
   label=int(row['label']);q=[int(row['q'+str(i)]) for i in range(6)];packed=sum(v<<(8*i) for i,v in enumerate(q));status[row['split'],row['status']]+=1
   all_aug[label,packed]+=1
   if row['status']!='eligible':ambiguities[row['status'],label]+=1;continue
   (counts if row['split']=='train' else dev)[label,packed]+=1

def arrays(rows):return np.asarray([unpack(p) for l,p,n in rows],dtype=np.int64),np.asarray([l for l,p,n in rows],dtype=int),np.asarray([n for l,p,n in rows],dtype=np.int64)
rows=[(l,p,n) for (l,p),n in sorted(counts.items())];drows=[(l,p,n) for (l,p),n in sorted(dev.items())]
x,y,n=arrays(rows);xd,yd,nd=arrays(drows);xo,yo,no=arrays(orig_rows)
def metrics(x,y,n,m):
 pred=infer(x,m).argmax(1);cm=np.zeros((3,3),dtype=np.int64);np.add.at(cm,(y,pred),n);return weighted_metrics(cm)
unique=[np.unique(x[y==l],axis=0) for l in range(3)];size=max(map(len,unique));rng=np.random.default_rng(23)
xfit=np.vstack([v[np.tile(rng.permutation(len(v)),int(np.ceil(size/len(v))))[:size]] for v in unique]);yfit=np.repeat(np.arange(3),size)
print('unique',list(map(len,unique)),'fitrows',len(xfit),'count windows',[sum(n[y==l]) for l in range(3)],'dev unique',[sum(yd==l) for l in range(3)],'status',status,flush=True)
records=[];best=None
for alpha,seeds in ([(v,(11,23,47)) for v in (.01,.1,1.)]+[(v,(5,7,13,19,31,59)) for v in (.003,.01,.03)] if a.search else [(.01,(5,))]):
 for seed in seeds:
  name=f'a{alpha}_s{seed}';folder=OUT/name
  if folder.exists():
   rec=json.loads((folder/'record.json').read_text());model=json.loads((folder/'model.json').read_text())
  else:
   folder.mkdir();clf=MLPClassifier(hidden_layer_sizes=(8,),activation='relu',solver='lbfgs',alpha=alpha,max_iter=2000,random_state=seed)
   with warnings.catch_warnings(record=True) as caught,threadpool_limits(limits=1):
    warnings.simplefilter('always',ConvergenceWarning);clf.fit(xfit/128.,yfit)
   model,cal=calibrate_integer_model(clf,x,y,n,seed)
   model.update(model_version='v6',divisors=[8,2,1,1,1,1],source_kind='same_source_packet_derived_development',selected_alpha=alpha,independent_test_evaluated=False)
   export_model(model,folder)
   floatmodel=dict(normalization_denominator=128.,w1=clf.coefs_[0].tolist(),w2=clf.coefs_[1].tolist(),b1=clf.intercepts_[0].tolist(),b2=clf.intercepts_[1].tolist(),activation='relu',class_order=[0,1,2])
   (folder/'float_model.json').write_text(json.dumps(floatmodel,indent=2))
   rec=dict(name=name,alpha=alpha,seed=seed,calibration=cal,original=metrics(xo,yo,no,model),train=metrics(x,y,n,model),development=metrics(xd,yd,nd,model),convergence_warnings=len(caught))
   (folder/'record.json').write_text(json.dumps(rec,indent=2))
  oc=rec['original']['confusion_matrix'];feasible=sum(oc[0][1:])<=12 and oc[1][1]==21 and oc[2][2]==4
  key=(int(feasible),rec['development']['macro_f1'],-rec['development']['false_positive_rate'],rec['train']['macro_f1'],-sum(oc[0][1:]))
  rec['key']=list(key);records.append(rec)
  if best is None or key>best[0]:best=key,name
  print(name,'orig',rec['original']['confusion_matrix'],'dev',rec['development']['confusion_matrix'],'key',key,flush=True)
(OUT/'training_summary.json').write_text(json.dumps(dict(best=best[1],records=records,source_manifest_sha256=hashlib.sha256((a.data/'MANIFEST.json').read_bytes()).hexdigest(),counts=dict(train=[int(sum(n[y==l])) for l in range(3)],dev=[int(sum(nd[yd==l])) for l in range(3)]),unique_by_class=list(map(len,unique)),status=[dict(split=a,status=b,windows=v) for (a,b),v in status.items()]),indent=2))
import sklearn,scipy
versions={'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'scikit-learn':sklearn.__version__}
(OUT/'LIBRARY_VERSIONS.json').write_text(json.dumps(versions,indent=2)+'\n')
selected=OUT/best[1]
actual=hashlib.sha256((selected/'model.json').read_bytes()).hexdigest()
if not best[0][0]:raise SystemExit('No candidate passed the original-cache regression gate; do not release.')
print('BEST',best,'model_sha256',actual,flush=True)
print('A new fit is a candidate only. Re-export RTL, rebuild C firmware and repeat all integration checks before replacing the frozen package.')
