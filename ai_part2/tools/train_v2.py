"""Train a separate 6-8-3 candidate on new train/val sessions; never consume test data."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from part2.development import train_v2

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', required=True)
    p.add_argument('--output', default='build/lab_model_v2')
    a = p.parse_args()
    try:
        report = train_v2(a.dataset, a.output)
    except (ValueError, OSError, KeyError) as e:
        p.error(str(e))
    print(json.dumps({'kind': report['kind'], 'metrics': report['metrics'],
                      'test_evaluated': False, 'rtl_vector_count': report['rtl_vector_count']}, indent=2))
    print('Saved:', a.output, '\nValidation only. Collect fresh holdout after this step.')
