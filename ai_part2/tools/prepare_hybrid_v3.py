import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from part2.hybrid_data import native_cache,read_cache,build_development
KIT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser(description='Build packet-derived hybrid DEVELOPMENT data, preserving source/split provenance')
    p.add_argument('--native-root',default='data/iot23_v3');p.add_argument('--cache',default='build/iot23_v3_cache')
    p.add_argument('--lab-v1',default='build/challenge_features_v1.csv');p.add_argument('--lab-v2',default='build/v2_holdout_v2test01.csv')
    p.add_argument('--output',default='build/hybrid_v3_features.csv');a=p.parse_args()
    try:
        paths=[]
        for source in json.loads((KIT/'spec/HYBRID_V3_SOURCES.json').read_text()):
            path=Path(a.cache)/(source['capture_id']+'.csv');paths.append(path)
            if path.exists():
                _,meta=read_cache(path)
                if meta['source']!=source:raise ValueError('Cached source annotation differs; inspect and use a new cache path')
            else:
                print('Extracting',source['capture_id'],flush=True)
                native_cache(Path(a.native_root)/source['relative_pcap'],source,path)
        protocol=json.loads((KIT/'spec/HYBRID_V3_PROTOCOL.json').read_text())
        meta=build_development(a.lab_v1,a.lab_v2,paths,protocol,a.output)
        print('Saved',a.output,'rows=',meta['rows'],'captures=',len(meta['captures']))
    except (ValueError,OSError,KeyError) as e:p.error(str(e))
