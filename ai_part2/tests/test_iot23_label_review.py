"""Regression fixtures test label correction; no claim of SYN flood truth."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import review_iot23_extraction_labels as repair


def fixture(root,count=1):
    root.mkdir();all_rows=[[count,60,127,1,1,1]]*9+[[150,60,84,1,1,1]]
    candidates=root/'syn_da_kiem_tra';complete=root/'tat_ca_cua_so_dich'
    candidates.mkdir();complete.mkdir()
    for folder,rows in ((candidates,all_rows[:9]),(complete,all_rows)):
        repair.write_csv(folder/'X_6_raw.csv',repair.NAMES,rows)
        repair.write_csv(folder/'X_6_fpga.csv',['q0','q1','q2','q3','q4','q5'],
                         [[min(127,value//div) for value,div in zip(row,repair.DIVISORS)] for row in rows])
    repair.write_csv(candidates/'y.csv',['class'],[[1]]*9)
    repair.write_csv(candidates/'THONG_TIN_DONG.csv',['row_number','capture_id','protected_ip','window_start','episode_id'],
                     [[i+1,'CTU-IoT-Malware-Capture-35-1','216.18.168.16',101+i,1] for i in range(9)])
    repair.write_csv(complete/'BANG_CHUNG.csv',['row_number','window_start','syn_open_packets','native_ddos_syn_packets','other_or_unmatched_syn_packets','verified_syn_label'],
                     [[i+1,101+i,count,count,0,1] for i in range(9)]+[[10,200,100,90,10,'']])
    report=dict(status='complete',capture_id='CTU-IoT-Malware-Capture-35-1',
                verification=dict(target='216.18.168.16',eligible_nonempty_complete_windows=10,verified_syn_windows=9),
                pcap_extraction=dict(retained_tcp_flag_bytes={'216.18.168.16':{'02':9*count+100,'10':50}}))
    (root/'BAO_CAO_PCAP.json').write_text(json.dumps(report))
    (root/'MO_KET_QUA_PCAP.html').write_text('<h1>Legacy generated page</h1>')
    (root/'preserved.pcap').write_bytes(b'PCAP sentinel: must not be edited or opened by this CSV review')
    return candidates


class LabelReviewChecks(unittest.TestCase):
    def test_sparse_rows_not_flood_labels_and_mixed_windows_are_reviewed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'input';candidate=fixture(source)
            preserved=[source/'BAO_CAO_PCAP.json',source/'preserved.pcap',candidate/'X_6_raw.csv',candidate/'X_6_fpga.csv',source/'tat_ca_cua_so_dich/BANG_CHUNG.csv']
            before={str(p):repair.sha(p) for p in preserved};y_sha=repair.sha(candidate/'y.csv')
            original_page=(source/'MO_KET_QUA_PCAP.html').read_bytes()
            report=repair.review(source,root/'result')
            self.assertEqual(report['candidate_packet_count_range'],[1,1])
            self.assertEqual(report['unique_candidate_raw_vectors'],1)
            self.assertEqual(report['peak_syn_packets_per_second'],100)
            self.assertEqual(report['peak_native_ddos_syn_packets_per_second'],90)
            self.assertEqual(report['highest_syn_windows'][0]['window_start'],200)
            self.assertFalse(report['project_labels_created']);self.assertFalse(report['normal_labels_created'])
            self.assertFalse(report['syn_flood_verified']);self.assertFalse(report['model_changed'])
            self.assertFalse(report['archive_opened']);self.assertFalse(report['pcap_opened'])
            self.assertFalse((candidate/'y.csv').exists())
            self.assertEqual(repair.sha(candidate/'y_LEGACY_KHONG_DUNG_TRAIN.csv'),y_sha)
            self.assertEqual((source/'MO_KET_QUA_PCAP_TRUOC_SUA_NHAN.html').read_bytes(),original_page)
            self.assertEqual(before,{str(p):repair.sha(p) for p in preserved})
            self.assertFalse(list((root/'result').rglob('y.csv')))
            names,rows=repair.read(root/'result/TOM_TAT_SUA_NHAN.csv')
            self.assertEqual(len(names),7);self.assertEqual(rows[0]['candidate_min_packets'],'1')
            self.assertEqual(rows[0]['candidate_max_packets'],'1')
            self.assertEqual(rows[0]['automatic_flood_labels'],'0')
            # A repeat preserves the original backup and does not overwrite it.
            again=repair.review(source,root/'result2')
            self.assertEqual(again['legacy_label_sha256'],y_sha)
            self.assertEqual((source/'MO_KET_QUA_PCAP_TRUOC_SUA_NHAN.html').read_bytes(),original_page)

    def test_high_rate_metadata_also_does_not_automatically_create_labels(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'input';fixture(source,count=500)
            report=repair.review(source,root/'result')
            self.assertEqual(report['candidate_packet_count_range'],[500,500])
            self.assertFalse(report['syn_flood_verified'])
            self.assertFalse(list((root/'result').rglob('y.csv')))

    def test_user_changed_labels_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'input';candidate=fixture(source)
            repair.write_csv(candidate/'y.csv',['class'],[[0]]*9)
            before=repair.sha(candidate/'y.csv')
            with self.assertRaisesRegex(ValueError,'Legacy labels differ'):repair.review(source,root/'result')
            self.assertEqual(repair.sha(candidate/'y.csv'),before)
            self.assertFalse((root/'result').exists())

    def test_misaligned_candidate_is_not_silently_repaired(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'input';candidate=fixture(source)
            repair.write_csv(candidate/'X_6_raw.csv',repair.NAMES,[[2,60,127,1,1,1]]+[[1,60,127,1,1,1]]*8)
            with self.assertRaisesRegex(ValueError,'does not match'):repair.review(source,root/'result')
            self.assertTrue((candidate/'y.csv').exists())
            self.assertFalse((root/'result').exists())


if __name__=='__main__':unittest.main()
