"""Synthetic flow fixtures check filtering; never measure AI detection quality."""
import csv
import gzip
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import filter_iot23_native_labels as filtering

HEADER=b'#fields\tts\tduration\tid.orig_h\tid.orig_p\tid.resp_h\tid.resp_p\tproto\ttunnel_parents   label   det_label\n'
ROWS=(b'100.1\t0.1\t198.18.0.3\t40000\t198.18.0.1\t80\ttcp\t-   Malicious   DDoS\n'
      b'100.2\t0.1\t198.18.0.3\t40001\t198.18.0.1\t80\tudp\t-   Malicious   DDoS\n'
      b'101.0\t0.2\t198.18.0.3\t40002\t198.18.0.1\t23\ttcp\t-   Malicious   PartOfAHorizontalPortScan\n'
      b'102.0\t0.1\t198.18.0.3\t40003\t198.18.0.1\t443\ttcp\t-   benign   -\n')


class NativeFilterChecks(unittest.TestCase):
    def test_original_rows_preserved_and_no_syn_vertical_relabel(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=HEADER+ROWS+b'#close 105\n'
            result=filtering.filter_log(io.BytesIO(data),dict(capture_id='CTU-Honeypot-Capture-4-1',bytes=len(data),benign_scenario=True),root,1024*1024)
            self.assertEqual(result['connection_records'],4)
            self.assertEqual(result['ddos_protocols'],{'tcp':1,'udp':1})
            self.assertEqual(result['tcp_ddos_candidate_rows'],1)
            self.assertEqual(result['normal_scenario_rows'],1)
            with gzip.open(root/result['tcp_candidates'],'rb') as stream:chosen=stream.read()
            self.assertIn(ROWS.splitlines(keepends=True)[0],chosen)
            self.assertNotIn(b'udp\t-',chosen)
            self.assertNotIn(b'HorizontalPortScan',chosen)
            self.assertIn(b'Malicious   DDoS',chosen)
            self.assertNotIn(b'SYN',chosen)
            with gzip.open(root/result['normal_log'],'rb') as stream:normal=stream.read()
            self.assertIn(b'benign   -',normal)

    def test_udp_only_is_not_a_tcp_candidate_or_training_label(self):
        with tempfile.TemporaryDirectory() as d:
            data=HEADER+ROWS.splitlines(keepends=True)[1]
            result=filtering.filter_log(io.BytesIO(data),dict(capture_id='CTU-IoT-Malware-Capture-7-1',bytes=len(data),benign_scenario=False),Path(d),1024*1024)
            self.assertEqual(result['ddos_protocols'],{'udp':1})
            self.assertIsNone(result['tcp_candidates'])
            self.assertFalse(list(Path(d).rglob('*.log.gz')))

    def test_streaming_archive_screening_and_failed_variant_diagnostic(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=HEADER+ROWS
            member='opt/data/CTU-IoT-Malware-Capture-34-1/bro/conn.log.labeled'
            archive=root/'input.tar.gz'
            with tarfile.open(archive,'w:gz') as tar:
                entry=tarfile.TarInfo(member);entry.size=len(data);tar.addfile(entry,io.BytesIO(data))
                entry=tarfile.TarInfo('../escape');entry.size=1;tar.addfile(entry,io.BytesIO(b'x'))
            inventory=root/'KIEM_KE.csv'
            def inventory_size(size):
                with inventory.open('w',newline='') as stream:
                    writer=csv.writer(stream);writer.writerow(['archive_path','bytes','type','selected']);writer.writerow([member,size,'file','False'])
            inventory_size(len(data));report=filtering.screen(archive,inventory,root/'result')
            self.assertEqual(report['status'],'complete')
            self.assertEqual(report['total_tcp_ddos_candidate_rows'],1)
            self.assertFalse(report['project_labels_created'])
            self.assertFalse(report['vertical_class_verified'])
            self.assertFalse((root/'escape').exists())
            self.assertEqual(report['archive_sha256'],filtering.hashlib.sha256(archive.read_bytes()).hexdigest())
            inventory_size(len(data)+1)
            with self.assertRaisesRegex(ValueError,'changed labelled log'):
                filtering.screen(archive,inventory,root/'failed')
            self.assertEqual(json.loads((root/'failed/BAO_CAO_LOC.json').read_text())['status'],'failed')
            self.assertTrue((root/'failed/MO_KET_QUA_LOC.html').exists())
            inventory_size(len(data));(root/'BAO_CAO.json').write_text(json.dumps({'archive_sha256':'0'*64}))
            with self.assertRaisesRegex(ValueError,'Archive differs'):
                filtering.screen(archive,inventory,root/'wrong_archive')
            self.assertEqual(json.loads((root/'wrong_archive/BAO_CAO_LOC.json').read_text())['status'],'failed')

    def test_unsafe_inventory_path_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'inventory.csv'
            path.write_text('archive_path,bytes,type,selected\n../CTU-IoT-Malware-Capture-34-1/bro/conn.log.labeled,10,file,False\n')
            with self.assertRaisesRegex(ValueError,'Unsafe'):filtering.checked_inventory(path)


if __name__=='__main__':unittest.main()
