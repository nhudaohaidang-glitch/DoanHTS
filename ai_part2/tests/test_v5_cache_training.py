"""Actual-cache regression, integer conversion and packet/feature agreement."""
import csv
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np
from scapy.utils import RawPcapReader

KIT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(KIT),str(KIT/'tools')]
from part2.features import NAMES,extract,values,quantize
from part2.filtered_calibration import calibrate_integer_model
from part2.filtered_training import unpack
from part2.integer import infer
from prepare_gowin import validate
from train_from_v4_cache import read_base,evaluate_cache

RESULT=KIT/'examples/user_v5_from_full_cache'
VARIANTS=KIT/'examples/scan_time_variants_v5'
SOURCE=KIT/'examples/public_vertical_scan/vertical_scan/pcap/chris_sanders_synscan_vertical.pcap'


class V5CacheChecks(unittest.TestCase):
    def test_actual_base_identity_exact_metrics_and_original_patterns_kept(self):
        base,metrics,cache,info=read_base(RESULT/'V4_GOC')
        self.assertEqual(info['model_sha256'],'51050d9c05fbbbdda6cca1e21f26366ffcfeddbe7e3a01479a38eb70e790d906')
        self.assertEqual([sum(s['label']==i for s in info['original_sources']) for i in range(3)],[28,1,1])
        before,unique,windows=evaluate_cache(cache,base)
        self.assertEqual(unique,[1513,1,4]);self.assertEqual(windows,[39253935,21,4])
        self.assertEqual(before['confusion_matrix'],metrics['training_fit']['integer']['confusion_matrix'])
        model,count=validate(RESULT/'candidate_v5/model')
        self.assertEqual(count,1896)
        after,_,_=evaluate_cache(cache,model)
        self.assertEqual(before['confusion_matrix'],after['confusion_matrix'])
        # All original labeled points and multiplicities survive augmentation.
        with sqlite3.connect(cache) as old,sqlite3.connect(RESULT/'candidate_v5/model/training_patterns.sqlite') as new:
            for label,packed,n in old.execute('SELECT label,packed,count FROM patterns'):
                total=new.execute('SELECT count FROM patterns WHERE label=? AND packed=?',(label,packed)).fetchone()[0]
                self.assertEqual(total,n) if label!=2 else self.assertGreaterEqual(total,n)
        with tempfile.TemporaryDirectory() as d:
            damaged=Path(d)/'base';shutil.copytree(RESULT/'V4_GOC',damaged)
            target=damaged/'candidate_v4/model/model.json';target.write_bytes(target.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'changed/missing'):read_base(damaged)

    def test_integer_calibration_protects_frequent_benign_patterns(self):
        folder=RESULT/'candidate_v5/model';floating=json.loads((folder/'float_model.json').read_text())
        clf=SimpleNamespace(coefs_=[np.asarray(floating[k]) for k in ('w1','w2')],
                            intercepts_=[np.asarray(floating[k]) for k in ('b1','b2')])
        with sqlite3.connect(folder/'training_patterns.sqlite') as db:
            rows=list(db.execute('SELECT label,packed,count FROM patterns ORDER BY label,packed'))
        model,report=calibrate_integer_model(clf,[unpack(p) for l,p,n in rows],[l for l,p,n in rows],[n for l,p,n in rows],23)
        actual=json.loads((folder/'model.json').read_text())
        for key in ('w1','w2','b1','b2','shift1','shift2'):self.assertEqual(model[key],actual[key])
        self.assertFalse(report['engineered_probes_used']);self.assertFalse(report['independent_validation_used'])
        self.assertEqual(report['selected']['window_errors_by_class'],[12,0,0])
        self.assertGreater(report['candidates'][0]['window_errors_by_class'][0],20_000_000)
        self.assertEqual(int(infer([[0,20,127,1,1,1]],model).argmax(1)[0]),0)

    def test_time_variants_preserve_frames_and_match_canonical_extractor(self):
        manifest=json.loads((VARIANTS/'AUGMENTATION_MANIFEST.json').read_text())
        self.assertEqual(manifest['new_independent_episodes'],0)
        self.assertEqual(len(manifest['variants']),28)
        with RawPcapReader(str(SOURCE)) as reader:original=list(reader)
        first=min(m.sec*1_000_000+m.usec for raw,m in original)
        accepted=sparse=0
        for spec in manifest['variants']:
            self.assertEqual(spec['parent_group'],manifest['original_parent_group'])
            with RawPcapReader(str(VARIANTS/spec['pcap'])) as reader:changed=list(reader)
            self.assertEqual(len(original),len(changed))
            for (raw,a),(out,b) in zip(original,changed):
                self.assertEqual(raw,out);self.assertEqual(a.wirelen,b.wirelen)
                self.assertEqual(b.sec*1_000_000+b.usec,spec['first_scan_timestamp_us']+(a.sec*1_000_000+a.usec-first)*spec['scale'])
            with (VARIANTS/spec['feature_csv']).open(newline='') as stream:rows=list(csv.DictReader(stream))
            accepted+=sum(r['training_label']=='2' for r in rows);sparse+=sum(r['training_label']=='' for r in rows)
            for row in rows:
                self.assertEqual(row['training_label']=='2',int(row['dst_port_count'])>=3)
                if row['training_label']=='':self.assertEqual(row['window_scope'],'needs_multiwindow_context')
            if (spec['scale'],spec['phase_microseconds']) in ((2,0),(32,250000),(128,750000)):
                windows,stats=extract(VARIANTS/spec['pcap'],'64.13.134.52/32',1.,'exact')
                for row in rows:
                    raw=values(windows[int(row['window_start'])],'exact')
                    self.assertEqual(raw,[int(row[n]) for n in NAMES])
                    self.assertEqual(quantize(raw,[8,2,1,1,1,1]).tolist(),[int(row[f'q{i}']) for i in range(6)])
        self.assertEqual(accepted,1423);self.assertEqual(sparse,192)


if __name__=='__main__':unittest.main()
