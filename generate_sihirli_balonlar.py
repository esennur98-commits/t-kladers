#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tıkladers — "Sihirli Balonlar" oyunu üretici (v2 — katmanlı).

Her görsel öğe ayrı bir HTML elemanı olarak üretilir (metinler gerçek metin,
her balon dilimi / mat karesi / kart ayrı şekil) — Canva içe aktarımında her
biri ayrı, düzenlenebilir katman olur.

Mekanik: pastel gökyüzü mozaiği (6x7) + balon/uçurtma pencereli şablonlar.
Her hedefin matta TAM BİR konumu vardır (tekillik betikte doğrulanır).
"""
import random

PAGE_W, PAGE_H = 794, 1123
CELL = 100
COLS, ROWS = 6, 7
PALETTE = {
    "pembe":   "#F9A8C9",
    "lila":    "#C3A6E8",
    "mint":    "#A8E6CF",
    "mavi":    "#A3D8F4",
    "sari":    "#FFE29A",
    "seftali": "#FFC49B",
    "mercan":  "#FF9AA2",
}
COLORS = list(PALETTE.values())
INK = "#4A4A68"
DASH = "#7FB8E6"
BASKET = "#C9A227"
BASKET_D = "#8B6F5E"
HOLE = "#EFEFEF"
FONT = "'Comic Sans MS','Chalkboard SE','Trebuchet MS',sans-serif"

# ---------------------------------------------------------------- mat üretimi
def build_mat(seed):
    rng = random.Random(seed)
    grid = [[None] * COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            banned = set()
            if r > 0: banned.add(grid[r - 1][c])
            if c > 0: banned.add(grid[r][c - 1])
            grid[r][c] = rng.choice([x for x in COLORS if x not in banned])
    return grid

def pick_targets(grid, rng):
    pairs = {}
    for r in range(ROWS - 1):
        for c in range(COLS):
            pairs.setdefault((grid[r][c], grid[r + 1][c]), []).append((r, c))
    uniq_pairs = [k for k, v in pairs.items() if len(v) == 1]
    quads = {}
    for r in range(ROWS - 1):
        for c in range(COLS - 1):
            t = (grid[r][c], grid[r][c + 1], grid[r + 1][c], grid[r + 1][c + 1])
            quads.setdefault(t, []).append((r, c))
    uniq_quads = [k for k, v in quads.items() if len(v) == 1]
    if len(uniq_pairs) < 6 or len(uniq_quads) < 12:
        return None
    rng.shuffle(uniq_pairs); rng.shuffle(uniq_quads)
    easy = [(k, pairs[k][0]) for k in uniq_pairs[:6]]
    med  = [(k, quads[k][0]) for k in uniq_quads[:6]]
    kite = [(k, quads[k][0]) for k in uniq_quads[6:12]]
    return easy, med, kite

seed = 0
while True:
    grid = build_mat(seed)
    res = pick_targets(grid, random.Random(seed + 999))
    if res: break
    seed += 1
easy_t, med_t, kite_t = res
print(f"seed={seed}  kolay={len(easy_t)} orta={len(med_t)} ucurtma={len(kite_t)}")

# ---------------------------------------------------------------- temel öğeler
def D(x, y, w, h, style, inner=""):
    return (f'<div style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;'
            f'width:{w:.0f}px;height:{h:.0f}px;{style}">{inner}</div>')

def SVG(x, y, w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'style="position:absolute;left:{x:.0f}px;top:{y:.0f}px" '
            f'width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}">{body}</svg>')

def TXT(x, y, w, size, color, text, weight=800, align="center"):
    return D(x, y, w, size * 1.6,
             f'font-size:{size}px;font-weight:{weight};color:{color};'
             f'text-align:{align};line-height:{size*1.5:.0f}px', text)

def cloud(x, y, s=1.0, op=0.9):
    w, h = 160 * s, 60 * s
    return SVG(x - w / 2, y - h / 2, w, h,
               f'<g fill="#FFFFFF" opacity="{op}">'
               f'<ellipse cx="{80*s}" cy="{26*s}" rx="{46*s}" ry="{26*s}"/>'
               f'<ellipse cx="{46*s}" cy="{34*s}" rx="{30*s}" ry="{18*s}"/>'
               f'<ellipse cx="{114*s}" cy="{34*s}" rx="{30*s}" ry="{18*s}"/></g>')

def logo(cx=PAGE_W / 2, top=16):
    out = D(cx - 42, top, 84, 60,
            f'background:#fff;border:2.5px solid {INK};border-radius:6px')
    out += TXT(cx - 42, top + 2, 84, 15, INK, "TIK")
    out += TXT(cx - 42, top + 19, 84, 15, "#E85D75", "-LA-")
    out += TXT(cx - 42, top + 36, 84, 15, INK, "DERS")
    out += SVG(cx + 26, top + 40, 26, 26,
               f'<path d="M 4 2 l 10 12 l 3 -6 l 7 -1 z" fill="{INK}"/>')
    return out

def face(cx, cy, s=1.0):
    out = SVG(cx - 30 * s, cy - 12 * s, 60 * s, 34 * s,
              f'<g fill="{INK}"><circle cx="{14*s}" cy="{8*s}" r="{4.5*s}"/>'
              f'<circle cx="{46*s}" cy="{8*s}" r="{4.5*s}"/></g>'
              f'<path d="M {20*s} {18*s} Q {30*s} {28*s} {40*s} {18*s}" '
              f'stroke="{INK}" stroke-width="{3.5*s}" fill="none" stroke-linecap="round"/>')
    for dx in (-26, 26):
        out += D(cx + dx * s - 6 * s, cy + 6 * s - 6 * s, 12 * s, 12 * s,
                 "background:#FF9AA2;border-radius:50%;opacity:0.55")
    return out

QUARTER_PATHS = {
    "tl": lambda r: f'M {r} {r} L {r} 0 A {r} {r} 0 0 0 0 {r} Z',
    "tr": lambda r: f'M 0 {r} L 0 0 A {r} {r} 0 0 1 {r} {r} Z',
    "bl": lambda r: f'M {r} 0 L 0 0 A {r} {r} 0 0 0 {r} {r} Z',
    "br": lambda r: f'M 0 0 L {r} 0 A {r} {r} 0 0 1 0 {r} Z',
}
QUARTER_POS = {"tl": (-1, -1), "tr": (0, -1), "bl": (-1, 0), "br": (0, 0)}

def big_balloon(cx, cy, tl, tr, bl, br, s=1.0, with_face=False):
    """Zarf merkezi (cx, cy-30s); her dilim ayrı katman."""
    r = 62 * s
    ex, ey = cx, cy - 30 * s
    out = ""
    for q, col in zip(("tl", "tr", "bl", "br"), (tl, tr, bl, br)):
        ox, oy = QUARTER_POS[q]
        out += SVG(ex + ox * r, ey + oy * r, r, r,
                   f'<path d="{QUARTER_PATHS[q](r)}" fill="{col}"/>')
    sw = max(2.5, 3.5 * s)
    pad = sw + 1
    box = 2 * r + 2 * pad
    out += SVG(ex - r - pad, ey - r - pad, box, box,
               f'<circle cx="{r+pad}" cy="{r+pad}" r="{r}" fill="none" stroke="{INK}" stroke-width="{sw}"/>'
               f'<line x1="{pad}" y1="{r+pad}" x2="{2*r+pad}" y2="{r+pad}" stroke="{INK}" stroke-width="{sw*0.6}"/>'
               f'<line x1="{r+pad}" y1="{pad}" x2="{r+pad}" y2="{2*r+pad}" stroke="{INK}" stroke-width="{sw*0.6}"/>')
    out += SVG(cx - 34 * s, cy + 22 * s, 68 * s, 30 * s,
               f'<line x1="0" y1="0" x2="{14*s}" y2="{30*s}" stroke="{INK}" stroke-width="{2.5*s}"/>'
               f'<line x1="{68*s}" y1="0" x2="{54*s}" y2="{30*s}" stroke="{INK}" stroke-width="{2.5*s}"/>')
    out += D(cx - 24 * s, cy + 52 * s, 48 * s, 34 * s,
             f'background:{BASKET};border:{max(2, 3*s):.0f}px solid {BASKET_D};'
             f'border-radius:{7*s:.0f}px')
    if with_face:
        out += face(ex, ey, s * 0.9)
    return out

def small_balloon(cx, cy, top, bottom, s=1.0):
    out = D(cx - 46 * s, cy - 84 * s, 92 * s, 92 * s,
            f'background:{top};border:{max(2.5, 3.5*s):.1f}px solid {INK};border-radius:50%')
    out += D(cx - 28 * s, cy - 62 * s, 24 * s, 16 * s,
             "background:#fff;border-radius:50%;opacity:0.5")
    out += SVG(cx - 22 * s, cy + 2 * s, 44 * s, 32 * s,
               f'<line x1="0" y1="0" x2="{5*s}" y2="{32*s}" stroke="{INK}" stroke-width="{2.5*s}"/>'
               f'<line x1="{44*s}" y1="0" x2="{39*s}" y2="{32*s}" stroke="{INK}" stroke-width="{2.5*s}"/>')
    out += D(cx - 26 * s, cy + 34 * s, 52 * s, 42 * s,
             f'background:{bottom};border:{max(2.5, 3.5*s):.1f}px solid {INK};'
             f'border-radius:{8*s:.0f}px')
    return out

KITE_PATHS = {
    "tl": lambda r: f'M {r} 0 L {r} {r} L 0 {r} Z',
    "tr": lambda r: f'M 0 0 L {r} {r} L 0 {r} Z',
    "bl": lambda r: f'M 0 0 L {r} 0 L {r} {r} Z',
    "br": lambda r: f'M 0 0 L {r} 0 L 0 {r} Z',
}

def kite(cx, cy, tl, tr, bl, br, s=1.0):
    r = 62 * s
    out = ""
    for q, col in zip(("tl", "tr", "bl", "br"), (tl, tr, bl, br)):
        ox, oy = QUARTER_POS[q]
        out += SVG(cx + ox * r, cy + oy * r, r, r,
                   f'<path d="{KITE_PATHS[q](r)}" fill="{col}"/>')
    sw = max(2.5, 3.5 * s)
    pad = sw + 1
    box = 2 * r + 2 * pad
    out += SVG(cx - r - pad, cy - r - pad, box, box,
               f'<path d="M {r+pad} {pad} L {2*r+pad} {r+pad} L {r+pad} {2*r+pad} L {pad} {r+pad} Z" '
               f'fill="none" stroke="{INK}" stroke-width="{sw}"/>'
               f'<line x1="{r+pad}" y1="{pad}" x2="{r+pad}" y2="{2*r+pad}" stroke="{INK}" stroke-width="{sw*0.55}"/>'
               f'<line x1="{pad}" y1="{r+pad}" x2="{2*r+pad}" y2="{r+pad}" stroke="{INK}" stroke-width="{sw*0.55}"/>')
    out += SVG(cx - 5 * s, cy + r, 30 * s, 44 * s,
               f'<path d="M {5*s} 0 Q {19*s} {22*s} {9*s} {40*s}" stroke="{INK}" '
               f'stroke-width="{2.5*s}" fill="none"/>')
    out += SVG(cx + 6 * s, cy + r + 10 * s, 12 * s, 10 * s,
               f'<path d="M 0 {8*s} l {10*s} -{8*s} l 0 {10*s} z" fill="#FF9AA2" '
               f'stroke="{INK}" stroke-width="1.5"/>')
    out += SVG(cx + 0 * s, cy + r + 28 * s, 12 * s, 10 * s,
               f'<path d="M 0 {8*s} l {10*s} -{8*s} l 0 {10*s} z" fill="#A3D8F4" '
               f'stroke="{INK}" stroke-width="1.5"/>')
    return out

def card_frame(x, y, w, h):
    out = D(x - 8, y - 8, w + 16, h + 16,
            f'border:2.5px dashed {DASH};border-radius:18px')
    out += D(x, y, w, h, f'background:#FFFFFF;border:2px solid {INK};border-radius:14px')
    return out

def badge(x, y, num, color):
    return D(x, y, 38, 38,
             f'background:{color};border-radius:50%;color:#fff;font-size:20px;'
             'font-weight:800;text-align:center;line-height:38px', str(num))

def scissors(x, y):
    return SVG(x - 14, y - 11, 28, 22,
               f'<g stroke="{INK}" stroke-width="2" fill="none">'
               '<circle cx="6" cy="17" r="4"/><circle cx="6" cy="5" r="4"/>'
               '<line x1="9" y1="15" x2="26" y2="4"/><line x1="9" y1="7" x2="26" y2="18"/></g>')

def page(pid, label, elements):
    return (f'<div data-document-role="page" data-label="{label}" '
            f'style="position:relative;width:{PAGE_W}px;height:{PAGE_H}px;'
            f'overflow:hidden;font-family:{FONT}">'
            + "".join(elements) + '</div>')

def sky():
    return D(0, 0, PAGE_W, PAGE_H,
             "background:linear-gradient(180deg,#CDE9FF 0%,#E9F6FF 60%,#FFF3F8 100%)")

pages = []

# ------------------------------------------------------------------ 1. kapak
els = [sky(), logo()]
els += [cloud(120, 200, 1.2), cloud(660, 260, 1.0, 0.8),
        cloud(90, 640, 0.9, 0.8), cloud(700, 700, 1.3)]
els.append(TXT(0, 120, PAGE_W, 60, INK, "Sihirli Balonlar"))
els.append(TXT(0, 196, PAGE_W, 25, "#E85D75", "Kes &#8226; Kaydır &#8226; Eşleştir", 700))
els.append(big_balloon(PAGE_W / 2, 560, PALETTE["pembe"], PALETTE["mavi"],
                       PALETTE["sari"], PALETTE["mint"], s=3.2, with_face=True))
els.append(kite(160, 880, PALETTE["mercan"], PALETTE["sari"],
                PALETTE["mavi"], PALETTE["lila"], s=0.8))
els.append(small_balloon(650, 900, PALETTE["lila"], PALETTE["seftali"], s=0.9))
els.append(D(PAGE_W / 2 - 150, 1020, 300, 52,
             f'background:#fff;border:2.5px solid {INK};border-radius:26px'))
els.append(TXT(PAGE_W / 2 - 150, 1030, 300, 23, INK, "3 - 8 yaş", 700))
pages.append(page(1, "Kapak", els))

# ------------------------------------------------------------------ 2. mat
els = [sky(), logo()]
els.append(TXT(0, 92, PAGE_W, 29, INK, "Gökyüzü Matı"))
mx, my = (PAGE_W - COLS * CELL) / 2, 150
els.append(D(mx - 16, my - 16, COLS * CELL + 32, ROWS * CELL + 32,
             f'background:#FFFFFF;border:3px solid {INK};border-radius:20px'))
for r in range(ROWS):
    for c in range(COLS):
        els.append(D(mx + c * CELL + 2, my + r * CELL + 2, CELL - 4, CELL - 4,
                     f'background:{grid[r][c]};border-radius:10px'))
els += [cloud(90, 1010, 0.8), cloud(700, 1030, 1.0)]
els.append(TXT(0, 1016, PAGE_W, 19, INK,
               "Bu sayfayı kesmeyin — pencereyi üzerinde kaydırın!", 600))
pages.append(page(2, "Gökyüzü Matı", els))

# ------------------------------------------------------------------ 3. pencereler
els = [sky(), logo()]
els.append(TXT(0, 92, PAGE_W, 29, INK, "Sihirli Pencereler"))
# küçük balon penceresi — kart (70,170) 220x280
els.append(card_frame(70, 170, 220, 280))
els.append(TXT(70, 190, 220, 17, INK, "Küçük Balon", 700))
els.append(D(70 + 60, 170 + 70, 100, 100,
             f'background:{HOLE};border:2px dashed #999;border-radius:50%'))
els.append(SVG(70 + 85, 170 + 163, 50, 27,
               f'<line x1="0" y1="0" x2="5" y2="27" stroke="{INK}" stroke-width="2.5"/>'
               f'<line x1="50" y1="0" x2="45" y2="27" stroke="{INK}" stroke-width="2.5"/>'))
els.append(D(70 + 75, 170 + 190, 70, 60,
             f'background:{HOLE};border:2px dashed #999;border-radius:8px'))
els.append(scissors(70 + 110, 170 + 120))
els.append(scissors(70 + 110, 170 + 220))
# büyük balon penceresi — kart (330,170) 290x310
els.append(card_frame(330, 170, 290, 310))
els.append(TXT(330, 190, 290, 17, INK, "Büyük Balon", 700))
els.append(D(330 + 45, 170 + 50, 200, 200,
             f'background:{HOLE};border:2px dashed #999;border-radius:50%'))
els.append(SVG(330 + 95, 170 + 237, 100, 25,
               f'<line x1="0" y1="0" x2="20" y2="25" stroke="{INK}" stroke-width="2.5"/>'
               f'<line x1="100" y1="0" x2="80" y2="25" stroke="{INK}" stroke-width="2.5"/>'))
els.append(D(330 + 117, 170 + 258, 56, 30,
             f'background:{BASKET};border:2.5px solid {BASKET_D};border-radius:7px'))
els.append(scissors(330 + 145, 170 + 150))
# uçurtma penceresi — kart (70,530) 290x290
els.append(card_frame(70, 530, 290, 290))
els.append(TXT(70, 550, 290, 17, INK, "Uçurtma", 700))
els.append(SVG(70 + 45, 530 + 55, 200, 200,
               f'<path d="M 100 0 L 200 100 L 100 200 L 0 100 Z" fill="{HOLE}" '
               'stroke="#999" stroke-width="2" stroke-dasharray="6 5"/>'))
els.append(scissors(70 + 145, 530 + 155))
# yönerge
steps = [("1", "Gri pencereleri kesin"),
         ("2", "Matın üzerinde kaydırın"),
         ("3", "Hedef renkleri yakalayın!")]
for i, (n, t) in enumerate(steps):
    y = 560 + i * 78
    els.append(D(401, y - 24, 48, 48,
                 "background:#E85D75;border-radius:50%;color:#fff;font-size:22px;"
                 "font-weight:800;text-align:center;line-height:48px", n))
    els.append(TXT(462, y - 15, 280, 20, INK, t, 600, "left"))
els.append(cloud(680, 950, 0.9))
els.append(small_balloon(160, 960, PALETTE["mint"], PALETTE["pembe"], 0.75))
pages.append(page(3, "Pencereler ve Yönerge", els))

# ------------------------------------------------------------------ hedef sayfaları
def target_page(pid, title, items, kind, label, start_num, num_color):
    els = [sky(), logo()]
    els.append(TXT(0, 92, PAGE_W, 29, INK, title))
    CW, CH = 300, 280
    gx, gy = (PAGE_W - 2 * CW - 60) / 2, 160
    for i, (colors, pos) in enumerate(items):
        col, row = i % 2, i // 2
        x = gx + col * (CW + 60)
        y = gy + row * (CH + 40)
        els.append(card_frame(x, y, CW, CH))
        if kind == "easy":
            els.append(small_balloon(x + CW / 2, y + CH / 2 + 10, colors[0], colors[1], 1.15))
        elif kind == "med":
            els.append(big_balloon(x + CW / 2, y + CH / 2 + 6, *colors, s=1.25))
        else:
            els.append(kite(x + CW / 2, y + CH / 2 - 20, *colors, s=1.0))
        els.append(badge(x + 11, y + 11, start_num + i, num_color))
    return page(pid, label, els)

pages.append(target_page(4, "Küçük Balonları Bul", easy_t, "easy", "Kolay Hedefler", 1, "#5BB98C"))
pages.append(target_page(5, "Büyük Balonları Bul", med_t, "med", "Orta Hedefler", 7, "#E8A33D"))
pages.append(target_page(6, "Uçurtmaları Bul", kite_t, "kite", "Uçurtma Hedefleri", 13, "#E85D75"))

# ------------------------------------------------------------------ çıktı
def key_lines():
    inv = {v: k for k, v in PALETTE.items()}
    out = []
    for i, (k, (r, c)) in enumerate(easy_t):
        out.append(f"kolay {i+1}: satır {r+1}, sütun {c+1} ({inv[k[0]]}/{inv[k[1]]})")
    for i, (k, (r, c)) in enumerate(med_t):
        out.append(f"orta {i+7}: satır {r+1}, sütun {c+1}")
    for i, (k, (r, c)) in enumerate(kite_t):
        out.append(f"uçurtma {i+13}: satır {r+1}, sütun {c+1}")
    return "\n".join(out)

html = ("<!DOCTYPE html>\n<html lang=\"tr\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<title>Tıkladers — Sihirli Balonlar</title>\n"
        "<style>body{margin:0;padding:0}</style>\n</head>\n<body>\n"
        "<!-- Cevap anahtarı:\n" + key_lines() + "\n-->\n"
        + "\n".join(pages) + "\n</body>\n</html>\n")
with open("sihirli_balonlar.html", "w", encoding="utf-8") as f:
    f.write(html)
print("yazıldı: sihirli_balonlar.html", len(html), "bayt")
