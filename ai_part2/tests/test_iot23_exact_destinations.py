"""Exact flow-metadata census tests, not packet-rate or attack-label tests."""
from collections import Counter
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import count_iot23_destinations_exact as exact

HEADER='#fields\tts\tduration\tid.orig_h\tid.resp_h\tid.resp_p\tproto\thistory\tconn_state\torig_pkts\tlabel\tdetailed-label\n'


def fixture(root,expected_offset=0):
    root.mkdir();path=root/'candidate.log.gz'
    rows=[]
    for i in range(4):rows.append(f'100.{i}\t0.01\t198.18.0.3\t198.18.0.1\t80\ttcp\tS\tS0\t2\tMalicious\tDDoS\n')
    rows+=[
        '101.0\t10.0\t198.18.0.3\t198.18.0.2\t81\ttcp\tS\tS0\t500\tMalicious\tDDoS\n',
        '103.0\t-\t198.18.0.3\t198.18.0.4\t82\ttcp\tC\tOTH\t-\tMalicious\tDDoS\n',
        '104.0\t-\t198.18.0.3\t198.18.0.5\t83\ttcp\tC\tOTH\t0\tMalicious\tDDoS\n',
    ]
    with gzip.open(path,'wt') as stream:stream.write(HEADER+''.join(rows))
    source=dict(capture_id='CTU-IoT-Malware-Capture-17-1',tcp_candidates=path.name,tcp_ddos_candidate_rows=len(rows)+expected_offset,
                export_sha256={path.name:exact.sha(path)})
    (root/'BAO_CAO_LOC.json').write_text(json.dumps(dict(status='complete',kind='native_source_screening_not_training_dataset',sources=[source])))
    return path


class ExactDestinationChecks(unittest.TestCase):
    def test_chunk_boundary_groups_weights_missing_and_rare_heavy_flow(self):
        data=np.array([(1,2)]*3+[(2,100),(3,exact.UNKNOWN),(4,0)]+[(5,1)]*65,dtype=[('dst','<u4'),('packets','<u8')])
        data.sort(order='dst')
        for chunk_size in (1,2,11,131072):
            result=exact.group_exact(data,chunk_size=chunk_size,top_k=1)
            self.assertEqual(result['unique_destination_ips'],5)
            self.assertEqual(result['max_flow_records_per_destination'],65)
            self.assertEqual(result['max_known_orig_pkts_sum_per_destination'],100)
            self.assertEqual(result['max_orig_pkts_in_one_flow'],100)
            self.assertEqual(result['missing_orig_pkts_rows'],1)
            self.assertEqual(result['known_orig_pkts_sum'],171)
            self.assertEqual(result['flow_records_grouped'],len(data))
            self.assertEqual(result['exact_rankings']['flow_records'],['0.0.0.5'])
            self.assertEqual(result['exact_rankings']['known_orig_pkts_sum'],['0.0.0.2'])
        big=np.array([(1,(1<<53)+1)],dtype=[('dst','<u4'),('packets','<u8')])
        self.assertEqual(exact.group_exact(big)['known_orig_pkts_sum'],(1<<53)+1)

    def test_full_cli_logic_exact_recount_preserves_input_and_never_creates_pps_or_labels(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=fixture(root/'source');before=exact.sha(path)
            report=exact.run(root/'source',root/'result')
            result=report['exact'];self.assertEqual(result['unique_destination_ips'],4)
            self.assertEqual(result['max_flow_records_per_destination'],4)
            self.assertEqual(result['max_known_orig_pkts_sum_per_destination'],500)
            self.assertEqual(result['missing_orig_pkts_rows'],1)
            self.assertEqual(result['selected_destinations']['198.18.0.2']['last_known_flow_end'],111.)
            self.assertEqual(result['selected_destinations']['198.18.0.4']['missing_orig_pkts_recounted'],1)
            self.assertFalse(report['packet_rates_inferred_from_flows']);self.assertFalse(report['project_labels_created'])
            self.assertFalse(report['archive_opened']);self.assertFalse(report['pcap_opened'])
            self.assertEqual(exact.sha(path),before)
            self.assertFalse(list((root/'result').rglob('*.tmp')))
            self.assertFalse(list((root/'result').rglob('y.csv')))

    def test_changed_candidate_hash_stops_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=fixture(root/'source')
            with path.open('ab') as stream:stream.write(b'changed')
            with self.assertRaisesRegex(ValueError,'hash differs'):exact.run(root/'source',root/'result')
            self.assertFalse((root/'result').exists())

    def test_row_count_mismatch_is_failed_not_a_complete_census(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=fixture(root/'source',expected_offset=-1);before=exact.sha(path)
            with self.assertRaisesRegex(ValueError,'exceeds'):exact.run(root/'source',root/'failed')
            report=json.loads((root/'failed/BAO_CAO_DICH.json').read_text())
            self.assertEqual(report['status'],'failed')
            self.assertEqual(exact.sha(path),before)
            self.assertTrue((root/'failed/MO_DICH.html').exists())


if __name__=='__main__':unittest.main()
