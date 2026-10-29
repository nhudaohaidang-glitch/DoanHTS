import csv,json,tempfile,unittest
from pathlib import Path
import numpy as np
from scapy.all import Ether,IP,TCP,UDP,Raw,wrpcap
from part2.features import extract,values,quantize,fit_divisors,build_dataset
from part2.integer import infer,write_vectors

class FeaturesTest(unittest.TestCase):
 def test_direction_synack_empty_and_integer_counts(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'case.pcap'
   packets=[Ether(src="02:00:00:00:00:02",dst="02:00:00:00:00:01")/IP(src='198.18.0.2',dst='198.18.0.1')/TCP(dport=1883,flags='S'),
            Ether(src="02:00:00:00:00:02",dst="02:00:00:00:00:01")/IP(src='198.18.0.2',dst='198.18.0.1')/TCP(dport=1884,flags='SA'),
            Ether(src="02:00:00:00:00:02",dst="02:00:00:00:00:01")/IP(src='198.18.0.3',dst='198.18.0.1')/UDP(dport=1883)/Raw(b'abcd'),
            Ether(src="02:00:00:00:00:02",dst="02:00:00:00:00:01")/IP(src='198.18.0.1',dst='198.18.0.2')/TCP(flags='SA')]
   for i,pkt in enumerate(packets):pkt.time=100.1+i*.1
   wrpcap(str(p),packets)
   w,s=extract(p,'198.18.0.1/32')
   self.assertEqual(values(w[100],'exact'),[3,37,42,2,1,2])
   self.assertEqual(values(None,'exact'),[0]*6)
   self.assertEqual(s['ingress_ipv4'],3)
 def test_out_of_order_packets_preserve_windows_and_file(self):
  import hashlib
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);packets=[]
   for t,port,flags in [(101.1,80,'S'),(100.9,81,'SA'),(100.1,53,'A'),(101.8,83,'S')]:
    pkt=Ether(src="02:00:00:00:00:02",dst="02:00:00:00:00:01")/IP(src='198.18.0.2',dst='198.18.0.1')/TCP(dport=port,flags=flags)
    pkt.time=t;packets.append(pkt)
   original=root/'unordered.pcap';ordered=root/'ordered.pcap'
   wrpcap(str(original),packets)
   wrpcap(str(ordered),sorted(packets,key=lambda p:float(p.time)))
   digest=hashlib.sha256(original.read_bytes()).hexdigest()
   windows,stats=extract(original,'198.18.0.1/32')
   reference,_=extract(ordered,'198.18.0.1/32')
   self.assertEqual(windows,reference)
   self.assertEqual(values(windows[100],'exact'),[2,40,0,1,1,2])
   self.assertEqual(values(windows[101],'exact'),[2,40,127,1,1,2])
   self.assertEqual(stats['ingress_ipv4'],4)
   self.assertEqual(stats['timestamp_reversals'],2)
   self.assertAlmostEqual(stats['max_backward_seconds'],.8)
   self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),digest)
 def test_dataset_reports_reordering_without_losing_rows(self):
  import warnings
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);packets=[]
   for t in (101.1,100.1):
    pkt=Ether(src="02:00:00:00:00:02",dst="02:00:00:00:00:01")/IP(src='198.18.0.2',dst='198.18.0.1')/TCP(flags='S')
    pkt.time=t;packets.append(pkt)
   wrpcap(str(root/'x.pcap'),packets)
   row=dict(capture_id='realistic_order',pcap='x.pcap',split='train',label=1,start=100,end=102,source_kind='synthetic')
   with (root/'manifest.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader();writer.writerow(row)
   with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always')
    meta=build_dataset(root/'manifest.csv',root/'features.csv')
   self.assertEqual(meta['captures'][0]['stats']['timestamp_reversals'],1)
   self.assertTrue(any('timestamp reversals' in str(w.message) for w in caught))
   with (root/'features.csv').open() as f:rows=list(csv.DictReader(f))
   self.assertEqual(len(rows),2)
   self.assertEqual(sum(int(r['packet_count']) for r in rows),2)

 def test_divisors_and_clipping(self):
  raw=np.array([[254,126,127,1,1,1],[0,0,0,0,0,0]])
  divisors=fit_divisors(raw)
  self.assertEqual(divisors,[2,1,1,1,1,1])
  self.assertEqual(quantize([[1000]*6],divisors).tolist(),[[127]*6])
 def test_fragment_excluded(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'f.pcap'
   pkt=Ether(src="02:00:00:00:00:02",dst="02:00:00:00:00:01")/IP(dst='198.18.0.1',flags='MF')/TCP(flags='S');pkt.time=101
   wrpcap(str(path),[pkt]);w,s=extract(path,'198.18.0.1/32')
   self.assertFalse(w);self.assertEqual(s['fragments_skipped'],1)
 def test_duplicate_capture_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);pkt=Ether(src="02:00:00:00:00:02",dst="02:00:00:00:00:01")/IP(dst='198.18.0.1')/TCP();pkt.time=100.1
   wrpcap(str(root/'x.pcap'),[pkt])
   fields=['capture_id','pcap','split','label','start','end','source_kind']
   with (root/'manifest.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for cap,split in [('a','train'),('b','test')]:
     w.writerow(dict(capture_id=cap,pcap='x.pcap',split=split,label=0,start=100,end=102,source_kind='synthetic'))
   with self.assertRaisesRegex(ValueError,'Duplicate capture content'):
    build_dataset(root/'manifest.csv',root/'out.csv')

class IntegerTest(unittest.TestCase):
 def test_negative_shift_and_saturation(self):
  model=dict(w1=np.zeros((8,6),dtype=int).tolist(),b1=[-1]*8,shift1=1,
             w2=np.zeros((3,8),dtype=int).tolist(),b2=[-3,100000,-100000],shift2=1)
  self.assertEqual(infer([[0]*6],model).tolist(),[[-2,32767,-32768]])
 def test_vector_pack(self):
  model=dict(w1=np.zeros((8,6),dtype=int).tolist(),b1=[0]*8,shift1=0,
             w2=np.zeros((3,8),dtype=int).tolist(),b2=[1,-2,3],shift2=0)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'v.txt';write_vectors([[1,2,3,4,5,6]],model,p)
   self.assertEqual(p.read_text().strip(),'060504030201 0003fffe0001 2')


class LogTest(unittest.TestCase):
 def test_checksum_and_source_format(self):
  from part2.logs import encode,decode
  frame=encode('BLK,198.18.0.3,DOS,60')
  self.assertEqual(decode(frame)['kind'],'BLK')
  with self.assertRaises(ValueError):decode(frame[:-2]+'00')
  with self.assertRaises(ValueError):decode(encode('CNT,1,2'))

if __name__=='__main__':unittest.main()
