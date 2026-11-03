"""Disk-backed, bidirectional IPv4 native-label intervals for packet filtering.

Every non-Benign label blocks overlapping Benign time. No label is inferred
from TCP flags. Files are private scratch data, not a training dataset.
"""
from collections import Counter
from functools import lru_cache
import ipaddress
import math
from pathlib import Path

import numpy as np

RAW = np.dtype([('h','<u8'),('a','<u8'),('b','<u8'),('s','<f8'),('e','<f8'),('n','u1')])
KEY = np.dtype([('h','<u8'),('a','<u8'),('b','<u8'),('lo','<u8'),('hi','<u8')])
SPAN = np.dtype([('s','<f8'),('e','<f8')])
CHUNK = 250_000
TOLERANCE = .001


def mix(x):
    with np.errstate(over='ignore'):
        x = np.asarray(x, dtype=np.uint64)
        x = (x ^ (x >> np.uint64(30))) * np.uint64(0xbf58476d1ce4e5b9)
        x = (x ^ (x >> np.uint64(27))) * np.uint64(0x94d049bb133111eb)
        return x ^ (x >> np.uint64(31))


def hashes(a, b):
    return mix(np.asarray(a, dtype=np.uint64) ^ mix(b))


@lru_cache(maxsize=16384)
def ip4(text):
    return int(ipaddress.IPv4Address(text))


def flow_key(proto, src, sport, dst, dport):
    if proto == 1:
        # Zeek uses ICMP type/code as orig/resp ports. Echo request and reply
        # belong to one flow; other types remain separate.
        family = ({0:8, 14:13, 16:15, 18:17}.get(sport, sport) << 8) | dport
        sport = dport = family
    x, y = (src << 16) | sport, (dst << 16) | dport
    return (proto << 48) | min(x, y), max(x, y)


class Builder:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.raw_path = self.folder / 'rows.tmp'
        self.stream = self.raw_path.open('wb')
        self.buffer = []
        self.counts = Counter()

    def observe(self, row):
        self.counts['native_rows'] += 1
        proto = {'tcp':6, 'udp':17, 'icmp':1}.get(row['proto'])
        if proto is None:
            self.counts['unsupported_protocol_rows'] += 1
            return
        try:
            src, dst = ip4(row['id.orig_h']), ip4(row['id.resp_h'])
        except ipaddress.AddressValueError:
            self.counts['non_ipv4_rows'] += 1
            return
        sport, dport = int(row['id.orig_p']), int(row['id.resp_p'])
        if not (0 <= sport <= 65535 and 0 <= dport <= 65535):
            raise ValueError('Invalid native flow port')
        if proto == 1 and (sport > 255 or dport > 255):
            raise ValueError('Invalid native ICMP type/code')
        a, b = flow_key(proto, src, sport, dst, dport)
        start = float(row['ts'])
        duration = 0. if row['duration'] in ('-', '(empty)') else float(row['duration'])
        if not math.isfinite(start) or not math.isfinite(duration) or duration < 0:
            raise ValueError('Invalid native flow time; packet labels cannot be associated safely')
        self.buffer.append((0, a, b, start-TOLERANCE, start+duration+TOLERANCE,
                            row['label'].casefold() == 'benign'))
        self.counts['indexed_rows'] += 1
        if len(self.buffer) >= 100_000:
            self.flush()

    def flush(self):
        if self.buffer:
            rows = np.array(self.buffer, dtype=RAW)
            rows['h'] = hashes(rows['a'], rows['b'])
            rows.tofile(self.stream)
            self.buffer.clear()

    def close(self):
        if not self.stream.closed:
            self.flush()
            self.stream.close()

    def finish(self):
        self.close()
        count = self.raw_path.stat().st_size // RAW.itemsize
        self.counts.update(compile_index(self.raw_path, count, self.folder))
        self.raw_path.unlink()
        return dict(self.counts)


def merged(rows, normal):
    """Streaming interval union, including groups larger than RAM."""
    pending = None
    for at in range(0, len(rows), CHUNK):
        block = rows[at:at+CHUNK]
        chosen = block[block['n'] == normal]
        if not len(chosen):
            continue
        maximum = np.maximum.accumulate(chosen['e'])
        edges = np.r_[0, np.flatnonzero(chosen['s'][1:] > maximum[:-1])+1, len(chosen)]
        for left, right in zip(edges[:-1], edges[1:]):
            start, end = float(chosen['s'][left]), float(maximum[right-1])
            if pending is not None and start <= pending[1]:
                pending = (pending[0], max(pending[1], end))
            else:
                if pending is not None:
                    yield pending
                pending = (start, end)
    if pending is not None:
        yield pending


def allowed(rows):
    negative = iter(merged(rows, 0))
    block = next(negative, None)
    for start, end in merged(rows, 1):
        while block is not None and block[1] < start:
            block = next(negative, None)
        cursor = start
        while block is not None and block[0] <= end:
            if block[0] > cursor:
                yield cursor, min(end, float(np.nextafter(block[0], -np.inf)))
            cursor = max(cursor, float(np.nextafter(block[1], np.inf)))
            if cursor > end:
                break
            block = next(negative, None)
        if cursor <= end:
            yield cursor, end


def compile_index(raw_path, count, folder):
    keys_path, spans_path = folder/'keys.bin', folder/'spans.bin'
    nkeys = nspans = 0
    if not count:
        keys_path.write_bytes(b''); spans_path.write_bytes(b''); (folder/'hashes.bin').write_bytes(b'')
        return dict(keys=0, allowed_intervals=0)
    rows = np.memmap(raw_path, dtype=RAW, mode='r+', shape=(count,))
    print(f'Sorting {count:,} native label intervals on disk', flush=True)
    rows.sort(order=['h','a','b','s'], kind='quicksort')
    rows.flush()
    with keys_path.open('wb') as keyfile, spans_path.open('wb') as spanfile:
        def groups(start, ends):
            nonlocal nkeys, nspans
            starts = np.r_[start, ends[:-1]]
            lengths = ends-starts
            singleton = starts[(lengths == 1) & (rows['n'][starts] == 1)]
            if len(singleton):
                chosen = rows[singleton]
                keys = np.empty(len(chosen), dtype=KEY)
                for name in ('h','a','b'):
                    keys[name] = chosen[name]
                keys['lo'] = np.arange(nspans, nspans+len(chosen), dtype=np.uint64)
                keys['hi'] = keys['lo']+1
                spans = np.empty(len(chosen), dtype=SPAN)
                spans['s'], spans['e'] = chosen['s'], chosen['e']
                keys.tofile(keyfile); spans.tofile(spanfile)
                nkeys += len(chosen); nspans += len(chosen)
            for left, right in zip(starts[lengths > 1], ends[lengths > 1]):
                group = rows[left:right]
                if not np.any(group['n']):
                    continue
                first = nspans
                buffer = []
                for interval in allowed(group):
                    buffer.append(interval)
                    nspans += 1
                    if len(buffer) == 100_000:
                        np.array(buffer, dtype=SPAN).tofile(spanfile); buffer.clear()
                if buffer:
                    np.array(buffer, dtype=SPAN).tofile(spanfile)
                if nspans > first:
                    row = group[0]
                    np.array([(row['h'], row['a'], row['b'], first, nspans)], dtype=KEY).tofile(keyfile)
                    nkeys += 1
        pending = 0
        for at in range(0, count, CHUNK):
            end = min(count, at+CHUNK)
            left = max(1, at)
            change = ((rows['a'][left:end] != rows['a'][left-1:end-1]) |
                      (rows['b'][left:end] != rows['b'][left-1:end-1]))
            boundaries = left + np.flatnonzero(change)
            if len(boundaries):
                groups(pending, boundaries)
                pending = int(boundaries[-1])
        groups(pending, np.array([count]))
    del rows
    if nkeys:
        keys = np.memmap(keys_path, dtype=KEY, mode='r+', shape=(nkeys,))
        keys.sort(order=['h','a','b'], kind='quicksort'); keys.flush()
        with (folder/'hashes.bin').open('wb') as stream:
            for at in range(0, nkeys, CHUNK):
                keys['h'][at:at+CHUNK].tofile(stream)
        del keys
    else:
        (folder/'hashes.bin').write_bytes(b'')
    return dict(keys=nkeys, allowed_intervals=nspans)


class Index:
    def __init__(self, folder):
        folder = Path(folder)
        def mapping(name, dtype):
            path = folder/name
            return np.memmap(path, dtype=dtype, mode='r') if path.stat().st_size else np.empty(0, dtype=dtype)
        self.keys = mapping('keys.bin', KEY)
        self.hashes = mapping('hashes.bin', '<u8')
        self.spans = mapping('spans.bin', SPAN)

    def contains(self, a, b, times):
        a, b, times = np.asarray(a, dtype=np.uint64), np.asarray(b, dtype=np.uint64), np.asarray(times)
        result = np.zeros(len(a), dtype=bool)
        if not len(self.keys) or not len(a):
            return result
        h = hashes(a, b)
        left = np.searchsorted(self.hashes, h, side='left')
        right = np.searchsorted(self.hashes, h, side='right')
        found = np.full(len(a), -1, dtype=np.int64)
        # Full tuple comparison is mandatory even when the 64-bit hashes agree.
        while np.any(left < right):
            active = np.flatnonzero(left < right)
            key = self.keys[left[active]]
            same = (key['a'] == a[active]) & (key['b'] == b[active])
            found[active[same]] = left[active[same]]
            left[active[same]] = right[active[same]]
            left[active[~same]] += 1
        active = np.flatnonzero(found >= 0)
        if not len(active):
            return result
        key = self.keys[found[active]]
        lo, hi = key['lo'].astype(np.int64), key['hi'].astype(np.int64)
        origin = lo.copy()
        while np.any(lo < hi):
            use = np.flatnonzero(lo < hi)
            mid = (lo[use]+hi[use])//2
            earlier = self.spans['s'][mid] <= times[active[use]]
            lo[use[earlier]] = mid[earlier]+1
            hi[use[~earlier]] = mid[~earlier]
        valid = np.flatnonzero(lo > origin)
        result[active[valid]] = self.spans['e'][lo[valid]-1] >= times[active[valid]]
        return result
