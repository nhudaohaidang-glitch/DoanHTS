"""Reuse extracted Syn34 and verify/supplement Hue4 without reopening a tar.gz."""
import argparse
from fractions import Fraction
import json
import lzma
from pathlib import Path
import shutil
import sys
from urllib.request import urlopen

import process_iot23_full as processor


def inspect(path, source):
    if not path.is_file():
        return dict(path=str(path),status='missing')
    size=path.stat().st_size
    if size!=source['pcap_bytes']:
        return dict(path=str(path),status='size_differs',bytes=size)
    digest=processor.sha(path)
    return dict(path=str(path),bytes=size,sha256=digest,
                status='verified' if digest==source['pcap_sha256'] else 'hash_differs')


def official_hue(source, output):
    """Bound both compressed and expanded bytes; never accept a changed source."""
    target=output/'official_reference'/source['relative_pcap']
    target.parent.mkdir(parents=True,exist_ok=True)
    compressed=Path(str(target)+'.xz')
    temporary=Path(str(compressed)+'.part')
    expanded=Path(str(target)+'.part')
    try:
        print(f"Downloading official Hue4 reference: {source['download_bytes']} bytes; not the full archive.",flush=True)
        size=0
        with urlopen(source['pcap_url'],timeout=45) as response,temporary.open('wb') as dst:
            while block:=response.read(64*1024):
                size+=len(block)
                if size>source['download_bytes']:raise ValueError('Official download exceeds pinned size')
                dst.write(block)
        if size!=source['download_bytes'] or processor.sha(temporary)!=source['download_sha256']:
            raise ValueError('Official download checksum/size differs; no labels created')
        temporary.replace(compressed)
        size=0
        with lzma.open(compressed,'rb') as src,expanded.open('wb') as dst:
            while block:=src.read(64*1024):
                size+=len(block)
                if size>source['pcap_bytes']:raise ValueError('Expanded Hue4 exceeds pinned size')
                dst.write(block)
        if size!=source['pcap_bytes'] or processor.sha(expanded)!=source['pcap_sha256']:
            raise ValueError('Expanded official Hue4 checksum differs; no labels created')
        expanded.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
        expanded.unlink(missing_ok=True)
    return target


def packet_equivalence(candidate, reference):
    """Global PCAP header differences alone need not change the packet sequence.

    Require identical link type, exact timestamps, captured/wire lengths, order,
    and all packet bytes. A feature-only comparison cannot approve a variant.
    """
    from scapy.error import Scapy_Exception
    from scapy.utils import RawPcapReader
    count=0
    try:
        with Path(candidate).open('rb') as candidate_file,Path(reference).open('rb') as reference_file,RawPcapReader(candidate_file) as a,RawPcapReader(reference_file) as b:
            if a.linktype!=b.linktype:
                return dict(equivalent=False,reason='link_type_differs')
            while True:
                x=next(a,None);y=next(b,None)
                if x is None or y is None:
                    return dict(equivalent=x is None and y is None,
                                reason='all_packet_records_equal' if x is None and y is None else 'packet_count_differs',
                                compared_packets=count)
                xm,ym=x[1],y[1]
                xt=Fraction(xm.sec)+Fraction(xm.usec,10**9 if a.nano else 10**6)
                yt=Fraction(ym.sec)+Fraction(ym.usec,10**9 if b.nano else 10**6)
                if (x[0],xt,xm.caplen,xm.wirelen)!=(y[0],yt,ym.caplen,ym.wirelen):
                    return dict(equivalent=False,reason='packet_record_differs',first_different_packet=count+1)
                count+=1
    except (OSError,ValueError,AttributeError,EOFError,Scapy_Exception) as e:
        return dict(equivalent=False,reason='cannot_compare_packet_records',detail=str(e))


def recover(work, output):
    try:
        import numpy
        from scapy.utils import RawPcapReader
    except ImportError:
        raise ValueError('Run with ~/ai_part2/.venv/bin/python; NumPy and Scapy are required')
    work=Path(work).expanduser().resolve()
    output=Path(output).expanduser().resolve()
    if output.exists():raise ValueError('Output exists; choose a new folder to preserve previous results')
    original_report=work/'BAO_CAO.json'
    if not original_report.is_file():raise ValueError('Previous BAO_CAO.json not found: '+str(original_report))
    previous=json.loads(original_report.read_text(encoding='utf-8'))
    registry=json.loads(processor.REGISTRY.read_text())
    sources=[next(s for s in registry if s['capture_id']==sid) for sid in ('iot23_hue4','iot23_syn34')]
    hue,syn=sources
    syn_path=work/'raw'/syn['relative_pcap']
    syn_check=inspect(syn_path,syn)
    if syn_check['status']!='verified':
        raise ValueError('Extracted Syn34 is missing or differs; keep old files and send the error. No archive read or download attempted.')
    output.parent.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(output.parent).free<32*processor.MIB:raise ValueError('Need 32 MiB free in the output drive')
    output.mkdir()
    report=dict(status='in_progress',previous_work=str(work),previous_report_sha256=processor.sha(original_report),
                previous_archive_name=previous.get('archive_name'),
                previous_archive_sha256_recorded=previous.get('archive_sha256'),
                archive_opened=False,original_files_changed=False,model_changed=False,
                purpose='Reproduce existing V3 development sources; not new independent test or retraining',
                receipts=[dict(capture_id=syn['capture_id'],method='reuse_verified_extracted_pcap',**syn_check)])
    report_path=output/'BAO_CAO.json'
    try:
        report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('Verified extracted Syn34; the 21 GB archive will not be opened.',flush=True)
        hue_path=work/'raw'/hue['relative_pcap']
        hue_check=inspect(hue_path,hue)
        record=dict(capture_id=hue['capture_id'],previous_candidate=hue_check)
        if hue_check['status']=='verified':
            record.update(method='reuse_verified_extracted_pcap',used_pcap=hue_check)
        else:
            reference=official_hue(hue,output)
            record.update(reference_url=hue['pcap_url'],download_bytes=hue['download_bytes'],
                          download_sha256=hue['download_sha256'])
            equivalence=packet_equivalence(hue_path,reference) if hue_check['status']=='hash_differs' else dict(equivalent=False,reason='no_same_size_candidate')
            record['packet_comparison']=equivalence
            if equivalence['equivalent']:
                record.update(method='reuse_extracted_pcap_after_exact_packet_equivalence_to_pinned_reference',
                              used_pcap=hue_check,reference_pcap=inspect(reference,hue))
                print('Hue4: every packet record matches the official reference; using extracted PCAP.',flush=True)
            else:
                hue_path=reference
                record.update(method='official_individual_source_supplement',used_pcap=inspect(reference,hue))
                print('Hue4: using verified official individual source; archive variant is preserved and unused.',flush=True)
        report['receipts'].append(record)
        report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
        origin='Đã dùng lại Syn34 được xác minh từ thư mục cũ. Hue4: '+('dùng lại bản đã trích sau kiểm tra; xem báo cáo nguồn.' if record['method']!='official_individual_source_supplement' else 'bổ sung bản riêng chính thức đã kiểm tra hash; bản Hue4 khác trong archive được giữ nguyên và không dùng để gán nhãn.')
        return processor.write_results(output,sources,{'iot23_hue4':hue_path,'iot23_syn34':syn_path},report,origin)
    except Exception as e:
        report.update(status='failed',error=str(e))
        report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
        processor.diagnostic_page(output,e)
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',required=True,help='Previous iot23_work_01 folder; read only')
    p.add_argument('--output',required=True,help='New output folder')
    a=p.parse_args()
    try:recover(a.work,a.output)
    except (ValueError,OSError,EOFError) as e:p.exit(1,'ERROR: '+str(e)+'\n')
