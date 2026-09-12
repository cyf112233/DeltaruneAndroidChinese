#!/usr/bin/env python3
"""cmp_wrap.py -- 和我们自己的字宽比：每句话的换行数量、每行宽度是否超上限。

对手：好人汉化组 PC 补丁的 lang_en.json（逐条完全一致率 ~12%，但换行结构可对照）。
上限：引擎换行宽度 = charline(33) × hspace(8) = 264px；自动换行时会补一个 "*" 占位。
"""
import json, os, re, sys

W = "/media/cyf112233/data/deltarune/work"
PC = "/media/cyf112233/data/steamgames/steamapps/common/DELTARUNE"
LIMIT = 33 * 8

CTRL = re.compile(r"\\[A-Za-z][0-9]?|\^[0-9]+|~[0-9]?|%%?|/%")
BREAK = re.compile(r"[\n&#]|\\n")


def width(s, adv):
    """按我们的字形步进量测一行有多宽；控制码不占宽。"""
    total = 0
    i = 0
    while i < len(s):
        m = CTRL.match(s, i)
        if m:
            i = m.end()
            continue
        c = s[i]
        total += adv.get(ord(c), adv.get(ord("?"), 12))
        i += 1
    return total


def lines(s):
    return [x for x in BREAK.split(s)]


def main():
    tot = mism = 0
    over_ours = over_good = 0
    samples = []
    for c in "12345":
        adv = {g["c"]: g["shift"] for g in
               json.load(open(f"{W}/mt/gl{c}/glyphs_ch{c}_fnt_main.json", encoding="utf-8"))}
        ours = json.load(open(f"{W}/out/ch{c}_lang/lang_en.json", encoding="utf-8"))
        p = f"{PC}/chapter{c}_windows/lang/lang_en.json"
        if not os.path.exists(p):
            print(f"ch{c}: 没有好人对照文件 {p}")
            continue
        good = json.load(open(p, encoding="utf-8"))
        n = m = 0
        for k, v in ours.items():
            if not isinstance(v, str) or not any("\u4e00" <= ch <= "\u9fff" for ch in v):
                continue
            g = good.get(k)
            if not isinstance(g, str):
                continue
            n += 1
            lo, lg = lines(v), lines(g)
            wo = max((width(x, adv) for x in lo), default=0)
            wg = max((width(x, adv) for x in lg), default=0)
            if wo > LIMIT:
                over_ours += 1
            if wg > LIMIT:
                over_good += 1
            if len(lo) != len(lg):
                m += 1
                if len(samples) < 6:
                    samples.append((c, k, v, g, len(lo), len(lg), wo, wg))
        print(f"ch{c}: 对照 {n} 条；换行数不一致 {m} 条 ({m/max(n,1)*100:.1f}%)；"
              f"最长行超 {LIMIT}px：我们 {over_ours} 条 / 好人 {over_good} 条")
        tot += n
        mism += m
    print(f"\n合计对照 {tot} 条，换行数不一致 {mism} 条；超宽：我们 {over_ours} / 好人 {over_good}")
    for c, k, v, g, a, b, wo, wg in samples:
        print(f"\n--- ch{c} {k}  行数 我们{a} vs 好人{b}  最宽 {wo} vs {wg}")
        print(f"  我们: {v[:150]!r}")
        print(f"  好人: {g[:150]!r}")


if __name__ == "__main__":
    main()
