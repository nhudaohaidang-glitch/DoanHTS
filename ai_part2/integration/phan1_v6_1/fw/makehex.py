#!/usr/bin/env python3
"""Doi firmware.bin thanh firmware.hex cho $readmemh: moi dong 1 tu 32 bit (little-endian),
dem du MEM_WORDS dong.

Cach dung:  python makehex.py firmware.bin 4096 > firmware.hex
"""
import sys


def main():
    if len(sys.argv) != 3:
        sys.exit("Cach dung: python makehex.py <firmware.bin> <so_tu_32bit>")
    path, nwords = sys.argv[1], int(sys.argv[2])
    with open(path, "rb") as f:
        data = f.read()
    size = len(data)
    if size > 4 * nwords:
        sys.exit(f"Loi: firmware {size} byte, vuot qua RAM {4 * nwords} byte")
    data += b"\0" * (4 * nwords - size)
    out = []
    for i in range(nwords):
        word = int.from_bytes(data[4 * i:4 * i + 4], "little")
        out.append(f"{word:08x}")
    sys.stdout.write("\n".join(out) + "\n")
    print(f"firmware: {size} byte / {4 * nwords} byte RAM", file=sys.stderr)


if __name__ == "__main__":
    main()
