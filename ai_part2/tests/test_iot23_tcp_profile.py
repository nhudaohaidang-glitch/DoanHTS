"""Synthetic logs verify candidate profiling, never AI accuracy or SYN labels."""
from collections import Counter
import gzip
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import profile_iot23_tcp_candidates as profiling

HEADER='#fields\tts\tduration\tid.orig_h\tid.resp_h\tid.resp_p\tproto\thistory\tconn_state\torig_pkts\tlabel\tdet_label\n'
ROWS=[
 '100.1\t1.25\t198.18.0.3\t198.18.0.1\t80\ttcp\tS\tS0\t3\tMalicious\tDDoS\n',
 '100.2\t0.5\t198.18.0.3\t198.18.0.1\t80\ttcp\tS\tS0\t2\tMalicious\tDDoS\n',
 '101.1\t-\t198.18.0.3\t198.18.0.2\t81\ttcp\tC\tOTH\t0\tMalicious\tDDoS\n',
 '103.1\t2.0\t198.18.0.3\t198.18.0.1\t443\ttcp\tShADad\tSF\t4\tMalicious\tDDoS\n',
]


class TCPProfileChecks(unittest.TestCase):
    def fixture(self,root,rows=ROWS):
        root.mkdir();path=root/'candidate.log.gz'
        with gzip.open(path,'wt') as stream:stream.write(HEADER+''.join(rows))
        source=dict(capture_id='CTU-IoT-Malware-Capture-34-1',tcp_candidates=path.name,
                    tcp_ddos_candidate_rows=len(rows),export_sha256={path.name:profiling.sha(path)})
        (root/'BAO_CAO_LOC.json').write_text(json.dumps(dict(status='complete',kind='native_source_screening_not_training_dataset',sources=[source])))
        return path

    def test_bounded_candidates_and_omitted_destination_guarantee(self):
        sequence=['heavy']*900+[str(i) for i in range(3000)];random.Random(7).shuffle(sequence)
        sketch=profiling.FrequentTargets(7)
        for key in sequence:
            sketch.add(key);self.assertLessEqual(len(sketch.counts),7)
        actual=Counter(sequence);self.assertIn('heavy',sketch.counts)
        for key,count in actual.items():
            if key not in sketch.counts:self.assertLessEqual(count,sketch.decrements)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rows=[];totals=Counter();syns=Counter()
            for i in range(80):
                dst=f'198.18.0.{i+1}';history='C' if i%3==0 else 'S'
                line=ROWS[0].replace('198.18.0.1\t80',dst+'\t80').replace('\tS\t','\t'+history+'\t')
                rows.extend([line]*(i+1));totals[dst]+=i+1
                if history=='S':syns[dst]+=i+1
            path=self.fixture(root/'many',rows)
            for capacity in (4,100):
                result=profiling.profile(path,'synthetic',len(rows),capacity)
                shown={r['dst']:r for r in result['displayed_destinations']}
                self.assertLessEqual(len(shown),20)
                for dst,count in totals.items():
                    if dst in shown:self.assertEqual(shown[dst]['flow_records'],count)
                    else:
                        self.assertLessEqual(count,result['unshown_destination_max_flow_records'])
                        self.assertLessEqual(syns[dst],result['unshown_destination_max_syn_history_rows'])

    def test_exact_recount_histories_time_bounds_and_no_project_labels(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=root/'data';path=self.fixture(data);before=profiling.sha(path)
            report=profiling.run(data,root/'result')
            result=report['sources'][0]
            self.assertEqual(result['flow_records'],4)
            self.assertEqual(result['origin_syn_history_rows'],3)
            self.assertEqual(result['checksum_history_rows'],1)
            self.assertEqual(result['orig_pkts_metadata_sum'],9)
            targets={r['dst']:r for r in result['displayed_destinations']}
            self.assertEqual(targets['198.18.0.1']['distinct_destination_ports'],2)
            self.assertEqual(targets['198.18.0.1']['last_known_flow_end'],105.1)
            self.assertIsNone(targets['198.18.0.2']['last_known_flow_end'])
            self.assertFalse(report['archive_opened']);self.assertFalse(report['pcap_opened'])
            self.assertFalse(report['project_labels_created']);self.assertFalse(report['vertical_scan_audited'])
            self.assertEqual(before,profiling.sha(path))

    def test_changed_candidate_file_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=root/'data';path=self.fixture(data)
            with path.open('ab') as stream:stream.write(b'changed')
            with self.assertRaisesRegex(ValueError,'checksum differs'):profiling.run(data,root/'result')
            self.assertFalse((root/'result').exists())

    def test_wrong_native_selection_fails_with_diagnostic_page(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=root/'data';self.fixture(data,[ROWS[0].replace('\ttcp\t','\tudp\t')])
            with self.assertRaisesRegex(ValueError,'outside original'):profiling.run(data,root/'failed')
            report=json.loads((root/'failed/BAO_CAO_NGUON.json').read_text())
            self.assertEqual(report['status'],'failed')
            self.assertTrue((root/'failed/MO_NGUON_SYN.html').is_file())


if __name__=='__main__':unittest.main()
