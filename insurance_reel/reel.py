"""9:16 explainer reel: มีประกันสุขภาพแล้ว… ทำไมยังต้องมีประกันโรคร้าย?

Render:   python3 insurance_reel/reel.py            (full video -> insurance_reel/output/)
Stills:   python3 insurance_reel/reel.py --still 5,10,20,36

1080x1920, 30 fps, H.264 + AAC. Graphics are drawn in code (cairo + PIL/raqm,
Kanit font). The colour palette follows the client's reference post (blue
gradient, white cards, pink-red highlight, yellow badge, lime accents). The
video carries no third-party brand, logo or product claims.
"""
import argparse
import math
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from src.audio import dsp  # noqa: E402  (shared synth helpers)

W, H, FPS = 1080, 1920, 30
DURATION = 40.0
OUT = HERE / "output"
BUILD = OUT / "build"
FONTS = HERE / "fonts"

# ---------------------------------------------------------------- palette
NAVY = (14, 38, 96)
BLUE_DEEP = (9, 46, 128)
BLUE = (22, 94, 214)
BLUE_LIGHT = (98, 172, 242)
SKY = (196, 226, 252)
WHITE = (255, 255, 255)
PINK = (236, 34, 96)
PINK_DARK = (196, 18, 72)
YELLOW = (255, 203, 38)
LIME = (150, 202, 38)
LIME_DARK = (92, 150, 18)
GREY = (110, 124, 150)


# ================================================================ helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= b)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back_out(x, s=2.2):
    """Overshoot ease for pop-ups."""
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def surface(w, h):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(w), int(h))
    c = cairo.Context(s)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    return s, c


def to_pil(s):
    s.flush()
    w, h = s.get_width(), s.get_height()
    a = np.frombuffer(s.get_data(), np.uint8).reshape(h, s.get_stride() // 4, 4)[:, :w].astype(np.float32)
    al = np.maximum(a[..., 3:4], 1) / 255.0
    rgb = np.clip(a[..., [2, 1, 0]] / al, 0, 255)
    return Image.fromarray(np.dstack([rgb, a[..., 3]]).astype(np.uint8), "RGBA")


def col(c, rgb, a=1.0):
    c.set_source_rgba(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, a)


def rrect(c, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    c.close_path()


def lin(c, x0, y0, x1, y1, stops):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for o, rgb, a in stops:
        g.add_color_stop_rgba(o, rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, a)
    c.set_source(g)


def rad(c, cx, cy, r0, r1, stops):
    g = cairo.RadialGradient(cx, cy, r0, cx, cy, r1)
    for o, rgb, a in stops:
        g.add_color_stop_rgba(o, rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, a)
    c.set_source(g)


def with_alpha(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return im


def paste_scaled(frame, im, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    """Composite ``im`` centred at (cx, cy) with scale / alpha / rotation."""
    if alpha <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    im = with_alpha(im, alpha)
    x, y = int(round(cx - im.width / 2)), int(round(cy - im.height / 2))
    if x >= frame.width or y >= frame.height or x + im.width <= 0 or y + im.height <= 0:
        return
    sx, sy = max(0, -x), max(0, -y)
    frame.alpha_composite(im, dest=(max(0, x), max(0, y)), source=(sx, sy))


# ================================================================ text
@lru_cache(maxsize=32)
def font(weight, size):
    return ImageFont.truetype(str(FONTS / f"Kanit-{weight}.ttf"), int(size), layout_engine=ImageFont.Layout.RAQM)


@lru_cache(maxsize=512)
def text(s, weight="Bold", size=60, fill=WHITE, stroke=0, stroke_fill=NAVY, shadow=0, align="center", spacing=6):
    f = font(weight, size)
    lines = s.split("\n")
    d0 = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    boxes = [d0.textbbox((0, 0), ln, font=f, stroke_width=stroke) for ln in lines]
    asc, desc = f.getmetrics()
    lh = asc + desc
    w = max(b[2] - min(0, b[0]) for b in boxes) + stroke * 2 + 8
    h = lh * len(lines) + spacing * (len(lines) - 1) + stroke * 2 + 12
    pad = shadow * 3 + 4
    im = Image.new("RGBA", (int(w + pad * 2), int(h + pad * 2)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = pad + stroke + 4
    for ln, b in zip(lines, boxes):
        lw = b[2] - b[0]
        x = pad + stroke + (w - 8 - stroke * 2 - lw) / 2 - b[0] if align == "center" else pad + stroke - b[0]
        d.text((x, y), ln, font=f, fill=tuple(fill) + (255,), stroke_width=stroke, stroke_fill=tuple(stroke_fill) + (255,))
        y += lh + spacing
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.45)))
        sh = sh.filter(ImageFilter.GaussianBlur(shadow))
        out = Image.new("RGBA", im.size, (0, 0, 0, 0))
        out.alpha_composite(sh, dest=(0, shadow // 2 + 2))
        out.alpha_composite(im)
        return out
    return im


# ================================================================ icons (white line icons, 100x100 box)
def _icon_canvas(size=100):
    s, c = surface(size, size)
    c.scale(size / 100, size / 100)
    c.set_line_width(7)
    col(c, WHITE)
    return s, c


def icon(name, size=100):
    return _icon(name, size)


@lru_cache(maxsize=64)
def _icon(name, size):
    s, c = _icon_canvas(size)
    if name == "bed":
        c.move_to(14, 30); c.line_to(14, 78); c.move_to(14, 62); c.line_to(86, 62); c.line_to(86, 78)
        c.stroke()
        rrect(c, 22, 44, 20, 12, 5); c.fill()
        rrect(c, 46, 42, 40, 16, 6); c.fill()
    elif name == "doctor":
        c.arc(50, 30, 14, 0, 2 * math.pi); c.fill()
        c.move_to(22, 86); c.curve_to(22, 58, 78, 58, 78, 86); c.close_path(); c.fill()
        col(c, BLUE); c.set_line_width(5)
        c.move_to(40, 62); c.curve_to(40, 76, 60, 76, 60, 62); c.stroke()
        c.arc(60, 60, 4, 0, 2 * math.pi); c.fill()
    elif name == "pill":
        c.save(); c.translate(50, 50); c.rotate(-0.75)
        rrect(c, -34, -15, 68, 30, 15); c.stroke()
        c.rectangle(-34 + 4, -11, 30, 22); c.fill()
        c.restore()
    elif name == "clipboard":
        rrect(c, 22, 18, 56, 70, 8); c.stroke()
        rrect(c, 38, 12, 24, 14, 4); c.fill()
        c.move_to(34, 54); c.line_to(46, 66); c.line_to(68, 42); c.stroke()
    elif name == "car":
        c.move_to(12, 64); c.line_to(18, 44); c.curve_to(22, 34, 30, 32, 38, 32); c.line_to(64, 32)
        c.curve_to(72, 32, 78, 36, 82, 44); c.line_to(88, 64); c.close_path(); c.fill()
        col(c, BLUE)
        rrect(c, 30, 38, 18, 12, 3); c.fill(); rrect(c, 52, 38, 20, 12, 3); c.fill()
        col(c, WHITE)
        for x in (30, 70):
            c.arc(x, 70, 10, 0, 2 * math.pi); c.fill()
    elif name == "house":
        c.move_to(14, 48); c.line_to(50, 18); c.line_to(86, 48); c.stroke()
        c.move_to(24, 42); c.line_to(24, 84); c.line_to(76, 84); c.line_to(76, 42); c.stroke()
        c.save(); c.translate(56, 62); c.rotate(0.8)
        rrect(c, -4, -18, 8, 32, 3); c.fill()
        c.arc(0, -20, 9, 0, 2 * math.pi); c.fill()
        c.restore()
    elif name == "wheelchair":
        c.arc(34, 16, 8, 0, 2 * math.pi); c.fill()
        c.move_to(34, 28); c.line_to(36, 56); c.line_to(62, 56); c.line_to(72, 80); c.stroke()
        c.arc(40, 66, 20, 0.6, 2 * math.pi - 0.6); c.stroke()
    elif name == "wallet":
        rrect(c, 12, 30, 64, 46, 8); c.stroke()
        c.arc(62, 53, 5, 0, 2 * math.pi); c.fill()
        c.set_line_width(7)
        c.move_to(86, 18); c.line_to(86, 60); c.stroke()
        c.move_to(76, 50); c.line_to(86, 62); c.line_to(96, 50); c.stroke()
    elif name == "receipt":
        c.move_to(24, 12); c.line_to(76, 12); c.line_to(76, 88)
        for i in range(5):
            c.line_to(76 - (i * 2 + 1) * 5.2, 80 if i % 2 == 0 else 88)
        c.line_to(24, 88); c.close_path(); c.stroke()
        c.move_to(50, 30); c.line_to(50, 56); c.stroke()
        c.arc(50, 70, 4.5, 0, 2 * math.pi); c.fill()
    elif name == "shield":
        c.move_to(50, 8); c.line_to(86, 22); c.curve_to(86, 60, 70, 82, 50, 94)
        c.curve_to(30, 82, 14, 60, 14, 22); c.close_path(); c.fill()
        col(c, BLUE)
        c.rectangle(44, 30, 12, 40); c.fill(); c.rectangle(30, 44, 40, 12); c.fill()
    elif name == "heart":
        c.move_to(50, 88)
        c.curve_to(10, 60, 4, 34, 18, 20); c.curve_to(30, 8, 46, 14, 50, 28)
        c.curve_to(54, 14, 70, 8, 82, 20); c.curve_to(96, 34, 90, 60, 50, 88); c.close_path(); c.fill()
        col(c, PINK); c.set_line_width(6)
        c.move_to(18, 48); c.line_to(36, 48); c.line_to(44, 34); c.line_to(54, 62); c.line_to(62, 48); c.line_to(82, 48)
        c.stroke()
    return to_pil(s)


# ================================================================ background
@lru_cache(maxsize=1)
def background_base():
    s, c = surface(W, H)
    lin(c, 0, 0, 0, H, [(0, BLUE_DEEP, 1), (0.45, BLUE, 1), (0.8, BLUE_LIGHT, 1), (1, (150, 200, 245), 1)])
    c.paint()
    rad(c, W * 0.5, H * 0.18, 0, 900, [(0, (130, 200, 255), 0.55), (1, BLUE, 0)])
    c.paint()
    # soft diagonal light beams
    for i, (x, w_, a) in enumerate([(-200, 260, 0.06), (260, 160, 0.05), (720, 300, 0.05)]):
        c.save()
        c.translate(x, 0)
        c.rotate(-0.35)
        lin(c, 0, 0, w_, 0, [(0, WHITE, 0), (0.5, WHITE, a), (1, WHITE, 0)])
        c.rectangle(0, -400, w_, H + 800)
        c.fill()
        c.restore()
    return to_pil(s)


BOKEH = [(np.random.default_rng(3).uniform(0, W), np.random.default_rng(i).uniform(0, H),
          np.random.default_rng(i + 50).uniform(14, 60), np.random.default_rng(i + 90).uniform(0.04, 0.16), i)
         for i in range(26)]


def background(t):
    frame = background_base().copy()
    s, c = surface(W, H)
    for (x0, y0, r, a, i) in BOKEH:
        x = (x0 + i * 97 + math.sin(t * 0.3 + i) * 30) % W
        y = (y0 - t * (10 + i % 5 * 4)) % H
        rad(c, x, y, 0, r, [(0, WHITE, a), (0.7, WHITE, a * 0.6), (1, WHITE, 0)])
        c.arc(x, y, r, 0, 2 * math.pi)
        c.fill()
    frame.alpha_composite(to_pil(s))
    return frame


# ================================================================ components
@lru_cache(maxsize=64)
def pill(label, fg, bg, outline=None, size=40, padx=34, pady=12, weight="SemiBold", radius=None):
    t_ = text(label, weight, size, fg)
    w, h = t_.width + padx * 2, t_.height + pady * 2 - 10
    s, c = surface(w + 8, h + 8)
    rrect(c, 4, 4, w, h, radius or h / 2)
    col(c, bg)
    c.fill_preserve()
    if outline:
        col(c, outline)
        c.set_line_width(4)
        c.stroke()
    im = to_pil(s)
    im.alpha_composite(t_, dest=(int(4 + w / 2 - t_.width / 2), int(4 + h / 2 - t_.height / 2)))
    return im


@lru_cache(maxsize=32)
def icon_badge(name, bg, size=92, ring=WHITE):
    s, c = surface(size + 12, size + 12)
    cx = cy = (size + 12) / 2
    c.arc(cx, cy + 3, size / 2, 0, 2 * math.pi)
    col(c, (0, 0, 0), 0.18)
    c.fill()
    c.arc(cx, cy, size / 2, 0, 2 * math.pi)
    lin(c, 0, 0, 0, size, [(0, tuple(min(255, v + 30) for v in bg), 1), (1, bg, 1)])
    c.fill_preserve()
    col(c, ring)
    c.set_line_width(4)
    c.stroke()
    im = to_pil(s)
    ic = icon(name, int(size * 0.58))
    im.alpha_composite(ic, dest=(int(cx - ic.width / 2), int(cy - ic.height / 2)))
    return im


@lru_cache(maxsize=32)
def item_row(label, icon_name, accent, width=470):
    """White pill row: icon badge + label (pop-up unit)."""
    h = 118
    s, c = surface(width + 20, h + 20)
    rrect(c, 10, 14, width, h - 8, 26)
    col(c, (0, 30, 90), 0.18)
    c.fill()
    rrect(c, 10, 8, width, h - 8, 26)
    col(c, WHITE)
    c.fill()
    rrect(c, 10, 8, 14, h - 8, 7)
    col(c, accent)
    c.fill()
    im = to_pil(s)
    b = icon_badge(icon_name, accent, 80)
    im.alpha_composite(b, dest=(30, int(8 + (h - 8) / 2 - b.height / 2)))
    tx = text(label, "SemiBold", 36 if "\n" not in label else 32, NAVY, spacing=-6, align="left")
    im.alpha_composite(tx, dest=(30 + b.width + 10, int(8 + (h - 8) / 2 - tx.height / 2)))
    return im


@lru_cache(maxsize=4)
def column_card(header, accent, icon_name, height=1040, width=500):
    s, c = surface(width + 30, height + 40)
    rrect(c, 15, 26, width, height, 42)
    col(c, (0, 20, 70), 0.25)
    c.fill()
    rrect(c, 15, 15, width, height, 42)
    lin(c, 0, 15, 0, height, [(0, (246, 250, 255), 0.97), (1, (226, 238, 252), 0.97)])
    c.fill()
    # header band
    c.save()
    rrect(c, 15, 15, width, height, 42)
    c.clip()
    c.rectangle(15, 15, width, 222)
    lin(c, 0, 15, 0, 237, [(0, tuple(min(255, v + 25) for v in accent), 1), (1, accent, 1)])
    c.fill()
    c.restore()
    im = to_pil(s)
    b = icon_badge(icon_name, accent, 96)
    im.alpha_composite(b, dest=(int(15 + width / 2 - b.width / 2), 24))
    t_ = text(header, "Bold", 52, WHITE, shadow=6)
    im.alpha_composite(t_, dest=(int(15 + width / 2 - t_.width / 2), 118))
    return im


# ================================================================ timeline (seconds)
T_HOOK = 0.0
T_SPLIT = 4.0                 # header shrinks, cards appear
LEFT = {"card": 4.4, "chip": 5.7, "items": [6.8, 7.8, 8.8, 9.9]}
RIGHT = {"card": 12.2, "chip": 13.5, "items": [15.0, 16.2, 17.5, 18.9, 20.3]}
T_BOTH = 22.4                 # both columns lit + "ต้องมีทั้งคู่"
T_INSIGHT = 25.6
T_CTA = 30.6
LEFT_ITEMS = [("ค่าห้อง", "bed"), ("ค่าหมอ", "doctor"), ("ค่ายา", "pill"), ("รักษาพยาบาล\nตามเงื่อนไข", "clipboard")]
RIGHT_ITEMS = [("ค่าเดินทาง", "car"), ("ค่าปรับปรุงบ้าน", "house"), ("รถเข็น /\nอุปกรณ์ช่วยเหลือ", "wheelchair"),
               ("รายได้ที่หายไป", "wallet"), ("ค่ารักษาบางส่วน\nที่อยู่นอกสิทธิ์", "receipt")]

# narration lines (shown as captions; the timing is ready for a recorded voice-over)
CAPTIONS = [
    (4.6, 7.0, "ประกันสุขภาพมีไว้สำหรับ “ค่ารักษา”"),
    (7.0, 11.6, "ค่าห้อง ค่าหมอ ค่ายา\nและรักษาพยาบาลตามเงื่อนไข"),
    (12.3, 14.9, "ส่วนประกันโรคร้ายแรง\nมีไว้สำหรับ “ค่าใช้จ่ายแฝง”"),
    (14.9, 18.8, "เช่น ค่าเดินทาง ค่าปรับปรุงบ้าน\nรถเข็นหรืออุปกรณ์ช่วยเหลือ"),
    (18.8, 22.3, "รายได้ที่หายไป และค่ารักษา\nบางส่วนที่อยู่นอกสิทธิ์"),
]

COL_W = 500
LX, RX = 30, W - 30 - COL_W
CARD_Y = 400
ROW_Y0 = CARD_Y + 362
ROW_STEP = 128


def pop(t, t0, dur=0.42):
    p = prog(t, t0, t0 + dur)
    return back_out(p) if p > 0 else 0.0, clamp(p * 2.5)


# ================================================================ scenes
def draw_header(frame, t):
    """Hook title -> shrinks into the top header during the split section."""
    out = ease_in_out(prog(t, T_INSIGHT - 0.4, T_INSIGHT))
    if out >= 1:
        return
    m = ease_in_out(prog(t, T_SPLIT - 0.3, T_SPLIT + 0.4))   # 0 = big hook, 1 = header
    a_all = 1 - out
    # line 1
    s1, a1 = pop(t, 0.25)
    l1 = text("มีประกันสุขภาพแล้ว…", "SemiBold", 76, WHITE, shadow=10)
    y1 = 640 + (170 - 640) * m
    sc1 = s1 * (1 - 0.42 * m)
    paste_scaled(frame, l1, W / 2, y1, sc1, a1 * a_all)
    # line 2
    s2, a2 = pop(t, 1.05)
    l2 = text("ทำไมยังต้องมี", "Bold", 92, WHITE, shadow=10)
    y2 = 790 + (242 - 790) * m
    x2 = W / 2 + (-170) * m
    paste_scaled(frame, l2, x2, y2, s2 * (1 - 0.5 * m), a2 * a_all)
    # "ประกันโรคร้าย?" pink, pulsing
    s3, a3 = pop(t, 1.6, 0.5)
    pulse = 1 + 0.03 * math.sin(t * 6) * (1 - m)
    l3 = text("ประกันโรคร้าย?", "ExtraBold", 138, PINK, stroke=7, stroke_fill=WHITE, shadow=12)
    y3 = 960 + (242 - 960) * m
    x3 = W / 2 + 165 * m
    paste_scaled(frame, l3, x3, y3, s3 * pulse * (1 - 0.62 * m), a3 * a_all)
    # yellow badge (hook only)
    sb, ab = pop(t, 2.4)
    if m < 1:
        badge = pill("คลิปนี้มีคำตอบ!", NAVY, YELLOW, size=46, padx=40, pady=18, weight="Bold")
        paste_scaled(frame, badge, W / 2 + 230, 1150, sb, ab * (1 - m) * a_all, rot=6)


def draw_columns(frame, t):
    if t < LEFT["card"] - 0.1 or t > T_INSIGHT + 0.6:
        return
    leave = ease_in_out(prog(t, T_INSIGHT - 0.35, T_INSIGHT + 0.35))
    # focus: left dims while the right side is presented, both lit at the end
    left_dim = 0.45 * prog(t, RIGHT["card"] - 0.3, RIGHT["card"]) * (1 - prog(t, T_BOTH, T_BOTH + 0.4))
    for side in ("L", "R"):
        spec = LEFT if side == "L" else RIGHT
        x = LX if side == "L" else RX
        accent = BLUE if side == "L" else PINK
        sc, a = pop(t, spec["card"], 0.5)
        if a <= 0:
            continue
        dx = (-1 if side == "L" else 1) * leave * 700
        card = column_card("ประกันสุขภาพ" if side == "L" else "ประกันโรคร้าย", accent,
                           "shield" if side == "L" else "heart")
        cx, cy = x + COL_W / 2 + dx, CARD_Y + card.height / 2 - 15
        layer = Image.new("RGBA", (card.width, card.height), (0, 0, 0, 0))
        layer.alpha_composite(card)
        # sub chip
        cs, ca = pop(t, spec["chip"])
        if ca > 0:
            chip = pill("ค่ารักษา" if side == "L" else "ค่าใช้จ่ายแฝง", accent, WHITE, outline=accent, size=44,
                        weight="Bold")
            ch = chip.resize((max(1, int(chip.width * cs)), max(1, int(chip.height * cs))), Image.BICUBIC)
            layer.alpha_composite(with_alpha(ch, ca), dest=(int(card.width / 2 - ch.width / 2), int(292 - ch.height / 2)))
        items = LEFT_ITEMS if side == "L" else RIGHT_ITEMS
        for i, ((label, ic), t0) in enumerate(zip(items, spec["items"])):
            isc, ia = pop(t, t0)
            if ia <= 0:
                continue
            row = item_row(label, ic, accent, COL_W - 30)
            rw = row.resize((max(1, int(row.width * isc)), max(1, int(row.height * isc))), Image.BICUBIC)
            ry = ROW_Y0 - CARD_Y + i * ROW_STEP + 60
            layer.alpha_composite(with_alpha(rw, ia), dest=(int(card.width / 2 - rw.width / 2), int(ry - rw.height / 2)))
        dim = left_dim if side == "L" else 0.0
        if dim > 0:
            shade = Image.new("RGBA", layer.size, (8, 30, 90, 0))
            shade.putalpha(layer.getchannel("A").point(lambda v: int(v * dim)))
            layer.alpha_composite(shade)
        paste_scaled(frame, layer, cx, cy, 0.9 + 0.1 * sc, a * (1 - leave))
    # "+" and the conclusion bar
    ps, pa = pop(t, T_BOTH, 0.5)
    if pa > 0:
        plus = icon_badge_plus()
        paste_scaled(frame, plus, W / 2, CARD_Y + 600, ps, pa * (1 - leave))
        bar = pill("คุ้มครองครบ ต้องมีทั้งคู่!", WHITE, BLUE_DEEP, outline=YELLOW, size=50, padx=50, pady=22,
                   weight="Bold")
        bs, ba = pop(t, T_BOTH + 0.35, 0.5)
        paste_scaled(frame, bar, W / 2, CARD_Y + 1075, bs, ba * (1 - leave))


@lru_cache(maxsize=1)
def icon_badge_plus():
    s, c = surface(150, 150)
    c.arc(75, 79, 62, 0, 2 * math.pi)
    col(c, (0, 0, 0), 0.2)
    c.fill()
    c.arc(75, 75, 62, 0, 2 * math.pi)
    col(c, YELLOW)
    c.fill_preserve()
    col(c, WHITE)
    c.set_line_width(6)
    c.stroke()
    col(c, NAVY)
    c.set_line_width(14)
    c.move_to(75, 47); c.line_to(75, 103); c.move_to(47, 75); c.line_to(103, 75)
    c.stroke()
    return to_pil(s)


def draw_insight(frame, t):
    if t < T_INSIGHT or t > T_CTA + 0.4:
        return
    out = ease_in_out(prog(t, T_CTA - 0.35, T_CTA + 0.2))
    a_all = 1 - out
    s1, a1 = pop(t, T_INSIGHT + 0.2)
    paste_scaled(frame, text("ป่วยหนักหนึ่งครั้ง…", "SemiBold", 80, WHITE, shadow=10), W / 2, 640, s1, a1 * a_all)
    s2, a2 = pop(t, T_INSIGHT + 1.1, 0.5)
    paste_scaled(frame, text("ค่าใช้จ่ายไม่ได้จบ\nแค่ที่โรงพยาบาล", "ExtraBold", 104, YELLOW, stroke=6,
                             stroke_fill=NAVY, shadow=12, spacing=-10), W / 2, 860, s2, a2 * a_all)
    # floating cost icons
    names = ["car", "house", "wheelchair", "wallet", "receipt", "pill"]
    for i, n in enumerate(names):
        si, ai = pop(t, T_INSIGHT + 1.8 + i * 0.18)
        ang = -math.pi * 0.9 + i * (math.pi * 0.8 / (len(names) - 1))
        r = 380
        x = W / 2 + math.cos(ang + math.pi) * r * -1
        y = 1230 + math.sin(t * 2 + i) * 10
        x = 160 + i * 152
        paste_scaled(frame, icon_badge(n, PINK if i % 2 else BLUE, 110), x, y, si, ai * a_all)
    s3, a3 = pop(t, T_INSIGHT + 2.9)
    paste_scaled(frame, text("ประกันสุขภาพจ่าย “ค่ารักษา”\nประกันโรคร้ายช่วยดูแล “ชีวิตที่ต้องไปต่อ”",
                             "Medium", 46, WHITE, shadow=8, spacing=0), W / 2, 1420, s3, a3 * a_all)


def draw_cta(frame, t):
    if t < T_CTA:
        return
    s1, a1 = pop(t, T_CTA + 0.1)
    paste_scaled(frame, text("อย่ารอให้ป่วยก่อน", "Bold", 92, WHITE, shadow=10), W / 2, 430, s1, a1)
    s2, a2 = pop(t, T_CTA + 0.7, 0.5)
    paste_scaled(frame, text("แล้วค่อยรู้ว่า “ไม่พอ”", "ExtraBold", 112, PINK, stroke=7, stroke_fill=WHITE, shadow=12),
                 W / 2, 580, s2, a2)
    # equation card
    s3, a3 = pop(t, T_CTA + 1.9, 0.5)
    if a3 > 0:
        paste_scaled(frame, equation_card(), W / 2, 900, 0.9 + 0.1 * s3, a3)
    # button
    s4, a4 = pop(t, T_CTA + 3.4, 0.5)
    if a4 > 0:
        pulse = 1 + 0.035 * max(0.0, math.sin((t - T_CTA - 4.0) * 5)) if t > T_CTA + 4.0 else 1
        btn = pill("เช็กความคุ้มครองของคุณวันนี้", NAVY, YELLOW, outline=WHITE, size=54, padx=56, pady=30, weight="Bold")
        paste_scaled(frame, btn, W / 2, 1210, s4 * pulse, a4)
        s5, a5 = pop(t, T_CTA + 4.0)
        paste_scaled(frame, text("ทักแชท เพื่อวางแผนให้ครบทั้งสองแบบ", "Medium", 44, WHITE, shadow=8), W / 2, 1330, s5, a5)
    # disclaimer
    da = prog(t, T_CTA + 2.0, T_CTA + 2.6)
    if da > 0:
        d = text("ผู้ซื้อควรทำความเข้าใจรายละเอียดความคุ้มครอง เงื่อนไข และข้อยกเว้น\nก่อนตัดสินใจทำประกันภัยทุกครั้ง",
                 "Regular", 26, WHITE, spacing=0)
        paste_scaled(frame, d, W / 2, 1460, 1.0, da * 0.85)


@lru_cache(maxsize=1)
def equation_card():
    w, h = 960, 330
    s, c = surface(w + 30, h + 40)
    rrect(c, 15, 27, w, h, 40)
    col(c, (0, 20, 70), 0.25)
    c.fill()
    rrect(c, 15, 15, w, h, 40)
    col(c, WHITE, 0.97)
    c.fill()
    im = to_pil(s)
    a = pill("ประกันสุขภาพ", WHITE, BLUE, size=44, weight="Bold")
    b = pill("ประกันโรคร้าย", WHITE, PINK, size=44, weight="Bold")
    plus = text("+", "Black", 70, NAVY)
    total = a.width + plus.width + b.width + 20
    x = 15 + w / 2 - total / 2
    y = 60
    im.alpha_composite(a, dest=(int(x), y))
    im.alpha_composite(plus, dest=(int(x + a.width + 10), y - 14))
    im.alpha_composite(b, dest=(int(x + a.width + plus.width + 20), y))
    t_ = text("= คุ้มครองครบ ทั้ง “ค่ารักษา”\nและ “ค่าใช้จ่ายแฝง”", "Bold", 52, NAVY, spacing=-4)
    im.alpha_composite(t_, dest=(int(15 + w / 2 - t_.width / 2), 160))
    return im


@lru_cache(maxsize=16)
def caption_img(s):
    t_ = text(s, "Medium", 46, WHITE, spacing=-2)
    w, h = t_.width + 70, t_.height + 24
    sf, c = surface(w, h)
    rrect(c, 0, 0, w, h, 26)
    col(c, (6, 24, 70), 0.72)
    c.fill()
    im = to_pil(sf)
    im.alpha_composite(t_, dest=(35, 12))
    return im


def draw_captions(frame, t):
    for t0, t1, s in CAPTIONS:
        if t0 <= t <= t1:
            a = min(prog(t, t0, t0 + 0.2), 1 - prog(t, t1 - 0.15, t1))
            rise = (1 - ease_out(prog(t, t0, t0 + 0.25))) * 16
            paste_scaled(frame, caption_img(s), W / 2, 1535 + rise, 1.0, a)


def render_frame(t):
    frame = background(t)
    draw_header(frame, t)
    draw_columns(frame, t)
    draw_insight(frame, t)
    draw_cta(frame, t)
    draw_captions(frame, t)
    # fade in / out
    fade = min(prog(t, 0, 0.35), 1 - prog(t, DURATION - 0.5, DURATION))
    if fade < 1:
        frame.alpha_composite(Image.new("RGBA", frame.size, (0, 0, 0, int(255 * (1 - fade)))))
    return frame.convert("RGB")


# ================================================================ audio
POPS = ([0.25, 1.05, 1.6, 2.4] + [LEFT["card"], LEFT["chip"]] + LEFT["items"] + [RIGHT["card"], RIGHT["chip"]]
        + RIGHT["items"] + [T_BOTH, T_BOTH + 0.35] + [T_INSIGHT + 0.2, T_INSIGHT + 1.1]
        + [T_INSIGHT + 1.8 + i * 0.18 for i in range(6)] + [T_CTA + 0.1, T_CTA + 0.7, T_CTA + 1.9])
WHOOSH = [T_SPLIT - 0.3, T_INSIGHT - 0.35, T_CTA - 0.35]
DING = [T_CTA + 3.4]


def sfx_pop(pitch=1.0):
    n = int(0.12 * dsp.SR)
    t = np.arange(n) / dsp.SR
    f = (520 + 900 * np.exp(-t * 40)) * pitch
    x = np.sin(2 * np.pi * np.cumsum(f) / dsp.SR) * np.exp(-t * 32)
    return x * 0.7


def sfx_whoosh():
    n = int(0.55 * dsp.SR)
    x = dsp.noise(n, 7)
    out = np.zeros(n)
    for k in range(8):
        a, b = k * n // 8, (k + 1) * n // 8
        cf = 400 + 2600 * math.sin(math.pi * (k + 0.5) / 8)
        out[a:b] = dsp.bp(x, cf * 0.7, cf * 1.4)[a:b]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2 * 0.5


def sfx_ding():
    t = np.arange(int(1.2 * dsp.SR)) / dsp.SR
    x = sum(np.sin(2 * np.pi * f * t) * g for f, g in [(1318.5, 0.6), (1975.5, 0.3), (2637, 0.15)])
    return x * np.exp(-t * 4) * 0.5


def music(total):
    """Bright, friendly pop-pluck bed (original, royalty-free), 112 BPM."""
    sr, bpm = dsp.SR, 112
    beat = 60 / bpm
    n = int((total + 2) * sr)
    out = np.zeros((n, 2))
    prog_ = [(48, [60, 64, 67, 72]), (43, [59, 62, 67, 71]), (45, [60, 64, 69, 72]), (41, [57, 60, 65, 69])]  # C G Am F

    def add(clip, t, g=1.0, pan=0.0):
        i = int(t * sr)
        if i >= n:
            return
        c = dsp.pan_stereo(clip, pan)
        m = min(len(c), n - i)
        out[i:i + m] += c[:m] * g

    def pluck(f, dur=0.32, cut=3000):
        t = np.arange(int(dur * sr)) / sr
        x = dsp.saw(f, t) * 0.5 + np.sin(2 * np.pi * f * t) * 0.6
        return dsp.lp(x, cut) * np.exp(-t * 9)

    def pad(f, dur):
        t = np.arange(int(dur * sr)) / sr
        x = (dsp.saw(f, t, -0.004) + dsp.saw(f, t, 0.004)) * 0.3
        return dsp.lp(x, 1400) * dsp.env_adsr(len(t), 0.3, 0.3, 0.8, 0.6)

    def kick():
        t = np.arange(int(0.3 * sr)) / sr
        return np.sin(2 * np.pi * np.cumsum(50 + 90 * np.exp(-t * 30)) / sr) * np.exp(-t * 9)

    def clap():
        m = int(0.18 * sr)
        return dsp.bp(dsp.noise(m, 4), 900, 4000) * np.exp(-np.arange(m) / sr * 22) * 0.6

    def shaker():
        m = int(0.06 * sr)
        return dsp.hp(dsp.noise(m, 9), 6000) * np.exp(-np.arange(m) / sr * 60) * 0.4

    steps = int(total / (beat / 2))
    for s in range(steps):
        t = s * beat / 2
        bar = int(t / (beat * 4))
        bass, chord = prog_[bar % 4]
        pos = s % 8
        insight = T_INSIGHT <= t < T_CTA          # breakdown: soft pad only
        full = T_SPLIT <= t < T_INSIGHT or t >= T_CTA + 0.8
        if pos == 0:
            for k, m in enumerate(chord):
                add(pad(dsp.midi_hz(m), beat * 4), t, 0.05 if not insight else 0.07, (k - 1.5) * 0.3)
        if not insight:
            m = chord[[0, 2, 1, 3, 2, 1, 3, 2][pos]] + 12
            add(pluck(dsp.midi_hz(m), cut=2600 if full else 1600), t, 0.09, 0.35 if pos % 2 else -0.35)
            if t >= T_SPLIT - 0.5:
                add(pluck(dsp.midi_hz(bass), 0.28, 500), t, 0.22 if pos % 2 == 0 else 0.12)
            if full:
                if pos % 2 == 0:
                    add(kick(), t, 0.55)
                if pos in (2, 6):
                    add(clap(), t, 0.35)
                add(shaker(), t + beat / 4, 0.18, 0.3)
    out = dsp.convolve_stereo(out, dsp.reverb_ir(1.6)) * 0.25 + out
    fade = np.ones(n)
    i0, i1 = int((total - 1.5) * sr), int(total * sr)
    fade[i0:i1] = np.linspace(1, 0, i1 - i0)
    fade[i1:] = 0
    out *= fade[:, None]
    return out[: int(total * sr)]


def build_audio(path):
    total = DURATION
    m = music(total)
    m = m / (np.abs(m).max() + 1e-9) * 0.55
    fx = np.zeros_like(m)

    def place(clip, t, g):
        i = int(t * dsp.SR)
        c = np.stack([clip, clip], -1)
        k = min(len(c), len(fx) - i)
        if k > 0:
            fx[i:i + k] += c[:k] * g

    for i, t in enumerate(POPS):
        place(sfx_pop(1.0 + (i % 5) * 0.06), t, 0.45)
    for t in WHOOSH:
        place(sfx_whoosh(), t, 0.5)
    for t in DING:
        place(sfx_ding(), t, 0.5)
    mix = dsp.soft_limit(m + fx, 0.9)
    mix *= 0.7 / (np.abs(mix).max() + 1e-9)
    dsp.write_wav(path, mix)
    # loudness to ~-14 LUFS for social platforms
    import re
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])
    g = dsp.db(-14.0 - lufs)
    mix = dsp.soft_limit(mix * g, 0.95)
    pk = np.abs(mix).max()
    if pk > dsp.db(-2.0):
        mix *= dsp.db(-2.0) / pk
    dsp.write_wav(path, mix)


# ================================================================ render
def render_chunk(args):
    f0, f1, path = args
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "17", "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(np.asarray(render_frame(f / FPS)).tobytes())
    p.stdin.close()
    p.wait()
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", default="")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    a = ap.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    if a.still:
        for s in a.still.split(","):
            render_frame(float(s)).save(BUILD / f"still_{float(s):05.1f}.png")
        return
    n = int(DURATION * FPS)
    chunk = 60
    tasks = [(f, min(n, f + chunk), BUILD / f"chunk_{f:05d}.mp4") for f in range(0, n, chunk)]
    with ProcessPoolExecutor(a.jobs) as ex:
        list(ex.map(render_chunk, tasks))
    lst = BUILD / "chunks.txt"
    lst.write_text("".join(f"file '{t[2]}'\n" for t in tasks))
    video = BUILD / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    str(video)], check=True)
    audio = BUILD / "audio.wav"
    build_audio(audio)
    out = OUT / "health_vs_critical_illness_reel_9x16.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(out)], check=True)
    # captions sidecar (for platform auto-captions / translation)
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    srt = "".join(f"{i}\n{ts(t0)} --> {ts(t1)}\n{s}\n\n" for i, (t0, t1, s) in enumerate(CAPTIONS, 1))
    (OUT / "health_vs_critical_illness_reel_9x16.th.srt").write_text(srt, encoding="utf-8")
    print("done ->", out)


if __name__ == "__main__":
    main()
