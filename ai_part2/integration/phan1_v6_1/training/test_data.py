"""Check provenance, packet bytes/checksums, and independently extracted features."""
import collections,csv,gzip,hashlib,json,sqlite3,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'runtime'))
import numpy as np
from scapy.utils import RawPcapReader,checksum
from part2.features import NAMES,extract,values,quantize
from part2.integer import infer

def records(path):
    with RawPcapReader(str(path)) as stream:
        return [(raw,meta.wirelen) for raw,meta in stream]

class DataChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/'data/MANIFEST.json').read_text())
        cls.model=json.loads((ROOT/'frozen/model.json').read_text())

    def test_sources_and_all_generated_files_have_recorded_identity(self):
        for source in self.manifest['sources'].values():
            self.assertEqual(hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest(),source['sha256'])
        for source in self.manifest['profiles']:
            for kind in ('pcap','features'):
                self.assertEqual(hashlib.sha256((ROOT/'data'/source[kind]).read_bytes()).hexdigest(),source[kind+'_sha256'])
        self.assertEqual(len(self.manifest['profiles']),120)
        self.assertEqual(self.manifest['new_independent_attack_episodes'],0)

    def test_canonical_scapy_extraction_and_attack_packet_integrity(self):
        syn=records(ROOT/'sources/syn34.pcap.gz')
        scan=[r for r in records(ROOT/'sources/vertical_scan.pcap') if r[0][30:34]==bytes([64,13,134,52])]
        ids={'syn_train_32_one_syn','syn_development_384_sensor7','scan_train_128_two_sensors14','normal_development_96_sensor7_other'}
        for source in self.manifest['profiles']:
            if source['id'] not in ids:continue
            path=ROOT/'data'/source['pcap'];windows,stats=extract(path,source['target']+'/32')
            self.assertEqual(stats['fragments_skipped']+stats['truncated_skipped'],0)
            with gzip.open(ROOT/'data'/source['features'],'rt') as stream:
                for row in csv.DictReader(stream):
                    raw=values(windows[int(row['window_start'])],'exact')
                    self.assertEqual(raw,[int(row[n]) for n in NAMES])
                    self.assertEqual(quantize(raw,[8,2,1,1,1,1]).tolist(),[int(row['q'+str(i)]) for i in range(6)])
            attack=[]
            for raw,wire in records(path):
                if raw[26:29]!=bytes([198,18,0]):
                    attack.append((raw,wire));continue
                ip=raw[14:];ihl=(ip[0]&15)*4;total=int.from_bytes(ip[2:4],'big')
                self.assertEqual(checksum(ip[:ihl]),0)
                tcp=ip[ihl:total]
                self.assertEqual(checksum(ip[12:20]+struct.pack('!BBH',0,6,len(tcp))+tcp),0)
            expected=syn[:12000] if source['id'].startswith('syn_train') else syn[12000:24000] if source['id'].startswith('syn_development') else scan if source['label']==2 else []
            self.assertEqual(attack,expected)

    def test_original_labels_and_known_errors_remain_visible(self):
        with sqlite3.connect(ROOT/'cache/native_patterns.sqlite') as db:
            rows=list(db.execute('SELECT label,packed,count FROM patterns ORDER BY label,packed'))
        counts=collections.Counter();cm=np.zeros((3,3),dtype=np.int64)
        for label,packed,n in rows:
            counts[label]+=n;q=[(packed>>(8*i))&255 for i in range(6)]
            cm[label,int(infer([q],self.model).argmax(1)[0])]+=n
        self.assertEqual([counts[i] for i in range(3)],[39253935,21,4])
        self.assertEqual(cm.tolist(),[[39253923,12,0],[0,21,0],[0,0,4]])
        statuses=collections.Counter()
        for spec in self.manifest['profiles']:
            for status,n in spec['status_counts'].items():statuses[spec['split'],status]+=n
        self.assertEqual(statuses['train','native_label_alias_ambiguous'],12)
        self.assertEqual(statuses['development','native_label_alias_ambiguous'],9)
        self.assertEqual(statuses['train','eligible'],4273)
        self.assertEqual(statuses['development','eligible'],3344)

if __name__=='__main__':unittest.main()
