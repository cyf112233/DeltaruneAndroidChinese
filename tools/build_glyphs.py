#!/usr/bin/env python3
"""
build_glyphs.py -- render EVERY glyph a font needs from Noto into one band, and
give the font a dedicated page holding nothing but that band.

Why everything, including ASCII: the previous builds kept the port's own Latin
bitmaps and re-pointed them into the new page.  Those bitmaps are full-cell
rectangles whose ink sits wherever the original drawing program put it, and
copying them around kept producing broken Latin and punctuation in game.  The
port's Latin is also not what we want visually next to Source Han hanzi, so this
script renders ASCII, punctuation and hanzi alike from one face, with one
baseline, into one clean 1-bit band.

Baseline, which was the real defect in every earlier attempt: a glyph must NOT be
centred by its own ink box.  Noto places 中 at y 5..19 from the draw origin and 一
at y 11..13 -- they share a baseline -- so centring each glyph independently
floats 一 to the middle of the cell while 口 sits on the baseline.  Every glyph is
therefore positioned by the distance from its ink bottom to the shared baseline.

Sizes: the five faces 好人汉化组 also ships use THEIR measured cell (CJK ink height
and full-width advance), so the Chinese reads at the same size as their patch.

Outputs per font in --outdir:
    page_ch<C>_<font>.png      the dedicated page (the band, nothing else)
    glyphs_ch<C>_<font>.json   [{c,x,y,w,h,shift,off}] absolute page coords
    meta_ch<C>_<font>.json     page size and counters

Usage: build_glyphs.py --chapter 5 --chars mt/need_ch5.txt
"""
import argparse, json, os, re, sys
from PIL import Image, ImageDraw, ImageFont

WORK = "/media/cyf112233/data/deltarune/work"
TTF = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
REF = "\u4e2d"                      # 中 -- full-height, sits on the baseline

# font -> (cjk ink height, cjk advance, latin cap height)
#
# 好人汉化组's own cells, measured from their ch5 patch (goodall/ch5/all_fonts.json):
#     fnt_ja_main        ink 17  adv 14      fnt_ja_mainbig   ink 33  adv 28
#     fnt_ja_dotumche    ink 20  adv 11      fnt_ja_kakugo    ink 25  adv 15
#     fnt_ja_8bit        ink 18  adv 16      fnt_ja_8bit_mixed ink 24 adv 20
#     fnt_ja_small       ink 15  adv  8      fnt_ja_tinynoelle ink 29 adv 16
#     fnt_ja_comicsans   ink 33  adv 30
# The faces 好人 left ASCII-only are scaled from fnt_ja_small's ratio (they are
# the same size class).  Reproducing these makes our Chinese match theirs rather
# than the port's larger Japanese cells.
# (cjk ink height, cjk advance, latin cap height).
#
# 好人汉化组's measured cells for the faces they ship -- both numbers matter, the
# advance is what spaces hanzi on the line:
#     ink  adv          ink  adv          ink  adv
#      15    8   small   17   14  main    18   16  8bit
#      20   11  dotum   24   20  8bit_m   25   15  kakugo
#      29   16  tinyn   33   28  mainbig  33   30  comicsans
# Faces 好人 left ASCII-only keep their measured ink height and take the advance
# implied by their own cell ratio, so hanging punctuation stays centred.
SPEC = {
    "fnt_main":             (17, 14, 16),
    "fnt_main_mono":        (17, 14, 16),
    "fnt_mainbig_mono":     (17, 14, 16),
    "fnt_main_mono_podium": (17, 14, 16),
    "fnt_mainbig":          (33, 28, 32),
    "fnt_dotumche":         (20, 11, 14),
    "fnt_tinynoelle":       (15,  8,  9),
    "fnt_small":            (15,  8,  8),
    "fnt_comicsans":        (19, 16, 15),   # 对话里用，按正文字号（原版 33 太大）
    "fnt_8bit":             (18, 16, 16),
    "fnt_legend":           (17, 14, 14),
    "fnt_ja_kakugo":        (25, 15, 25),
    "fnt_ja_8bit":          (18, 16, 18),
    "fnt_ja_8bit_mixed":    (24, 20, 24),
    "fnt_ja_legend":        (17, 14, 16),
    "fnt_ja_legend_alt":    (17, 14, 14),
}
# Non-ASCII codepoints 好人's faces carry that the port's own tables do not, so
# they have to come from us: middle dot, macron vowels, curly quotes, the Roman
# numeral three and the four arrows.
EXTRA_CODEPOINTS = [0xB7, 0x101, 0x113, 0x2014, 0x201C, 0x201D, 0x2162,
                    0x2190, 0x2191, 0x2192, 0x2193]

ALIAS_TARGET = {
    "fnt_ja_main": "fnt_main",
    "fnt_ja_mainbig": "fnt_mainbig",
    "fnt_dotumche_ja": "fnt_dotumche",
    "fnt_ja_dotumche": "fnt_dotumche",
    "fnt_ja_tinynoelle": "fnt_tinynoelle",
    "fnt_ja_small": "fnt_small",
    "fnt_ja_comicsans": "fnt_comicsans",
}
BAND_W = 2048
PAD = 2                 # breathing room between neighbouring tiles
# Global size trim applied to every target ink height.
SCALE = 0.8
# Hanzi cell: the ink fills the cell the way the port's own faces do, plus a fixed
# gap so the Chinese is not set solid.  The gap is a pixel measurement baked into
# the atlas, never a font parameter.
CJK_GAP = 3
# Extra blank column between a glyph's ink and its rectangle's right edge, so the
# engine cannot sample the neighbouring glyph.  Without it every character showed
# a stray white mark on its right.
INK_SAFETY = 1
# The measured offset is divided by this before it is drawn.
OFFSET_DIV = 2
# Headroom above the tallest ink inside a cell.
CELL_PAD_TOP = 1
# Latin letters, digits and symbols keep a narrow advance; only the horizontal ink
# offset is dropped, never the glyph's natural width.
LAT_GAP = 1
LAT_MIN_ADV = 4
SPACE = " "
BLANK = {0x00A0, 0x200B, 0xFEFF, 0x3000}


def spec_for(font, scale=None):
    """(cjk ink height, cjk advance, latin cap height), optionally scaled."""
    v = SPEC.get(font)
    if v is None:
        t = ALIAS_TARGET.get(font)
        v = SPEC.get(t) if t else None
    if v is None:
        return None
    k = SCALE if scale is None else scale
    cjk_h = max(3, round(v[0] * k))
    cjk_adv = max(3, round(v[1] * k))        # fallback only; ink decides
    # Latin and digits are set at three quarters of the hanzi ink height, which
    # keeps them clearly readable next to full-width Chinese.
    lat_h = max(3, round(cjk_h * 3 / 4))
    return (cjk_h, cjk_adv, lat_h)


def is_cjk(ch):
    """Anything that takes a full-width cell.

    That is Han and kana, CJK symbols and punctuation, AND the fullwidth forms
    block U+FF01-FF60 -- ，！？（）：； sit there, not next to the hanzi, and
    treating them as half-width gave them narrow advances and put them off the
    line.
    """
    o = ord(ch)
    return (0x2E80 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF
            or 0x3000 <= o <= 0x303F or 0xFF01 <= o <= 0xFF60
            or 0xFFE0 <= o <= 0xFFE6)


def is_symbol(ch):
    """ASCII punctuation and the symbol block: drawn on the text baseline."""
    o = ord(ch)
    return 0x21 <= o <= 0x2F or 0x3A <= o <= 0x40 or 0x5B <= o <= 0x60 \
        or 0x7B <= o <= 0x7E or o in (0xB7, 0xD7, 0x2014, 0x201C, 0x201D,
                                      0x2026, 0x2190, 0x2191, 0x2192, 0x2193)


def is_letter(ch):
    o = ord(ch)
    return 0x30 <= o <= 0x39 or 0x41 <= o <= 0x5A or 0x61 <= o <= 0x7A \
        or o in (0x101, 0x113, 0x2162)


def ink_box(ch, face):
    """Ink box of `ch` relative to the text draw origin."""
    bb = face.getbbox(ch)
    if bb is None or len(bb) != 4:
        return None
    if bb[2] - bb[0] <= 0 or bb[3] - bb[1] <= 0:
        return None
    return bb


# Characters Source Han only has as bare outlines (or not at all) render as a
# near-white smear that thresholds away to nothing, so the glyph ends up missing.
# Those are drawn from a halfwidth/as-is relative instead, scaled up to the cell.
FALLBACK = {"\uFF0F": "/", "\uFF3C": "\\", "\uFF5C": "|", "\uFF5E": "~",
            "\u301C": "~", "\uFFE0": "\u00A2", "\uFFE1": "\u00A3"}


def tile(ch, face, target_h=None):
    """1-bit ink-tight tile, plus how far its ink bottom sits ABOVE the draw
    origin (positive = above, because y grows downwards in the image but the
    origin is the pen position on the baseline).

    Characters Source Han only has as bare outlines (or not at all) rasterise to a
    near-white smear that thresholds away to nothing, so the glyph goes missing
    entirely -- \uFF0F was one of those.  Those are drawn from a substitute
    character at the size that gives the same ink height.
    """
    t, a, l = _tile_raw(ch, face)
    if t is None and ch in FALLBACK:
        fb = FALLBACK[ch]
        want = target_h if target_h else max(8, int(face.size * 0.9))
        try:
            big = ImageFont.truetype(TTF, point_for(want, fb))
            t2, a2, l2 = _tile_raw(fb, big)
        except Exception:
            t2 = None
        if t2 is not None:
            return t2, a2, l2
    return t, a, l


def _tile_raw(ch, face):
    bb = ink_box(ch, face)
    if bb is None:
        return None, 0, 0
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    big = Image.new("L", (w + 2, h + 2), 0)
    ImageDraw.Draw(big).text((1 - bb[0], 1 - bb[1]), ch, font=face, fill=255)
    big = big.point(lambda v: 255 if v >= 128 else 0)
    b = big.getbbox()
    if not b:
        return None, 0, 0
    # Ink bottom relative to the draw origin, in the ORIGINAL coordinate system.
    # The tile was pasted at (1 - bb[0], 1 - bb[1]), so inside the padded image
    # the ink bottom is at b[3]; mapping that back through the paste gives
    # b[3] + 1 - bb[1] BELOW the origin.  `above` is its negation, i.e. how far
    # the ink bottom sits above the origin.
    #
    # Getting this expression wrong is what made "certain characters sit at
    # different heights": a wrong `above` puts 一 and 。 roughly 15px off the
    # baseline the full-height hanzi use, while looking harmless for 中 and 口.
    # The tile was pasted at (1 - bb[0], 1 - bb[1]), so a padded-image row b[3]
    # corresponds to original coordinate b[3] + bb[1] - 1.  `above` is how far
    # that ink bottom sits above the pen point, which grows downwards, hence the
    # negation.  Verified empirically: 中/口/日 all give 22, 一 gives 14, and
    # English capitals 20 -- one shared baseline.
    ink_bottom_above_origin = (b[3] + bb[1] - 1)
    return big.crop(b), ink_bottom_above_origin, (b[0] + bb[0] - 1)


def point_for(target_h, ch="H", prefer_bigger=False):
    """Point size whose `ch` ink is closest to target_h.

    The ink height only takes integer values as the point size grows, so an exact
    hit is not always available.  `prefer_bigger` breaks a tie towards the larger
    face: at the top end (好人's ink 33, 25, 24) rounding down was losing 2px.
    """
    best = (10 ** 9, 10)
    for px in range(5, 90):
        f = ImageFont.truetype(TTF, px)
        bb = ink_box(ch, f)
        if bb is None:
            continue
        h = bb[3] - bb[1]
        d = abs(h - target_h)
        if d < best[0] or (d == best[0] and ((px > best[1]) if prefer_bigger else (px < best[1]))):
            best = (d, px)
    return best[1]


def build_band(font, chars, scale=None):
    """Give every glyph a tile of the SAME height, with the blank space above the
    ink drawn in.

    The rule, in the user's words: take the glyph's width and height offsets from
    the font, then THROW THE WIDTH OFFSET AWAY, and where the ink starts some
    distance below the top of the line, draw that many pixels of blank and the
    glyph underneath.  So a glyph whose ink top sits 20px down and is 2px tall
    becomes a 22px-tall tile that is 20px blank plus 2px of ink.

    The result is that every glyph is the same tall rectangle with its ink on one
    shared line, exactly like the game's own faces -- the glyph table shows only
    ink rectangles, but what the game samples is a uniform box, so 一 and 。 cannot
    look like they sit anywhere other than on that line.
    """
    cjk_h, cjk_adv, lat_h = spec_for(font, scale)
    f_cjk = ImageFont.truetype(TTF, point_for(cjk_h, REF, prefer_bigger=True))
    f_lat = ImageFont.truetype(TTF, point_for(lat_h))

    # ---- measure -----------------------------------------------------------
    # Rectangles are ONE CELL tall (like the port's own faces, where 中 一 三 。 A 1
    # are all 15x16), so the engine has a stable top edge to hang each glyph on.
    # Width is the glyph's own advance, so neighbouring rectangles never overlap.
    # The ink is drawn inside that rectangle: its bottom rests on the cell's
    # ink-bottom line, which lines every full-height glyph up and leaves the short
    # ones with their blank space above -- the "centred in the cell" look.
    tiles, above_of = {}, {}
    lost = 0
    for ch in chars:
        face = f_cjk if is_cjk(ch) else f_lat
        t, above, _left = tile(ch, face, target_h=cjk_h if is_cjk(ch) else lat_h)
        if t is None:
            lost += 1
            continue
        tiles[ch] = t
        above_of[ch] = above
    if not tiles:
        return None, [], 0, 0, 0, lost

    hanzi = [c for c in tiles if is_cjk(c)]
    ink_w = max((tiles[c].width for c in hanzi), default=cjk_adv)
    REF_H = max(above_of[c] + tiles[c].height for c in tiles)
    CELL_H = REF_H + CELL_PAD_TOP          # one cell tall
    CELL_W = max(cjk_adv, ink_w + CJK_GAP) # hanzi cell, for tracking

    lat_adv = max(LAT_MIN_ADV, round(lat_h * 0.6))
    x, y = 0, 0
    glyphs = []
    for ch in chars:
        if ch == SPACE:
            continue
        t = tiles.get(ch)
        if t is None:
            continue
        # ------------------------------------------------------------------
        # The engine samples a glyph through its rectangle, so the rectangle MUST
        # cover the ink AND stop before the next glyph's ink.  Since glyphs are
        # packed adjacently on the page, that means:
        #     advance >= ink width + a safety column
        # otherwise the right edge of every character picks up the first stroke of
        # its neighbour -- which is exactly the "stray white mark on the right of
        # every character" symptom.
        # ------------------------------------------------------------------
        # column width (= advance).  CJK keeps the fixed cell so tracking is even;
        # Latin takes its own ink plus a safety column.
        adv = CELL_W if is_cjk(ch) else max(lat_adv, t.width + LAT_GAP)
        if t.width + INK_SAFETY > adv:
            adv = t.width + INK_SAFETY
        # and make sure the PREVIOUS glyph's ink cannot reach into this column:
        # the column is only as wide as adv, so ink wider than adv would spill.
        if t.width > adv:
            adv = t.width
        if x + adv > BAND_W:
            x, y = 0, y + CELL_H
        # ink bottom on the cell's ink-bottom line
        bottom_in_cell = CELL_H - (REF_H - above_of[ch])
        top = y + bottom_in_cell - t.height
        glyphs.append({"c": ord(ch), "x": x, "y": y, "w": adv, "h": CELL_H,
                       "shift": adv, "off": 0, "row": y,
                       "ink_x": x, "ink_y": top, "ink_w": t.width, "ink_h": t.height,
                       "dy": bottom_in_cell - t.height})
        # each glyph owns its own column as wide as its advance, so no ink --
        # its own or a neighbour's -- can ever fall inside another glyph's window
        x += adv
    space_adv = max(3, CELL_W // 2)
    space_row = y + CELL_H
    glyphs.insert(0, {"c": 0x20, "x": 0, "y": space_row, "w": space_adv, "h": CELL_H,
                      "shift": space_adv, "off": 0, "row": space_row,
                      "ink_x": 0, "ink_y": space_row, "ink_w": 1, "ink_h": 1, "dy": 0})
    height = space_row + CELL_H + 2
    img = Image.new("RGBA", (BAND_W, height), (0, 0, 0, 0))
    for g in glyphs:
        if g["c"] == 0x20:
            continue
        t = tiles[chr(g["c"])]
        rgba = Image.new("RGBA", t.size, (255, 255, 255, 255))
        rgba.putalpha(t)
        img.paste(rgba, (g["ink_x"], g["ink_y"]), rgba)
    return img, glyphs, CELL_H, CELL_H, 0, lost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--chars", required=True)
    ap.add_argument("--fonts", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--scale", type=float, default=SCALE,
                    help=f"multiply every target ink height (default {SCALE})")
    a = ap.parse_args()
    C = a.chapter
    outdir = a.outdir or f"{WORK}/mt/gl{C}"
    os.makedirs(outdir, exist_ok=True)

    spec = json.load(open(f"{WORK}/fontsrc/ch{C}/font_spec.json"))
    index = {f["name"]: f for f in spec["fonts"]}
    fonts = a.fonts.split(",") if a.fonts else [n for n in index if spec_for(n)]
    need = [ch for ch in open(a.chars, encoding="utf-8").read()
            if ord(ch) >= 0x21 and ord(ch) not in BLANK]
    # every printable ASCII character, because the UI draws symbols the dialogue
    # text never mentions ("*", arrows, brackets), plus 好人's extra codepoints
    need = sorted(set(need)
                  | {chr(c) for c in range(0x21, 0x7F)}
                  | {SPACE}
                  | {chr(c) for c in EXTRA_CODEPOINTS}, key=ord)
    print(f"ch{C}: {len(fonts)} fonts, {len(need)} codepoints (text + full ASCII)")

    for font in fonts:
        fi = index[font]
        # everything the text needs, plus every codepoint the font already had
        # that the text might reach through a placeholder
        have = {chr(g["c"]) for g in fi["glyphs"] if 0x21 <= g["c"] <= 0x2E7F}
        chars = sorted(set(need) | have | {SPACE} | {chr(c) for c in range(0x21, 0x7F)},
                       key=ord)
        img, glyphs, baseline, cell, wide, lost = build_band(font, chars, a.scale)
        img.save(f"{outdir}/page_ch{C}_{font}.png")
        json.dump(glyphs, open(f"{outdir}/glyphs_ch{C}_{font}.json", "w", encoding="utf-8"),
                  ensure_ascii=False)
        meta = {"font": font, "page": list(img.size), "baseline": baseline,
                "cell": cell, "glyphs": len(glyphs), "wide": wide, "lost": lost}
        json.dump(meta, open(f"{outdir}/meta_ch{C}_{font}.json", "w", encoding="utf-8"),
                  ensure_ascii=False)
        cjk = sum(1 for g in glyphs if is_cjk(chr(g["c"])))
        print(f"  {font:24s} cell={cell:3d} baseline={baseline:3d} page={img.size[0]}x{img.size[1]} "
              f"glyphs={len(glyphs):5d} (cjk {cjk}, latin {len(glyphs)-cjk}) wide={wide} lost={lost}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
