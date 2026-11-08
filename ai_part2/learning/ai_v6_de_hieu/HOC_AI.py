"""Study the frozen AI V6 offline: real examples, raw/counter conversion and scores."""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from ai_reference import infer, prepare, unpack
SHA = '3f1b2052ca30aad7f493b9f9091b86bcaf37dbf4c209363dea0c841f70f11515'
CLASSES = ['Normal', 'SYN flood', 'Vertical scan']
NAMES = ['normal', 'syn', 'scan']


def raw_q(raw, model):
    if len(raw) != 6 or any(type(x) is not int or x < 0 for x in raw):
        raise ValueError('Can sau so nguyen khong am')
    if raw[2] > 127:
        raise ValueError('syn_ratio_q127 phai trong 0..127, khong phai phan tram')
    return [min(127, x // d) for x, d in zip(raw, model['divisors'])]


def show(raw, model):
    if raw[0] == 0:
        print('N=0: BO SUY LUAN; khong co class/score moi.')
        return
    q = raw_q(raw, model)
    acc = [sum(x*w for x, w in zip(q, row)) + b for row, b in zip(model['w1'], model['b1'])]
    hidden = [max(0, min(127, x >> model['shift1'])) for x in acc]
    scores = infer(q, model)
    pred = max(range(3), key=lambda i: scores[i])
    print('raw =', raw, '\nq =', q)
    print('feat = 0x%012x' % sum(x << (8*i) for i, x in enumerate(q)))
    print('hidden accumulators =', acc, '\nhidden =', hidden)
    print('scores =', scores, '\nclass =', pred, CLASSES[pred])
    print('Day la du doan theo q, khong tu xac nhan nhan hoac nguon doc lap.')


def check(model, facts):
    for e in facts['examples']:
        valid, word = prepare(e['counters'], model)
        assert valid and unpack(word) == e['q'] and '%012x' % word == e['feat_hex']
        assert infer(e['q'], model) == e['scores']
        row = e['row']
        raw = [int(row[k]) for k in ('packet_count', 'mean_ip_bytes', 'syn_ratio_q127', 'src_count', 'dst_count', 'dst_port_count')]
        assert raw_q(raw, model) == e['q']
        path = ROOT / 'vi_du' / (e['id'] + '.pcap.gz')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == e['pcap_sha256']
        csv_path = ROOT / 'vi_du' / (e['id'] + '.csv')
        assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest() == e['uncompressed_pcap_sha256']
        assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == e['csv_sha256']
    for e in facts['additional_numeric_cases']:
        scores = infer(e['q'], model)
        assert scores == e['scores']
        assert max(range(3), key=lambda i: scores[i]) == e['predicted']
    assert prepare([0, 0, 0, 0, 0, 0], model) == (False, 0)
    assert prepare([7, 427, 1, 1, 1, 1], model)[0]
    print('PASS: dung model V6; 3 vi du va 4 case so hoc khop; N=0 skip, N=7 valid.')
    print('Kiem byte/checksum file hoc; khong phai test phat hien tren nguon doc lap.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action')
    p = sub.add_parser('vi-du'); p.add_argument('name', choices=NAMES)
    for name in ('raw', 'counter'):
        p = sub.add_parser(name); p.add_argument('values', type=int, nargs=6)
    sub.add_parser('kiem-tra'); sub.add_parser('giai-nen-pcap')
    args = parser.parse_args()
    path = ROOT / 'model/model.json'
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA:
        raise ValueError('Model da thay doi; dung ban V6 di kem goi hoc')
    model = json.loads(path.read_text())
    facts = json.loads((ROOT / 'VI_DU_DA_DOI_CHIEU.json').read_text())
    if args.action == 'raw':
        raw_q(args.values, model); show(args.values, model)
    elif args.action == 'counter':
        valid, word = prepare(args.values, model)
        if not valid: show([0]*6, model)
        else:
            n, b, s, ns, nd, np = args.values
            print('counter =', args.values)
            show([n, b//n, 127*s//n, ns, nd, np], model)
    elif args.action == 'vi-du':
        e = facts['examples'][NAMES.index(args.name)]
        print('Profile:', e['id'], 'label:', e['row']['label'], 'status:', e['row']['status'])
        print('counter =', e['counters'])
        show([int(e['row'][k]) for k in ('packet_count','mean_ip_bytes','syn_ratio_q127','src_count','dst_count','dst_port_count')], model)
    elif args.action == 'kiem-tra':
        check(model, facts)
    elif args.action == 'giai-nen-pcap':
        target = ROOT / 'vi_du/pcap_da_giai_nen'; target.mkdir(exist_ok=True)
        for e in facts['examples']:
            data = gzip.decompress((ROOT / 'vi_du' / (e['id'] + '.pcap.gz')).read_bytes())
            out = target / (e['id'] + '.pcap')
            if out.exists() and out.read_bytes() != data:
                raise ValueError('Tep dich da ton tai va khac noi dung: ' + str(out))
            out.write_bytes(data)
            print(out)
    else:
        print('Hoc AI V6: mo BAT_DAU_HOC_AI_V6.html hoac PDF truoc.')
        print('Lenh: vi-du normal|syn|scan; raw <6 so>; counter <6 so>; kiem-tra; giai-nen-pcap')
        for e in facts['examples']:
            print(e['id'], 'q=', e['q'], 'scores=', e['scores'], 'class=', e['predicted'])


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, AssertionError) as error:
        raise SystemExit('ERROR: ' + str(error))
