#!/usr/bin/env python3
"""Sinh bang cho firmware va testbench (chay lai khi doi font hoac vector cua Phan 2):
  fw/font5x7.c        font 5x7 ASCII 0x20..0x7E lay tu glcdfont.c (Adafruit GFX, giay phep BSD)
  sim/font5x7.hex     cung font, moi dong 1 ky tu (5 byte) - testbench dung de doc lai chu tren OLED
  fw/ai_vectors.h     vector tich hop cua Phan 2 (INTEGRATION_VECTORS.json) de firmware tu kiem AI qua bus
Cach dung: python3 tools/gen_tables.py <glcdfont.c> <INTEGRATION_VECTORS.json>
"""
import json, re, sys, os, hashlib

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
glcd, vec = sys.argv[1], sys.argv[2]
v = json.load(open(vec))
model_path = os.path.join(root,"rtl","part2_ai","model.json")
if v.get("model_sha256") != hashlib.sha256(open(model_path,"rb").read()).hexdigest():
    raise SystemExit("Vector references do not match the active model")

data = [int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{2})", open(glcd).read())]
assert len(data) >= 256 * 5, len(data)
glyphs = [data[5 * c: 5 * c + 5] for c in range(0x20, 0x7F)]

with open(os.path.join(root, "fw", "font5x7.c"), "w") as f:
    f.write("/* font5x7.c - font 5x7 ASCII 0x20..0x7E, moi ky tu 5 cot, bit 0 = dong tren cung.\n"
            " * Trich tu glcdfont.c cua Adafruit GFX Library (BSD, xem font5x7_LICENSE.txt).\n"
            " * Tu sinh boi tools/gen_tables.py - khong sua tay. */\n")
    f.write("#include <stdint.h>\nconst uint8_t font5x7[95][5] = {\n")
    for c, g in zip(range(0x20, 0x7F), glyphs):
        ch = chr(c)
        cm = ch if ch not in "\\*/" else " "
        f.write("    {" + ", ".join("0x%02X" % b for b in g) + "},  /* '%s' */\n" % cm)
    f.write("};\n")

with open(os.path.join(root, "sim", "font5x7.hex"), "w") as f:
    for g in glyphs:
        f.write("".join("%02x" % b for b in g) + "\n")

ex = v["examples"]
with open(os.path.join(root, "fw", "ai_vectors.h"), "w") as f:
    f.write("/* ai_vectors.h - vector tich hop AI v5 (Phan 2, INTEGRATION_VECTORS.json).\n"
            " * Firmware dung luc khoi dong: kiem ai_v5_prepare_window() va AI qua bus.\n"
            " * Tu sinh boi tools/gen_tables.py - khong sua tay. */\n")
    f.write("#ifndef AI_VECTORS_H\n#define AI_VECTORS_H\n#include <stdint.h>\n")
    f.write("typedef struct { uint32_t cnt[6]; uint32_t valid; uint32_t feat_lo, feat_hi;"
            " int16_t score[3]; uint8_t cls; } ai_vec_t;\n")
    f.write("#define AI_VEC_N %d\nstatic const ai_vec_t ai_vec[AI_VEC_N] = {\n" % len(ex))
    for e in ex:
        fh = int(e["feat_hex"], 16)
        f.write("    {{%s}, %d, 0x%08Xu, 0x%04Xu, {%s}, %d},\n" % (
            ", ".join("%du" % x for x in e["counter_inputs"]), 1 if e["decision_valid"] else 0,
            fh & 0xFFFFFFFF, fh >> 32, ", ".join(str(s) for s in e["scores"]), e["class_id"]))
    f.write("};\n#endif\n")
print("OK: fw/font5x7.c, sim/font5x7.hex, fw/ai_vectors.h (%d vector)" % len(ex))
