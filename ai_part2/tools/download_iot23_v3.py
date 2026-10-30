"""Download only the predeclared native PCAPs, with streaming/hash verification."""
import argparse,hashlib,json,lzma,os,sys,tempfile,time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from part2.development import sha256,verify_freeze
KIT=Path(__file__).resolve().parents[1]

def download(url,dest,expected_sha=None,expected_size=None,max_bytes=512*1024*1024):
    dest=Path(dest)
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname!='mcfp.felk.cvut.cz' or not parsed.path.startswith('/publicDatasets/IoT-23-Dataset/IndividualScenarios/') or not parsed.path.endswith(('.pcap','.pcap.xz')):
        raise ValueError('Only the declared official PCAP source is supported')
    if dest.exists():
        if expected_sha and sha256(dest)!=expected_sha:raise ValueError('Existing file checksum differs: '+str(dest))
        return dict(url=url,bytes=dest.stat().st_size,sha256=sha256(dest),reused=True)
    dest.parent.mkdir(parents=True,exist_ok=True);temp=None
    try:
        with tempfile.NamedTemporaryFile(dir=dest.parent,suffix='.download-part',delete=False) as f:
            temp=Path(f.name);h=hashlib.sha256();size=0;last=time.monotonic()
            with urlopen(url,timeout=45) as response:
                declared=response.headers.get('Content-Length')
                if declared and int(declared)>max_bytes:raise ValueError('Declared response exceeds download budget')
                while True:
                    b=response.read(1024*1024)
                    if not b:break
                    size+=len(b)
                    if size>max_bytes:raise ValueError('Download budget exceeded')
                    h.update(b);f.write(b)
                    if time.monotonic()-last>10:print(dest.name,size,'bytes',flush=True);last=time.monotonic()
            if declared and int(declared)!=size:raise ValueError('Content-Length mismatch')
            if expected_size is not None and size!=expected_size:raise ValueError('Reviewed file size mismatch')
            if expected_sha and h.hexdigest()!=expected_sha:raise ValueError('Reviewed checksum mismatch')
            f.flush();os.fsync(f.fileno())
        os.replace(temp,dest);temp=None
        return dict(url=url,bytes=size,sha256=h.hexdigest(),reused=False)
    finally:
        if temp and temp.exists():temp.unlink()


def development(root):
    root=Path(root);records=[]
    for s in json.loads((KIT/'spec/HYBRID_V3_SOURCES.json').read_text()):
        pcap=root/s['relative_pcap'];target=Path(str(pcap)+'.xz') if s.get('compression')=='xz' else pcap
        record=download(s['pcap_url'],target,s['download_sha256'],s['download_bytes'])
        if s.get('compression')=='xz' and not pcap.exists():
            expanded=None
            try:
                with lzma.open(target,'rb') as source,tempfile.NamedTemporaryFile(dir=pcap.parent,suffix='.expand-part',delete=False) as out:
                    expanded=Path(out.name);size=0
                    while True:
                        b=source.read(1024*1024)
                        if not b:break
                        size+=len(b)
                        if size>s['pcap_bytes']:raise ValueError('Expanded data exceeds pinned size')
                        out.write(b)
                if size!=s['pcap_bytes'] or sha256(expanded)!=s['pcap_sha256']:raise ValueError('Expanded PCAP differs from pinned source')
                os.replace(expanded,pcap);expanded=None
            finally:
                if expanded and expanded.exists():expanded.unlink()
        if sha256(pcap)!=s['pcap_sha256'] or pcap.stat().st_size!=s['pcap_bytes']:raise ValueError('PCAP hash/size mismatch')
        records.append(dict(source_id=s['capture_id'],**record))
        print('Verified',s['capture_id'],flush=True)
    (root/'DEVELOPMENT_DOWNLOADS.json').write_text(json.dumps(records,indent=2))


def reserved_test(root,model_dir):
    root=Path(root);freeze=verify_freeze(model_dir);source=freeze['reserved_external_test']
    folder=root/source['capture_id'];folder.mkdir(parents=True,exist_ok=True)
    record=folder/'TEST_RECEIPT.json'
    if record.exists():
        old=json.loads(record.read_text())
        if old['model_sha256']!=freeze['model_sha256']:raise ValueError('Reserved test already belongs to another frozen model')
        if sha256(folder/old['filename'])!=old['sha256']:raise ValueError('Existing test PCAP changed')
        return old
    # Record the selection before reading any test packet bytes.
    selection=dict(model_sha256=freeze['model_sha256'],source_plan=source,selected_at=time.time())
    (folder/'TEST_SELECTION.json').write_text(json.dumps(selection,indent=2))
    filename=Path(urlparse(source['pcap_url']).path).name
    result=download(source['pcap_url'],folder/filename,max_bytes=32*1024*1024)
    receipt=dict(selection,filename=filename,**result)
    record.write_text(json.dumps(receipt,indent=2))
    print('Reserved test downloaded after model freeze:',filename,flush=True)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['development','test'])
    p.add_argument('--root',default='data/iot23_v3');p.add_argument('--model-dir',default='build/hybrid_model_v3');a=p.parse_args()
    try:
        if a.phase=='development':development(a.root)
        else:reserved_test(a.root,a.model_dir)
    except (ValueError,OSError,KeyError) as e:p.error(str(e))
