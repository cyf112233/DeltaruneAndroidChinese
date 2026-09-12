#!/usr/bin/env python3
"""
rewrap.py -- make the translated lines fit the box the game actually gives them.

The dialogue writer wraps on PIXELS: a line is broken once
`current_line_width + char_width > charline * hspace`.  With the default
`charline = 33` and `hspace = 8` that is 264px, and because a Han glyph advances
16px where the original Latin advanced ~8px, only ~16 Han fit on a line where the
English fitted 33 characters.  Our text was translated line-for-line against the
source's own breaks, so many lines are far too wide: the game then wraps them
itself, and because `aster` is set by a leading "*" it also AUTO-INSERTS a "*" at
the start of every line it wraps -- which is what "开头换行" and "开头的*之后就换行"
look like on screen.

This script re-breaks those lines so the game never has to:
  * only lines that exceed the limit are touched, so short lines and every
    hand-placed break (menu choices, name entry, dramatic three-liners) are kept;
  * control codes (\\E \\M \\F \\C \\I \\T \\S \\c, ^n, ~n, ..., ) cost no width;
  * a break is preferred after Chinese punctuation (，。、！？：；）】》」…) and
    never placed immediately before closing punctuation or after an opening one;
  * a break is never placed between a placeholder (\\Cn / ~n) and its text, and
    never in the middle of an ASCII word;
  * a line that would end up a single orphan character is pulled back.

Usage:
    rewrap.py --chapter 5                 # report only
    rewrap.py --chapter 5 --apply         # write out/ch5_lang/lang_en.json

Re-run this whenever the font advance changes: the numbers above are read off the
built atlas, and a stale value here is exactly what leaves the game wrapping text
a second time (which also auto-inserts a "*" at the start of each wrapped line).
"""
import argparse, json, os, re, sys

WORK = "/media/cyf112233/data/deltarune/work"
HSPACE = 8              # px per character-cell in the writer
CHARLINE = 33           # default charline of obj_writer
LIMIT_PX = CHARLINE * HSPACE          # 264

# tokens that cost no width at all
CTRL = re.compile(r'\\[A-Za-z][0-9]?|[\^~][0-9]+')
# Chinese punctuation that may end a line
BREAK_AFTER = "，。、！？：；）】》」』…—～"
# punctuation that must never start a line
NO_LINE_START = "，。、！？：；）】》」』…—～％"
# punctuation that must never end a line
NO_LINE_END = "（【《「『"


# Advances must match what the built fonts actually report, or the game wraps
# again on top of our breaks.  Measured from the built atlas:
#   hanzi / full-width punctuation : 17px
#   Latin letters and digits       : 3..12px, median 8
# and the writer's own limit is still charline * hspace = 33 * 8 = 264px, so only
# 264 // 17 = 15 hanzi fit on a line.
CJK_ADV = 17
LAT_ADV = 8


def cell_px(ch):
    if ch == " ":
        return LAT_ADV // 2
    return CJK_ADV if ord(ch) > 0x2E7F else LAT_ADV


def tokens(seg):
    """Split into (text, width) tokens; control codes are zero width."""
    out, i = [], 0
    while i < len(seg):
        m = CTRL.match(seg, i)
        if m:
            out.append((m.group(0), 0))
            i = m.end()
        else:
            out.append((seg[i], cell_px(seg[i])))
            i += 1
    return out


def width(seg):
    """Drawn width of a line.

    Trailing whitespace, and the terminator run (/ % %%), are not drawn: the
    writer consumes them as control (a trailing space only sets `remspace`, which
    is where it *may* wrap).  Counting them made lines look over-long and
    produced pointless wraps such as "...罢了...！ \n/%".
    """
    toks = tokens(seg)
    end = len(toks)
    while end > 0 and (toks[end - 1][0].isspace() or toks[end - 1][0] in "/%"):
        end -= 1
    return sum(w for _, w in toks[:end])


def visible(seg):
    return CTRL.sub("", seg)


def best_break(toks, limit):
    """Index to split `toks` at, so the left side is as full as possible."""
    best = None
    acc = 0
    for i, (t, w) in enumerate(toks):
        if acc + w > limit:
            break
        acc += w
        # a break here means toks[i] ends the line and toks[i+1] starts the next
        if i + 1 >= len(toks):
            break
        nxt = toks[i + 1][0]
        cur = t
        if cur and cur[0] == "\\":
            continue                      # never split right after a control code
        if nxt and nxt[0] == "\\":
            continue                      # nor right before one
        if t == " ":
            best = i
            continue
        if t in BREAK_AFTER:
            best = i
            continue
        if nxt in NO_LINE_START:
            continue
        if cur in NO_LINE_END:
            continue
        if best is None:
            best = i                      # first legal spot if nothing better
    return best


def rewrap_segment(seg, limit):
    """Return [seg] unchanged if it fits, else a list of lines that do."""
    if width(seg) <= limit:
        return [seg]
    lines = []
    rest = seg
    guard = 0
    while width(rest) > limit and guard < 40:
        guard += 1
        toks = tokens(rest)
        i = best_break(toks, limit)
        if i is None:
            break
        left = "".join(t for t, _ in toks[:i + 1])
        rest = "".join(t for t, _ in toks[i + 1:])
        # an orphan single visible character is ugly; pull it back when possible
        if len(visible(left).strip()) <= 1 and lines:
            break
        lines.append(left)
    lines.append(rest)
    return lines


def rewrap_text(v, limit):
    """Re-break each existing line of one value. Keeps the break characters."""
    # split on newlines / & but remember which separator was used
    parts = re.split(r'([\n&])', v)
    out = []
    for part in parts:
        if part in ("\n", "&"):
            out.append(part)
            continue
        segs = rewrap_segment(part, limit)
        out.append("\n".join(segs))
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--limit", type=int, default=LIMIT_PX,
                    help=f"max line width in px (default {LIMIT_PX})")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    path = f"{WORK}/out/ch{a.chapter}_lang/lang_en.json"
    d = json.load(open(path, encoding="utf-8"))
    changed = 0
    examples = []
    for k, v in d.items():
        if not isinstance(v, str) or k == "date":
            continue
        nv = rewrap_text(v, a.limit)
        if nv != v:
            changed += 1
            if len(examples) < 6:
                examples.append((k, v, nv))
            d[k] = nv
    print(f"ch{a.chapter}: limit={a.limit}px  改写 {changed} 条")
    for k, v, nv in examples:
        print(f"  {k[:40]}")
        print(f"    旧={v[:66]!r}")
        print(f"    新={nv[:66]!r}")
    still = sum(1 for k, v in d.items()
                if isinstance(v, str) and k != "date"
                and any(width(s) > a.limit for s in re.split(r'[\n&]', v)))
    print(f"  仍超宽的行: {still}")
    if a.apply:
        json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  -> 已写回 {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
