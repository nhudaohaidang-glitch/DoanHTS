"""Artificial feature fixtures test protocol/exports, not measured network accuracy."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from part2.development import (DIVISORS_V2, evaluate_v2, load_dataset,
                              train_v2, verify_freeze)
from part2.features import NAMES, quantize

KIT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('collect_v2', KIT / 'lab/collect_v2.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def fixture(root, splits=('train', 'val'), offset=100):
    root.mkdir(parents=True, exist_ok=True)
    rows, captures = [], []
    for split in splits:
        for label in range(3):
            for session in range(2):
                cid = f'{split}_{label}_{session}'
                start = offset + len(captures) * 10
                digest = hashlib.sha256(f'{cid}-{offset}'.encode()).hexdigest()
                captures.append(dict(capture_id=cid, split=split, label=str(label),
                                     source_kind='lab', sha256=digest, start=start, end=start+4))
                for i in range(4):
                    raw = ([12+i, 70, 15, 1, 1, 1] if label == 0 and session == 0 else
                           [16+i, 65, 71, 2, 1, 2] if label == 0 else
                           [120+i, 42, 118, 2, 1, 1] if label == 1 else
                           [13+i, 58, 63, 2, 1, 6])
                    rows.append(dict(capture_id=cid, split=split, label=str(label),
                                     source_kind='lab', window_start=start+i, **dict(zip(NAMES, raw))))
    path = root / 'features.csv'
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    path.with_suffix('.meta.json').write_text(json.dumps(dict(
        features=NAMES, distinct='exact', window_seconds=1., rows=len(rows), captures=captures)))
    return path


class DevelopmentTest(unittest.TestCase):
    def test_small_port_counts_preserved_without_changing_raw_semantics(self):
        raw = [[16, 65, 71, 2, 1, 2], [13, 58, 58, 2, 1, 6]]
        self.assertEqual(quantize(raw, DIVISORS_V2)[:, 5].tolist(), [2, 6])
        self.assertEqual(quantize(raw, [8, 1, 1, 1, 1, 4])[:, 5].tolist(), [0, 1])

    def test_train_freeze_evaluate_and_detect_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            dev = fixture(root / 'dev')
            model = root / 'model'
            report = train_v2(dev, model)
            self.assertFalse(report['test_evaluated'])
            self.assertNotIn('test', report['metrics'])
            self.assertEqual(len(report['candidates']), 3)
            self.assertEqual(json.loads((model / 'model.json').read_text())['architecture'], [6, 8, 3])
            freeze = verify_freeze(model)
            holdout = fixture(root / 'holdout', ('challenge',), offset=1000)
            meta = json.loads(holdout.with_suffix('.meta.json').read_text())
            record = dict(selection=freeze, capture_ids=[c['capture_id'] for c in meta['captures']], collection_started_at=900)
            record_path = root / 'COLLECTION.json'
            record_path.write_text(json.dumps(record))
            result, predictions = evaluate_v2(holdout, model, record_path)
            self.assertEqual(result['kind'], 'v2_pinned_holdout_evaluation')
            self.assertEqual(len(predictions), 24)
            self.assertFalse(result['model_retrained'])
            record['selection']['model_sha256'] = '0' * 64
            record_path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'different frozen'):
                evaluate_v2(holdout, model, record_path)
            (model / 'model.json').write_text((model / 'model.json').read_text() + '\n')
            with self.assertRaisesRegex(ValueError, 'changed after selection'):
                verify_freeze(model)
            with self.assertRaisesRegex(ValueError, 'Output exists'):
                train_v2(dev, model)

    def test_mixed_holdout_or_reused_content_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = fixture(Path(d), ('train', 'challenge'))
            with self.assertRaisesRegex(ValueError, 'Unexpected split'):
                load_dataset(path, {'train', 'val'})
            path = fixture(Path(d))
            meta_path = path.with_suffix('.meta.json')
            meta = json.loads(meta_path.read_text())
            meta['captures'][1]['sha256'] = meta['captures'][0]['sha256']
            meta_path.write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, 'Duplicate PCAP'):
                load_dataset(path, {'train', 'val'})

    def test_holdout_cannot_reuse_development_or_predate_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            dev = fixture(root / 'dev')
            model = root / 'model'
            train_v2(dev, model)
            freeze = verify_freeze(model)
            holdout = fixture(root / 'holdout', ('challenge',), offset=1000)
            meta_path = holdout.with_suffix('.meta.json')
            meta = json.loads(meta_path.read_text())
            record = dict(selection=freeze, capture_ids=[c['capture_id'] for c in meta['captures']], collection_started_at=900)
            record_path = root / 'COLLECTION.json'
            record_path.write_text(json.dumps(record))
            meta['captures'][0]['sha256'] = freeze['development_capture_sha256'][0]
            meta_path.write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, 'PCAP reused'):
                evaluate_v2(holdout, model, record_path)
            fixture(root / 'holdout', ('challenge',), offset=1000)
            record['collection_started_at'] = 1100
            record_path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'before model freeze'):
                evaluate_v2(holdout, model, record_path)

    def test_plans_separate_roots_and_reset_each_session(self):
        root, commands = collector.plan('dev', 'fixture01')
        self.assertEqual(root, 'v2_development/fixture01')
        self.assertEqual(len(commands), 20)
        self.assertEqual({r['command'][3] for r in commands}, {'train', 'val'})
        self.assertEqual(len({r['capture_id'] for r in commands}), 20)
        plan = collector.collect('holdout', 'fixture02', '/nonexistent', dry_run=True)
        self.assertEqual(len(plan['sessions']), 10)
        self.assertTrue(plan['resets_owned_lab_before_every_session'])
        self.assertTrue(all(r['command'][3] == 'challenge' for r in plan['sessions']))
        with self.assertRaises(ValueError):
            collector.plan('dev', '../escape')

    def test_collection_resets_owned_lab_and_checks_drops(self):
        # Exercise orchestration with a fake runner, never touch host networking.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            marker = root / 'build/lab.created'
            marker.parent.mkdir()
            marker.write_text('Created by ai_part2 lab/setup_lab.sh\n')
            calls = []
            def fake_run(args, **kwargs):
                calls.append(args)
                if args[1] == 'lab/setup_lab.sh':
                    if args[2] == 'down':
                        marker.unlink()
                    else:
                        self.assertFalse(marker.exists())
                        marker.write_text('Created by ai_part2 lab/setup_lab.sh\n')
                else:
                    folder = root / 'data' / args[-1] / args[4]
                    folder.mkdir(parents=True)
                    (folder / 'capture.log').write_text('0 packets dropped by kernel\n')
            with patch.object(collector, 'KIT', root), patch.object(collector.os, 'geteuid', return_value=0), patch.object(collector.subprocess, 'run', side_effect=fake_run):
                result = collector.collect('dev', 'fixture01', '/not-used')
            self.assertEqual(result['sessions'], 20)
            self.assertEqual(sum(a[1:] == ['lab/setup_lab.sh', 'down'] for a in calls), 20)
            self.assertTrue((Path(result['saved']) / 'COMPLETE.json').exists())
            self.assertEqual(len(calls), 60)
            with patch.object(collector, 'KIT', root), patch.object(collector.os, 'geteuid', return_value=0):
                with self.assertRaisesRegex(ValueError, 'directory exists'):
                    collector.collect('dev', 'fixture01', '/not-used')


if __name__ == '__main__':
    unittest.main()
