"""Artificial fixtures verify hybrid v3 protocol, never measured model quality."""
import csv,hashlib,json,tempfile,unittest
from pathlib import Path
from scapy.all import Ether,IP,TCP,wrpcap
from test_v2_development import fixture
from part2.development import sha256
from part2.features import NAMES
from part2.hybrid_data import native_cache,read_cache,build_development,csv_write
from part2.hybrid_training import train_hybrid
from part2.hybrid_evaluation import evaluate_hybrid
from lab.collect_v2 import plan

KIT=Path(__file__).resolve().parents[1]


def development(root):
    path=fixture(root/'dev')
    meta=json.loads(path.with_suffix('.meta.json').read_text())
    with path.open() as f:rows=list(csv.DictReader(f))
    for c in meta['captures']:
        c['source_dataset']='controlled_lab'
        if c['label']=='0' and c['capture_id'].endswith('_0'):
            c.update(source_kind='external',source_dataset='IoT-23',source={'role':c['split']})
            for row in rows:
                if row['capture_id']==c['capture_id']:row['source_kind']='external'
    csv_write(path,rows)
    protocol=json.loads((KIT/'spec/HYBRID_V3_PROTOCOL.json').read_text())
    protocol['selection'].update(alpha=[.01],seeds=[11])
    meta.update(csv_sha256=sha256(path),protocol=protocol)
    path.with_suffix('.meta.json').write_text(json.dumps(meta))
    model=root/'model';train_hybrid(path,model)
    return model,meta


def external_test(root,model):
    freeze=json.loads((model/'FREEZE.json').read_text());plan=freeze['reserved_external_test']
    source=dict(capture_id=plan['capture_id'],label=0,role='reserved_test',protected_ip=plan['protected_ip'],
                pcap_url=plan['pcap_url'],pcap_sha256='9'*64)
    rows=[dict(capture_id=source['capture_id'],split='unassigned',label=0,source_kind='external',window_start=1000,
               **dict(zip(NAMES,[12,70,15,1,1,1])))]
    path=root/'external.csv';csv_write(path,rows)
    path.with_suffix('.meta.json').write_text(json.dumps(dict(features=NAMES,window_seconds=1.,distinct='exact',rows=1,
        csv_sha256=sha256(path),source=source,complete_time_slots=3,
        test_receipt={'model_sha256':freeze['model_sha256'],'source_plan':plan,'sha256':source['pcap_sha256']})))
    return path


def fresh_lab(root,model):
    _,commands=plan('holdout','unitfresh','hybrid-v3')
    rows=[];captures=[]
    for i,c in enumerate(commands):
        cid=c['capture_id'];mode=c['command'][2];label=0 if mode in ('normal','normal_probe') else 1 if mode=='syn' else 2
        raw=[16,65,71,2,1,2] if label==0 else [120,42,118,2,1,1] if label==1 else [13,58,63,2,1,6]
        for j in range(3):
            sample=[0]*6 if i==3 and j==0 else raw
            rows.append(dict(capture_id=cid,split='challenge',label=str(label),source_kind='lab',window_start=2000+i*10+j,
                             **dict(zip(NAMES,sample))))
        captures.append(dict(capture_id=cid,split='challenge',label=str(label),source_kind='lab',start=2000+i*10,
                             sha256=hashlib.sha256(cid.encode()).hexdigest()))
    path=root/'lab.csv';csv_write(path,rows)
    path.with_suffix('.meta.json').write_text(json.dumps(dict(features=NAMES,window_seconds=1.,distinct='exact',rows=len(rows),captures=captures)))
    record=root/'COLLECTION.json';record.write_text(json.dumps(dict(selection=json.loads((model/'FREEZE.json').read_text()),protocol_profile='hybrid-v3',
        plan=commands,capture_ids=[c['capture_id'] for c in commands],collection_started_at=1900)))
    return path,record


class HybridTest(unittest.TestCase):
    def test_native_cache_packet_windows_and_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);packets=[]
            for t in [100.1,101.1,102.9]:
                p=Ether(src='02:00:00:00:00:03',dst='02:00:00:00:00:01')/IP(src='198.18.0.3',dst='198.18.0.1')/TCP(flags='S',dport=80)
                p.time=t;packets.append(p)
            pcap=root/'fixture.pcap';wrpcap(str(pcap),packets)
            source=dict(capture_id='unit_native',role='train',label=1,protected_ip='198.18.0.1',pcap_sha256=sha256(pcap),
                        verified_episode_start=100.1,verified_episode_end=102.9,verified_syn_packets=3)
            cache=root/'cache.csv';meta=native_cache(pcap,source,cache)
            self.assertEqual(meta['rows'],1)
            rows,_=read_cache(cache);self.assertEqual(int(rows[0]['syn_ratio_q127']),127)
            with self.assertRaisesRegex(ValueError,'Cache exists'):native_cache(pcap,source,cache)
            cache.write_text(cache.read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'checksum'):read_cache(cache)

    def test_train_external_and_full_fresh_test(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);model,meta=development(root)
            self.assertEqual(json.loads((model/'model.json').read_text())['model_version'],'v3')
            metrics=json.loads((model/'metrics.json').read_text());self.assertFalse(metrics.get('test_evaluated'))
            self.assertIn('IoT-23',metrics['metrics']['val']['integer']['per_source'])
            cache=external_test(root,model)
            report,details=evaluate_hybrid(model,cache)
            self.assertFalse(report['all_three_class_test_complete']);self.assertEqual(report['native_missing_classes'],[1,2])
            lab,record=fresh_lab(root,model)
            report,details=evaluate_hybrid(model,cache,lab,record)
            self.assertTrue(report['all_three_class_test_complete'])
            self.assertEqual(report['lab_empty_windows_skipped'],1)
            self.assertEqual(report['lab']['integer']['windows'],32)
            self.assertEqual(report['combined_missing_classes'],[])
            r=json.loads(record.read_text());r['protocol_profile']='v2';record.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'profile'):evaluate_hybrid(model,cache,lab,record)
            (model/'float_model.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Floating weights'):evaluate_hybrid(model,cache)

    def test_source_reuse_and_wrong_test_model_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);model,meta=development(root);cache=external_test(root,model)
            p=cache.with_suffix('.meta.json');m=json.loads(p.read_text());m['test_receipt']['model_sha256']='0'*64;p.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'receipt'):evaluate_hybrid(model,cache)
            cache=external_test(root,model);lab,record=fresh_lab(root,model)
            p=lab.with_suffix('.meta.json');m=json.loads(p.read_text());m['captures'][0]['sha256']=meta['captures'][0]['sha256'];p.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'reuses development'):evaluate_hybrid(model,cache,lab,record)

    def test_profile_is_separate_and_keeps_v2_plan(self):
        self.assertEqual(len(plan('holdout','x')[1]),10)
        root,commands=plan('holdout','x','hybrid-v3')
        self.assertEqual(root,'v3_holdout/x');self.assertEqual(len(commands),11)
        sparse=next(c for c in commands if c['capture_id'].endswith('normal_sparse'))
        self.assertEqual(sparse['command'][7],'2.5')
        with self.assertRaises(ValueError):plan('dev','x','hybrid-v3')


if __name__=='__main__':unittest.main()
