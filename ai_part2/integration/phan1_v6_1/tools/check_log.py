#!/usr/bin/env python3
"""Kiem tra log UART cua firmware (sim/out/uart.log hoac log chup tu kit).

Cach dung:
  python3 tools/check_log.py sim/out/uart.log            # kiem tra kich ban mo phong tb_gateway
  python3 tools/check_log.py log_kit.txt --format-only   # chi kiem dinh dang + checksum (log that)

Kiem tra:
  - moi dong '$' dung checksum (XOR cac ky tu giua '$' va '*'), dung so truong
  - cua so rong: co bit3, khong goi AI (lat = 0)
  - khong bao gio chan IP trong danh sach trang (broker .2, cam bien .20)
  - kich ban: chan .50 (DOS) va .51 (SCAN), go ca hai, khong chan IP gia 10.x, lop 2 bo goi
In them bang so sanh AI tho / ket luan / luat nguong de dua vao bao cao.
"""
import sys

FIELDS = {"$IDS": 17, "$BLK": 3, "$UNB": 1, "$CNT": 5, "$MODE": 1}
ALLOW = {"192.168.10.2", "192.168.10.20"}
NAMES = ["BT", "DoS", "SCAN"]


def parse(path):
    recs, errors = [], []
    for n, raw in enumerate(open(path, encoding="ascii", errors="replace"), 1):
        line = raw.rstrip("\r\n")
        if not line or line.startswith("#"):
            continue
        if not line.startswith("$") or "*" not in line:
            errors.append("dong %d: khong dung dinh dang: %r" % (n, line))
            continue
        body, cs = line[1:].rsplit("*", 1)
        calc = 0
        for ch in body:
            calc ^= ord(ch)
        if cs != "%02X" % calc:
            errors.append("dong %d: sai checksum (%s, dung la %02X): %r" % (n, cs, calc, line))
            continue
        parts = body.split(",")
        tag = "$" + parts[0]
        if tag in FIELDS and len(parts) - 1 != FIELDS[tag]:
            errors.append("dong %d: %s can %d truong, co %d" % (n, tag, FIELDS[tag], len(parts) - 1))
            continue
        recs.append((n, tag, parts[1:]))
    return recs, errors


def main():
    path = sys.argv[1]
    fmt_only = "--format-only" in sys.argv
    recs, errors = parse(path)
    ok = []

    def check(cond, msg):
        (ok if cond else errors).append(msg)

    ids = [(n, f) for n, t, f in recs if t == "$IDS"]
    blk = [(n, f) for n, t, f in recs if t == "$BLK"]
    unb = [(n, f) for n, t, f in recs if t == "$UNB"]
    cnt = [(n, f) for n, t, f in recs if t == "$CNT"]
    mode = [(n, f[0]) for n, t, f in recs if t == "$MODE"]
    syn = [(n, f) for n, t, f in recs if t == "$SYN"]

    # ---- quy tac chung (ca log that)
    for n, f in ids:
        win, cls, alert, pkt, avg, synp, src, dst, port, flags, lat = (int(x) for x in f[:11])
        if pkt == 0 and not (flags & 8 and lat == 0 and cls == 0 and alert == 0):
            errors.append("dong %d: cua so rong nhung van goi AI hoac bao dong" % n)
        if pkt > 0 and not (flags & 2) and lat == 0:
            errors.append("dong %d: cua so co goi nhung lat = 0" % n)
    for n, f in blk:
        if f[0] in ALLOW:
            errors.append("dong %d: chan IP trong danh sach trang %s" % (n, f[0]))
    check(True, "%d dong '$' dung checksum va so truong" % len(recs))

    if not fmt_only:
        blk_ip = {f[0]: (n, f[1]) for n, f in reversed(blk)}       # lan chan dau tien
        unb_ip = {f[0]: n for n, f in unb}
        check(len(ids) >= 35, "co %d dong $IDS (>= 35 cua so)" % len(ids))
        check("192.168.10.50" in blk_ip and blk_ip["192.168.10.50"][1] == "DOS",
              "chan 192.168.10.50 voi ly do DOS")
        check("192.168.10.51" in blk_ip and blk_ip["192.168.10.51"][1] == "SCAN",
              "chan 192.168.10.51 voi ly do SCAN")
        check(all(ip in unb_ip and unb_ip[ip] > blk_ip[ip][0] for ip in blk_ip),
              "moi IP bi chan deu duoc go ($UNB) sau do")
        check(not any(ip.startswith("10.") for ip in blk_ip),
              "khong chan IP gia 10.x (IP nghi van khong chiem qua nua SYN)")
        check([m for _, m in mode] == ["DETECT", "BLOCK", "DETECT"],
              "$MODE: DETECT (khoi dong) -> BLOCK -> DETECT")
        check([f[0] for _, f in syn] == ["ON", "OFF"], "$SYN,ON roi $SYN,OFF")
        on = syn[0][0] if syn else 10**9
        off = syn[1][0] if len(syn) > 1 else 10**9
        check(any(int(f[2]) > 0 for n, f in cnt if on < n < off), "lop 2 bo goi SYN khi bat ($CNT drop_syn > 0)")
        check(all(int(f[2]) == 0 for n, f in cnt if n < on), "lop 2 khong bo goi nao khi dang tat")
        # truoc khi bat lop 2, khi khong co IP nao bi chan: khong bo goi nao
        first_blk = blk[0][0] if blk else 10**9
        check(all(int(f[1]) == 0 for n, f in cnt if n < first_blk), "khong bo goi nao truoc lan $BLK dau")
        # cua so chi co cam bien (7 goi, 1 SYN): ket luan cuoi cung phai la BT
        sensor_only = [f for n, f in ids if int(f[3]) == 7 and int(f[8]) == 1]
        check(len(sensor_only) > 0 and all(int(f[2]) == 0 for f in sensor_only),
              "%d cua so chi co cam bien: khong bao dong" % len(sensor_only))

    # ---- bang so sanh cho bao cao
    tab = {}
    for n, f in ids:
        if int(f[3]) == 0:
            continue
        key = (NAMES[int(f[1])], NAMES[int(f[2])], NAMES[int(f[11])], bool(int(f[9]) & 16))
        tab[key] = tab.get(key, 0) + 1
    print("So cua so co goi theo (AI tho, ket luan, luat nguong, cong kiem tra doi ket qua):")
    for k in sorted(tab):
        print("   AI=%-4s  ket luan=%-4s  luat=%-4s  cong=%-3s : %d" % (k[0], k[1], k[2], "co" if k[3] else "-", tab[k]))
    for m in ok:
        print("OK   " + m)
    for e in errors:
        print("LOI  " + e)
    print("PASS" if not errors else "FAIL: %d loi" % len(errors))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
