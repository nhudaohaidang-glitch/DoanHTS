"""AI v2 development: separate sessions, integer validation, and a pinned holdout.

Raw six-feature semantics and the 6-8-3 RTL stay unchanged. No code here alters
the reviewed v1 model or treats previously inspected challenge data as a test.
"""
import csv
import hashlib
import json
import math
import warnings
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPClassifier

from part2.assessment import classification_metrics, evaluate_frozen
from part2.features import NAMES, quantize
from part2.integer import export_model, infer, write_vectors

# Fixed before collecting v2 development/holdout. Preserve small port counts;
# large cardinalities intentionally saturate instead of hiding slow scans.
DIVISORS_V2 = [8, 2, 1, 1, 1, 1]
SEEDS_V2 = (11, 23, 47)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_dataset(path, allowed_splits, allowed_sources=('lab',)):
    path = Path(path)
    meta = json.loads(path.with_suffix('.meta.json').read_text())
    if (meta.get('features') != NAMES or meta.get('distinct') != 'exact'
            or meta.get('window_seconds') != 1.0):
        raise ValueError('Requires the same six features, exact counts, 1-second windows')
    with path.open() as f:
        rows = list(csv.DictReader(f))
    if not rows or len(rows) != meta.get('rows'):
        raise ValueError('Empty dataset or metadata row count mismatch')
    captures = {c['capture_id']: c for c in meta['captures']}
    if len(captures) != len(meta['captures']):
        raise ValueError('Duplicate metadata capture IDs')
    hashes = [c['sha256'] for c in captures.values()]
    if len(set(hashes)) != len(hashes):
        raise ValueError('Duplicate PCAP content across sessions')
    if set(r['capture_id'] for r in rows) != set(captures):
        raise ValueError('Capture IDs differ from metadata')
    groups = {}
    seen = set()
    for row in rows:
        capture = captures[row['capture_id']]
        if row['split'] not in allowed_splits or row['source_kind'] not in allowed_sources:
            raise ValueError('Unexpected split or non-lab source')
        if row['split'] != capture['split'] or row['label'] != str(capture['label']):
            raise ValueError('Row labels/split differ from provenance')
        if capture['source_kind'] not in allowed_sources or capture['source_kind'] != row['source_kind'] or len(capture['sha256']) != 64:
            raise ValueError('Invalid capture provenance')
        key = (row['capture_id'], float(row['window_start']))
        if key in seen or not math.isfinite(key[1]):
            raise ValueError('Duplicate or invalid window')
        seen.add(key)
        groups.setdefault(row['capture_id'], set()).add(row['split'])
    if any(len(s) != 1 for s in groups.values()):
        raise ValueError('Capture leakage across splits')
    raw = np.array([[int(r[k]) for k in NAMES] for r in rows], dtype=np.int64)
    if (raw < 0).any() or not {int(r['label']) for r in rows} <= {0, 1, 2}:
        raise ValueError('Invalid raw feature or label')
    return rows, meta


def arrays(rows):
    return (np.array([[int(r[k]) for k in NAMES] for r in rows], dtype=np.int64),
            np.array([int(r['label']) for r in rows], dtype=int))


def integer_model(clf, qtrain, seed):
    w1, w2 = clf.coefs_
    b1, b2 = clf.intercepts_

    def exponent(w):
        return max(0, min(12, math.floor(math.log2(127 / max(float(np.abs(w).max()), 1e-9)))))

    p1, p2 = exponent(w1), exponent(w2)
    hidden = np.maximum(0, qtrain / 128.0 @ w1 + b1)
    he = max(0, min(7, math.floor(math.log2(127 / max(float(hidden.max()), 1e-9)))))
    s1, s2 = p1 + 7 - he, max(0, p2 + he - 7)
    model = dict(architecture=[6, 8, 3], model_version='v2', divisors=DIVISORS_V2,
                 shift1=s1, shift2=s2,
                 w1=np.rint(w1.T * 2**p1).clip(-127, 127).astype(int).tolist(),
                 w2=np.rint(w2.T * 2**p2).clip(-127, 127).astype(int).tolist(),
                 b1=np.rint(b1 * 128 * 2**p1).astype(np.int64).tolist(),
                 b2=np.rint(b2 * 2**he * 2**p2).astype(np.int64).tolist(),
                 weight_fraction_bits=[p1, p2], hidden_scale=2**he,
                 score_scale=2**(p2 + he - s2), source_kind='lab_or_external',
                 selected_seed=seed,
                 arithmetic='round-to-nearest-even; arithmetic shifts; hidden 0..127; int16 scores; first argmax')
    for wk, bk in [('w1', 'b1'), ('w2', 'b2')]:
        w, b = np.asarray(model[wk], dtype=np.int64), np.asarray(model[bk], dtype=np.int64)
        if (b < -2**31).any() or (b >= 2**31).any() or int((127 * np.abs(w).sum(1) + np.abs(b)).max()) >= 2**31:
            raise ValueError('int32 accumulator bound exceeded')
    return model


def rule_predictions(raw, rule):
    pt, dt, st = [rule[k] for k in ('packet_threshold', 'port_threshold', 'syn_ratio_q127_threshold')]
    return np.where((raw[:, 5] >= dt) & (raw[:, 2] >= st), 2,
                    np.where((raw[:, 0] >= pt) & (raw[:, 2] >= st), 1, 0))


def train_v2(dataset, output):
    output = Path(output)
    if output.exists():
        raise ValueError('Output exists; preserve the old model and choose a new path')
    rows, meta = load_dataset(dataset, {'train', 'val'})
    splits = {s: [r for r in rows if r['split'] == s] for s in ('train', 'val')}
    for s, selected in splits.items():
        for label in range(3):
            ids = {r['capture_id'] for r in selected if int(r['label']) == label}
            if len(ids) < 2:
                raise ValueError(f'{s} needs at least two different captures for class {label}')
    data = {s: arrays(v) for s, v in splits.items()}
    q = {s: quantize(v[0], DIVISORS_V2) for s, v in data.items()}
    candidates = []
    best = None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', ConvergenceWarning)
        for seed in SEEDS_V2:
            clf = MLPClassifier(hidden_layer_sizes=(8,), activation='relu', solver='lbfgs',
                                alpha=.01, max_iter=1600, random_state=seed)
            clf.fit(q['train'] / 128.0, data['train'][1])
            model = integer_model(clf, q['train'], seed)
            metrics = classification_metrics(data['val'][1], infer(q['val'], model).argmax(1))
            key = (metrics['macro_f1'], -metrics['false_positive_rate'])
            candidates.append({'seed': seed, 'integer_validation': metrics})
            if best is None or key > best[0]:
                best = key, model, clf
    _, model, clf = best
    report = dict(kind='v2_development_validation', test_evaluated=False,
                  selection='Integer validation macro-F1; tie: smaller normal false-positive rate; then seed order',
                  candidates=candidates, metrics={},
                  convergence_warning_count=sum(issubclass(w.category, ConvergenceWarning) for w in caught),
                  dataset_sha256=sha256(dataset), data_provenance=meta,
                  note='Validation selected this model. This is NOT an independent test result or hardware measurement.')
    for s, (raw, labels) in data.items():
        report['metrics'][s] = {
            'float': classification_metrics(labels, clf.predict(q[s] / 128.0)),
            'integer': classification_metrics(labels, infer(q[s], model).argmax(1)),
            'input_clipped_fraction': ((raw // np.array(DIVISORS_V2)) > 127).mean(0).tolist()}
    best_rule = None
    # Frozen candidate grid declared in code; selected using validation only.
    for pt in (8, 16, 24, 32, 64):
        for dt in (3, 4, 5, 8, 16):
            for st in (32, 64, 96):
                rule = dict(packet_threshold=pt, port_threshold=dt, syn_ratio_q127_threshold=st)
                metrics = classification_metrics(data['val'][1], rule_predictions(data['val'][0], rule))
                key = metrics['macro_f1'], -metrics['false_positive_rate']
                if best_rule is None or key > best_rule[0]:
                    best_rule = key, rule, metrics
    report['threshold_baseline'] = dict(best_rule[1], validation=best_rule[2])
    export_model(model, output)
    rng = np.random.default_rng(112)
    edges = np.vstack([np.zeros((1, 6), dtype=int), np.full((1, 6), 127),
                       np.eye(6, dtype=int) * 127, rng.integers(0, 128, (256, 6))])
    report['rtl_vector_count'] = write_vectors(np.vstack([q['val'], edges]), model, output / 'vectors.txt')
    (output / 'metrics.json').write_text(json.dumps(report, indent=2))
    # Copy this immutable selection record into the holdout BEFORE collection.
    freeze = dict(format=1, model_sha256=sha256(output / 'model.json'),
                  metrics_sha256=sha256(output / 'metrics.json'), threshold_baseline=best_rule[1],
                  development_capture_sha256=[c['sha256'] for c in meta['captures']],
                  development_capture_ids=[c['capture_id'] for c in meta['captures']])
    (output / 'FREEZE.json').write_text(json.dumps(freeze, indent=2))
    return report


def verify_freeze(model_dir):
    model_dir = Path(model_dir)
    freeze = json.loads((model_dir / 'FREEZE.json').read_text())
    if (freeze['model_sha256'] != sha256(model_dir / 'model.json')
            or freeze['metrics_sha256'] != sha256(model_dir / 'metrics.json')):
        raise ValueError('Model/metrics changed after selection; do not silently replace a frozen model')
    return freeze


def evaluate_v2(dataset, model_dir, collection_record):
    model_dir = Path(model_dir)
    freeze = verify_freeze(model_dir)
    record = json.loads(Path(collection_record).read_text())
    if record['selection'] != freeze:
        raise ValueError('Holdout was collected for a different frozen model/baseline')
    rows, meta = load_dataset(dataset, {'challenge'})
    allowed = set(record['capture_ids'])
    if set(r['capture_id'] for r in rows) != allowed:
        raise ValueError('Holdout capture IDs differ from the pre-collection plan')
    if set(freeze['development_capture_ids']) & allowed:
        raise ValueError('Capture ID reused from development')
    if set(freeze['development_capture_sha256']) & {c['sha256'] for c in meta['captures']}:
        raise ValueError('PCAP reused from development')
    if any(float(c['start']) <= float(record['collection_started_at']) for c in meta['captures']):
        raise ValueError('Holdout contains captures from before model freeze/collection record')
    if {int(r['label']) for r in rows} != {0, 1, 2}:
        raise ValueError('Holdout needs all three classes')
    model = json.loads((model_dir / 'model.json').read_text())
    report, predictions = evaluate_frozen(rows, model, freeze['threshold_baseline'])
    report.update(kind='v2_pinned_holdout_evaluation', model_sha256=freeze['model_sha256'],
                  dataset_sha256=sha256(dataset), data_provenance=meta,
                  holdout_collection=record,
                  note='New sessions after freezing; lab parameters remain limited. No Ethernet blocking measurement.')
    return report, predictions
