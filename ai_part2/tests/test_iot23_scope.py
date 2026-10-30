"""Artificial packet/log fixtures check audit parsing, not model accuracy."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from scapy.all import Ether, Dot1Q, IP, IPv6, TCP, UDP, Raw, wrpcap

KIT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit_iot23',KIT/'tools/audit_iot23_scope.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class IoT23ScopeTest(unittest.TestCase):
    def test_detailed_label_aliases_lowercase_benign_and_combined_columns(self):
        with tempfile.TemporaryDirectory() as d:
            for alias in ('det_label','detailed-label','detailedlabel'):
                p=Path(d)/alias
                p.write_text('#fields\tts\tduration\tid.orig_h\tid.orig_p\tid.resp_h\tid.resp_p\tproto\ttunnel_parents   label   '+alias+'\n'
                             '100.1\t-\t198.18.0.3\t40000\t198.18.0.1\t80\ttcp\t-   benign   -\n'
                             '101.2\t1.0\t198.18.0.3\t40001\t198.18.0.1\t81\ttcp\t-   Malicious   DDoS\n')
                rows=list(audit.labelled_flows(p))
                self.assertEqual(rows[0]['coarse_canonical'],'benign')
                self.assertEqual(rows[0]['label'],'benign')
                self.assertEqual(rows[1]['detailed-label'],'DDoS')
                report,index=audit.flow_audit(p)
                self.assertEqual(report['connection_records'],2)
                self.assertEqual(report['max_tcp_destination_ports_per_directed_pair'],2)

    def test_tcp_flags_vlan_fragments_and_truncation(self):
        packet=Ether(src="02:00:00:00:00:03",dst="02:00:00:00:00:01")/Dot1Q(vlan=2)/IP(src='198.18.0.3',dst='198.18.0.1')/TCP(sport=40000,dport=80,flags='S')
        header,error=audit.packet_header(bytes(packet),1)
        self.assertIsNone(error);self.assertEqual(header['flags'],2);self.assertEqual(header['dport'],80)
        header,error=audit.packet_header(bytes(packet)[:-1],1)
        self.assertIsNone(header);self.assertEqual(error,'truncated_or_invalid_ipv4')
        packet=Ether(src="02:00:00:00:00:03",dst="02:00:00:00:00:01")/IP(src='198.18.0.3',dst='198.18.0.1',flags='MF')/TCP(flags='S')
        self.assertEqual(audit.packet_header(bytes(packet),1)[1],'ipv4_fragment')
        self.assertEqual(audit.packet_header(bytes(Ether(src="02:00:00:00:00:03",dst="02:00:00:00:00:01")/IPv6()/TCP()),1)[1],'non_ipv4')

    def test_reply_ports_are_not_counted_as_syn_open_scan(self):
        with tempfile.TemporaryDirectory() as d:
            packets=[]
            for i in range(5):
                for src,dst,sport,dport,flags in [('198.18.0.3','198.18.0.1',40000+i,80,'S'),
                                               ('198.18.0.1','198.18.0.3',80,40000+i,'SA'),
                                               ('198.18.0.1','198.18.0.3',80,40000+i,'A')]:
                    packet=Ether(src="02:00:00:00:00:03",dst="02:00:00:00:00:01")/IP(src=src,dst=dst)/TCP(sport=sport,dport=dport,flags=flags)
                    packet.time=100+i*.1;packets.append(packet)
            p=Path(d)/'fixture.pcap';wrpcap(str(p),packets)
            report=audit.pcap_audit(p)
            self.assertEqual(report['counters']['syn_open'],5)
            self.assertEqual(report['max_tcp_destination_ports_per_directed_pair'],5)
            self.assertEqual(report['max_syn_open_destination_ports_per_directed_pair'],1)

    def test_match_requires_origin_tuple_time_and_unambiguous_label(self):
        key=(1,2,40000,80)
        packet=dict(src=1,dst=2,sport=40000,dport=80)
        index={key:([100.,101.],[(100.,105.,'Malicious','DDoS'),(101.,101.,'Benign','-')])}
        self.assertEqual(audit.match_origin(index,packet,104.),('Malicious','DDoS'))
        self.assertIsNone(audit.match_origin(index,packet,101.))
        self.assertIsNone(audit.match_origin(index,packet,99.))
        self.assertIsNone(audit.match_origin(index,dict(src=2,dst=1,sport=80,dport=40000),104.))


if __name__=='__main__':unittest.main()
