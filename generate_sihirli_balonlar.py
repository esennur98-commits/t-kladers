#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tıkladers — "Sihirli Balonlar" oyunu üretici.

Mekanik: pastel gökyüzü mozaiği (6x7 kare) + balon/uçurtma pencereli şablon
kartlar. Çocuk pencereyi mat üzerinde kaydırıp hedef karttaki renk
kombinasyonunu yakalar. Her hedefin matta TAM BİR konumu vardır (tekillik
betikte doğrulanır).

Çıktı: sihirli_balonlar.html — Canva'ya import edilebilen 6 sayfalık A4 seti.
"""
import random

PAGE_W, PAGE_H = 794, 1123          # A4 @96dpi
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
INK = "#4A4A68"          # ana çizgi rengi
DASH = "#7FB8E6"         # kesim çizgisi
BASKET = "#C9A227"       # sepet sarısı-kahve
BASKET_D = "#8B6F5E"

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
    # kolay: dikey ikili (üst, alt) — tekil çiftler
    pairs = {}
    for r in range(ROWS - 1):
        for c in range(COLS):
            pairs.setdefault((grid[r][c], grid[r + 1][c]), []).append((r, c))
    uniq_pairs = [k for k, v in pairs.items() if len(v) == 1]
    # 2x2 blok — tekil dörtlüler
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

# ---------------------------------------------------------------- svg parçaları
def cloud(x, y, s=1.0, op=0.9):
    return (f'<g transform="translate({x},{y}) scale({s})" fill="#FFFFFF" opacity="{op}">'
            '<ellipse cx="0" cy="0" rx="46" ry="26"/>'
            '<ellipse cx="-34" cy="8" rx="30" ry="18"/>'
            '<ellipse cx="34" cy="8" rx="30" ry="18"/></g>')

def logo(x=PAGE_W / 2):
    return (f'<g transform="translate({x},46)">'
            f'<rect x="-42" y="-30" width="84" height="60" rx="6" fill="#fff" stroke="{INK}" stroke-width="2.5"/>'
            f'<text y="-10" text-anchor="middle" font-size="16" font-weight="800" fill="{INK}">TIK</text>'
            f'<text y="7" text-anchor="middle" font-size="16" font-weight="800" fill="#E85D75">-LA-</text>'
            f'<text y="24" text-anchor="middle" font-size="16" font-weight="800" fill="{INK}">DERS</text>'
            f'<path d="M 30 14 l 10 12 l 3 -6 l 7 -1 z" fill="{INK}"/></g>')

def sky_defs(pid):
    return (f'<defs><linearGradient id="sky{pid}" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#CDE9FF"/><stop offset="0.6" stop-color="#E9F6FF"/>'
            '<stop offset="1" stop-color="#FFF3F8"/></linearGradient></defs>'
            f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="url(#sky{pid})"/>')

def face(cx, cy, s=1.0):
    return (f'<g transform="translate({cx},{cy}) scale({s})">'
            f'<circle cx="-16" cy="-4" r="4.5" fill="{INK}"/><circle cx="16" cy="-4" r="4.5" fill="{INK}"/>'
            f'<path d="M -10 8 Q 0 18 10 8" stroke="{INK}" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
            '<circle cx="-26" cy="6" r="6" fill="#FF9AA2" opacity="0.55"/>'
            '<circle cx="26" cy="6" r="6" fill="#FF9AA2" opacity="0.55"/></g>')

def quad_circle(cx, cy, r, tl, tr, bl, br, sw=3):
    """4 çeyrekli balon zarfı."""
    return (f'<g><clipPath id="q{cx}_{cy}_{r}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
            f'<g clip-path="url(#q{cx}_{cy}_{r})">'
            f'<rect x="{cx-r}" y="{cy-r}" width="{r}" height="{r}" fill="{tl}"/>'
            f'<rect x="{cx}" y="{cy-r}" width="{r}" height="{r}" fill="{tr}"/>'
            f'<rect x="{cx-r}" y="{cy}" width="{r}" height="{r}" fill="{bl}"/>'
            f'<rect x="{cx}" y="{cy}" width="{r}" height="{r}" fill="{br}"/></g>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{INK}" stroke-width="{sw}"/>'
            f'<line x1="{cx-r}" y1="{cy}" x2="{cx+r}" y2="{cy}" stroke="{INK}" stroke-width="{sw*0.6}"/>'
            f'<line x1="{cx}" y1="{cy-r}" x2="{cx}" y2="{cy+r}" stroke="{INK}" stroke-width="{sw*0.6}"/></g>')

def basket(cx, cy, w=44, h=34, sw=3):
    return (f'<rect x="{cx-w/2}" y="{cy}" width="{w}" height="{h}" rx="7" fill="{BASKET}" '
            f'stroke="{BASKET_D}" stroke-width="{sw}"/>'
            f'<line x1="{cx-w/2+8}" y1="{cy+6}" x2="{cx+w/2-8}" y2="{cy+6}" stroke="{BASKET_D}" stroke-width="{sw*0.7}"/>')

def small_balloon(cx, cy, top, bottom, s=1.0):
    """Kolay hedef: zarf=üst renk, sepet=alt renk."""
    g = f'<g transform="translate({cx},{cy}) scale({s})">'
    g += f'<circle cx="0" cy="-38" r="46" fill="{top}" stroke="{INK}" stroke-width="3.5"/>'
    g += f'<ellipse cx="-16" cy="-54" rx="12" ry="8" fill="#fff" opacity="0.5"/>'
    g += f'<line x1="-22" y1="2" x2="-17" y2="34" stroke="{INK}" stroke-width="2.5"/>'
    g += f'<line x1="22" y1="2" x2="17" y2="34" stroke="{INK}" stroke-width="2.5"/>'
    g += (f'<rect x="-26" y="34" width="52" height="42" rx="8" fill="{bottom}" '
          f'stroke="{INK}" stroke-width="3.5"/>')
    g += f'<line x1="-26" y1="48" x2="26" y2="48" stroke="{INK}" stroke-width="2" opacity="0.5"/>'
    g += '</g>'
    return g

def big_balloon(cx, cy, tl, tr, bl, br, s=1.0, with_face=False):
    g = f'<g transform="translate({cx},{cy}) scale({s})">'
    g += quad_circle(0, -30, 62, tl, tr, bl, br, sw=3.5)
    g += f'<line x1="-34" y1="22" x2="-20" y2="52" stroke="{INK}" stroke-width="2.5"/>'
    g += f'<line x1="34" y1="22" x2="20" y2="52" stroke="{INK}" stroke-width="2.5"/>'
    g += basket(0, 52, 48, 34)
    if with_face:
        g += face(0, -30, 1.0)
    g += '</g>'
    return g

def kite(cx, cy, tl, tr, bl, br, s=1.0):
    g = f'<g transform="translate({cx},{cy}) scale({s})">'
    g += (f'<path d="M 0 -62 L 62 0 L 0 62 L -62 0 Z" fill="#fff"/>'
          f'<path d="M 0 -62 L 0 0 L -62 0 Z" fill="{tl}"/>'
          f'<path d="M 0 -62 L 62 0 L 0 0 Z" fill="{tr}"/>'
          f'<path d="M -62 0 L 0 0 L 0 62 Z" fill="{bl}"/>'
          f'<path d="M 0 0 L 62 0 L 0 62 Z" fill="{br}"/>'
          f'<path d="M 0 -62 L 62 0 L 0 62 L -62 0 Z" fill="none" stroke="{INK}" stroke-width="3.5"/>'
          f'<line x1="0" y1="-62" x2="0" y2="62" stroke="{INK}" stroke-width="2"/>'
          f'<line x1="-62" y1="0" x2="62" y2="0" stroke="{INK}" stroke-width="2"/>')
    g += (f'<path d="M 0 62 Q 14 84 4 102" stroke="{INK}" stroke-width="2.5" fill="none"/>'
          f'<path d="M 8 80 l 8 -6 l 0 12 z" fill="#FF9AA2" stroke="{INK}" stroke-width="1.5"/>'
          f'<path d="M 2 98 l 8 -6 l 0 12 z" fill="#A3D8F4" stroke="{INK}" stroke-width="1.5"/>')
    g += '</g>'
    return g

def card(x, y, w, h, inner, num=None, num_color="#E85D75"):
    g = (f'<g transform="translate({x},{y})">'
         f'<rect x="-8" y="-8" width="{w+16}" height="{h+16}" rx="18" fill="none" '
         f'stroke="{DASH}" stroke-width="2.5" stroke-dasharray="9 7"/>'
         f'<rect width="{w}" height="{h}" rx="14" fill="#FFFFFF" stroke="{INK}" stroke-width="2"/>' )
    g += inner
    if num is not None:
        g += (f'<circle cx="30" cy="30" r="19" fill="{num_color}"/>'
              f'<text x="30" y="37" text-anchor="middle" font-size="20" font-weight="800" fill="#fff">{num}</text>')
    g += '</g>'
    return g

def scissors(x, y):
    return (f'<g transform="translate({x},{y})" stroke="{INK}" stroke-width="2" fill="none">'
            '<circle cx="-8" cy="6" r="4"/><circle cx="-8" cy="-6" r="4"/>'
            '<line x1="-5" y1="4" x2="12" y2="-7"/><line x1="-5" y1="-4" x2="12" y2="7"/></g>')

FONT = "font-family=\"'Comic Sans MS','Chalkboard SE','Trebuchet MS',sans-serif\""

def svg_page(pid, body, label):
    return (f'<div data-document-role="page" data-label="{label}" '
            f'style="width:{PAGE_W}px;height:{PAGE_H}px;overflow:hidden">'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" height="{PAGE_H}" '
            f'viewBox="0 0 {PAGE_W} {PAGE_H}" {FONT}>{sky_defs(pid)}{body}</svg></div>')

pages = []

# ------------------------------------------------------------------ 1. kapak
b = logo()
b += cloud(120, 200, 1.2) + cloud(660, 260, 1.0, 0.8) + cloud(90, 640, 0.9, 0.8) + cloud(700, 700, 1.3)
b += f'<text x="{PAGE_W/2}" y="175" text-anchor="middle" font-size="64" font-weight="800" fill="{INK}">Sihirli Balonlar</text>'
b += f'<text x="{PAGE_W/2}" y="220" text-anchor="middle" font-size="26" fill="#E85D75" font-weight="700">Kes &#8226; Kaydır &#8226; Eşleştir</text>'
b += big_balloon(PAGE_W / 2, 560, PALETTE["pembe"], PALETTE["mavi"], PALETTE["sari"], PALETTE["mint"], s=3.2, with_face=True)
b += kite(160, 900, PALETTE["mercan"], PALETTE["sari"], PALETTE["mavi"], PALETTE["lila"], s=0.8)
b += small_balloon(650, 900, PALETTE["lila"], PALETTE["seftali"], s=0.9)
b += (f'<rect x="{PAGE_W/2-150}" y="1020" width="300" height="52" rx="26" fill="#fff" stroke="{INK}" stroke-width="2.5"/>'
      f'<text x="{PAGE_W/2}" y="1054" text-anchor="middle" font-size="24" font-weight="700" fill="{INK}">3 - 8 yaş</text>')
pages.append(svg_page(1, b, "Kapak"))

# ------------------------------------------------------------------ 2. mat
b = logo()
mx, my = (PAGE_W - COLS * CELL) / 2, 150
b += f'<text x="{PAGE_W/2}" y="120" text-anchor="middle" font-size="30" font-weight="800" fill="{INK}">Gökyüzü Matı</text>'
b += (f'<rect x="{mx-16}" y="{my-16}" width="{COLS*CELL+32}" height="{ROWS*CELL+32}" rx="20" '
      f'fill="#FFFFFF" stroke="{INK}" stroke-width="3"/>')
for r in range(ROWS):
    for c in range(COLS):
        b += (f'<rect x="{mx+c*CELL+2}" y="{my+r*CELL+2}" width="{CELL-4}" height="{CELL-4}" '
              f'rx="10" fill="{grid[r][c]}"/>')
b += cloud(90, 1010, 0.8, 0.9) + cloud(700, 1030, 1.0, 0.9)
b += (f'<text x="{PAGE_W/2}" y="1040" text-anchor="middle" font-size="20" fill="{INK}">'
      'Bu sayfayı kesmeyin — pencereyi üzerinde kaydırın!</text>')
pages.append(svg_page(2, b, "Gökyüzü Matı"))

# ------------------------------------------------------------------ 3. pencereler
b = logo()
b += f'<text x="{PAGE_W/2}" y="120" text-anchor="middle" font-size="30" font-weight="800" fill="{INK}">Sihirli Pencereler</text>'
HOLE = "#EFEFEF"
# küçük balon penceresi
inner = f'<text x="110" y="36" text-anchor="middle" font-size="18" font-weight="700" fill="{INK}">Küçük Balon</text>'
inner += f'<circle cx="110" cy="120" r="50" fill="{HOLE}" stroke="#999" stroke-width="2" stroke-dasharray="6 5"/>'
inner += f'<line x1="85" y1="163" x2="90" y2="185" stroke="{INK}" stroke-width="2.5"/>'
inner += f'<line x1="135" y1="163" x2="130" y2="185" stroke="{INK}" stroke-width="2.5"/>'
inner += f'<rect x="75" y="190" width="70" height="60" rx="8" fill="{HOLE}" stroke="#999" stroke-width="2" stroke-dasharray="6 5"/>'
inner += scissors(110, 120) + scissors(110, 220)
c1 = card(70, 170, 220, 280, inner)
# büyük balon penceresi
inner = f'<text x="145" y="36" text-anchor="middle" font-size="18" font-weight="700" fill="{INK}">Büyük Balon</text>'
inner += f'<circle cx="145" cy="150" r="100" fill="{HOLE}" stroke="#999" stroke-width="2" stroke-dasharray="6 5"/>'
inner += f'<line x1="95" y1="237" x2="115" y2="262" stroke="{INK}" stroke-width="2.5"/>'
inner += f'<line x1="195" y1="237" x2="175" y2="262" stroke="{INK}" stroke-width="2.5"/>'
inner += basket(145, 258, 56, 30)
inner += scissors(145, 150)
c2 = card(330, 170, 290, 310, inner)
# uçurtma penceresi
inner = f'<text x="145" y="36" text-anchor="middle" font-size="18" font-weight="700" fill="{INK}">Uçurtma</text>'
inner += (f'<path d="M 145 55 L 245 155 L 145 255 L 45 155 Z" fill="{HOLE}" '
          'stroke="#999" stroke-width="2" stroke-dasharray="6 5"/>')
inner += scissors(145, 155)
c3 = card(70, 530, 290, 290, inner)
b += c1 + c2 + c3
# yönerge
steps = [("1", "Gri pencereleri kesin"),
         ("2", "Matın üzerinde kaydırın"),
         ("3", "Hedef renkleri yakalayın!")]
sy = 560
for i, (n, t) in enumerate(steps):
    y = sy + i * 78
    b += (f'<circle cx="425" cy="{y}" r="24" fill="#E85D75"/>'
          f'<text x="425" y="{y+8}" text-anchor="middle" font-size="22" font-weight="800" fill="#fff">{n}</text>'
          f'<text x="462" y="{y+8}" font-size="20" font-weight="600" fill="{INK}">{t}</text>')
b += cloud(680, 950, 0.9) + small_balloon(160, 960, PALETTE["mint"], PALETTE["pembe"], 0.75)
pages.append(svg_page(3, b, "Pencereler ve Yönerge"))

# ------------------------------------------------------------------ hedef sayfaları
def target_page(pid, title, items, draw, label, start_num, num_color):
    b = logo()
    b += f'<text x="{PAGE_W/2}" y="120" text-anchor="middle" font-size="30" font-weight="800" fill="{INK}">{title}</text>'
    CW, CH = 300, 280
    gx, gy = (PAGE_W - 2 * CW - 60) / 2, 160
    for i, (colors, pos) in enumerate(items):
        col, row = i % 2, i // 2
        x = gx + col * (CW + 60)
        y = gy + row * (CH + 40)
        inner = draw(colors, CW, CH)
        b += card(x, y, CW, CH, inner, num=start_num + i, num_color=num_color)
    return svg_page(pid, b, label)

def draw_easy(colors, w, h):
    top, bottom = colors
    return small_balloon(w / 2, h / 2 + 10, top, bottom, 1.15)

def draw_med(colors, w, h):
    tl, tr, bl, br = colors
    return big_balloon(w / 2, h / 2 + 6, tl, tr, bl, br, 1.25)

def draw_kite(colors, w, h):
    tl, tr, bl, br = colors
    return kite(w / 2, h / 2 - 20, tl, tr, bl, br, 1.0)

pages.append(target_page(4, "Küçük Balonları Bul", easy_t, draw_easy, "Kolay Hedefler", 1, "#5BB98C"))
pages.append(target_page(5, "Büyük Balonları Bul", med_t, draw_med, "Orta Hedefler", 7, "#E8A33D"))
pages.append(target_page(6, "Uçurtmaları Bul", kite_t, draw_kite, "Uçurtma Hedefleri", 13, "#E85D75"))

# ------------------------------------------------------------------ cevap anahtarı (yorum olarak)
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

html = ("<!-- Tıkladers — Sihirli Balonlar. Cevap anahtarı:\n" + key_lines() + "\n-->\n"
        + "\n".join(pages))
with open("sihirli_balonlar.html", "w", encoding="utf-8") as f:
    f.write(html)
print("yazıldı: sihirli_balonlar.html", len(html), "bayt")
