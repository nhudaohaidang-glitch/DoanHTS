"""Recovery guards use artificial files; they do not measure AI accuracy."""
import hashlib
import io
import json
import lzma
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import recover_iot23_partial as recovery


def pcap(packet=b'example-packet',seconds=100,linktype=1,count=1):
    header=struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,linktype)
    record=struct.pack('<IIII',seconds,123,len(packet),len(packet))+packet
    return header+record*count


class RecoveryGuards(unittest.TestCase):
    def test_only_global_header_difference_can_pass_packet_equivalence(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.pcap',Path(d)/'b.pcap'
            original=pcap();a.write_bytes(original)
            changed=bytearray(original);changed[8:12]=struct.pack('<I',3600)
            b.write_bytes(changed)
            self.assertTrue(recovery.packet_equivalence(a,b)['equivalent'])
            wire_changed=bytearray(original);wire_changed[36:40]=struct.pack('<I',999)
            micro_changed=bytearray(original);micro_changed[28:32]=struct.pack('<I',124)
            for different in (pcap(packet=b'changed-packet'),pcap(seconds=101),pcap(linktype=101),pcap(count=2),wire_changed,micro_changed,b'not a pcap'):
                b.write_bytes(different)
                self.assertFalse(recovery.packet_equivalence(a,b)['equivalent'])

    def test_download_checks_both_compressed_and_expanded_bytes(self):
        original=pcap();compressed=lzma.compress(original)
        source=dict(relative_pcap='hue4/test.pcap',pcap_url='https://example.invalid/test.pcap.xz',
                    pcap_bytes=len(original),pcap_sha256=hashlib.sha256(original).hexdigest(),
                    download_bytes=len(compressed),download_sha256=hashlib.sha256(compressed).hexdigest())
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(recovery,'urlopen',return_value=io.BytesIO(compressed)):
                target=recovery.official_hue(source,root/'valid')
            self.assertEqual(target.read_bytes(),original)
            for name,payload,changes in (
                ('long',compressed+b'bad',{}),
                ('bad_compressed_hash',compressed,{'download_sha256':'0'*64}),
                ('bad_expanded_hash',compressed,{'pcap_sha256':'0'*64}),
            ):
                with self.subTest(name=name),patch.object(recovery,'urlopen',return_value=io.BytesIO(payload)):
                    with self.assertRaises(ValueError):
                        recovery.official_hue(dict(source,**changes),root/name)
                    self.assertFalse((root/name/'official_reference'/source['relative_pcap']).exists())
                    self.assertFalse(list((root/name).rglob('*.part')))

    def test_unverified_syn_stops_before_download_or_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);work=root/'work';work.mkdir()
            original=json.dumps({'found':['iot23_syn34']})
            (work/'BAO_CAO.json').write_text(original)
            source=dict(capture_id='iot23_syn34',relative_pcap='syn/test.pcap',pcap_bytes=3,pcap_sha256='0'*64)
            registry=root/'sources.json'
            registry.write_text(json.dumps([dict(capture_id='iot23_hue4'),source]))
            bad=work/'raw'/source['relative_pcap'];bad.parent.mkdir(parents=True);bad.write_bytes(b'bad')
            with patch.object(recovery.processor,'REGISTRY',registry),patch.object(recovery,'urlopen') as network:
                with self.assertRaisesRegex(ValueError,'Syn34'):
                    recovery.recover(work,root/'result')
                network.assert_not_called()
            self.assertFalse((root/'result').exists())
            self.assertEqual((work/'BAO_CAO.json').read_text(),original)
            self.assertEqual(bad.read_bytes(),b'bad')


if __name__=='__main__':unittest.main()
