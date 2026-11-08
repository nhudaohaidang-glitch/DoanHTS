"""Handoff safety, original source identity and q0/empty-window integration."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

KIT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(KIT),str(KIT/'tools')]
from prepare_v5_handoff import prepare,source_inventory,MODEL_SHA
from train_filtered_three_classes import verify_files
from review_trained_v4 import scalar_scores

RELEASE=KIT/'examples/user_v5_from_full_cache'


class V5HandoffChecks(unittest.TestCase):
    def test_original_model_cache_and_labels_preserved_and_vector_contract(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'handoff';before=(RELEASE/'candidate_v5/model/model.json').read_bytes()
            report=prepare(RELEASE,output)
            self.assertEqual(report['source_inventory_counts'],[28,1,1])
            self.assertEqual(report['original_windows_by_class'],[39253935,21,4])
            self.assertFalse(report['model_retrained']);self.assertFalse(report['group_hardware_interface_verified'])
            self.assertFalse(report['automatic_blocking_ready']);self.assertFalse(report['local_sources']['checked'])
            self.assertEqual((output/'model/model.json').read_bytes(),before)
            self.assertEqual(hashlib.sha256(before).hexdigest(),MODEL_SHA)
            model=json.loads(before);cases=json.loads((output/'INTEGRATION_V5.json').read_text())['cases']
            self.assertEqual(len(cases),37);self.assertFalse(cases[0]['valid_window'])
            self.assertIsNone(cases[0]['expected_class_id']);self.assertIsNone(cases[0]['expected_scores'])
            for case in cases[1:]:
                n=case['packet_count'];self.assertGreater(n,0)
                raw=[n,case['ip_byte_sum']//n,127*case['syn_open_count']//n,case['src_count'],case['dst_count'],case['dst_port_count']]
                q=[min(127,v//div) for v,div in zip(raw,model['divisors'])]
                packed=sum(v<<(8*i) for i,v in enumerate(q))
                self.assertEqual(q,case['q']);self.assertEqual(raw,case['raw'])
                self.assertEqual(case['feat_lo'],packed&0xffffffff);self.assertEqual(case['feat_hi'],packed>>32)
                self.assertEqual(scalar_scores(q,model),case['expected_scores'])
            sparse=next(c for c in cases if c['case']=='single_legitimate_syn')
            self.assertEqual(sparse['q'][0],0);self.assertTrue(sparse['valid_window'])
            complete=json.loads((output/'HANDOFF_COMPLETE.json').read_text());verify_files(output,complete['files'])
            with self.assertRaisesRegex(ValueError,'Output exists'):prepare(RELEASE,output)

    def test_local_files_and_hashes_are_distinguished_and_changes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);sources=[]
            for label,folder in enumerate(('binh_thuong','syn_flood','vertical_scan')):
                path=root/folder/'pcap/fixture.pcap';path.parent.mkdir(parents=True);path.write_bytes(bytes([label]))
                csv=root/folder/'csv';csv.mkdir();(csv/'fixture.csv').write_text('label\n')
                sources.append(dict(label=label,path=str(path.relative_to(root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            state=dict(base=dict(original_sources=sources))
            result=source_inventory(state,root)
            self.assertEqual(result['selected_pcaps_by_class'],[1,1,1]);self.assertFalse(result['pcap_checksums_recomputed'])
            self.assertTrue(source_inventory(state,root,True)['pcap_checksums_recomputed'])
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'differs from training'):source_inventory(state,root,True)
            path.unlink()
            with self.assertRaisesRegex(ValueError,'Missing original'):source_inventory(state,root)
            with self.assertRaisesRegex(ValueError,'Supply --data'):source_inventory(state,None,True)

    def test_changed_model_never_exported_as_reviewed_v5(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'release';shutil.copytree(RELEASE,source)
            path=source/'candidate_v5/model/model.json';path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'changed/missing'):prepare(source,root/'handoff')
            self.assertFalse((root/'handoff').exists())


if __name__=='__main__':unittest.main()
