"""Conceptual still plates (pre-visualisation art), generated procedurally.

Each builder returns a dict {layer_name: PIL RGBA} with layers among
``bg`` (far), ``mid``, ``fx`` and ``fg`` (near). They are written to
``assets/images/<plate>__<layer>.png`` by ``scripts/build_assets.py`` and can be
swapped for real photography / AI stills later (keep 16:9, >= 2304x1296).

Composition rule: key subjects sit inside plate x = 850..1450 (the centre
column that survives a future 9:16 crop).
"""
import math

import cairo
from PIL import Image

from . import config as C
from .engine.canvas import (blur, fast_blur, glow, glow_spot, linear_fill, radial_fill,
                            rounded_rect, set_col, surface, to_pil)
from .engine.pcb import (circuit_backdrop, draw_board, node, random_traces, route,
                         stroke_poly)
from .engine import props as P
from .engine.util import rng

PW, PH = 2304, 1296
CX, CY = PW / 2, PH / 2
REGISTRY = {}


def plate(name):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco


def L():
    return surface(PW, PH)


def img(s, b=0):
    im = to_pil(s)
    return fast_blur(im, b) if b else im


def warm_room_light(ctx, x, y, r, a=0.55, col=C.WARM):
    radial_fill(ctx, x, y, 0, r, [(0, col, a), (0.5, col, a * 0.35), (1, col, 0)])
    ctx.paint()


# ============================================================ 01 HOOK
@plate("hook_solder")
def hook_solder():
    s, ctx = L()
    set_col(ctx, (6, 8, 7), 1)
    ctx.paint()
    feats = draw_board(ctx, -300, -200, 2900, 1700, seed=3, mask=(14, 40, 26), density=1.4,
                       label="HOME CIRCUIT", sub="PROTO-01")
    warm = to_pil(s)
    # depth of field: sharp band in the middle
    far = fast_blur(warm, 10)
    bg = Image.composite(warm, far, _band_mask(PH, 0.5, 0.26))
    s2, c2 = L()
    radial_fill(c2, CX, CY, 0, 1300, [(0, (0, 0, 0), 0), (1, (0, 0, 0), 0.75)])
    c2.paint()
    bg.alpha_composite(to_pil(s2))
    # solder pads at the joint
    s3, c3 = L()
    for i in range(6):
        px = CX - 150 + i * 60
        c3.arc(px, CY + 40, 16, 0, 2 * math.pi)
        radial_fill(c3, px - 5, CY + 35, 0, 18, [(0, (250, 250, 250), 1), (1, (150, 150, 155), 1)])
        c3.fill()
    mid = to_pil(s3)
    # iron (foreground, sharp) coming from top right
    s4, c4 = L()
    P.soldering_iron(c4, PW + 200, -260, CX + 40, CY + 22, width=120)
    P.wire(c4, [(CX + 30, CY + 40), (CX + 260, CY + 160), (CX + 520, CY + 330), (CX + 700, PH + 50)], (205, 205, 210), 10)
    fg = to_pil(s4)
    return {"bg": bg, "mid": mid, "fg": fg}


def _band_mask(h, center=0.5, width=0.25, w=PW):
    import numpy as np
    y = np.linspace(0, 1, h)[:, None]
    m = np.clip(1 - np.abs(y - center) / width, 0, 1) ** 0.8
    m = np.repeat(m, w, 1)
    return Image.fromarray((m * 255).astype("uint8"), "L")


@plate("hook_components")
def hook_components():
    s, ctx = L()
    # dark cutting mat
    set_col(ctx, (14, 22, 18), 1)
    ctx.paint()
    set_col(ctx, (60, 110, 80), 0.25)
    ctx.set_line_width(1.5)
    for gx in range(0, PW, 64):
        ctx.move_to(gx, 0)
        ctx.line_to(gx, PH)
    for gy in range(0, PH, 64):
        ctx.move_to(0, gy)
        ctx.line_to(PW, gy)
    ctx.stroke()
    radial_fill(ctx, CX - 200, CY - 300, 0, 1500, [(0, C.WARM, 0.18), (1, (0, 0, 0), 0.0)])
    ctx.paint()
    bg = to_pil(s)
    s2, c2 = L()
    r = rng(12)
    for i in range(26):
        x, y = r.uniform(300, PW - 300), r.uniform(200, PH - 200)
        k = r.random()
        if k < 0.4:
            P.through_hole_resistor(c2, x, y, r.uniform(70, 110), r.uniform(0, math.pi), r)
        elif k < 0.6:
            P.electrolytic(c2, x, y, r.uniform(30, 55))
        elif k < 0.8:
            P.dip_ic(c2, x, y, r.uniform(180, 240), r.uniform(70, 90), r.uniform(-0.5, 0.5), r.choice(["ATmega", "ESP32", "LM358", "HC595"]))
        else:
            P.led_5mm(c2, x, y, r.uniform(18, 26), r.choice([C.GREEN, (255, 90, 60), (250, 250, 240)]), on=False)
    mid = to_pil(s2)
    # hero component sharp, others blurred by distance from centre
    sharp = mid.copy()
    soft = fast_blur(mid, 9)
    mid = Image.composite(sharp, soft, _radial_mask(PW, PH, 520))
    s3, c3 = L()
    P.dip_ic(c3, CX + 20, CY, 420, 150, -0.12, "HC32-M0")
    P.electrolytic(c3, CX - 330, CY + 170, 60)
    P.through_hole_resistor(c3, CX + 250, CY + 230, 140, 0.3, r)
    hero = to_pil(s3)
    s4, c4 = L()
    for i in range(5):
        P.through_hole_resistor(c4, r.uniform(0, PW), r.choice([r.uniform(-50, 200), r.uniform(PH - 200, PH + 50)]), 260, r.uniform(0, 3), r)
    fg = fast_blur(to_pil(s4), 26)
    return {"bg": bg, "mid": mid, "fx": hero, "fg": fg}


def _radial_mask(w, h, r):
    import numpy as np
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((x - w / 2) ** 2 + (y - h / 2) ** 2)
    m = np.clip(1 - (d - r) / (r * 0.9), 0, 1)
    return Image.fromarray((m * 255).astype("uint8"), "L")


@plate("hook_code")
def hook_code():
    s, ctx = L()
    set_col(ctx, (10, 12, 13), 1)
    ctx.paint()
    # editor chrome
    set_col(ctx, (16, 19, 20), 1)
    ctx.rectangle(0, 0, PW, PH)
    ctx.fill()
    set_col(ctx, (24, 28, 29), 1)
    ctx.rectangle(0, 0, 260, PH)
    ctx.fill()
    ctx.rectangle(0, 0, PW, 70)
    ctx.fill()
    for i, w in enumerate([240, 200, 180]):
        rounded_rect(ctx, 290 + i * 260, 16, w, 40, 6)
        set_col(ctx, (34, 40, 40) if i else (40, 52, 46), 1)
        ctx.fill()
    set_col(ctx, C.GREEN, 0.9)
    ctx.rectangle(290, 54, 240, 3)
    ctx.fill()
    for j in range(22):
        rounded_rect(ctx, 30, 110 + j * 44, 120 + (j * 37) % 100, 16, 4)
        set_col(ctx, (70, 78, 78), 0.5)
        ctx.fill()
    bg = to_pil(s)
    s2, c2 = L()
    # screen glass reflection
    linear_fill(c2, 0, 0, PW, PH, [(0, (255, 255, 255), 0.05), (0.4, (255, 255, 255), 0.0), (1, (255, 255, 255), 0.02)])
    c2.paint()
    fg = to_pil(s2)
    return {"bg": bg, "fg": fg}


@plate("hook_scope")
def hook_scope():
    s, ctx = L()
    set_col(ctx, (8, 9, 10), 1)
    ctx.paint()
    # large bezel around a screen that fills most of the frame
    rounded_rect(ctx, 180, 110, PW - 360, PH - 220, 30)
    set_col(ctx, (30, 32, 34), 1)
    ctx.fill()
    rounded_rect(ctx, 230, 160, PW - 460, PH - 320, 12)
    set_col(ctx, (5, 10, 8), 1)
    ctx.fill()
    ctx.select_font_face("Noto Sans Mono")
    ctx.set_font_size(30)
    set_col(ctx, C.GREEN, 0.9)
    ctx.move_to(270, 215)
    ctx.show_text("CH1  2.00V/div   500us/div   TRIG ↑ 1.65V")
    set_col(ctx, (230, 190, 90), 0.9)
    ctx.move_to(PW - 900, 215)
    ctx.show_text("CH2  1.00V   RUN")
    bg = to_pil(s)
    s2, c2 = L()
    linear_fill(c2, 0, 0, PW * 0.6, PH, [(0, (255, 255, 255), 0.06), (0.5, (255, 255, 255), 0.0)])
    c2.paint()
    return {"bg": bg, "fg": to_pil(s2)}


SCOPE_RECT_HOOK = (230, 250, PW - 460, PH - 410)


@plate("hook_hands")
def hook_hands():
    s, ctx = L()
    set_col(ctx, (8, 8, 8), 1)
    ctx.paint()
    draw_board(ctx, 200, 150, 1900, 1100, seed=21, mask=(16, 46, 30), density=1.2, label="HOME CIRCUIT", sub="IO-EXP REV B")
    # empty footprint at centre (where the chip is placed)
    for i in range(8):
        ctx.rectangle(CX - 170 + i * 44, CY - 110, 22, 40)
        ctx.rectangle(CX - 170 + i * 44, CY + 70, 22, 40)
    set_col(ctx, (220, 200, 150), 1)
    ctx.fill()
    radial_fill(ctx, CX, CY, 0, 1300, [(0, C.WARM, 0.12), (1, (0, 0, 0), 0.7)])
    ctx.paint()
    bg = to_pil(s)
    bg = Image.composite(bg, fast_blur(bg, 8), _radial_mask(PW, PH, 560))
    # out-of-focus hands (foreground)
    s2, c2 = L()
    P.hand_blob(c2, CX - 900, CY + 420, 380, -0.5)
    P.hand_blob(c2, CX + 1000, CY - 480, 360, 2.6)
    fg = fast_blur(to_pil(s2), 36)
    return {"bg": bg, "fg": fg}


@plate("hook_drone")
def hook_drone():
    s, ctx = L()
    set_col(ctx, (10, 11, 12), 1)
    ctx.paint()
    # carbon weave
    for i in range(-PH, PW, 18):
        ctx.move_to(i, 0)
        ctx.line_to(i + PH, PH)
        set_col(ctx, (30, 32, 35), 0.5 if (i // 18) % 2 else 0.2)
        ctx.set_line_width(9)
        ctx.stroke()
    radial_fill(ctx, CX, CY, 0, 1400, [(0, (0, 0, 0), 0), (1, (0, 0, 0), 0.8)])
    ctx.paint()
    bg = to_pil(s)
    s2, c2 = L()
    # flight controller stack macro
    draw_board(c2, CX - 520, CY - 420, 840, 840, seed=41, mask=(12, 18, 15), density=0.9, label="HC-FC", sub="F4 STACK", terminals=False)
    # motor bell with windings (right)
    mx, my = CX + 560, CY + 120
    c2.arc(mx, my, 260, 0, 2 * math.pi)
    radial_fill(c2, mx - 40, my - 40, 0, 280, [(0, (120, 124, 130), 1), (1, (26, 27, 29), 1)])
    c2.fill()
    for k in range(12):
        a = k / 12 * 2 * math.pi
        c2.save()
        c2.translate(mx + math.cos(a) * 150, my + math.sin(a) * 150)
        c2.rotate(a)
        rounded_rect(c2, -40, -26, 80, 52, 10)
        c2.restore()
        radial_fill(c2, mx, my, 100, 200, [(0, (220, 140, 60), 1), (1, (140, 80, 30), 1)])
        c2.fill()
    c2.arc(mx, my, 60, 0, 2 * math.pi)
    set_col(c2, (180, 184, 190), 1)
    c2.fill()
    # wires
    for i, col in enumerate([(200, 40, 40), (20, 20, 20), (200, 200, 60)]):
        P.wire(c2, [(CX + 300, CY + 250 + i * 26), (CX + 380, CY + 330), (mx - 200, my + 200), (mx - 120, my + 180 + i * 20)], col, 16)
    mid = to_pil(s2)
    return {"bg": bg, "mid": mid}


# ============================================================ 02 BEGINNING
@plate("home_exterior")
def home_exterior():
    s, ctx = L()
    linear_fill(ctx, 0, 0, 0, PH, [(0, (10, 16, 34), 1), (0.5, (44, 46, 78), 1), (0.78, (170, 96, 70), 1), (1, (236, 150, 86), 1)])
    ctx.paint()
    r = rng(4)
    for _ in range(90):
        set_col(ctx, (255, 255, 255), r.uniform(0.2, 0.7))
        ctx.arc(r.uniform(0, PW), r.uniform(0, PH * 0.35), r.uniform(0.8, 1.8), 0, 2 * math.pi)
        ctx.fill()
    # distant tree line / neighbour roofs
    ctx.move_to(0, PH)
    x = 0
    while x < PW:
        ctx.line_to(x, PH * 0.8 - r.uniform(0, 70) - (60 if r.random() < 0.2 else 0))
        x += r.uniform(30, 80)
    ctx.line_to(PW, PH)
    ctx.close_path()
    set_col(ctx, (22, 22, 34), 1)
    ctx.fill()
    bg = blur(to_pil(s), 3)
    # house
    s2, c2 = L()
    hx, hy, hw, hh = CX - 520, PH * 0.42, 1040, PH * 0.6
    # roof (hip)
    c2.move_to(hx - 90, hy)
    c2.line_to(hx + 180, hy - 190)
    c2.line_to(hx + hw - 180, hy - 190)
    c2.line_to(hx + hw + 90, hy)
    c2.close_path()
    set_col(c2, (26, 22, 26), 1)
    c2.fill()
    c2.rectangle(hx, hy, hw, hh)
    linear_fill(c2, hx, hy, hx, hy + hh, [(0, (46, 40, 44), 1), (1, (26, 24, 28), 1)])
    c2.fill()
    # second floor slab / balcony
    c2.rectangle(hx - 40, hy + 250, hw + 80, 26)
    set_col(c2, (30, 26, 30), 1)
    c2.fill()
    # windows upper
    for i in range(3):
        wx = hx + 110 + i * 300
        c2.rectangle(wx, hy + 60, 180, 140)
        lit = i == 1
        set_col(c2, (255, 196, 120) if lit else (40, 44, 64), 1 if lit else 0.9)
        c2.fill()
        set_col(c2, (30, 26, 30), 1)
        c2.set_line_width(8)
        c2.move_to(wx + 90, hy + 60)
        c2.line_to(wx + 90, hy + 200)
        c2.stroke()
    # ground floor workshop window (big, warm, with silhouettes)
    wx, wy, ww, wh = CX - 330, hy + 330, 660, 300
    c2.rectangle(wx, wy, ww, wh)
    linear_fill(c2, wx, wy, wx, wy + wh, [(0, (255, 214, 150), 1), (1, (230, 140, 70), 1)])
    c2.fill()
    # interior silhouettes inside window
    P.pendant_lamp(c2, CX, wy + 30, 110, wy)
    set_col(c2, (70, 40, 24), 1)
    c2.rectangle(wx, wy + wh * 0.72, ww, wh * 0.28)
    c2.fill()
    for i, px in enumerate([CX - 210, CX - 60, CX + 110, CX + 240]):
        P.person(c2, px, wy + wh * 0.78, 150 + (i % 2) * 20, col=(60, 34, 22), arm_to=(px + 30, wy + wh * 0.74), arm2_to=(px - 30, wy + wh * 0.74))
    # window frame
    set_col(c2, (24, 22, 24), 1)
    c2.set_line_width(12)
    c2.rectangle(wx, wy, ww, wh)
    c2.stroke()
    c2.move_to(wx + ww / 3, wy)
    c2.line_to(wx + ww / 3, wy + wh)
    c2.move_to(wx + 2 * ww / 3, wy)
    c2.line_to(wx + 2 * ww / 3, wy + wh)
    c2.stroke()
    # door + AC unit
    c2.rectangle(hx + hw - 230, hy + 360, 150, 330)
    set_col(c2, (36, 30, 30), 1)
    c2.fill()
    rounded_rect(c2, hx + 60, hy + 290 + 80, 150, 90, 8)
    set_col(c2, (70, 70, 76), 1)
    c2.fill()
    # fence
    for fx in range(0, PW, 46):
        c2.rectangle(fx, PH * 0.88, 10, PH * 0.12)
    c2.rectangle(0, PH * 0.9, PW, 10)
    set_col(c2, (14, 13, 16), 1)
    c2.fill()
    # electric pole & sagging wires (Thai street detail)
    px = PW - 380
    c2.rectangle(px, PH * 0.1, 26, PH * 0.9)
    set_col(c2, (18, 18, 22), 1)
    c2.fill()
    c2.rectangle(px - 120, PH * 0.16, 270, 14)
    c2.fill()
    for k in range(5):
        y0 = PH * 0.16 + (k % 2) * 60 + k * 14
        c2.move_to(-50, y0 - 40 + k * 18)
        c2.curve_to(PW * 0.3, y0 + 120, PW * 0.6, y0 + 110, px + 10, y0)
        set_col(c2, (12, 12, 16), 0.95)
        c2.set_line_width(3)
        c2.stroke()
    mid = to_pil(s2)
    # window glow halo
    s3, c3 = L()
    glow_spot(c3, CX, wy + wh / 2, 700, C.WARM, 0.35)
    glow_spot(c3, hx + 110 + 300 + 90, hy + 130, 260, C.WARM, 0.3)
    fx = to_pil(s3)
    # foreground foliage (banana leaves)
    s4, c4 = L()
    for base_x, base_y, sc, flip in [(-60, PH + 40, 1.3, 1), (PW + 80, PH + 60, 1.1, -1)]:
        for k in range(5):
            a = -math.pi / 2 + flip * (0.3 + k * 0.28)
            L_ = 700 * sc * (1 - k * 0.08)
            ex, ey = base_x + math.cos(a) * L_, base_y + math.sin(a) * L_
            c4.move_to(base_x, base_y)
            c4.curve_to(base_x + math.cos(a - 0.3) * L_ * 0.5, base_y + math.sin(a - 0.3) * L_ * 0.5,
                        ex + 80, ey + 40, ex, ey)
            c4.curve_to(ex - 60, ey + 80, base_x + math.cos(a + 0.35) * L_ * 0.5, base_y + math.sin(a + 0.35) * L_ * 0.5, base_x, base_y)
            set_col(c4, (8, 14, 10), 1)
            c4.fill()
    fg = fast_blur(to_pil(s4), 10)
    return {"bg": bg, "mid": mid, "fx": fx, "fg": fg}


@plate("workshop_wide")
def workshop_wide():
    s, ctx = L()
    # back wall
    linear_fill(ctx, 0, 0, 0, PH, [(0, (46, 34, 26), 1), (1, (26, 20, 16), 1)])
    ctx.paint()
    # window (evening blue) left
    wx, wy, ww, wh = 180, 170, 560, 520
    ctx.rectangle(wx, wy, ww, wh)
    linear_fill(ctx, wx, wy, wx, wy + wh, [(0, (28, 40, 80), 1), (1, (90, 90, 130), 1)])
    ctx.fill()
    ctx.move_to(wx, wy + wh * 0.8)
    for i in range(12):
        ctx.line_to(wx + i * ww / 11, wy + wh * (0.72 + (i % 3) * 0.04))
    ctx.line_to(wx + ww, wy + wh)
    ctx.line_to(wx, wy + wh)
    ctx.close_path()
    set_col(ctx, (18, 20, 34), 1)
    ctx.fill()
    set_col(ctx, (20, 16, 14), 1)
    ctx.set_line_width(16)
    ctx.rectangle(wx, wy, ww, wh)
    ctx.move_to(wx + ww / 2, wy)
    ctx.line_to(wx + ww / 2, wy + wh)
    ctx.stroke()
    # curtain
    ctx.move_to(wx - 90, wy - 40)
    ctx.curve_to(wx - 30, wy + 200, wx - 110, wy + 400, wx - 60, wy + wh + 80)
    ctx.line_to(wx + 30, wy + wh + 80)
    ctx.curve_to(wx + 10, wy + 300, wx + 60, wy + 100, wx + 20, wy - 40)
    set_col(ctx, (70, 52, 40), 1)
    ctx.fill()
    # pegboard with tools (right)
    px, py = 1500, 150
    rounded_rect(ctx, px, py, 620, 430, 8)
    set_col(ctx, (70, 56, 42), 1)
    ctx.fill()
    set_col(ctx, (40, 30, 22), 1)
    for i in range(24):
        for j in range(17):
            ctx.arc(px + 20 + i * 25, py + 20 + j * 24, 3, 0, 2 * math.pi)
            ctx.fill()
    for i, (tx, tl) in enumerate([(1560, 200), (1640, 160), (1720, 230), (1820, 180), (1930, 150), (2020, 210)]):
        ctx.move_to(tx, py + 60)
        ctx.line_to(tx + (i % 2) * 20, py + 60 + tl)
        set_col(ctx, (30, 30, 32) if i % 2 else (140, 40, 30), 1)
        ctx.set_line_width(18 if i % 3 else 10)
        ctx.stroke()
    # drawer cabinet on shelf
    P.drawer_cabinet(ctx, 880, 240, 6, 4, 70, 50)
    ctx.rectangle(820, 470, 560, 16)
    set_col(ctx, (60, 44, 32), 1)
    ctx.fill()
    for i in range(5):
        rounded_rect(ctx, 850 + i * 100, 400, 80, 70, 6)
        set_col(ctx, [(120, 60, 40), (40, 80, 120), (60, 60, 64), (160, 140, 90), (40, 90, 60)][i], 0.9)
        ctx.fill()
    # standing fan (Thai home detail)
    P.standing_fan(ctx, 2150, 560, 300, col=(24, 24, 26))
    bg = to_pil(s)
    # lamp light on wall
    s1, c1 = L()
    warm_room_light(c1, CX, 420, 1300, 0.42)
    bg.alpha_composite(to_pil(s1))
    bg = fast_blur(bg, 6)
    # --- mid: table + engineers
    s2, c2 = L()
    ty = 820
    # far side people
    people = [(CX - 470, ty + 20, 360, dict(arm_to=(CX - 420, ty + 40), arm2_to=(CX - 520, ty + 30))),
              (CX - 60, ty + 10, 390, dict(arm_to=(CX - 10, ty + 30), arm2_to=(CX - 110, ty + 40), lean=0.06)),
              (CX + 380, ty + 20, 370, dict(arm_to=(CX + 330, ty + 40), arm2_to=(CX + 450, ty + 30), lean=-0.05))]
    for x, y, sc, kw in people:
        P.person(c2, x, y, sc, col=(18, 14, 12), **kw)
    # standing engineer leaning over (left)
    P.person(c2, CX - 820, ty - 80, 420, col=(16, 13, 12), lean=0.28, arm_to=(CX - 650, ty + 30), standing_h=300)
    ppl = P.rim_light(to_pil(s2), dx=-7, dy=6, col=(255, 180, 110), strength=1.0, spread=2.5)
    s3, c3 = L()
    # table
    c3.move_to(80, ty + 30)
    c3.line_to(PW - 80, ty + 30)
    c3.line_to(PW + 200, PH)
    c3.line_to(-200, PH)
    c3.close_path()
    c3.save()
    c3.clip()
    P.wood_surface(c3, -200, ty + 30, PW + 400, PH - ty, base=(110, 72, 44), seed=3)
    c3.restore()
    radial_fill(c3, CX, ty + 150, 0, 1100, [(0, C.WARM, 0.35), (1, C.WARM, 0.0)])
    c3.paint()
    # laptops, scope, board on table
    scr1 = P.laptop_open(c3, CX - 330, ty + 110, 300)
    scr2 = P.laptop_open(c3, CX + 250, ty + 120, 280)
    for sx, sy, sw, sh in (scr1, scr2):
        linear_fill(c3, sx, sy, sx, sy + sh, [(0, (30, 60, 46), 1), (1, (12, 22, 18), 1)])
        c3.rectangle(sx, sy, sw, sh)
        c3.fill()
        for k in range(7):
            c3.rectangle(sx + 14, sy + 14 + k * 20, (k * 53) % (sw * 0.7) + 40, 7)
        set_col(c3, (140, 220, 170), 0.7)
        c3.fill()
    scope_scr = P.oscilloscope(c3, CX - 40, ty - 60, 280, 170)
    draw_board(c3, CX + 620, ty + 180, 300, 190, seed=9, mask=(16, 46, 30), density=0.6, label="HC", sub="")
    P.multimeter(c3, CX - 900, ty + 170, 120)
    P.wire(c3, [(CX - 840, ty + 180), (CX - 700, ty + 120), (CX - 500, ty + 300), (CX - 380, ty + 220)], (200, 40, 40), 8)
    P.wire(c3, [(CX - 820, ty + 190), (CX - 680, ty + 260), (CX - 520, ty + 360), (CX - 360, ty + 260)], (22, 22, 22), 8)
    P.pendant_lamp(c3, CX, 200, 240, -10)
    table = to_pil(s3)
    mid = table.copy()
    # people sit behind the table: composite people first then table on top
    mid = ppl.copy()
    mid.alpha_composite(table)
    # --- fx: lamp glow + screen glow
    s4, c4 = L()
    glow_spot(c4, CX, 300, 520, (255, 210, 150), 0.55)
    for sx, sy, sw, sh in (scr1, scr2):
        glow_spot(c4, sx + sw / 2, sy + sh / 2, 300, (120, 230, 170), 0.18)
    fx = to_pil(s4)
    # --- fg: near person (back to camera) + mug, heavily blurred
    s5, c5 = L()
    P.person(c5, CX + 820, PH + 330, 760, col=(10, 9, 9), arm_to=(CX + 560, PH + 60))
    fg = fast_blur(to_pil(s5), 22)
    return {"bg": bg, "mid": mid, "fx": fx, "fg": fg}


@plate("workshop_table")
def workshop_table():
    """Overhead flat-lay of the workbench."""
    s, ctx = L()
    P.wood_surface(ctx, 0, 0, PW, PH, base=(104, 70, 44), seed=8, lines=260)
    bg = to_pil(s)
    s2, c2 = L()
    r = rng(5)
    # breadboard with wiring
    P.breadboard(c2, CX - 520, CY - 120, 560, 250)
    for i in range(7):
        col = r.choice([(200, 40, 40), (30, 30, 30), (230, 190, 40), (40, 120, 220), (40, 170, 90)])
        x0 = CX - 480 + i * 70
        P.wire(c2, [(x0, CY - 60), (x0 + 30, CY - 240), (CX + 120 + i * 20, CY - 260), (CX + 150 + i * 22, CY - 110)], col, 8)
    # dev board (HC) centre-right
    feats = draw_board(c2, CX + 80, CY - 150, 520, 330, seed=15, mask=(14, 40, 26), density=0.9,
                       label="HOME CIRCUIT", sub="DEV-KIT v0.3")
    # multimeter bottom-left with probes
    disp, _ = P.multimeter(c2, CX - 900, CY + 40, 250)
    P.wire(c2, [(CX - 820, CY + 470), (CX - 700, CY + 600), (CX - 300, CY + 500), (CX + 160, CY + 150)], (200, 40, 40), 10)
    P.wire(c2, [(CX - 760, CY + 470), (CX - 600, CY + 650), (CX - 200, CY + 560), (CX + 250, CY + 170)], (20, 20, 20), 10)
    # soldering iron top-right on stand
    P.soldering_iron(c2, PW + 120, -60, CX + 720, CY - 360, width=70, tip_hot=False)
    c2.arc(PW - 200, 180, 90, 0, 2 * math.pi)
    set_col(c2, (200, 180, 120), 0.8)
    c2.fill()
    # solder spool
    c2.arc(CX + 850, CY + 300, 110, 0, 2 * math.pi)
    set_col(c2, (180, 184, 190), 1)
    c2.fill()
    c2.arc(CX + 850, CY + 300, 40, 0, 2 * math.pi)
    set_col(c2, (30, 30, 30), 1)
    c2.fill()
    # component tray bottom
    for i in range(10):
        P.through_hole_resistor(c2, CX - 300 + i * 50, CY + 350 + (i % 2) * 20, 70, 1.2, r)
    P.electrolytic(c2, CX + 150, CY + 360, 36)
    P.electrolytic(c2, CX + 240, CY + 380, 30)
    # notebook with sketch (top-left)
    c2.save()
    c2.translate(260, 120)
    c2.rotate(-0.08)
    c2.rectangle(0, 0, 520, 380)
    set_col(c2, (236, 230, 214), 1)
    c2.fill()
    for k in range(14):
        c2.move_to(20, 30 + k * 25)
        c2.line_to(500, 30 + k * 25)
    set_col(c2, (150, 170, 200), 0.4)
    c2.set_line_width(1.5)
    c2.stroke()
    c2.rectangle(70, 90, 190, 130)
    c2.move_to(260, 150)
    c2.line_to(380, 150)
    c2.rectangle(380, 110, 90, 80)
    set_col(c2, (60, 60, 64), 0.85)
    c2.set_line_width(3)
    c2.stroke()
    c2.restore()
    mid = to_pil(s2)
    shadow = fast_blur(mid, 14)
    import numpy as np
    sh = np.asarray(shadow).copy()
    sh[..., :3] = 0
    sh[..., 3] = (sh[..., 3] * 0.6).astype(np.uint8)
    shadow = Image.fromarray(sh, "RGBA")
    base = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    base.alpha_composite(shadow, dest=(18, 22))
    base.alpha_composite(mid)
    s3, c3 = L()
    radial_fill(c3, CX - 300, CY - 300, 0, 1700, [(0, C.WARM, 0.25), (0.6, (0, 0, 0), 0.0), (1, (0, 0, 0), 0.6)])
    c3.paint()
    base.alpha_composite(to_pil(s3))
    return {"bg": bg, "mid": base}


MULTIMETER_DISPLAY_TABLE = (CX - 900 + 250 * 0.16, CY + 40 + 250 * 0.2, 250 * 0.68, 250 * 0.42)


@plate("workshop_scope")
def workshop_scope():
    s, ctx = L()
    linear_fill(ctx, 0, 0, 0, PH, [(0, (40, 30, 24), 1), (1, (20, 16, 14), 1)])
    ctx.paint()
    P.bokeh(ctx, PW, PH, 30, 3, [C.WARM, (255, 220, 170)], 30, 110, 0.05, 0.2, (0, 0, PW, PH * 0.6))
    # background engineer (blurred)
    P.person(ctx, CX + 620, 980, 620, col=(20, 16, 14), lean=-0.18, arm_to=(CX + 350, 980))
    bg = fast_blur(to_pil(s), 14)
    bg = P.rim_light(bg, -8, 0, C.WARM, 0.3, 6)
    s2, c2 = L()
    # table
    c2.rectangle(0, 900, PW, PH - 900)
    P.wood_surface(c2, 0, 900, PW, PH - 900, base=(100, 66, 40), seed=12, lines=60)
    # laptop (right, background-ish)
    scr = P.laptop_open(c2, CX + 250, 880, 560)
    set_col(c2, (14, 20, 18), 1)
    c2.rectangle(*scr)
    c2.fill()
    # scope (hero, centre-left)
    sc = P.oscilloscope(c2, CX - 620, 470, 760, 470)
    mid = to_pil(s2)
    s3, c3 = L()
    glow_spot(c3, CX - 400, 300, 700, C.WARM, 0.25)
    fx = to_pil(s3)
    return {"bg": bg, "mid": mid, "fx": fx}


SCOPE_RECT_WS = (CX - 620 + 760 * 0.06, 470 + 470 * 0.11, 760 * 0.54, 470 * 0.68)
LAPTOP_RECT_WS = (CX + 250 + 560 * 0.03, 880 - 560 * 0.62 + 560 * 0.03, 560 * 0.94, 560 * 0.62 - 560 * 0.06)


@plate("workshop_enclosure")
def workshop_enclosure():
    s, ctx = L()
    linear_fill(ctx, 0, 0, 0, PH, [(0, (34, 26, 20), 1), (1, (16, 12, 10), 1)])
    ctx.paint()
    P.bokeh(ctx, PW, PH, 26, 8, [C.WARM, (255, 230, 190)], 40, 120, 0.05, 0.22, (0, 0, PW, PH * 0.55))
    bg = fast_blur(to_pil(s), 10)
    s2, c2 = L()
    P.wood_surface(c2, 0, 760, PW, PH - 760, base=(96, 62, 38), seed=21, lines=80)
    # 3D printed enclosure (open) - oblique box
    bx, by, bw, bh, bd = CX - 420, 640, 840, 300, 360
    dx, dy = P.box_oblique(c2, bx, by, bw, bh, bd, -0.5, front=(44, 46, 48), top=(60, 62, 64), side=(28, 29, 31))
    # inner cavity with the board visible on the top face
    c2.save()
    c2.transform(P.top_face_matrix(bx, by, bw, bd, -0.5))
    c2.rectangle(0.04, 0.08, 0.92, 0.84)
    set_col(c2, (16, 17, 18), 1)
    c2.fill()
    c2.scale(1 / 1000, 1 / 1000)
    draw_board(c2, 70, 110, 860, 780, seed=31, mask=(14, 40, 26), density=0.7, label="HOME CIRCUIT", sub="PROTO-02")
    c2.restore()
    # layer lines (3D print texture) on front
    for k in range(0, int(bh), 6):
        c2.move_to(bx, by + k)
        c2.line_to(bx + bw, by + k)
    set_col(c2, (255, 255, 255), 0.03)
    c2.set_line_width(1)
    c2.stroke()
    # front status LED bezel (the LED that turns on at BUILD IT)
    c2.arc(bx + bw * 0.82, by + bh * 0.4, 18, 0, 2 * math.pi)
    set_col(c2, (20, 20, 20), 1)
    c2.fill()
    c2.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    c2.set_font_size(30)
    set_col(c2, (200, 204, 204), 0.7)
    c2.move_to(bx + 40, by + bh - 40)
    c2.show_text("PROTO-02")
    # soldering iron resting at left
    P.soldering_iron(c2, -200, 1180, CX - 520, 900, width=80)
    P.wire(c2, [(bx + bw - 40, by + bh * 0.8), (bx + bw + 200, by + bh + 80), (PW - 300, 1100), (PW + 100, 1180)], (30, 30, 30), 12)
    mid = to_pil(s2)
    s3, c3 = L()
    glow_spot(c3, CX - 200, 380, 900, C.WARM, 0.25)
    return {"bg": bg, "mid": mid, "fx": to_pil(s3)}


ENCLOSURE_LED = (CX - 420 + 840 * 0.82, 640 + 300 * 0.4)


# ============================================================ 03 IDEA -> HARDWARE
BOARD_RECT = (CX - 520, CY - 300, 1040, 620)   # shared match-cut rectangle (plate space)


@plate("paper")
def paper():
    s, ctx = L()
    set_col(ctx, (232, 226, 210), 1)
    ctx.paint()
    r = rng(2)
    for _ in range(4000):
        set_col(ctx, (120, 110, 90), r.uniform(0.02, 0.06))
        ctx.rectangle(r.uniform(0, PW), r.uniform(0, PH), r.uniform(1, 3), r.uniform(1, 3))
        ctx.fill()
    for k in range(40):
        ctx.move_to(0, 60 + k * 34)
        ctx.line_to(PW, 60 + k * 34)
    set_col(ctx, (140, 160, 200), 0.3)
    ctx.set_line_width(1.5)
    ctx.stroke()
    ctx.move_to(260, 0)
    ctx.line_to(260, PH)
    set_col(ctx, (220, 120, 120), 0.4)
    ctx.stroke()
    radial_fill(ctx, CX, CY, 0, 1500, [(0, (255, 220, 170), 0.1), (1, (40, 20, 0), 0.55)])
    ctx.paint()
    bg = to_pil(s)
    s2, c2 = L()
    # pencil (fg)
    c2.save()
    c2.translate(CX + 760, CY + 260)
    c2.rotate(-0.7)
    rounded_rect(c2, 0, -20, 700, 40, 6)
    set_col(c2, (46, 48, 50), 1)
    c2.fill()
    c2.rectangle(0, -20, 700, 8)
    set_col(c2, C.GREEN_DIM, 1)
    c2.fill()
    c2.move_to(0, -20)
    c2.line_to(-90, 0)
    c2.line_to(0, 20)
    set_col(c2, (220, 190, 150), 1)
    c2.fill()
    c2.move_to(-60, -7)
    c2.line_to(-90, 0)
    c2.line_to(-60, 7)
    set_col(c2, (40, 40, 40), 1)
    c2.fill()
    c2.restore()
    return {"bg": bg}


@plate("cad_dark")
def cad_dark():
    s, ctx = L()
    set_col(ctx, (12, 14, 14), 1)
    ctx.paint()
    set_col(ctx, (22, 25, 25), 1)
    ctx.rectangle(0, 0, PW, 64)
    ctx.fill()
    ctx.rectangle(0, 64, 90, PH)
    ctx.fill()
    ctx.rectangle(PW - 300, 64, 300, PH)
    ctx.fill()
    for i in range(12):
        rounded_rect(ctx, 20, 100 + i * 70, 50, 50, 8)
        set_col(ctx, (40, 46, 46) if i != 3 else C.GREEN_DIM, 1)
        ctx.fill()
    ctx.select_font_face("Noto Sans Mono")
    ctx.set_font_size(22)
    for j, t in enumerate(["LAYERS", "  F.Cu", "  B.Cu", "  F.Silk", "  Edge.Cuts", "", "NETS", "  +3V3", "  GND", "  SDA", "  SCL", "  RELAY"]):
        set_col(ctx, C.GREEN if t.strip() in ("F.Cu", "+3V3") else (150, 156, 156), 0.9)
        ctx.move_to(PW - 270, 120 + j * 40)
        ctx.show_text(t)
    set_col(ctx, (140, 146, 146), 0.8)
    ctx.move_to(130, 42)
    ctx.show_text("HC-DEV.kicad_pcb   —   DRC: 0 errors")
    return {"bg": to_pil(s)}


@plate("build_pcb")
def build_pcb():
    s, ctx = L()
    set_col(ctx, (10, 11, 12), 1)
    ctx.paint()
    radial_fill(ctx, CX, CY - 200, 0, 1400, [(0, (60, 64, 66), 0.8), (1, (8, 8, 9), 0.0)])
    ctx.paint()
    bg = to_pil(s)
    s2, c2 = L()
    x, y, w, h = BOARD_RECT
    # shadow
    rounded_rect(c2, x + 30, y + 40, w, h, 20)
    set_col(c2, (0, 0, 0), 0.6)
    c2.fill()
    draw_board(c2, x, y, w, h, seed=15, mask=(14, 40, 26), density=1.0, label="HOME CIRCUIT", sub="HC-DEV REV A")
    board = to_pil(s2)
    board = Image.composite(board, fast_blur(board, 4), _radial_mask(PW, PH, 700))
    s3, c3 = L()
    linear_fill(c3, x, y, x + w, y + h, [(0, (255, 255, 255), 0.0), (0.45, (255, 255, 255), 0.0), (0.5, (255, 255, 255), 0.10), (0.55, (255, 255, 255), 0.0)])
    rounded_rect(c3, x, y, w, h, 14)
    c3.fill()
    return {"bg": bg, "mid": board, "fx": to_pil(s3)}


@plate("code_firmware")
def code_firmware():
    s, ctx = L()
    set_col(ctx, (12, 13, 14), 1)
    ctx.paint()
    P.bokeh(ctx, PW, PH, 20, 31, [(90, 200, 140), (255, 190, 120)], 40, 120, 0.04, 0.12)
    bg = fast_blur(to_pil(s), 12)
    s2, c2 = L()
    # large monitor/laptop screen filling centre
    rounded_rect(c2, CX - 900, 100, 1800, 1000, 26)
    set_col(c2, (26, 28, 30), 1)
    c2.fill()
    c2.rectangle(CX - 870, 130, 1740, 940)
    set_col(c2, (14, 17, 18), 1)
    c2.fill()
    c2.rectangle(CX - 870, 130, 1740, 50)
    set_col(c2, (24, 28, 29), 1)
    c2.fill()
    c2.select_font_face("Noto Sans Mono")
    c2.set_font_size(24)
    set_col(c2, (160, 166, 166), 1)
    c2.move_to(CX - 840, 164)
    c2.show_text("main.c  —  hc-firmware")
    # terminal panel bottom
    c2.rectangle(CX - 870, 800, 1740, 270)
    set_col(c2, (8, 10, 10), 1)
    c2.fill()
    c2.move_to(CX - 870, 800)
    c2.line_to(CX + 870, 800)
    set_col(c2, (46, 52, 52), 1)
    c2.set_line_width(2)
    c2.stroke()
    return {"bg": bg, "mid": to_pil(s2)}


CODE_RECT_FW = (CX - 850, 200, 1700, 590)
TERM_RECT_FW = (CX - 850, 820, 1700, 240)


@plate("test_bench")
def test_bench():
    s, ctx = L()
    linear_fill(ctx, 0, 0, 0, PH, [(0, (26, 26, 26), 1), (1, (12, 12, 12), 1)])
    ctx.paint()
    bg = to_pil(s)
    s2, c2 = L()
    P.wood_surface(c2, 0, 880, PW, PH - 880, base=(80, 56, 36), seed=40, lines=60)
    sc = P.oscilloscope(c2, CX - 780, 260, 1000, 620)
    disp, _ = P.multimeter(c2, CX + 330, 330, 300)
    draw_board(c2, CX + 20, 940, 560, 300, seed=15, mask=(14, 40, 26), density=0.8, label="HOME CIRCUIT", sub="HC-DEV REV A")
    P.wire(c2, [(CX - 520, 880), (CX - 450, 1000), (CX - 100, 1100), (CX + 120, 1050)], (230, 190, 40), 10)
    P.wire(c2, [(CX + 420, 900), (CX + 440, 1000), (CX + 380, 1050), (CX + 300, 1060)], (200, 40, 40), 10)
    mid = to_pil(s2)
    return {"bg": bg, "mid": mid}


SCOPE_RECT_TB = (CX - 780 + 1000 * 0.06, 260 + 620 * 0.11, 1000 * 0.54, 620 * 0.68)
METER_RECT_TB = (CX + 330 + 300 * 0.16, 330 + 300 * 0.2, 300 * 0.68, 300 * 0.42)


@plate("prototype_working")
def prototype_working():
    s, ctx = L()
    linear_fill(ctx, 0, 0, 0, PH, [(0, (22, 26, 26), 1), (1, (10, 11, 12), 1)])
    ctx.paint()
    P.bokeh(ctx, PW, PH, 26, 77, [(90, 220, 140), (255, 200, 140)], 30, 100, 0.04, 0.14, (0, 0, PW, 700))
    bg = fast_blur(to_pil(s), 10)
    s2, c2 = L()
    P.wood_surface(c2, 0, 820, PW, PH - 820, base=(84, 58, 38), seed=22, lines=70)
    bx, by, bw, bh, bd = CX - 380, 560, 760, 330, 300
    P.box_oblique(c2, bx, by, bw, bh, bd, -0.5, front=(38, 40, 43), top=(56, 58, 62), side=(24, 25, 27))
    # front panel details
    c2.rectangle(bx + 30, by + 40, bw - 60, 6)
    set_col(c2, C.GREEN, 0.9)
    c2.fill()
    from .engine.pcb import terminal_block
    terminal_block(c2, bx + bw - 300, by + 100, 6, 8)
    c2.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    c2.set_font_size(34)
    set_col(c2, C.WHITE, 0.9)
    c2.move_to(bx + 60, by + bh - 50)
    c2.show_text("HOME CIRCUIT  ·  PROTO-02")
    # wires out to a relay module + sensor
    for i, col in enumerate([(200, 40, 40), (20, 20, 20), (40, 120, 220), (230, 190, 40)]):
        P.wire(c2, [(bx + bw - 280 + i * 40, by + 150), (bx + bw - 250 + i * 40, by + bh + 160), (bx + bw + 250, 1110 + i * 16), (bx + bw + 330, 1030 + i * 12)], col, 9)
    draw_board(c2, bx + bw + 320, 960, 300, 180, seed=51, mask=(20, 40, 90), density=0.5, label="RELAY", sub="", terminals=True)
    P.sensor_box(c2, bx - 520, 900, 150, 200)
    P.wire(c2, [(bx, by + bh * 0.6), (bx - 150, by + bh), (bx - 250, 1000), (bx - 370, 1000)], (30, 30, 30), 10)
    mid = to_pil(s2)
    return {"bg": bg, "mid": mid}


PROTO_LEDS = [(CX - 380 + 80 + i * 56, 560 + 140) for i in range(4)]


# ============================================================ 04 PROJECTS
@plate("proj_freelance")
def proj_freelance():
    s, ctx = L()
    set_col(ctx, (14, 12, 12), 1)
    ctx.paint()
    P.bokeh(ctx, PW, PH, 30, 5, [C.WARM, (255, 220, 170)], 30, 90, 0.04, 0.16, (0, 0, PW, 600))
    bg = fast_blur(to_pil(s), 10)
    s2, c2 = L()
    P.wood_surface(c2, 0, 980, PW, PH - 980, base=(80, 52, 34), seed=4, lines=60)
    scr = P.laptop_open(c2, CX - 700, 1020, 1400, angle_h=0.6)
    set_col(c2, (16, 18, 20), 1)
    c2.rectangle(*scr)
    c2.fill()
    draw_board(c2, CX + 760, 1040, 320, 200, seed=61, mask=(14, 40, 26), density=0.5, label="HC", sub="")
    c2.arc(CX - 900, 1120, 70, 0, 2 * math.pi)
    set_col(c2, (220, 216, 210), 1)
    c2.fill()
    mid = to_pil(s2)
    return {"bg": bg, "mid": mid}


FREELANCE_SCREEN = (CX - 700 + 1400 * 0.03, 1020 - 1400 * 0.6 + 1400 * 0.03, 1400 * 0.94, 1400 * 0.6 - 1400 * 0.06)


@plate("proj_network")
def proj_network():
    s, ctx = L()
    set_col(ctx, (9, 11, 11), 1)
    ctx.paint()
    set_col(ctx, (255, 255, 255), 0.05)
    for gx in range(0, PW, 36):
        for gy in range(0, PH, 36):
            ctx.rectangle(gx, gy, 2, 2)
    ctx.fill()
    set_col(ctx, (255, 255, 255), 0.04)
    ctx.set_line_width(1)
    for k in range(0, PW, 216):
        ctx.move_to(k, 0)
        ctx.line_to(k, PH)
    for k in range(0, PH, 216):
        ctx.move_to(0, k)
        ctx.line_to(PW, k)
    ctx.stroke()
    return {"bg": to_pil(s)}


def network_nodes(seed=9, n=26):
    r = rng(seed)
    nodes = []
    labels = ["IoT", "GW", "UAV", "FARM", "EDU", "CTRL", "SENS", "EMB"]
    for i in range(n):
        a = r.uniform(0, 2 * math.pi)
        d = r.uniform(180, 1000)
        nodes.append((CX + math.cos(a) * d * 1.05, CY + math.sin(a) * d * 0.52, r.choice(labels) + f"-{r.randint(1, 40):02d}", d))
    nodes.sort(key=lambda n_: n_[3])
    return nodes


@plate("proj_iot")
def proj_iot():
    s, ctx = L()
    linear_fill(ctx, 0, 0, 0, PH, [(0, (12, 18, 30), 1), (0.7, (40, 44, 64), 1), (1, (90, 70, 70), 1)])
    ctx.paint()
    bg = to_pil(s)
    s2, c2 = L()
    # low building cluster
    blds = [(CX - 900, 600, 380, 700), (CX - 480, 380, 460, 920), (CX + 40, 520, 360, 780), (CX + 460, 700, 420, 600)]
    windows = []
    r = rng(3)
    for bx, by, bw, bh in blds:
        c2.rectangle(bx, by, bw, bh)
        linear_fill(c2, bx, by, bx + bw, by, [(0, (30, 34, 40), 1), (1, (20, 22, 26), 1)])
        c2.fill()
        for i in range(int(bw / 70)):
            for j in range(int(bh / 90)):
                wx, wy = bx + 24 + i * 70, by + 30 + j * 90
                lit = r.random() < 0.35
                c2.rectangle(wx, wy, 40, 50)
                set_col(c2, (255, 200, 130) if lit else (40, 46, 60), 0.85 if lit else 0.8)
                c2.fill()
                if lit:
                    windows.append((wx + 20, wy + 25))
    mid = to_pil(s2)
    return {"bg": bg, "mid": mid}


@plate("proj_gateway_cabinet")
def proj_gateway_cabinet():
    s, ctx = L()
    set_col(ctx, (150, 154, 156), 1)
    ctx.paint()
    linear_fill(ctx, 0, 0, PW, PH, [(0, (170, 174, 176), 1), (1, (90, 94, 96), 1)])
    ctx.paint()
    # wire ducts
    for y in (140, 640, 1140):
        ctx.rectangle(80, y - 50, PW - 160, 100)
        set_col(ctx, (186, 188, 190), 1)
        ctx.fill()
        for k in range(0, PW - 160, 34):
            ctx.rectangle(80 + k, y - 50, 14, 100)
        set_col(ctx, (120, 124, 126), 0.5)
        ctx.fill()
    for x in (80, PW - 180):
        ctx.rectangle(x, 90, 100, PH - 180)
        set_col(ctx, (180, 182, 184), 1)
        ctx.fill()
    # DIN rails
    for y in (390, 890):
        ctx.rectangle(180, y - 18, PW - 360, 36)
        linear_fill(ctx, 0, y - 18, 0, y + 18, [(0, (220, 222, 226), 1), (0.5, (150, 154, 158), 1), (1, (200, 202, 206), 1)])
        ctx.fill()
    bg = to_pil(s)
    s2, c2 = L()
    # breakers row 1
    for i in range(6):
        bx = 240 + i * 110
        rounded_rect(c2, bx, 250, 100, 280, 6)
        set_col(c2, (232, 232, 228), 1)
        c2.fill()
        c2.rectangle(bx + 32, 340, 36, 70)
        set_col(c2, (40, 40, 40), 1)
        c2.fill()
    # power supply
    rounded_rect(c2, 980, 250, 260, 290, 8)
    set_col(c2, (130, 136, 140), 1)
    c2.fill()
    # gateway (hero) on rail 1 centre-right
    P.gateway_front(c2, CX - 60, 230, 620, 320)
    # terminal blocks row 2
    for i in range(34):
        bx = 240 + i * 52
        rounded_rect(c2, bx, 800, 46, 180, 4)
        set_col(c2, (34, 160, 88) if i % 9 == 4 else (150, 154, 158), 1)
        c2.fill()
        c2.arc(bx + 23, 840, 10, 0, 2 * math.pi)
        c2.arc(bx + 23, 940, 10, 0, 2 * math.pi)
        set_col(c2, (70, 72, 74), 1)
        c2.fill()
    # wiring into the gateway
    r = rng(8)
    cols = [(40, 90, 200), (120, 70, 40), (20, 20, 20), (200, 40, 40), (230, 190, 40)]
    for i in range(12):
        x0 = CX + r.uniform(-20, 520)
        P.wire(c2, [(x0, 330), (x0, 140), (x0 + r.uniform(-200, 200), 130), (x0 + r.uniform(-300, 300), 90)], r.choice(cols), 10)
    for i in range(20):
        x0 = 260 + i * 80
        P.wire(c2, [(x0, 800), (x0, 690), (x0 + 30, 660), (x0 + 20, 610)], r.choice(cols), 9)
    mid = to_pil(s2)
    return {"bg": bg, "mid": mid}


GW_CAB_RECT = (CX - 60, 230, 620, 320)


@plate("proj_farm")
def proj_farm():
    s, ctx = L()
    linear_fill(ctx, 0, 0, 0, PH * 0.55, [(0, (40, 60, 96), 1), (0.6, (200, 140, 100), 1), (1, (250, 196, 120), 1)])
    ctx.rectangle(0, 0, PW, PH * 0.55)
    ctx.fill()
    glow_spot(ctx, CX - 500, PH * 0.52, 500, (255, 220, 150), 0.8)
    # far hills
    ctx.move_to(0, PH * 0.52)
    for i in range(13):
        ctx.line_to(i * PW / 12, PH * 0.5 - math.sin(i * 0.9) * 30)
    ctx.line_to(PW, PH * 0.56)
    ctx.line_to(0, PH * 0.56)
    ctx.close_path()
    set_col(ctx, (60, 70, 70), 1)
    ctx.fill()
    # field
    ctx.rectangle(0, PH * 0.54, PW, PH)
    linear_fill(ctx, 0, PH * 0.54, 0, PH, [(0, (60, 70, 40), 1), (1, (26, 34, 18), 1)])
    ctx.fill()
    vx, vy = CX - 200, PH * 0.53
    for k in range(-30, 31):
        x_bottom = CX + k * 190
        ctx.move_to(vx + k * 8, vy)
        ctx.line_to(x_bottom, PH + 20)
        set_col(ctx, (80, 130, 50) if k % 2 == 0 else (40, 60, 30), 0.9)
        ctx.set_line_width(26 if k % 2 == 0 else 8)
        ctx.stroke()
    bg = to_pil(s)
    bg = Image.composite(bg, fast_blur(bg, 6), _band_mask(PH, 0.72, 0.3))
    s2, c2 = L()
    # sensor pole (hero) centre-right
    px, py = CX + 200, 1180
    c2.rectangle(px - 10, 380, 20, py - 380)
    set_col(c2, (60, 62, 66), 1)
    c2.fill()
    P.solar_panel(c2, px - 190, 330, 360, 170, 0.18)
    P.sensor_box(c2, px - 80, 620, 160, 210)
    c2.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    c2.set_font_size(20)
    set_col(c2, (40, 40, 40), 1)
    c2.move_to(px - 60, 780)
    c2.show_text("HC-AGRI")
    # probe cable to soil
    P.wire(c2, [(px, 820), (px + 60, 1000), (px + 140, 1120), (px + 240, 1190)], (20, 20, 20), 8)
    mid = to_pil(s2)
    s3, c3 = L()
    r = rng(6)
    for i in range(40):
        x = r.uniform(-100, PW + 100)
        y = PH + r.uniform(-120, 60)
        c3.save()
        c3.translate(x, y)
        c3.rotate(r.uniform(-1.2, -0.4) if x < CX else r.uniform(-2.7, -1.9))
        c3.scale(r.uniform(160, 260), r.uniform(26, 40))
        c3.arc(0.5, 0, 0.5, 0, 2 * math.pi)
        c3.restore()
        set_col(c3, (20, 40, 16), 1)
        c3.fill()
    fg = fast_blur(to_pil(s3), 18)
    return {"bg": bg, "mid": mid, "fg": fg}


FARM_SENSOR_LED = (CX + 200 - 80 + 160 * 0.8, 620 + 210 * 0.3)


@plate("proj_drone")
def proj_drone():
    """Top view over fields (the drone itself is animated in dyn)."""
    s, ctx = L()
    set_col(ctx, (54, 70, 40), 1)
    ctx.paint()
    r = rng(14)
    for i in range(14):
        x0 = i * 190 - 100
        ctx.rectangle(x0, -50, 180, PH + 100)
        set_col(ctx, r.choice([(70, 96, 50), (86, 110, 56), (58, 80, 44), (110, 120, 70)]), 1)
        ctx.fill()
        for k in range(0, PH, 16):
            ctx.move_to(x0, k)
            ctx.line_to(x0 + 180, k)
        set_col(ctx, (30, 44, 24), 0.25)
        ctx.set_line_width(4)
        ctx.stroke()
    ctx.move_to(-50, PH * 0.7)
    ctx.curve_to(PW * 0.3, PH * 0.5, PW * 0.6, PH * 0.9, PW + 50, PH * 0.6)
    set_col(ctx, (150, 140, 110), 1)
    ctx.set_line_width(40)
    ctx.stroke()
    bg = fast_blur(to_pil(s), 5)
    s2, c2 = L()
    radial_fill(c2, CX, CY, 0, 1400, [(0, (0, 0, 0), 0.0), (1, (0, 0, 0), 0.55)])
    c2.paint()
    return {"bg": bg, "fx": to_pil(s2)}


@plate("proj_embedded")
def proj_embedded():
    s, ctx = L()
    set_col(ctx, (6, 7, 7), 1)
    ctx.paint()
    draw_board(ctx, -200, -150, PW + 400, PH + 300, seed=77, mask=(12, 14, 14), copper=(40, 46, 44), density=1.6,
               label="HOME CIRCUIT", sub="EMB-CTRL REV C", terminals=True, ethernet=True)
    bg = to_pil(s)
    bg = Image.composite(bg, fast_blur(bg, 9), _band_mask(PH, 0.5, 0.3))
    s2, c2 = L()
    radial_fill(c2, CX, CY, 0, 1500, [(0, (0, 0, 0), 0.0), (1, (0, 0, 0), 0.7)])
    c2.paint()
    return {"bg": bg, "fx": to_pil(s2)}


@plate("proj_public")
def proj_public():
    """Generic public-infrastructure monitoring station (no real agency)."""
    s, ctx = L()
    linear_fill(ctx, 0, 0, 0, PH * 0.5, [(0, (24, 34, 60), 1), (1, (190, 130, 110), 1)])
    ctx.rectangle(0, 0, PW, PH * 0.5)
    ctx.fill()
    ctx.move_to(0, PH * 0.5)
    r = rng(2)
    x = 0
    while x < PW:
        ctx.line_to(x, PH * 0.44 - r.uniform(0, 60))
        x += r.uniform(40, 90)
    ctx.line_to(PW, PH * 0.5)
    ctx.close_path()
    set_col(ctx, (26, 32, 36), 1)
    ctx.fill()
    ctx.rectangle(0, PH * 0.5, PW, PH * 0.5)
    linear_fill(ctx, 0, PH * 0.5, 0, PH, [(0, (120, 100, 110), 1), (1, (20, 26, 40), 1)])
    ctx.fill()
    for i in range(60):
        yy = PH * 0.52 + r.uniform(0, PH * 0.45)
        xx = r.uniform(0, PW)
        ctx.move_to(xx, yy)
        ctx.line_to(xx + r.uniform(80, 300), yy)
        set_col(ctx, (255, 210, 180), r.uniform(0.05, 0.2))
        ctx.set_line_width(3)
        ctx.stroke()
    bg = to_pil(s)
    s2, c2 = L()
    # bank
    c2.move_to(CX - 200, PH)
    c2.line_to(CX + 300, PH * 0.62)
    c2.line_to(PW, PH * 0.6)
    c2.line_to(PW, PH)
    c2.close_path()
    set_col(c2, (26, 28, 26), 1)
    c2.fill()
    # station
    px = CX + 300
    c2.rectangle(px - 14, 260, 28, PH * 0.62 - 260)
    set_col(c2, (70, 74, 78), 1)
    c2.fill()
    P.solar_panel(c2, px - 10, 250, 330, 160, 0.2)
    P.sensor_box(c2, px - 100, 470, 170, 230, antenna=True)
    # radar level arm over water
    c2.move_to(px, 420)
    c2.line_to(px - 420, 420)
    set_col(c2, (70, 74, 78), 1)
    c2.set_line_width(14)
    c2.stroke()
    rounded_rect(c2, px - 470, 400, 90, 80, 10)
    set_col(c2, (220, 222, 224), 1)
    c2.fill()
    # staff gauge
    c2.rectangle(CX - 60, PH * 0.55, 40, PH * 0.3)
    set_col(c2, (230, 230, 226), 0.9)
    c2.fill()
    for k in range(12):
        c2.rectangle(CX - 60, PH * 0.55 + k * 30, 20 if k % 2 else 40, 8)
    set_col(c2, (30, 30, 30), 0.9)
    c2.fill()
    mid = to_pil(s2)
    return {"bg": bg, "mid": mid}


PUBLIC_BEACON = (CX + 300 - 100 + 170 * 0.8, 470 + 230 * 0.3)


@plate("proj_university")
def proj_university():
    s, ctx = L()
    linear_fill(ctx, 0, 0, 0, PH, [(0, (52, 56, 58), 1), (1, (30, 32, 34), 1)])
    ctx.paint()
    # whiteboard
    ctx.rectangle(260, 120, PW - 520, 560)
    set_col(ctx, (224, 228, 228), 1)
    ctx.fill()
    ctx.select_font_face("Noto Sans Mono")
    ctx.set_font_size(40)
    set_col(ctx, (40, 60, 120), 0.85)
    for i, t in enumerate(["PID:  u = Kp·e + Ki∫e dt + Kd·de/dt", "v = (vL + vR) / 2", "ω = (vR − vL) / L", "d = t·343 / 2   [HC-SR04]"]):
        ctx.move_to(340, 220 + i * 110)
        ctx.show_text(t)
    ctx.rectangle(PW - 760, 220, 380, 260)
    set_col(ctx, (40, 60, 120), 0.7)
    ctx.set_line_width(4)
    ctx.stroke()
    bg = fast_blur(to_pil(s), 5)
    s2, c2 = L()
    for x, y, sc, kw in [(CX - 700, 1000, 520, dict(arm_to=(CX - 480, 1010), lean=0.12)),
                         (CX + 720, 1010, 540, dict(arm2_to=(CX + 480, 1010), lean=-0.1))]:
        P.person(c2, x, y, sc, col=(20, 20, 22), **kw)
    ppl = P.rim_light(to_pil(s2), 7, -4, (200, 220, 230), 0.8, 2)
    s3, c3 = L()
    c3.rectangle(0, 980, PW, PH - 980)
    set_col(c3, (60, 62, 64), 1)
    c3.fill()
    # robot car (hero) - oblique
    rx, ry = CX - 330, 800
    P.box_oblique(c3, rx, ry, 660, 150, 320, -0.5, front=(34, 36, 38), top=(46, 48, 52), side=(20, 21, 22))
    c3.save()
    c3.transform(P.top_face_matrix(rx, ry, 660, 320, -0.5))
    c3.scale(1 / 1000, 1 / 1000)
    draw_board(c3, 120, 120, 700, 700, seed=88, mask=(14, 40, 26), density=0.5, label="HC-EDU", sub="ROBOT KIT")
    c3.restore()
    for wx in (rx + 60, rx + 520):
        c3.arc(wx + 40, ry + 160, 90, 0, 2 * math.pi)
        set_col(c3, (16, 16, 16), 1)
        c3.fill()
        c3.arc(wx + 40, ry + 160, 40, 0, 2 * math.pi)
        set_col(c3, (230, 190, 40), 1)
        c3.fill()
    for ex in (rx + 240, rx + 360):
        c3.arc(ex, ry + 60, 36, 0, 2 * math.pi)
        set_col(c3, (200, 204, 208), 1)
        c3.fill()
        c3.arc(ex, ry + 60, 22, 0, 2 * math.pi)
        set_col(c3, (30, 30, 30), 1)
        c3.fill()
    laptop = P.laptop_open(c3, CX + 520, 1080, 360)
    set_col(c3, (20, 30, 26), 1)
    c3.rectangle(*laptop)
    c3.fill()
    mid = ppl
    mid.alpha_composite(to_pil(s3))
    return {"bg": bg, "mid": mid}


# ============================================================ 05 PRODUCT / DEVELOPER
@plate("studio_dark")
def studio_dark():
    s, ctx = L()
    set_col(ctx, (8, 9, 10), 1)
    ctx.paint()
    radial_fill(ctx, CX, CY - 150, 0, 1100, [(0, (48, 52, 54), 1), (1, (8, 9, 10), 1)])
    ctx.paint()
    ctx.rectangle(0, CY + 260, PW, PH)
    linear_fill(ctx, 0, CY + 260, 0, PH, [(0, (22, 24, 26), 1), (1, (6, 6, 7), 1)])
    ctx.fill()
    return {"bg": to_pil(s)}


@plate("dev_desk")
def dev_desk():
    s, ctx = L()
    linear_fill(ctx, 0, 0, 0, PH, [(0, (22, 26, 28), 1), (1, (10, 12, 13), 1)])
    ctx.paint()
    P.bokeh(ctx, PW, PH, 30, 55, [(120, 200, 170), (255, 210, 160), (200, 210, 220)], 30, 110, 0.04, 0.15, (0, 0, PW, 700))
    bg = fast_blur(to_pil(s), 10)
    s2, c2 = L()
    c2.rectangle(0, 900, PW, PH - 900)
    linear_fill(c2, 0, 900, 0, PH, [(0, (40, 42, 44), 1), (1, (18, 19, 20), 1)])
    c2.fill()
    scr = P.laptop_open(c2, CX - 1000, 960, 900, body=(70, 74, 78))
    set_col(c2, (14, 17, 18), 1)
    c2.rectangle(*scr)
    c2.fill()
    P.gateway_3q(c2, CX + 180, 700, 620, 300, 260, leds=(1, 1, 0, 0))
    mid = to_pil(s2)
    return {"bg": bg, "mid": mid}


DEV_LAPTOP = (CX - 1000 + 900 * 0.03, 960 - 900 * 0.62 + 900 * 0.03, 900 * 0.94, 900 * 0.62 - 900 * 0.06)
DEV_GW = (CX + 180, 700, 620, 300)


@plate("classroom")
def classroom():
    s, ctx = L()
    linear_fill(ctx, 0, 0, 0, PH, [(0, (30, 34, 36), 1), (1, (16, 18, 20), 1)])
    ctx.paint()
    # projector screen
    ctx.rectangle(CX - 620, 90, 1240, 650)
    set_col(ctx, (18, 22, 24), 1)
    ctx.fill()
    bg = to_pil(s)
    s2, c2 = L()
    # instructor
    P.person(c2, CX + 760, 820, 560, col=(22, 22, 24), arm_to=(CX + 520, 520), standing_h=400)
    # rows of students (backs) with laptops
    rows = [(760, 360, 7), (960, 470, 6), (1200, 600, 5)]
    for y, sc, n in rows:
        for i in range(n):
            x = CX + (i - (n - 1) / 2) * sc * 1.0
            P.laptop_back(c2, x - sc * 0.32, y - sc * 0.55, sc * 0.64, sc * 0.4)
            P.person(c2, x, y + sc * 0.35, sc, col=(14, 14, 16), hair=True)
    mid = P.rim_light(to_pil(s2), 0, 6, (150, 200, 190), 0.9, 2)
    s3, c3 = L()
    glow_spot(c3, CX, 420, 900, (120, 200, 170), 0.12)
    return {"bg": bg, "mid": mid, "fx": to_pil(s3)}


CLASS_SCREEN = (CX - 600, 110, 1200, 610)


@plate("brand_thinker")
def brand_thinker():
    s, ctx = L()
    set_col(ctx, (10, 12, 18), 1)
    ctx.paint()
    # window with night city bokeh
    ctx.rectangle(CX - 900, 80, 1400, 900)
    linear_fill(ctx, 0, 80, 0, 980, [(0, (10, 16, 34), 1), (1, (40, 40, 60), 1)])
    ctx.fill()
    P.bokeh(ctx, PW, PH, 70, 9, [(255, 200, 130), (255, 230, 200), (140, 180, 255)], 12, 50, 0.1, 0.45, (CX - 900, 500, CX + 500, 980))
    set_col(ctx, (12, 10, 10), 1)
    ctx.set_line_width(26)
    ctx.rectangle(CX - 900, 80, 1400, 900)
    ctx.move_to(CX - 200, 80)
    ctx.line_to(CX - 200, 980)
    ctx.stroke()
    bg = fast_blur(to_pil(s), 5)
    s2, c2 = L()
    # engineer in profile-ish silhouette (standing, looking out)
    P.person(c2, CX + 250, 1080, 720, col=(14, 12, 12), lean=-0.04, arm_to=(CX + 120, 820))
    ppl = P.rim_light(to_pil(s2), -9, 0, (255, 190, 120), 1.0, 3)
    s3, c3 = L()
    c3.rectangle(0, 1120, PW, PH)
    set_col(c3, (40, 28, 20), 1)
    c3.fill()
    glow_spot(c3, CX + 800, 900, 700, C.WARM, 0.35)
    ppl.alpha_composite(to_pil(s3))
    return {"bg": bg, "mid": ppl}


@plate("drone_sky")
def drone_sky():
    s, ctx = L()
    linear_fill(ctx, 0, 0, 0, PH, [(0, (60, 96, 140), 1), (0.65, (200, 170, 140), 1), (1, (240, 200, 150), 1)])
    ctx.paint()
    r = rng(3)
    for i in range(8):
        cx_, cy_ = r.uniform(0, PW), r.uniform(80, 500)
        for k in range(6):
            ctx.arc(cx_ + k * 70, cy_ + r.uniform(-20, 20), r.uniform(60, 120), 0, 2 * math.pi)
        set_col(ctx, (255, 240, 230), 0.12)
        ctx.fill()
    bg = fast_blur(to_pil(s), 8)
    s2, c2 = L()
    c2.move_to(0, 1030)
    for i in range(20):
        c2.line_to(i * PW / 19, 1030 - math.sin(i * 1.3) * 10)
    c2.line_to(PW, PH)
    c2.line_to(0, PH)
    c2.close_path()
    linear_fill(c2, 0, 1000, 0, PH, [(0, (60, 80, 40), 1), (1, (26, 36, 18), 1)])
    c2.fill()
    c2.save()
    c2.translate(CX, 1110)
    c2.scale(520, 60)
    c2.arc(0, 0, 1, 0, 2 * math.pi)
    c2.restore()
    set_col(c2, (60, 62, 64), 1)
    c2.fill()
    c2.save()
    c2.translate(CX, 1110)
    c2.scale(420, 46)
    c2.arc(0, 0, 1, 0, 2 * math.pi)
    c2.restore()
    set_col(c2, C.GREEN_DIM, 0.8)
    c2.set_line_width(0.06)
    c2.stroke()
    return {"bg": bg, "mid": to_pil(s2)}


@plate("dark_grid")
def dark_grid():
    return {"bg": circuit_backdrop(PW, PH, seed=5, col=(30, 70, 46), alpha=0.35)}


@plate("dark_grid_warm")
def dark_grid_warm():
    im = circuit_backdrop(PW, PH, seed=17, col=(80, 60, 40), alpha=0.25, bg=(20, 16, 13))
    return {"bg": im}


def build(name):
    return REGISTRY[name]()
