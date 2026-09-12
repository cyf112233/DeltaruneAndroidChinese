#!/usr/bin/env python3
"""audit_coverage.py -- 审计每一章：文本用到的码位是否都被图集覆盖。"""
import json, os, sys
sys.path.insert(0, "/media/cyf112233/data/deltarune/work/scripts_mt")
from render_selfcontained import in_band
W = "/media/cyf112233/data/deltarune/work"
A = "/media/cyf112233/data/deltarune/assets"

total_missing = 0
for c in "012345":
    used = set()
    # 章节文本
    p = f"{W}/out/ch{c}_lang/lang_en.json"
    if os.path.exists(p):
        for v in json.load(open(p, encoding="utf-8")).values():
            if isinstance(v, str):
                used.update(ch for ch in v if in_band(ch))
    # 硬编码汉化/英文映射
    for mp in (f"{W}/zh/cyr/merged_ch{c}.json",):
        if os.path.exists(mp):
            for v in json.load(open(mp, encoding="utf-8")).values():
                if isinstance(v, str):
                    used.update(ch for ch in v if in_band(ch))
    used.discard(" ")
    # 图集覆盖（取该章任一字体，各字体码位一致）
    gl = set()
    d = f"{W}/mt/gl{c}"
    for fn in os.listdir(d):
        if fn.startswith("glyphs_") and fn.endswith(".json"):
            gl |= {g["c"] for g in json.load(open(f"{d}/{fn}", encoding="utf-8"))}
            break
    miss = sorted(ch for ch in used if ord(ch) not in gl)
    print(f"ch{c}: 文本 {len(used)} 码位，图集缺 {len(miss)}  {''.join(miss[:40])}")
    total_missing += len(miss)
print(f"\n合计缺字 = {total_missing}")
