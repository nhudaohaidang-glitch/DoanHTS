"""Filtering/byte-integrity controls; these tests do not score an AI model."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import export_iot23_normal_syn as exporting
import iot23_label_index as indexing
import iot23_pcap_filter as packets

FIELDS = 'ts duration id.orig_h id.orig_p id.resp_h id.resp_p proto history orig_pkts resp_pkts label det_label'.split()
HEADER = ('#fields\t'+'\t'.join(FIELDS)+'\n').encode()


def flow(ts=100., duration=10., label='Benign', sport=5000, proto='tcp', src='192.0.2.1', dst='192.0.2.2', dport=80):
    return dict(zip(FIELDS, map(str, [ts,duration,src,sport,dst,dport,proto,'S',1,0,label,'-' if label=='Benign' else 'DDoS'])))


def native(rows):
    return HEADER+b''.join(('\t'.join(r[f] for f in FIELDS)+'\n').encode() for r in rows)


def spec(rows, identity='CTU-IoT-Malware-Capture-99-1'):
    data = native(rows)
    counts = {}
    for row in rows:
        label = row['label']+'/'+row['det_label']
        counts[label] = counts.get(label,0)+1
    return dict(capture_id=identity,source_bytes=len(data),source_sha256=hashlib.sha256(data).hexdigest(),connection_records=len(rows),native_labels=counts)


def frame(sport=5000, reverse=False, proto=6, vlan=False, flags=2):
    src, dst = b'\xc0\x00\x02\x01', b'\xc0\x00\x02\x02'
    dport = 80
    if reverse:
        src,dst,sport,dport = dst,src,dport,sport
    if proto == 6:
        transport = struct.pack('!HHIIBBHHH',sport,dport,0,0,0x50,flags,8192,0,0)
    elif proto == 17:
        transport = struct.pack('!HHHH',sport,dport,8,0)
    else:
        transport = bytes([0 if reverse else 8,0])+b'\0'*6
    ip = struct.pack('!BBHHHBBH4s4s',0x45,0,20+len(transport),0,0,64,proto,0,src,dst)
    ether = b'\0'*12+(b'\x81\x00\x00\x01\x08\x00' if vlan else b'\x08\x00')
    return ether+ip+transport


def pcap(rows, endian='<', nano=False):
    magic = {('<',False):b'\xd4\xc3\xb2\xa1',('>',False):b'\xa1\xb2\xc3\xd4',('<',True):b'\x4d\x3c\xb2\xa1',('>',True):b'\xa1\xb2\x3c\x4d'}[(endian,nano)]
    header = magic+struct.pack(endian+'HHiIII',2,4,0,0,65535,1)
    scale = 10**9 if nano else 10**6
    records = [struct.pack(endian+'IIII',int(t),round((t-int(t))*scale),len(data),len(data))+data for t,data in rows]
    return header+b''.join(records), header, records


class ExportChecks(unittest.TestCase):
    def test_interval_subtraction_bidirection_ports_icmp_and_hash_collisions(self):
        with tempfile.TemporaryDirectory() as d, patch.object(indexing,'CHUNK',3), patch.object(indexing,'hashes',lambda a,b:np.zeros(np.shape(a),dtype=np.uint64)):
            root=Path(d); builder=indexing.Builder(root)
            rows=[flow(),flow(104,2,'Malicious'),flow(sport=5001),flow(proto='icmp',sport=8,dport=0)]
            for r in rows:builder.observe(r)
            stats=builder.finish(); self.assertEqual(stats['keys'],3)
            index=indexing.Index(root)
            a,b=indexing.flow_key(6,indexing.ip4('192.0.2.1'),5000,indexing.ip4('192.0.2.2'),80)
            self.assertEqual(index.contains([a]*7,[b]*7,[99.998,100,103,104,106,107,110]).tolist(),[False,True,True,False,False,True,True])
            a,b=indexing.flow_key(6,indexing.ip4('192.0.2.2'),80,indexing.ip4('192.0.2.1'),5001)
            self.assertTrue(index.contains([a],[b],[105])[0])
            a,b=indexing.flow_key(6,indexing.ip4('192.0.2.1'),5002,indexing.ip4('192.0.2.2'),80)
            self.assertFalse(index.contains([a],[b],[105])[0])
            request,_=packets.packet(memoryview(frame(proto=1)),1)
            reply,_=packets.packet(memoryview(frame(proto=1,reverse=True)),1)
            self.assertEqual(request[:2],reply[:2])
            self.assertTrue(index.contains([reply[0]],[reply[1]],[105])[0])

    def test_random_intervals_match_direct_native_label_definition(self):
        rng=np.random.default_rng(219)
        with tempfile.TemporaryDirectory() as d, patch.object(indexing,'CHUNK',7):
            root=Path(d); builder=indexing.Builder(root); rows=[]
            for i in range(180):
                r=flow(float(rng.uniform(90,120)),float(rng.uniform(0,8)), 'Benign' if i%3 else 'Malicious',sport=5000+i%9)
                rows.append(r);builder.observe(r)
            builder.finish();index=indexing.Index(root)
            for port in range(5000,5010):
                t=rng.uniform(85,140,300)
                a,b=indexing.flow_key(6,indexing.ip4('192.0.2.1'),port,indexing.ip4('192.0.2.2'),80)
                expected=[]
                for instant in t:
                    labels=[r['label'] for r in rows if int(r['id.orig_p'])==port and float(r['ts'])-.001<=instant<=float(r['ts'])+float(r['duration'])+.001]
                    expected.append('Benign' in labels and all(x=='Benign' for x in labels))
                self.assertEqual(index.contains([a]*len(t),[b]*len(t),t).tolist(),expected)

    def test_pcap_byte_integrity_endianness_nano_vlan_and_no_false_syn(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); builder=indexing.Builder(root/'index')
            builder.observe(flow());builder.observe(flow(104,2,'Malicious'));builder.finish()
            for endian in '<>':
                for nano in (False,True):
                    original,header,records=pcap([(101.125,frame(vlan=True)),(102.,frame(reverse=True)),(105.,frame()),(108.,frame(sport=6000)),(110.5,frame())],endian,nano)
                    stem=str(ord(endian))+str(nano)
                    result=packets.filter_pcap(io.BytesIO(original),len(original),indexing.Index(root/'index'),root,stem)
                    self.assertEqual(result['normal_packets'],2)
                    self.assertEqual(result['reviewed_syn_flood_packets'],0)
                    exporting.publish(root,result)
                    self.assertEqual(gzip.decompress((root/result['files']['binh_thuong']['path']).read_bytes()),header+records[0]+records[1])
            self.assertFalse((root/'syn_flood').exists())

    def test_original_csv_malware_normal_and_empty_class_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rows=[flow(),flow(101,0,'Malicious',sport=6000)]
            result=exporting.export_log(io.BytesIO(native(rows)),spec(rows),root)
            self.assertEqual(result['normal_rows'],1)
            self.assertEqual(result['reviewed_syn_flood_rows'],0)
            exporting.publish(root,result)
            with gzip.open(root/result['files']['binh_thuong']['path'],'rt') as stream:
                values=list(csv.DictReader(stream))
            self.assertEqual(values[0],dict(rows[0],loai_da_loc='binh_thuong'))
            absent=root/'absent';absent.mkdir()
            result=exporting.export_log(io.BytesIO(native(rows[1:])),spec(rows[1:]),absent)
            self.assertEqual(result['files'],{})
            self.assertEqual(list(absent.rglob('*.gz')),[])
            changed=dict(spec(rows),source_sha256='0'*64)
            with self.assertRaisesRegex(ValueError,'differs'):
                exporting.export_log(io.BytesIO(native(rows)),changed,root/'changed')
            self.assertFalse(list((root/'changed').rglob('*.csv.gz')))

    def test_incomplete_final_record_keeps_only_complete_original_packets(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);builder=indexing.Builder(root/'index');builder.observe(flow());builder.finish()
            for endian in '<>':
                for nano in (False,True):
                    complete,header,records=pcap([(101.,frame()),(102.,frame(reverse=True)),(103.,frame())],endian,nano)
                    for missing in (7,len(records[-1])-5):
                        original=complete[:-missing]
                        stem=f'{ord(endian)}_{nano}_{missing}'
                        with self.assertRaisesRegex(ValueError,'incomplete record'):
                            packets.filter_pcap(io.BytesIO(original),len(original),indexing.Index(root/'index'),root,'strict_'+stem)
                        result=packets.filter_pcap(io.BytesIO(original),len(original),indexing.Index(root/'index'),root,stem,
                                                   allow_incomplete_final_record=True)
                        self.assertEqual(result['source_packets'],2)
                        self.assertEqual(result['normal_packets'],2)
                        tail=result['source_tail_excluded']
                        self.assertEqual(tail['excluded_bytes'],len(records[-1])-missing)
                        self.assertEqual(result['source_pcap_sha256'],hashlib.sha256(original).hexdigest())
                        exporting.publish(root,result)
                        self.assertEqual(gzip.decompress((root/result['files']['binh_thuong']['path']).read_bytes()),header+records[0]+records[1])
            with self.assertRaisesRegex(ValueError,'size changed'):
                packets.filter_pcap(io.BytesIO(complete),len(complete)+1,indexing.Index(root/'index'),root,'size',allow_incomplete_final_record=True)
            with self.assertRaisesRegex(ValueError,'no complete packet'):
                packets.filter_pcap(io.BytesIO(header),len(header),indexing.Index(root/'index'),root,'empty',allow_incomplete_final_record=True)
            broken=bytearray(complete)
            struct.pack_into(endian+'I',broken,24+4,10**9 if nano else 10**6)
            with self.assertRaisesRegex(ValueError,'Invalid PCAP record header'):
                packets.filter_pcap(io.BytesIO(broken),len(broken),indexing.Index(root/'index'),root,'corrupt',allow_incomplete_final_record=True)
            with self.assertRaisesRegex(ValueError,'incomplete record'):
                packets.filter_pcap(io.BytesIO(original),len(original),indexing.Index(root/'index'),root,'syn_tail',
                                    syn_rule=exporting.SYN_REVIEW,allow_incomplete_final_record=True)

    def test_archive_two_pass_resume_and_checksum_failures(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source_id='CTU-IoT-Malware-Capture-99-1'; prefix='opt/data/'+source_id
            log_member=prefix+'/bro/conn.log.labeled';pcap_member=prefix+'/mixed.pcap'
            rows=[flow(),flow(101,0,'Malicious',sport=6000)]; data=native(rows)
            original,_,_=pcap([(102.,frame()),(101.,frame(sport=6000))])
            original=original[:-7]  # Original source ends within its final packet.
            archive=root/'input.tar.gz'
            with tarfile.open(archive,'w:gz') as tar:
                for name,payload in [(pcap_member,original),(log_member,data),('../escape',b'x')]:
                    member=tarfile.TarInfo(name);member.size=len(payload);tar.addfile(member,io.BytesIO(payload))
            inventory=root/'KIEM_KE.csv'
            with inventory.open('w',newline='') as stream:
                writer=csv.writer(stream);writer.writerow(['archive_path','bytes','type','selected'])
                for name,payload in [(pcap_member,original),(log_member,data)]:writer.writerow([name,len(payload),'file','False'])
            screen=root/'screen';screen.mkdir()
            parent=dict(status='complete',kind='native_source_screening_not_training_dataset',archive_sha256=exporting.sha(archive),inventory_sha256=exporting.sha(inventory),sources=[dict(spec(rows),archive_member=log_member)])
            (screen/'BAO_CAO_LOC.json').write_text(json.dumps(parent))
            actual_filter=exporting.filter_pcap
            with patch.object(exporting,'filter_pcap',side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):exporting.run(archive,screen,inventory,root/'out',minimum_free_gib=0)
            self.assertFalse((root/'escape').exists())
            state=json.loads((root/'out/BAO_CAO_XUAT.json').read_text());self.assertEqual(state['passes_complete'],[1])
            # A released v1 checkpoint can be upgraded without recomputing CSV
            # or the saved label index. Arbitrary code changes remain blocked.
            state['fingerprint']['code']=exporting.COMPATIBLE_PREVIOUS_CODE.copy()
            (root/'out/BAO_CAO_XUAT.json').write_text(json.dumps(state))
            # Emulate interruption between manifest commit and output rename.
            item=next(iter(state['sources'][log_member]['files'].values()))
            final=root/'out'/item['path']; final.rename(str(final)+'.part')
            with patch.object(exporting,'export_log',side_effect=AssertionError('completed source reread')):
                report=exporting.run(archive,screen,inventory,root/'out',resume=True,minimum_free_gib=0)
            self.assertEqual(report['status'],'complete');self.assertEqual(report['normal_pcap_packets'],1)
            self.assertEqual(report['syn_flood_pcap_packets'],0)
            self.assertFalse(report['source_packet_records_complete'])
            self.assertEqual(len(report['source_integrity_warnings']),1)
            self.assertEqual(report['source_integrity_warnings'][0]['missing_payload_bytes'],7)
            self.assertIn('Có tệp nguồn thiếu bản ghi cuối',(root/'out/MO_DU_LIEU_DA_LOC.html').read_text())
            self.assertEqual(len(report['tool_upgrades']),1)
            self.assertTrue((root/'out/BAO_CAO_XUAT_TRUOC_SUA_DUOI.json').is_file())
            self.assertTrue(final.is_file());self.assertIs(actual_filter,exporting.filter_pcap)
            self.assertFalse(list((root/'out').rglob('*.part')))
            completed=(root/'out/BAO_CAO_XUAT.json').read_text()
            unknown=json.loads(completed);unknown['fingerprint']['code']['iot23_label_index.py']='0'*64
            (root/'out/BAO_CAO_XUAT.json').write_text(json.dumps(unknown))
            with self.assertRaisesRegex(ValueError,'inputs/tool differ'):
                exporting.run(archive,screen,inventory,root/'out',resume=True,minimum_free_gib=0)
            (root/'out/BAO_CAO_XUAT.json').write_text(completed)
            final.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'missing/changed'):
                exporting.run(archive,screen,inventory,root/'out',resume=True,minimum_free_gib=0)


if __name__=='__main__':
    unittest.main()
