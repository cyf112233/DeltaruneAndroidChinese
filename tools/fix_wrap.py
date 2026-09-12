#!/usr/bin/env python3
"""fix_wrap.py -- 按好人汉化组的换行结构校正我们的 lang_en.json。

三类问题（只对照好人是中文的条目）：
  A 前后缀换行不同   —— 菜单/选项靠行首换行对齐，丢了会整体上移一行
  B 中段行数不同     —— 合并/拆分到行数一致
  C 单行超过 264px   —— 引擎会自动换行并补 "*"，位置不受控，提前拆掉
换行符原样保留（引擎里 `&` 和真换行完全等价，见 obj_writer_Draw_0 第 235 行）。

用法： fix_wrap.py [--apply]
"""
import json, os, re, shutil, sys

W = "/media/cyf112233/data/deltarune/work"
PC = "/media/cyf112233/data/steamgames/steamapps/common/DELTARUNE"
LIMIT = 33 * 8          # 引擎换行宽度 = charline(33) × hspace(8)
RESERVE = 16            # 续行前引擎自动补 "* "，引擎自己按 hspace*2 = 16px 算
CTRL = re.compile(r"\\[A-Za-z][0-9]?|\^[0-9]+|~[0-9]?")
# 终止符本身不占宽，但它前面的空格占宽（引擎照样计入），所以空格留在正文里
TERM = re.compile(r"(?:/|%|%%|/%)(\s*)$")
SPLIT_RE = re.compile(r"[&\n]")
SEP_RE = re.compile(r"[&\n]")
GOODBRK = "。！？，、；：）」』…—"


def split_term(v):
    m = TERM.search(v)
    if not m:
        return v, ""
    return v[:m.start()], v[m.start():]


def atoms(s):
    out, i, buf = [], 0, ""
    while i < len(s):
        m = CTRL.match(s, i)
        if m:
            buf += m.group()
            i = m.end()
            continue
        out.append((buf + s[i], s[i]))
        buf = ""
        i += 1
    if buf:
        out.append((buf, ""))
    return out


def width(line, adv):
    return sum(adv.get(ord(ch), 12) for _, ch in atoms(line) if ch)


def parse(s):
    return SPLIT_RE.split(s), SEP_RE.findall(s)


def render(parts, seps):
    out = parts[0] if parts else ""
    for i, p in enumerate(parts[1:]):
        out += (seps[i] if i < len(seps) else "&") + p
    return out


def split_once(line, adv, limit, hard=False):
    at = atoms(line)
    acc, best, furthest = 0, None, None
    for i, (_, ch) in enumerate(at):
        if ch:
            acc += adv.get(ord(ch), 12)
        if acc > limit:
            break
        if ch:
            furthest = i + 1          # 兜底：任何一个字后面都能断
        if ch and (ch in GOODBRK or ch == " "):
            best = i + 1
    if best is None and hard:
        best = furthest                # 找不到标点/空格就在字间断（引擎自己也是这么断的）
    if best is None or best >= len(at):
        return None
    a = "".join(t for t, _ in at[:best]).rstrip(" ")
    b = "".join(t for t, _ in at[best:]).lstrip(" ")
    if not a or not b:
        return None
    return [a, b]


def avail(i, has_aster=True):
    """第 i 行可用宽度。

    接在换行后面的行，引擎会先补 "* "（hspace*2 = 16px），所以要留位置；
    但整条文本里没有 "*" 时 aster 一直是 0，引擎不会补，可用宽度就是满的 264。
    """
    return LIMIT - (RESERVE if (i > 0 and has_aster) else 0)


def merge_at(parts, seps, i):
    return parts[:i] + [parts[i] + parts[i + 1].lstrip(" ")] + parts[i + 2:], seps[:i] + seps[i + 1:]


def cut_at(parts, seps, i, adv, limit, hard=False):
    two = split_once(parts[i], adv, limit, hard)
    if not two:
        return None
    sep = seps[i] if i < len(seps) else "&"
    return parts[:i] + two + parts[i + 1:], seps[:i] + [sep] + seps[i:]


def main():
    apply = "--apply" in sys.argv
    tally = {"A 前后缀": 0, "B 中段行数": 0, "C 超宽拆分": 0, "C 超宽拆分(无对照)": 0,
             "C 行尾空格": 0, "拆不动": 0}
    ref = 0
    for c in "12345":
        adv = {g["c"]: g["shift"] for g in
               json.load(open(f"{W}/mt/gl{c}/glyphs_ch{c}_fnt_main.json", encoding="utf-8"))}
        ours_p = f"{W}/out/ch{c}_lang/lang_en.json"
        ours = json.load(open(ours_p, encoding="utf-8"))
        good = json.load(open(f"{PC}/chapter{c}_windows/lang/lang_en.json", encoding="utf-8"))
        changed = 0
        for k, v in list(ours.items()):
            if not isinstance(v, str) or not any("\u4e00" <= ch <= "\u9fff" for ch in v):
                continue
            g = good.get(k)
            if not isinstance(g, str) or not any("\u4e00" <= ch <= "\u9fff" for ch in g):
                continue
            ref += 1
            body, term = split_term(v)
            gbody, _ = split_term(g)

            # ---- A 前后缀换行：菜单对齐靠它 ----
            lm_o = re.match(r"^[&\n]*", body).group()
            tm_o = re.search(r"[&\n]*$", body).group()
            lm_g = re.match(r"^[&\n]*", gbody).group()
            tm_g = re.search(r"[&\n]*$", gbody).group()
            core = body[len(lm_o):len(body) - len(tm_o)]
            if (lm_o, tm_o) != (lm_g, tm_g):
                tally["A 前后缀"] += 1
            gcore = gbody[len(lm_g):len(gbody) - len(tm_g)]

            # 只看"内层"行数：前后缀换行由 A 单独负责，别在这儿又被合并回去
            has_aster = "*" in core
            parts, seps = parse(core)
            gparts = [x for x in SPLIT_RE.split(gcore) if x.strip() != ""]
            want = len(gparts)

            # ---- B 中段行数：向好人看齐 ----
            before = len(parts)
            guard = 0
            while len(parts) < want and guard < 8:
                guard += 1
                i = max(range(len(parts)), key=lambda j: width(parts[j], adv))
                r = cut_at(parts, seps, i, adv, LIMIT - RESERVE)
                if not r:
                    break
                parts, seps = r
            guard = 0
            while len(parts) > want and guard < 20:
                guard += 1
                done = False
                for i in range(len(parts) - 1):
                    cand = parts[i] + parts[i + 1].lstrip(" ")
                    if width(cand, adv) <= avail(i, has_aster):
                        parts, seps = merge_at(parts, seps, i)
                        done = True
                        break
                if not done:
                    break
            if len(parts) != before:
                tally["B 中段行数"] += 1
            parts = [p for p in parts if p.strip() != ""] or [""]
            seps = (seps + ["&"] * len(parts))[:max(0, len(parts) - 1)]

            # ---- C 超宽：必须拆，否则引擎自己乱换 ----
            guard = 0
            while guard < 12:
                guard += 1
                wide = [i for i, l in enumerate(parts) if width(l, adv) > avail(i, has_aster)]
                if not wide:
                    break
                i = wide[0]
                # 先试最省事的：行尾多余的空格（看不见，但引擎算 6px）
                stripped = parts[i].rstrip(" ")
                if stripped != parts[i] and width(stripped, adv) <= avail(i):
                    parts[i] = stripped
                    tally["C 行尾空格"] += 1
                    continue
                r = cut_at(parts, seps, i, adv, avail(i, has_aster), True)
                if not r:
                    tally["拆不动"] += 1
                    break
                parts, seps = r
                tally["C 超宽拆分"] += 1

            new = lm_g + render(parts, seps) + tm_g + term
            if new != v:
                ours[k] = new
                changed += 1
        # ---- 没有好人对照的中文条目：只修超宽 ----
        for k, v in list(ours.items()):
            if not isinstance(v, str) or not any("\u4e00" <= ch <= "\u9fff" for ch in v):
                continue
            g = good.get(k)
            if isinstance(g, str) and any("\u4e00" <= ch <= "\u9fff" for ch in g):
                continue                      # 上面已经处理过
            body, term = split_term(v)
            has_aster = "*" in body
            parts, seps = parse(body)
            guard = 0
            while guard < 12:
                guard += 1
                wide = [i for i, l in enumerate(parts) if width(l, adv) > avail(i, has_aster)]
                if not wide:
                    break
                i = wide[0]
                stripped = parts[i].rstrip(" ")
                if stripped != parts[i] and width(stripped, adv) <= avail(i):
                    parts[i] = stripped
                    tally["C 行尾空格"] += 1
                    continue
                r = cut_at(parts, seps, i, adv, avail(i, has_aster), True)
                if not r:
                    tally["拆不动"] += 1
                    break
                parts, seps = r
                tally["C 超宽拆分(无对照)"] += 1
            new = render(parts, seps) + term
            if new != v:
                ours[k] = new
                changed += 1
        if apply:
            shutil.copy2(ours_p, f"{W}/out/lang_backup_ch{c}.json")
            with open(ours_p, "w", encoding="utf-8") as f:
                json.dump(ours, f, ensure_ascii=False, indent=0)
        print(f"ch{c}: 改动 {changed} 条")
    print(f"\n对照好人中文条目 {ref}")
    for k, n in tally.items():
        print(f"  {k}: {n}")
    print("（仅统计，未写盘）" if not apply else "已写回 out/chN_lang/lang_en.json（原件备份在 out/lang_backup_chN.json）")


if __name__ == "__main__":
    main()
