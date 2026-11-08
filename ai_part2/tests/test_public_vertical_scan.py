"""Source/conversion/flow-label checks, not an AI detection benchmark."""
from collections import Counter
import csv
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from scapy.layers.inet import IP,TCP
from scapy.utils import PcapReader

TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0,str(TOOLS))
import install_public_vertical_scan as installation
import prepare_public_vertical_scan as preparation

DATA=TOOLS.parent/'examples/public_vertical_scan/vertical_scan'


class PublicVerticalChecks(unittest.TestCase):
    def test_original_source_and_classic_pcap_packet_bytes_time_order(self):
        source=DATA/'nguon_goc/synscan.pcapng'
        self.assertEqual(preparation.sha(source),preparation.SOURCE['sha256'])
        with tempfile.TemporaryDirectory() as d:
            report=preparation.build(source,DATA/'nguon_goc/README_CHRIS_SANDERS.md',Path(d)/'output')
            result=Path(d)/'output/vertical_scan/pcap'/(preparation.STEM+'.pcap')
            with PcapReader(str(source)) as original,PcapReader(str(result)) as converted:
                source_packets=list(original);output_packets=list(converted)
            self.assertEqual(len(source_packets),2011);self.assertEqual(len(output_packets),2011)
            for a,b in zip(source_packets,output_packets):
                self.assertEqual(bytes(a),bytes(b));self.assertEqual(a.time,b.time)
            self.assertEqual(report['evidence']['distinct_target_ports'],1000)
            self.assertFalse(report['publisher_flow_labels_available'])
            self.assertFalse(report['synthetic_packets_created'])
            self.assertEqual(report['evidence']['packet_tcp_payload_bytes'],0)
            changed=Path(d)/'changed.pcapng';changed.write_bytes(source.read_bytes()+b'x')
            with self.assertRaisesRegex(ValueError,'differs from reviewed'):
                preparation.build(changed,DATA/'nguon_goc/README_CHRIS_SANDERS.md',Path(d)/'wrong')
            self.assertFalse((Path(d)/'wrong').exists())

    def test_csv_reconstructs_source_flows_and_does_not_claim_original_labels(self):
        expected={};ports=set();ips=set();flags=Counter()
        with PcapReader(str(DATA/'nguon_goc/synscan.pcapng')) as reader:
            for p in reader:
                ip,tcp=p[IP],p[TCP]
                orig=ip.src==preparation.SOURCE['scanner_ip']
                key=(int(tcp.sport),int(tcp.dport)) if orig else (int(tcp.dport),int(tcp.sport))
                group=expected.setdefault(key,dict(orig=0,resp=0,orig_bytes=0,resp_bytes=0))
                group['orig' if orig else 'resp']+=1
                group['orig_bytes' if orig else 'resp_bytes']+=int(ip.len)
                flags[int(tcp.flags)]+=1
                if orig:ports.add(int(tcp.dport));ips.add(ip.dst)
        with (DATA/'csv'/(preparation.STEM+'.csv')).open(newline='') as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),1994)
        self.assertEqual(len(ports),1000);self.assertEqual(len(ips),1)
        self.assertEqual(flags,{2:1994,18:12,20:5})
        self.assertEqual(sum(int(r['orig_pkts']) for r in rows),1994)
        self.assertEqual(sum(int(r['resp_pkts']) for r in rows),17)
        for row in rows:
            group=expected.pop((int(row['id.orig_p']),int(row['id.resp_p'])))
            self.assertEqual([int(row[k]) for k in ('orig_pkts','resp_pkts','orig_ip_bytes','resp_ip_bytes')],
                             [group[k] for k in ('orig','resp','orig_bytes','resp_bytes')])
            self.assertEqual(row['loai_da_loc'],'vertical_scan')
            self.assertEqual(row['label_basis'],'project_reviewed_packet_behavior')
            self.assertNotIn('label',row)
        self.assertFalse(expected)

    def test_installer_keeps_existing_classes_checks_hashes_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle=root/'bundle';bundle.mkdir();shutil.copytree(DATA,bundle/'vertical_scan')
            def manifest():
                checksums={str(p.relative_to(bundle)):installation.sha(p) for p in (bundle/'vertical_scan').rglob('*') if p.is_file()}
                (bundle/'FILE_SHA256.json').write_text(json.dumps(checksums))
            manifest();output=root/'output';output.mkdir()
            for name in ('binh_thuong','syn_flood'):
                folder=output/name;folder.mkdir();(folder/'keep.txt').write_text('existing '+name)
            native_report=output/'BAO_CAO_XUAT.json';native_report.write_text('{"status":"complete"}')
            installation.install(bundle,output);installation.install(bundle,output)
            self.assertEqual(native_report.read_text(),'{"status":"complete"}')
            self.assertEqual((output/'binh_thuong/keep.txt').read_text(),'existing binh_thuong')
            self.assertEqual((output/'syn_flood/keep.txt').read_text(),'existing syn_flood')
            pcaps=list((output/'vertical_scan/pcap').glob('*.pcap'));self.assertEqual(len(pcaps),1)
            pcaps[0].write_bytes(b'changed local data')
            with self.assertRaisesRegex(ValueError,'Existing vertical_scan differs'):
                installation.install(bundle,output)
            self.assertEqual(pcaps[0].read_bytes(),b'changed local data')
            (bundle/'vertical_scan/csv'/(preparation.STEM+'.csv')).write_text('changed bundle')
            with self.assertRaisesRegex(ValueError,'Bundled file missing/changed'):
                installation.install(bundle,output)


if __name__=='__main__':
    unittest.main()
