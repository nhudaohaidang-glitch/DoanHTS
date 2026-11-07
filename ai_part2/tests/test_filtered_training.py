"""Feature-contract, source grouping and honest training-fit checks."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scapy.layers.inet import IP,TCP,UDP,ICMP
from scapy.layers.l2 import Ether,ARP
from scapy.utils import PcapWriter

KIT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(KIT));sys.path.insert(0,str(KIT/'tools'))
from part2 import filtered_training_data as data
from part2.features import extract,values,NAMES,quantize
from part2.filtered_training import train,weighted_metrics
import prepare_gowin


def write(path,packets):
    with PcapWriter(str(path),linktype=1,sync=True) as writer:
        for timestamp,p in packets:
            p[Ether].src='02:00:00:00:00:01';p[Ether].dst='02:00:00:00:00:02'
            p.time=timestamp;writer.write(p)


def spec(path,label=0,target=None,start=None,end=None):
    return dict(id='source',path=path.name,label=label,sha256=data.sha(path),target_ip=target,
                start=start,end=end,source_group='synthetic_test_only',class_provenance='test fixture, no traffic quality claim')


class FilteredTrainingChecks(unittest.TestCase):
    def test_external_sort_matches_canonical_features_for_each_receiver(self):
        with tempfile.TemporaryDirectory() as d,patch.object(data,'CHUNK',3):
            root=Path(d);path=root/'input.pcap'
            packets=[(99.4,Ether()/ARP()),(100.1,Ether()/IP(src='192.0.2.1',dst='192.0.2.3')/TCP(dport=80,flags='S')),
                     (101.2,Ether()/IP(src='192.0.2.2',dst='192.0.2.4')/UDP(dport=53)),
                     (100.2,Ether()/IP(src='192.0.2.2',dst='192.0.2.3')/TCP(dport=443,flags='SA')),
                     (100.3,Ether()/IP(src='192.0.2.1',dst='192.0.2.3')/TCP(dport=80,flags='S')),
                     (101.5,Ether()/IP(src='192.0.2.2',dst='192.0.2.3')/ICMP()),
                     (102.1,Ether()/IP(src='192.0.2.2',dst='192.0.2.3',flags='MF')/UDP(dport=53)),
                     (103.1,Ether()/IP(src='192.0.2.1',dst='192.0.2.4')/TCP(dport=81,flags='S')),
                     (104.2,Ether()/ARP())]
            write(path,packets)
            result=data.extract_source(root,spec(path),root/'features')
            with gzip.open(result['feature_csv'],'rt') as stream:rows=list(csv.DictReader(stream))
            actual={(r['target_ip'],int(r['window_start'])):[int(r[n]) for n in NAMES] for r in rows}
            expected={}
            for ip in ('192.0.2.3','192.0.2.4'):
                windows,_=extract(path,ip+'/32',1.,'exact')
                for slot,window in windows.items():
                    if 100<=slot<104:expected[ip,slot]=values(window,'exact')
            self.assertEqual(actual,expected)
            self.assertEqual(result['windows'],4)
            self.assertEqual(actual['192.0.2.3',100],[3,40,84,2,1,2])
            self.assertEqual(actual['192.0.2.3',101][-1],0)
            for row in rows:
                self.assertEqual([int(row['q'+str(i)]) for i in range(6)],quantize([int(row[n]) for n in NAMES],data.DIVISORS).tolist())
            compressed=root/'copy.pcap.gz'
            with gzip.open(compressed,'wb') as stream:stream.write(path.read_bytes())
            again=data.extract_source(root,spec(compressed),root/'gzip_features')
            self.assertEqual(again['windows'],result['windows'])

    def test_scan_positive_bounds_skip_partial_and_late_response_windows(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'scan.pcap'
            write(p,[(1.1,Ether()/IP(src='192.0.2.1',dst='192.0.2.2')/TCP(dport=80,flags='S')),
                     (2.2,Ether()/IP(src='192.0.2.1',dst='192.0.2.2')/TCP(dport=81,flags='S')),
                     (3.2,Ether()/IP(src='192.0.2.1',dst='192.0.2.2')/TCP(dport=82,flags='S')),
                     (8.2,Ether()/IP(src='192.0.2.2',dst='192.0.2.1')/TCP(flags='SA'))])
            r=data.extract_source(root,spec(p,2,'192.0.2.2',1.1,3.8),root/'features')
            with gzip.open(r['feature_csv'],'rt') as stream:rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),1);self.assertEqual(rows[0]['window_start'],'2')
            self.assertEqual(rows[0]['packet_count'],'1');self.assertEqual(rows[0]['q0'],'0')
            self.assertEqual(rows[0]['class'],'2')

    def test_zero_complete_windows_report_skip_and_changed_hash_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'one.pcap';write(path,[(1.2,Ether()/IP()/TCP())])
            r=data.extract_source(root,spec(path),root/'empty');self.assertEqual(r['windows'],0)
            self.assertEqual(r['status'],'skipped_no_complete_nonempty_window')
            wrong=spec(path);wrong['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'checksum changed'):data.extract_source(root,wrong,root/'wrong')

    def test_collision_is_preserved_and_metrics_are_training_only(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);sources=[]
            for label,point,count in [(0,[127,20,127,1,1,1],11),(1,[127,20,127,1,1,1],21),(2,[10,22,127,1,1,53],4)]:
                path=root/f'{label}.sqlite';packed=sum(v<<(8*i) for i,v in enumerate(point))
                with sqlite3.connect(path) as db:db.execute('CREATE TABLE patterns (packed INTEGER PRIMARY KEY,count INTEGER)');db.execute('INSERT INTO patterns VALUES (?,?)',(packed,count))
                sources.append(dict(id=str(label),label=label,source_group=str(label),sha256='0'*64,windows=count,patterns_db=str(path)))
            report=train(sources,root/'model',10)
            self.assertEqual(report['conflicting_quantized_patterns'],1)
            self.assertEqual(report['candidate_status'],'needs_label_review')
            self.assertFalse(report['independent_test_evaluated']);self.assertFalse(report['validation_used_for_selection'])
            self.assertFalse(report['ready_for_automatic_blocking'])
            self.assertEqual(report['training_windows_by_class'],[11,21,4])
            self.assertLess(report['training_fit']['integer']['accuracy'],1.)
            metadata=prepare_gowin.prepare(root/'model',root/'gowin',KIT)
            self.assertEqual(metadata['model_version'],'v4')
            self.assertTrue((root/'gowin/firmware/ai_quant_v4.h').exists())
            self.assertEqual(weighted_metrics([[10,1,0],[0,2,0],[0,0,3]])['false_positive_rate'],1/11)


if __name__=='__main__':unittest.main()
