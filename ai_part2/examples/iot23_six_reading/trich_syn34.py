"""Copy the previously verified SYN-only native episode, preserving PCAP bytes/time."""
import argparse
import hashlib
from pathlib import Path
import socket
import struct

ORIGINAL_SHA = '92ec7e2f6658ee4b007d0b816986c46cc0338bc5e2bec6ceaaca566c695e4699'
START, END = 1545475806.96806, 1545475828.998385


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while b := f.read(1024 * 1024): h.update(b)
    return h.hexdigest()


def cut(source, destination):
    source, destination = Path(source), Path(destination)
    if digest(source) != ORIGINAL_SHA: raise ValueError('Not the reviewed original capture34 PCAP')
    if destination.exists(): raise ValueError('Destination exists; preserve it')
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with source.open('rb') as src, destination.open('wb') as dst:
        header = src.read(24)
        encodings = {b'\xd4\xc3\xb2\xa1': ('<', 1e6), b'\xa1\xb2\xc3\xd4': ('>', 1e6),
                     b'\x4d\x3c\xb2\xa1': ('<', 1e9), b'\xa1\xb2\x3c\x4d': ('>', 1e9)}
        endian, scale = encodings[header[:4]]
        if struct.unpack(endian + 'I', header[20:24])[0] != 1: raise ValueError('Expected Ethernet PCAP')
        dst.write(header)
        while packet_header := src.read(16):
            if len(packet_header) != 16: raise ValueError('Truncated PCAP record')
            sec, fraction, captured, wire = struct.unpack(endian + 'IIII', packet_header)
            data = src.read(captured)
            if len(data) != captured: raise ValueError('Truncated PCAP frame')
            t = sec + fraction / scale
            if not START <= t <= END or len(data) < 54 or data[12:14] != b'\x08\x00': continue
            ip = data[14:]; ihl = (ip[0] & 15) * 4
            if ip[0] >> 4 != 4 or ip[9] != 6 or ihl < 20 or len(ip) < ihl + 20: continue
            if struct.unpack('!H', ip[6:8])[0] & 0x3fff: continue
            if ip[16:20] != socket.inet_aton('71.61.66.148'): continue
            if struct.unpack('!H', ip[ihl+2:ihl+4])[0] != 80 or ip[ihl+13] & 0x12 != 0x02: continue
            dst.write(packet_header); dst.write(data); count += 1
    if count != 40568: raise ValueError(f'Unexpected episode count: {count}')
    return count


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('original_pcap'); p.add_argument('output_pcap'); a = p.parse_args()
    print('Packets copied:', cut(a.original_pcap, a.output_pcap))
