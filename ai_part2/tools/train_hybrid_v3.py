import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from part2.hybrid_training import train_hybrid
if __name__=='__main__':
    p=argparse.ArgumentParser(description='Train v3 from explicit hybrid development sources; never access test data')
    p.add_argument('--dataset',required=True);p.add_argument('--output',default='build/hybrid_model_v3');a=p.parse_args()
    try:r=train_hybrid(a.dataset,a.output)
    except (ValueError,OSError,KeyError) as e:p.error(str(e))
    print(json.dumps(dict(test_evaluated=False,validation_integer=r['metrics']['val']['integer'],rtl_vector_count=r['rtl_vector_count']),indent=2))
