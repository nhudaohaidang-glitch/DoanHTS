"""Network lifecycle regression with a fake ip command; never changes host networking."""
import csv
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))
from lab.collect_v2 import collect, plan
from lab.recover_lab import recover_orphans

FAKE_IP = r'''
import json,os,sys
from pathlib import Path
p=Path(os.environ['PART2_TEST_NET_STATE'])
s=json.loads(p.read_text()) if p.exists() else {'names':[], 'links':{}, 'calls':[]}
a=sys.argv[1:];s['calls'].append(a);code=0
if a[:2]==['netns','list']:
    print('\n'.join(s['names']))
elif a[:2]==['netns','pids']:
    pass
elif a[:2]==['netns','add']:
    s['names'].append(a[2])
elif a[:2]==['netns','del']:
    s['names'].remove(a[2])
    # Model a namespace retained by a process after its name is deleted.
    # Its veth does not disappear automatically here.
elif a[:2]==['netns','exec']:
    pass
elif a[:2]==['link','show']:
    code=0 if a[2] in s['links'] else 1
elif a[:2]==['link','add']:
    if a[2] in s['links']:code=2
    else:s['links'][a[2]]={'kind':a[4]}
elif a[:2]==['link','set']:
    if a[2] not in s['links']:code=2
    elif len(a)>4:s['links'][a[2]][a[3]]=a[4]
elif a[:2]==['link','del']:
    if a[2] not in s['links']:code=1
    else:del s['links'][a[2]]
else:
    print('Unexpected fake ip command',a,file=sys.stderr);code=2
p.write_text(json.dumps(s));sys.exit(code)
'''


def write_capture(root, args):
    folder = root / args[4]
    folder.mkdir(parents=True)
    (folder / 'traffic.pcap').write_bytes(b'artificial-fixture-' + args[4].encode() * 2)
    (folder / 'capture.log').write_text('0 packets dropped by kernel\n')
    scenario = dict(mode=args[2], split=args[3], seconds=args[5], requested_pps=args[6],
                    sensor_interval=args[7], normal_clients=args[8], payload_bytes=args[9])
    (folder / 'scenario.txt').write_text(''.join(f'{k}={v}\n' for k,v in scenario.items()))
    row = dict(capture_id=args[4], pcap=args[4]+'/traffic.pcap', split=args[3],
               label={'normal':0,'normal_probe':0,'syn':1,'scan':2}[args[2]],
               start=100, end=117, source_kind='lab', target_net='198.18.0.1/32')
    manifest = root / 'manifest.csv'
    existed = manifest.exists()
    with manifest.open('a',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(row))
        if not existed:w.writeheader()
        w.writerow(row)


class LifecycleTest(unittest.TestCase):
    def test_bash_down_explicitly_removes_retained_host_veths_before_next_up(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'lab').mkdir();(root/'bin').mkdir()
            shutil.copy2(KIT/'lab/setup_lab.sh',root/'lab/setup_lab.sh')
            fake=root/'bin/ip';fake.write_text('#!'+sys.executable+'\n'+FAKE_IP);fake.chmod(0o755)
            fake=root/'bin/id';fake.write_text('#!/bin/sh\necho 0\n');fake.chmod(0o755)
            state=root/'state.json'
            env=dict(os.environ,PATH=str(root/'bin')+os.pathsep+os.environ['PATH'],PART2_TEST_NET_STATE=str(state))
            for action in ('up','down','up','down'):
                result=subprocess.run(['bash','lab/setup_lab.sh',action],cwd=root,env=env,capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            data=json.loads(state.read_text())
            self.assertEqual(data['links'],{});self.assertEqual(data['names'],[])
            calls=data['calls'];first_delete=calls.index(['netns','del','p2broker'])
            for name in ('p2brokerh','p2sensorh','p2sourceh'):
                self.assertLess(calls.index(['link','del',name]),first_delete)
            self.assertFalse((root/'build/lab.created').exists())

    def test_resume_keeps_six_registered_sessions_and_original_record(self):
        with tempfile.TemporaryDirectory() as d:
            kit=Path(d);(kit/'build').mkdir();marker=kit/'build/lab.created'
            prefix='v2dev01';relative,commands=plan('dev',prefix);root=kit/'data'/relative
            state={'ups':0,'fail':True};created=[]
            def runner(args,**kwargs):
                if args[1]=='lab/setup_lab.sh':
                    if args[2]=='down':marker.unlink()
                    else:
                        state['ups']+=1
                        if state['fail'] and state['ups']==7:raise subprocess.CalledProcessError(1,args)
                        marker.write_text('Created by ai_part2 lab/setup_lab.sh\n')
                else:
                    created.append(args[4]);write_capture(root,args)
            with patch('lab.collect_v2.KIT',kit),patch('lab.collect_v2.os.geteuid',return_value=0),patch('lab.collect_v2.subprocess.run',side_effect=runner):
                with self.assertRaises(subprocess.CalledProcessError):collect('dev',prefix,'unused')
                record=(root/'COLLECTION.json').read_bytes()
                saved={p:p.read_bytes() for row in commands[:6] for p in (root/row['capture_id']).iterdir()}
                state['fail']=False
                with patch('lab.recover_lab.recover_orphans',return_value=['p2sourceh']) as recover:
                    collect('dev',prefix,'unused',resume=True)
                    recover.assert_called_once_with(kit,root/'COLLECTION.json')
                self.assertEqual((root/'COLLECTION.json').read_bytes(),record)
                for path,content in saved.items():self.assertEqual(path.read_bytes(),content)
                self.assertEqual(created,[r['capture_id'] for r in commands])
                with (root/'manifest.csv').open() as f:self.assertEqual(len(list(csv.DictReader(f))),20)
                completed=(root/'COMPLETE.json').read_bytes()
                self.assertEqual(collect('dev',prefix,'unused',resume=True)['status'],'already_complete')
                self.assertEqual((root/'COMPLETE.json').read_bytes(),completed)

    def recovery_fixture(self,kit):
        relative,commands=plan('dev','fixture01');root=kit/'data'/relative;root.mkdir(parents=True)
        record=root/'COLLECTION.json'
        record.write_text(json.dumps(dict(format=1,phase='dev',capture_ids=[r['capture_id'] for r in commands],
                                          plan=commands,reset_owned_lab_each_session=True)))
        return record

    def test_recover_only_unattached_known_veths(self):
        with tempfile.TemporaryDirectory() as d:
            kit=Path(d);record=self.recovery_fixture(kit)
            links=[{'ifname':'p2sourceh','linkinfo':{'info_kind':'veth'}},
                   {'ifname':'enp0s3','linkinfo':{'info_kind':'ether'}}]
            with patch('lab.recover_lab.subprocess.check_output',side_effect=['',json.dumps(links)]),patch('lab.recover_lab.subprocess.run') as run:
                self.assertEqual(recover_orphans(kit,record),['p2sourceh'])
                run.assert_called_once_with(['ip','link','del','p2sourceh'],check=True)

    def test_recovery_refuses_foreign_links_live_namespace_and_changed_plan(self):
        with tempfile.TemporaryDirectory() as d:
            kit=Path(d);record=self.recovery_fixture(kit)
            bad=[{'ifname':'p2sourceh','linkinfo':{'info_kind':'veth'},'master':'otherbridge'}]
            with patch('lab.recover_lab.subprocess.check_output',side_effect=['',json.dumps(bad)]),patch('lab.recover_lab.subprocess.run') as run:
                with self.assertRaisesRegex(ValueError,'unattached'):recover_orphans(kit,record)
                run.assert_not_called()
            with patch('lab.recover_lab.subprocess.check_output',return_value='p2broker (id: 0)\n'),patch('lab.recover_lab.subprocess.run') as run:
                with self.assertRaisesRegex(ValueError,'namespaces remain'):recover_orphans(kit,record)
                run.assert_not_called()
            data=json.loads(record.read_text());data['plan'][0]['command'][2]='unexpected';record.write_text(json.dumps(data))
            with patch('lab.recover_lab.subprocess.run') as run:
                with self.assertRaisesRegex(ValueError,'ownership'):recover_orphans(kit,record)
                run.assert_not_called()


if __name__=='__main__':unittest.main()
