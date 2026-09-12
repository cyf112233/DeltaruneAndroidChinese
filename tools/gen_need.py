#!/usr/bin/env python3
"""gen_need.py -- 从"最终会被游戏读取的全部文本"重新生成每章 need_chN.txt。

来源必须和 audit_coverage.py 完全一致，否则又会出现"图集缺字"：
  * out/ch<N>_lang/lang_en.json   （章节文本）
  * zh/cyr/merged_ch<N>.json      （写进 data.win 的硬编码文本：中文 + 英文）
"""
import json, os, sys
sys.path.insert(0, "/media/cyf112233/data/deltarune/work/scripts_mt")
from render_selfcontained import in_band
W = "/media/cyf112233/data/deltarune/work"

for c in "012345":
    used = set()
    p = f"{W}/out/ch{c}_lang/lang_en.json"
    if os.path.exists(p):
        for v in json.load(open(p, encoding="utf-8")).values():
            if isinstance(v, str):
                used.update(ch for ch in v if in_band(ch))
    mp = f"{W}/zh/cyr/merged_ch{c}.json"
    if os.path.exists(mp):
        for v in json.load(open(mp, encoding="utf-8")).values():
            if isinstance(v, str):
                used.update(ch for ch in v if in_band(ch))
    used.discard(" ")
    txt = "".join(sorted(used, key=ord))
    open(f"{W}/mt/need_ch{c}.txt", "w", encoding="utf-8").write(txt)
    print(f"ch{c}: {len(txt)} 码位 -> mt/need_ch{c}.txt")
