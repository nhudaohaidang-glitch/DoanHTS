"""Artificial PCAPs test byte preservation and unlabelled packet candidates."""
import csv
import gzip
import hashlib
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from scapy.all import Ether,Dot1Q,IP,TCP,UDP,wrpcap

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import extract_iot23_selected_target as target_tool

SRC='198.18.0.3';DST='198.18.0.1'
HEADER='#fields\tts\tduration\tid.orig_h\tid.orig_p\tid.resp_h\tid.resp_p\tproto\tlabel\tdet_label\n'


def packet(t,flags='S'):
    value=Ether(src='02:00:00:00:00:03',dst='02:00:00:00:00:01')/IP(src=SRC,dst=DST)/TCP(sport=40000,dport=80,flags=flags)
    value.time=t;return value


class TargetExtractChecks(unittest.TestCase):
    def test_byte_exact_records_chunk_boundaries_endianness_and_link_types(self):
        ether=bytes(packet(100.1));ip=bytes(packet(100.1)[IP])
        vlan=bytes(Ether(src='02:00:00:00:00:03',dst='02:00:00:00:00:01',type=0x88a8)/Dot1Q(vlan=1,type=0x8100)/Dot1Q(vlan=2,type=0x800)/IP(src=SRC,dst=DST)/TCP(sport=40000,dport=80,flags='S'))
        for endian,nano,link,body in [('<',False,1,ether),('>',True,1,vlan),('<',True,113,b'\0'*14+b'\x08\x00'+ip),('>',False,101,ip),('<',False,228,ip)]:
            with self.subTest(endian=endian,nano=nano,link=link),tempfile.TemporaryDirectory() as d:
                root=Path(d);magic=0xa1b23c4d if nano else 0xa1b2c3d4
                header=struct.pack(endian+'IHHIIII',magic,2,4,0,0,65535,link)
                # Oversized captured padding forces a selected record across read chunks.
                padded=body+b'\0'*(target_tool.MIB+31)
                rec=struct.pack(endian+'IIII',100,123,len(padded),len(padded))+padded
                source=header+rec
                result=target_tool.copy_destinations(io.BytesIO(source),len(source),[DST],root)
                self.assertEqual((root/'pcap_da_loc'/f'{DST}.pcap').read_bytes(),source)
                self.assertEqual(result['source_pcap_sha256'],hashlib.sha256(source).hexdigest())
                self.assertEqual(result['retained_frames'][DST],1)

    def test_ingress_filter_keeps_ack_udp_and_fragments_without_selecting_syn_only(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'original.pcap'
            packets=[packet(100.1),packet(99.5,'A')]
            udp=Ether(src='02:00:00:00:00:03',dst='02:00:00:00:00:01')/IP(src=SRC,dst=DST)/UDP(dport=53);udp.time=102.1;packets.append(udp)
            frag=packet(103.1);frag[IP].flags='MF';packets.append(frag)
            outside=packet(104.1);outside[IP].dst='198.18.0.99';packets.append(outside)
            wrpcap(str(path),packets);before=target_tool.sha(path)
            result=target_tool.copy_destinations(io.BytesIO(path.read_bytes()),path.stat().st_size,[DST],root)
            self.assertEqual(result['retained_frames'][DST],4)
            self.assertEqual(result['source_first_timestamp'],99.5)
            with target_tool.RawPcapReader(str(path)) as reader:original=list(reader)
            with target_tool.RawPcapReader(str(root/'pcap_da_loc'/f'{DST}.pcap')) as reader:filtered=list(reader)
            self.assertEqual(filtered,original[:4])
            self.assertEqual(before,target_tool.sha(path))
            other=root/'budget';other.mkdir()
            with self.assertRaisesRegex(ValueError,'cache exceeds'):
                target_tool.copy_destinations(io.BytesIO(path.read_bytes()),path.stat().st_size,[DST],other,cache_limit=25)

    def test_pure_syn_candidates_remain_unlabelled_including_zero_q0(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);pcap=root/'in.pcap'
            packets=[packet(t) for t in (100.1,101.1,101.5,102.2,103.2,104.2,104.9)]
            mixed=Ether(src='02:00:00:00:00:03',dst='02:00:00:00:00:01')/IP(src=SRC,dst=DST)/UDP(dport=53);mixed.time=102.5
            packets.extend([mixed,packet(103.5,0x3a)])
            packets.sort(key=lambda value:float(value.time));wrpcap(str(pcap),packets)
            native=root/'native.log.gz'
            with gzip.open(native,'wt') as stream:stream.write(HEADER+f'100.1\t4.8\t{SRC}\t40000\t{DST}\t80\ttcp\tMalicious\tDDoS\n')
            out=root/'result';out.mkdir()
            report=target_tool.verify_windows(pcap,native,DST,(99.1,106.9),out)
            self.assertEqual(report['pure_native_ddos_syn_candidate_windows'],1)
            self.assertEqual(report['observed_tcp_flags']['3a'],1)
            with (out/'ung_vien_syn_chua_gan_nhan/X_6_fpga.csv').open() as stream:rows=list(csv.reader(stream))
            self.assertEqual(rows[1][0],'0')
            with (out/'ung_vien_syn_chua_gan_nhan/THONG_TIN_DONG.csv').open() as stream:info=list(csv.DictReader(stream))
            self.assertEqual(info[0]['window_start'],'101')
            self.assertFalse(report['training_ready'])
            self.assertFalse(report['project_labels_created'])
            self.assertFalse(report['syn_flood_verified'])
            self.assertFalse(list(out.rglob('y.csv')))
            no_syn=root/'no_syn.pcap';wrpcap(str(no_syn),[packet(t,0x3a) for t in (100.1,101.1,102.1,103.1,104.9)])
            no_syn_out=root/'no_syn_result';no_syn_out.mkdir()
            no_syn_report=target_tool.verify_windows(no_syn,native,DST,(99.1,106.9),no_syn_out)
            self.assertEqual(no_syn_report['pure_native_ddos_syn_candidate_windows'],0)
            self.assertFalse((no_syn_out/'ung_vien_syn_chua_gan_nhan').exists())

    def test_conflicting_native_benign_label_prevents_automatic_syn_label(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);pcap=root/'in.pcap';wrpcap(str(pcap),[packet(t) for t in (100.1,101.1,101.5,102.2,103.2,104.2,104.9)])
            native=root/'native.log.gz'
            with gzip.open(native,'wt') as stream:
                stream.write(HEADER+f'100.1\t4.8\t{SRC}\t40000\t{DST}\t80\ttcp\tMalicious\tDDoS\n'+f'101.0\t1.0\t{SRC}\t40000\t{DST}\t80\ttcp\tBenign\t-\n')
            out=root/'result';out.mkdir();target_tool.verify_windows(pcap,native,DST,(99.1,106.9),out)
            with (out/'tat_ca_cua_so_dich/BANG_CHUNG.csv').open() as stream:rows=list(csv.DictReader(stream))
            row=next(row for row in rows if row['window_start']=='101')
            self.assertEqual(row['pure_syn_native_ddos_candidate'],'0')
            self.assertEqual(int(row['other_or_unmatched_syn_packets']),2)

    def test_changed_full_native_log_cannot_be_used_as_a_verified_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=(HEADER+f'100.1\t4.8\t{SRC}\t40000\t{DST}\t80\ttcp\tMalicious\tDDoS\n').encode()
            spec={'source_bytes':len(data),'source_sha256':'0'*64}
            with self.assertRaisesRegex(ValueError,'differs from the previous screening hash'):
                target_tool.copy_target_log(io.BytesIO(data),spec,[DST],root)


if __name__=='__main__':unittest.main()
