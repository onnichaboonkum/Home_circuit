"""Reusable illustrated props (cairo). Everything is conceptual pre-vis art.

People are drawn as soft silhouettes with a rim light (documentary backlight
look) - deliberately non-specific so they read as "engineers" not as portraits.
"""
import math

import cairo
import numpy as np
from PIL import Image

from .. import config as C
from .canvas import (glow_spot, linear_fill, radial_fill, rounded_rect, set_col, surface,
                     to_pil)
from .pcb import draw_board, node, route, stroke_poly, terminal_block, rj45
from .util import rng


# ================================================================== people
def person(ctx, x, y, s, pose="sit", col=(16, 14, 14), lean=0.0, arm_to=None, arm2_to=None,
           hair=True, standing_h=0.0):
    """Upper-body silhouette. (x, y) = centre of the waist line, s = shoulder-to-waist height."""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(lean)
    set_col(ctx, col, 1)
    sw, ww, th = 0.52 * s, 0.40 * s, 0.62 * s
    # legs if standing
    if standing_h > 0:
        ctx.move_to(-ww / 2, 0)
        ctx.line_to(-ww / 2 + 0.02 * s, standing_h)
        ctx.line_to(-0.02 * s, standing_h)
        ctx.line_to(0, 0.1 * s)
        ctx.line_to(0.02 * s, standing_h)
        ctx.line_to(ww / 2 - 0.02 * s, standing_h)
        ctx.line_to(ww / 2, 0)
        ctx.close_path()
        ctx.fill()
    # torso
    ctx.move_to(-ww / 2, 0.02 * s)
    ctx.curve_to(-ww / 2, -th * 0.4, -sw / 2 - 0.02 * s, -th * 0.7, -sw / 2 + 0.06 * s, -th)
    ctx.curve_to(-sw / 4, -th - 0.07 * s, sw / 4, -th - 0.07 * s, sw / 2 - 0.06 * s, -th)
    ctx.curve_to(sw / 2 + 0.02 * s, -th * 0.7, ww / 2, -th * 0.4, ww / 2, 0.02 * s)
    ctx.close_path()
    ctx.fill()
    # neck + head
    ctx.rectangle(-0.055 * s, -th - 0.12 * s, 0.11 * s, 0.14 * s)
    ctx.fill()
    hx, hy = 0.0, -th - 0.25 * s
    ctx.save()
    ctx.translate(hx, hy)
    ctx.scale(0.105 * s, 0.135 * s)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.fill()
    if hair:
        ctx.save()
        ctx.translate(hx, hy - 0.012 * s)
        ctx.scale(0.11 * s, 0.13 * s)
        ctx.arc(0, 0, 1, math.pi * 1.05, math.pi * 1.95)
        ctx.restore()
        ctx.fill()
    # arms
    ctx.set_line_width(0.13 * s)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for side, target in ((-1, arm_to), (1, arm2_to)):
        shx, shy = side * (sw / 2 - 0.07 * s), -th + 0.08 * s
        if target is None:
            ex, ey = side * (sw / 2 + 0.02 * s), -th * 0.35
            hx2, hy2 = side * (sw / 2 - 0.02 * s), 0.05 * s
        else:
            tx, ty = target[0] - x, target[1] - y
            ex, ey = (shx + tx) / 2 + side * 0.12 * s, (shy + ty) / 2 + 0.12 * s
            hx2, hy2 = tx, ty
        ctx.move_to(shx, shy)
        ctx.curve_to(ex, ey, ex, ey, hx2, hy2)
        ctx.stroke()
    ctx.restore()


def rim_light(img, dx=6, dy=-3, col=C.WARM, strength=0.9, spread=2.0):
    """Add a one-sided rim light to a silhouette layer (PIL RGBA)."""
    a = np.asarray(img, np.float32)
    al = a[..., 3] / 255.0
    sh = np.roll(np.roll(al, int(dx), 1), int(dy), 0)
    rim = np.clip(al - sh, 0, 1) * strength
    if spread > 0:
        from PIL import ImageFilter
        rim_img = Image.fromarray((rim * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(spread))
        rim = np.asarray(rim_img, np.float32) / 255.0 * al
    out = a.copy()
    for i in range(3):
        out[..., i] = a[..., i] * (1 - rim) + col[i] * rim
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


# ================================================================== workshop objects
def wood_surface(ctx, x, y, w, h, base=(92, 62, 40), seed=1, lines=160):
    r = rng(seed)
    set_col(ctx, base, 1)
    ctx.rectangle(x, y, w, h)
    ctx.fill()
    for _ in range(lines):
        yy = y + r.uniform(0, h)
        amp = r.uniform(2, 10)
        ph = r.uniform(0, 6)
        dark = r.random() < 0.6
        col = tuple(int(c * (0.78 if dark else 1.15)) for c in base)
        ctx.move_to(x, yy)
        steps = 24
        for i in range(1, steps + 1):
            xx = x + w * i / steps
            ctx.line_to(xx, yy + math.sin(i * 0.5 + ph) * amp)
        set_col(ctx, col, r.uniform(0.15, 0.4))
        ctx.set_line_width(r.uniform(1, 4))
        ctx.stroke()


def laptop_open(ctx, x, y, w, screen_col=(14, 18, 20), body=(60, 63, 67), angle_h=0.62):
    """Front-ish view of an open laptop. Returns the screen rect."""
    sh = w * angle_h
    # screen lid
    rounded_rect(ctx, x, y - sh, w, sh, w * 0.02)
    set_col(ctx, (30, 32, 35), 1)
    ctx.fill()
    sx, sy, sw, shh = x + w * 0.03, y - sh + w * 0.03, w * 0.94, sh - w * 0.06
    set_col(ctx, screen_col, 1)
    ctx.rectangle(sx, sy, sw, shh)
    ctx.fill()
    # base (keyboard deck in perspective)
    ctx.move_to(x - w * 0.04, y + w * 0.1)
    ctx.line_to(x + w * 1.04, y + w * 0.1)
    ctx.line_to(x + w, y)
    ctx.line_to(x, y)
    ctx.close_path()
    linear_fill(ctx, 0, y, 0, y + w * 0.1, [(0, body, 1), (1, tuple(int(c * 0.6) for c in body), 1)])
    ctx.fill()
    return (sx, sy, sw, shh)


def laptop_back(ctx, x, y, w, h, glow_col=(180, 220, 200)):
    """Back of a laptop lid (seen from behind, e.g. classroom)."""
    rounded_rect(ctx, x, y, w, h, w * 0.03)
    linear_fill(ctx, x, y, x, y + h, [(0, (70, 74, 78), 1), (1, (40, 42, 45), 1)])
    ctx.fill()
    ctx.arc(x + w / 2, y + h * 0.45, w * 0.06, 0, 2 * math.pi)
    set_col(ctx, (120, 124, 128), 0.8)
    ctx.fill()


def oscilloscope(ctx, x, y, w, h, body=(52, 55, 58)):
    """Bench scope front view. Returns screen rect."""
    rounded_rect(ctx, x, y, w, h, w * 0.03)
    linear_fill(ctx, x, y, x, y + h, [(0, tuple(c + 18 for c in body), 1), (1, tuple(int(c * 0.65) for c in body), 1)])
    ctx.fill()
    # bezel
    rounded_rect(ctx, x + w * 0.04, y + h * 0.08, w * 0.58, h * 0.74, w * 0.01)
    set_col(ctx, (12, 13, 14), 1)
    ctx.fill()
    screen = (x + w * 0.06, y + h * 0.11, w * 0.54, h * 0.68)
    # knobs
    for i in range(3):
        for j in range(2):
            kx, ky = x + w * (0.72 + j * 0.13), y + h * (0.22 + i * 0.22)
            ctx.arc(kx, ky, w * 0.035, 0, 2 * math.pi)
            radial_fill(ctx, kx - w * 0.01, ky - w * 0.01, 0, w * 0.04, [(0, (120, 124, 128), 1), (1, (30, 32, 34), 1)])
            ctx.fill()
    # buttons
    for i in range(6):
        rounded_rect(ctx, x + w * (0.06 + i * 0.09), y + h * 0.86, w * 0.07, h * 0.06, 3)
        set_col(ctx, (90, 94, 98) if i != 2 else C.GREEN_DIM, 1)
        ctx.fill()
    # BNC inputs
    for i in range(2):
        bx, by = x + w * (0.72 + i * 0.13), y + h * 0.88
        ctx.arc(bx, by, w * 0.025, 0, 2 * math.pi)
        set_col(ctx, (180, 184, 188), 1)
        ctx.fill()
    return screen


def multimeter(ctx, x, y, w, reading_area=True, body=(38, 40, 42), bumper=(28, 120, 70)):
    """Top-view handheld multimeter. Returns (display rect, dial centre)."""
    h = w * 1.9
    rounded_rect(ctx, x, y, w, h, w * 0.14)
    set_col(ctx, bumper, 1)
    ctx.fill()
    rounded_rect(ctx, x + w * 0.07, y + w * 0.07, w * 0.86, h - w * 0.14, w * 0.1)
    linear_fill(ctx, x, y, x + w, y + h, [(0, tuple(c + 14 for c in body), 1), (1, body, 1)])
    ctx.fill()
    disp = (x + w * 0.16, y + w * 0.2, w * 0.68, w * 0.42)
    rounded_rect(ctx, *disp, w * 0.03)
    set_col(ctx, (150, 168, 150), 1)
    ctx.fill()
    dcx, dcy = x + w / 2, y + h * 0.56
    ctx.arc(dcx, dcy, w * 0.26, 0, 2 * math.pi)
    radial_fill(ctx, dcx - w * 0.06, dcy - w * 0.06, 0, w * 0.3, [(0, (90, 94, 98), 1), (1, (22, 23, 25), 1)])
    ctx.fill()
    ctx.move_to(dcx, dcy)
    ctx.line_to(dcx + w * 0.2, dcy - w * 0.12)
    set_col(ctx, (230, 230, 230), 1)
    ctx.set_line_width(w * 0.04)
    ctx.stroke()
    for i, colr in enumerate([(20, 20, 20), (200, 40, 40), (20, 20, 20)]):
        jx, jy = x + w * (0.25 + i * 0.25), y + h * 0.86
        ctx.arc(jx, jy, w * 0.06, 0, 2 * math.pi)
        set_col(ctx, colr, 1)
        ctx.fill()
    return disp, (dcx, dcy)


def soldering_iron(ctx, x0, y0, x1, y1, width=40, tip_hot=True):
    """Iron from handle end (x0,y0) to tip (x1,y1)."""
    ang = math.atan2(y1 - y0, x1 - x0)
    L = math.dist((x0, y0), (x1, y1))
    ctx.save()
    ctx.translate(x0, y0)
    ctx.rotate(ang)
    # cable
    ctx.move_to(0, 0)
    ctx.curve_to(-L * 0.3, width * 0.4, -L * 0.5, -width, -L, width * 2)
    set_col(ctx, (20, 20, 22), 1)
    ctx.set_line_width(width * 0.22)
    ctx.stroke()
    # handle
    rounded_rect(ctx, 0, -width / 2, L * 0.48, width, width * 0.45)
    linear_fill(ctx, 0, -width / 2, 0, width / 2, [(0, (70, 74, 78), 1), (0.45, (32, 34, 36), 1), (1, (12, 12, 13), 1)])
    ctx.fill()
    # grip rings
    for i in range(6):
        gx = L * 0.2 + i * width * 0.28
        ctx.rectangle(gx, -width / 2, width * 0.08, width)
        set_col(ctx, (10, 10, 10), 0.6)
        ctx.fill()
    # green accent ring
    ctx.rectangle(L * 0.44, -width / 2, width * 0.18, width)
    set_col(ctx, C.GREEN_DIM, 1)
    ctx.fill()
    # metal shaft
    ctx.move_to(L * 0.48, -width * 0.26)
    ctx.line_to(L * 0.86, -width * 0.14)
    ctx.line_to(L * 0.86, width * 0.14)
    ctx.line_to(L * 0.48, width * 0.26)
    ctx.close_path()
    linear_fill(ctx, 0, -width * 0.26, 0, width * 0.26, [(0, (220, 222, 226), 1), (0.5, (140, 144, 150), 1), (1, (70, 72, 76), 1)])
    ctx.fill()
    # tip
    ctx.move_to(L * 0.86, -width * 0.14)
    ctx.line_to(L, -width * 0.02)
    ctx.line_to(L, width * 0.02)
    ctx.line_to(L * 0.86, width * 0.14)
    ctx.close_path()
    linear_fill(ctx, L * 0.86, 0, L, 0, [(0, (150, 110, 70), 1), (1, (255, 190, 120) if tip_hot else (160, 150, 140), 1)])
    ctx.fill()
    ctx.restore()


def tweezers(ctx, x0, y0, x1, y1, width=18, gap=4):
    """Two tapered steel arms; ``width`` = half spread at the hinge, ``gap`` = half spread at tips."""
    ang = math.atan2(y1 - y0, x1 - x0)
    L = math.dist((x0, y0), (x1, y1))
    th0, th1 = width * 0.9, width * 0.35
    ctx.save()
    ctx.translate(x0, y0)
    ctx.rotate(ang)
    for side in (-1, 1):
        ctx.move_to(0, side * width)
        ctx.line_to(L, side * gap)
        ctx.line_to(L - th1 * 0.4, side * (gap + th1))
        ctx.line_to(0, side * (width + th0))
        ctx.close_path()
        linear_fill(ctx, 0, side * width, 0, side * (width + th0),
                    [(0, (240, 241, 243), 1), (0.5, (170, 174, 178), 1), (1, (90, 94, 98), 1)])
        ctx.fill()
    ctx.restore()


def wire(ctx, pts, col, width=6, a=1.0, shine=True):
    ctx.move_to(*pts[0])
    if len(pts) == 4:
        ctx.curve_to(*pts[1], *pts[2], *pts[3])
    else:
        for p in pts[1:]:
            ctx.line_to(*p)
    set_col(ctx, col, a)
    ctx.set_line_width(width)
    ctx.stroke_preserve() if shine else ctx.stroke()
    if shine:
        set_col(ctx, (255, 255, 255), 0.18 * a)
        ctx.set_line_width(width * 0.3)
        ctx.stroke()


def breadboard(ctx, x, y, w, h):
    rounded_rect(ctx, x, y, w, h, 8)
    set_col(ctx, (226, 224, 216), 1)
    ctx.fill()
    set_col(ctx, (60, 60, 60), 0.85)
    cols = int(w / 14)
    for i in range(cols):
        for j in range(5):
            ctx.rectangle(x + 12 + i * 14, y + h * 0.18 + j * 12, 4, 4)
            ctx.rectangle(x + 12 + i * 14, y + h * 0.58 + j * 12, 4, 4)
    ctx.fill()
    for yy, col in ((y + h * 0.06, (200, 60, 60)), (y + h * 0.94, (60, 90, 200))):
        ctx.move_to(x + 10, yy)
        ctx.line_to(x + w - 10, yy)
        set_col(ctx, col, 0.7)
        ctx.set_line_width(2)
        ctx.stroke()


def through_hole_resistor(ctx, x, y, L, ang, r):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.move_to(-L, 0)
    ctx.line_to(L, 0)
    set_col(ctx, (200, 202, 206), 1)
    ctx.set_line_width(L * 0.04)
    ctx.stroke()
    rounded_rect(ctx, -L * 0.4, -L * 0.13, L * 0.8, L * 0.26, L * 0.12)
    linear_fill(ctx, 0, -L * 0.13, 0, L * 0.13, [(0, (228, 206, 160), 1), (1, (170, 140, 96), 1)])
    ctx.fill()
    bands = [(150, 80, 30), (20, 20, 20), (220, 120, 30), (200, 170, 80)]
    for i, bc in enumerate(bands):
        ctx.rectangle(-L * 0.28 + i * L * 0.15, -L * 0.13, L * 0.06, L * 0.26)
        set_col(ctx, bc, 1)
        ctx.fill()
    ctx.restore()


def electrolytic(ctx, x, y, rr, col=(24, 26, 30)):
    ctx.arc(x, y, rr, 0, 2 * math.pi)
    radial_fill(ctx, x - rr * 0.3, y - rr * 0.3, 0, rr * 1.2, [(0, (90, 94, 110), 1), (1, col, 1)])
    ctx.fill()
    ctx.arc(x, y, rr * 0.75, 0, 2 * math.pi)
    set_col(ctx, (170, 174, 180), 1)
    ctx.fill()
    for a in (0, math.pi / 2):
        ctx.move_to(x - rr * 0.5 * math.cos(a), y - rr * 0.5 * math.sin(a))
        ctx.line_to(x + rr * 0.5 * math.cos(a), y + rr * 0.5 * math.sin(a))
    set_col(ctx, (110, 114, 120), 1)
    ctx.set_line_width(rr * 0.07)
    ctx.stroke()
    ctx.arc(x, y, rr, -0.6, 0.6)
    set_col(ctx, (200, 204, 220), 0.7)
    ctx.set_line_width(rr * 0.25)
    ctx.stroke()


def dip_ic(ctx, x, y, w, h, ang=0.0, label="ATmega"):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    n = 8
    set_col(ctx, (200, 202, 206), 1)
    for i in range(n):
        px = -w / 2 + w * (i + 0.5) / n
        ctx.rectangle(px - w * 0.025, -h / 2 - h * 0.14, w * 0.05, h * 0.14)
        ctx.rectangle(px - w * 0.025, h / 2, w * 0.05, h * 0.14)
    ctx.fill()
    rounded_rect(ctx, -w / 2, -h / 2, w, h, h * 0.06)
    linear_fill(ctx, 0, -h / 2, 0, h / 2, [(0, (48, 50, 54), 1), (1, (18, 18, 20), 1)])
    ctx.fill()
    ctx.arc(-w / 2, 0, h * 0.12, -math.pi / 2, math.pi / 2)
    set_col(ctx, (10, 10, 10), 1)
    ctx.fill()
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(h * 0.22)
    set_col(ctx, (150, 154, 158), 0.8)
    ctx.move_to(-w * 0.3, h * 0.08)
    ctx.show_text(label)
    ctx.restore()


def led_5mm(ctx, x, y, rr, col, on=False):
    if on:
        glow_spot(ctx, x, y, rr * 5, col, 0.6)
    ctx.arc(x, y, rr, 0, 2 * math.pi)
    radial_fill(ctx, x - rr * 0.3, y - rr * 0.3, 0, rr, [(0, tuple(min(255, c + 90) for c in col), 1), (1, tuple(int(c * (0.9 if on else 0.45)) for c in col), 1)])
    ctx.fill()


# ================================================================== 3D-ish boxes (oblique)
def box_oblique(ctx, x, y, w, h, d, ang=-0.55, front=(34, 36, 39), top=(52, 55, 58), side=(22, 23, 25), r=6):
    """Front face at (x,y,w,h); depth ``d`` projected along ``ang``. Returns (dx, dy)."""
    dx, dy = d * math.cos(ang), d * math.sin(ang)
    # top
    ctx.move_to(x, y)
    ctx.line_to(x + dx, y + dy)
    ctx.line_to(x + w + dx, y + dy)
    ctx.line_to(x + w, y)
    ctx.close_path()
    linear_fill(ctx, x, y + dy, x, y, [(0, tuple(min(255, c + 10) for c in top), 1), (1, top, 1)])
    ctx.fill()
    # side
    ctx.move_to(x + w, y)
    ctx.line_to(x + w + dx, y + dy)
    ctx.line_to(x + w + dx, y + h + dy)
    ctx.line_to(x + w, y + h)
    ctx.close_path()
    set_col(ctx, side, 1)
    ctx.fill()
    # front
    ctx.rectangle(x, y, w, h)
    linear_fill(ctx, x, y, x, y + h, [(0, tuple(min(255, c + 12) for c in front), 1), (1, tuple(int(c * 0.8) for c in front), 1)])
    ctx.fill()
    # edge highlights
    ctx.move_to(x, y)
    ctx.line_to(x + w, y)
    ctx.line_to(x + w + dx, y + dy)
    set_col(ctx, (255, 255, 255), 0.18)
    ctx.set_line_width(2)
    ctx.stroke()
    return dx, dy


def top_face_matrix(x, y, w, d, ang=-0.55):
    """cairo Matrix that maps unit square (0..1, 0..1) onto the oblique top face.
    u runs along the width, v runs from the back edge (0) to the front edge (1)."""
    dx, dy = d * math.cos(ang), d * math.sin(ang)
    # origin at back-left corner
    return cairo.Matrix(xx=w, yx=0, xy=-dx, yy=-dy, x0=x + dx, y0=y + dy)


# ================================================================== home circuit gateway (conceptual)
def gateway_front(ctx, x, y, w, h, leds=(1, 1, 0, 1), label=True):
    """Front panel of the conceptual HC gateway (DRAFT)."""
    u = w / 100
    # body front
    rounded_rect(ctx, x, y, w, h, 2.2 * u)
    linear_fill(ctx, x, y, x, y + h, [(0, (46, 49, 53), 1), (0.5, (28, 30, 33), 1), (1, (16, 17, 19), 1)])
    ctx.fill()
    # green accent line
    ctx.rectangle(x + 2 * u, y + h * 0.12, w - 4 * u, 0.7 * u)
    set_col(ctx, C.GREEN, 0.9)
    ctx.fill()
    # terminals (top row, green pluggable)
    terminal_block(ctx, x + 6 * u, y + h * 0.2, 6, u * 1.0, col=(34, 160, 88))
    terminal_block(ctx, x + 40 * u, y + h * 0.2, 4, u * 1.0, col=(34, 160, 88))
    # ethernet x2
    rj45(ctx, x + 64 * u, y + h * 0.2, u * 1.05)
    rj45(ctx, x + 80 * u, y + h * 0.2, u * 1.05)
    # LED row
    names = ["PWR", "RUN", "ERR", "LINK"]
    ctx.select_font_face("Noto Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(1.8 * u)
    led_pos = []
    for i, nm in enumerate(names):
        lx, ly = x + (8 + i * 9) * u, y + h * 0.72
        on = leds[i] if i < len(leds) else 0
        colr = (255, 90, 60) if nm == "ERR" else C.GREEN
        ctx.arc(lx, ly, 1.1 * u, 0, 2 * math.pi)
        set_col(ctx, colr if on else (60, 64, 62), 1)
        ctx.fill()
        set_col(ctx, (200, 204, 204), 0.8)
        ctx.move_to(lx - 2 * u, ly + 4 * u)
        ctx.show_text(nm)
        led_pos.append((lx, ly, colr))
    if label:
        ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(3.2 * u)
        set_col(ctx, C.WHITE, 0.95)
        ctx.move_to(x + 58 * u, y + h * 0.78)
        ctx.show_text("HOME CIRCUIT")
        ctx.set_font_size(2.0 * u)
        set_col(ctx, C.GREEN, 0.95)
        ctx.move_to(x + 58 * u, y + h * 0.78 + 3.6 * u)
        ctx.show_text("GW-01  EDGE GATEWAY")
    # screws
    for sx, sy in [(x + 2.2 * u, y + 2.2 * u), (x + w - 2.2 * u, y + 2.2 * u), (x + 2.2 * u, y + h - 2.2 * u), (x + w - 2.2 * u, y + h - 2.2 * u)]:
        ctx.arc(sx, sy, 0.8 * u, 0, 2 * math.pi)
        set_col(ctx, (90, 94, 98), 1)
        ctx.fill()
    return led_pos


def gateway_3q(ctx, x, y, w, h, d, leds=(1, 1, 0, 1), ang=-0.5):
    """Three-quarter view of the gateway: front panel + top with vents & logo."""
    dx, dy = box_oblique(ctx, x, y, w, h, d, ang, front=(30, 32, 35), top=(40, 43, 46), side=(18, 19, 21))
    # vents on top
    ctx.save()
    ctx.transform(top_face_matrix(x, y, w, d, ang))
    for i in range(14):
        rounded_rect(ctx, 0.08 + i * 0.03, 0.18, 0.012, 0.5, 0.006)
    set_col(ctx, (12, 13, 14), 1)
    ctx.fill()
    ctx.restore()
    # logo on top (drawn in a separate transformed context)
    ctx.save()
    ctx.transform(top_face_matrix(x, y, w, d, ang))
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.scale(1 / w, 1 / d)
    ctx.set_font_size(w * 0.045)
    set_col(ctx, C.WHITE, 0.8)
    ctx.move_to(w * 0.62, d * 0.55)
    ctx.show_text("HOME CIRCUIT")
    ctx.rectangle(w * 0.62, d * 0.62, w * 0.3, d * 0.02)
    set_col(ctx, C.GREEN, 0.9)
    ctx.fill()
    ctx.restore()
    # DIN clip on side
    ctx.rectangle(x + w + dx * 0.3, y + h * 0.3 + dy * 0.3, dx * 0.4, h * 0.4)
    set_col(ctx, (12, 12, 13), 0.8)
    ctx.fill()
    return gateway_front(ctx, x, y, w, h, leds)


# ================================================================== drone (top view)
def drone_top(ctx, cx, cy, s, arm_col=(30, 32, 34), prop_phase=None, leds=True):
    """X-frame quad seen from above. ``prop_phase`` None draws static blur discs."""
    arms = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    motor_pos = []
    for ax, ay in arms:
        mx, my = cx + ax * s * 0.62, cy + ay * s * 0.62
        motor_pos.append((mx, my))
        ctx.move_to(cx, cy)
        ctx.line_to(mx, my)
        set_col(ctx, arm_col, 1)
        ctx.set_line_width(s * 0.11)
        ctx.stroke()
        ctx.move_to(cx, cy)
        ctx.line_to(mx, my)
        set_col(ctx, (70, 74, 78), 0.5)
        ctx.set_line_width(s * 0.02)
        ctx.stroke()
    # body plates
    rounded_rect(ctx, cx - s * 0.3, cy - s * 0.42, s * 0.6, s * 0.84, s * 0.08)
    linear_fill(ctx, cx - s * 0.3, cy - s * 0.4, cx + s * 0.3, cy + s * 0.4, [(0, (48, 51, 54), 1), (1, (20, 21, 23), 1)])
    ctx.fill()
    # flight controller board
    ctx.save()
    fc = s * 0.34
    draw_board(ctx, cx - fc / 2, cy - fc / 2, fc, fc, seed=41, mask=(14, 20, 16), density=0.35,
               label="HC-FC", sub="", terminals=False, radius=fc * 0.08)
    ctx.restore()
    # GPS puck
    ctx.arc(cx, cy - s * 0.3, s * 0.09, 0, 2 * math.pi)
    radial_fill(ctx, cx - s * 0.02, cy - s * 0.32, 0, s * 0.1, [(0, (80, 84, 88), 1), (1, (26, 27, 29), 1)])
    ctx.fill()
    # battery strap
    ctx.rectangle(cx - s * 0.3, cy + s * 0.18, s * 0.6, s * 0.05)
    set_col(ctx, C.GREEN_DIM, 1)
    ctx.fill()
    for i, (mx, my) in enumerate(motor_pos):
        ctx.arc(mx, my, s * 0.12, 0, 2 * math.pi)
        radial_fill(ctx, mx - s * 0.03, my - s * 0.03, 0, s * 0.13, [(0, (150, 154, 160), 1), (0.6, (60, 62, 66), 1), (1, (20, 20, 22), 1)])
        ctx.fill()
        ctx.arc(mx, my, s * 0.05, 0, 2 * math.pi)
        set_col(ctx, (200, 150, 80), 1)
        ctx.fill()
        # prop disc
        ctx.arc(mx, my, s * 0.42, 0, 2 * math.pi)
        set_col(ctx, (190, 196, 200), 0.07)
        ctx.fill()
        if prop_phase is not None:
            ph = prop_phase * (1 if i % 2 == 0 else -1)
            for b in range(2):
                a = ph + b * math.pi
                for k in range(6):
                    aa = a - k * 0.09
                    ctx.move_to(mx + math.cos(aa) * s * 0.06, my + math.sin(aa) * s * 0.06)
                    ctx.line_to(mx + math.cos(aa) * s * 0.41, my + math.sin(aa) * s * 0.41)
                    set_col(ctx, (30, 32, 34), 0.5 * (1 - k / 6))
                    ctx.set_line_width(s * 0.05)
                    ctx.stroke()
        if leds:
            glow_spot(ctx, mx, my + s * 0.16, s * 0.08, C.GREEN if i < 2 else C.WHITE, 0.9)
    return motor_pos


def drone_side(ctx, cx, cy, s, prop_phase=0.0):
    """Side view (for take-off shot)."""
    # arms
    for sx in (-1, 1):
        ctx.move_to(cx, cy)
        ctx.line_to(cx + sx * s * 0.7, cy - s * 0.05)
        set_col(ctx, (26, 28, 30), 1)
        ctx.set_line_width(s * 0.06)
        ctx.stroke()
        mx = cx + sx * s * 0.7
        rounded_rect(ctx, mx - s * 0.06, cy - s * 0.16, s * 0.12, s * 0.12, s * 0.02)
        set_col(ctx, (60, 64, 68), 1)
        ctx.fill()
        # prop blur
        ctx.save()
        ctx.translate(mx, cy - s * 0.18)
        ctx.scale(1, 0.12)
        ctx.arc(0, 0, s * 0.36, 0, 2 * math.pi)
        ctx.restore()
        set_col(ctx, (200, 204, 208), 0.18)
        ctx.fill()
        bl = math.cos(prop_phase * (1 if sx > 0 else -1)) * s * 0.34
        ctx.move_to(mx - bl, cy - s * 0.18)
        ctx.line_to(mx + bl, cy - s * 0.18)
        set_col(ctx, (20, 20, 22), 0.6)
        ctx.set_line_width(s * 0.02)
        ctx.stroke()
    # body
    rounded_rect(ctx, cx - s * 0.3, cy - s * 0.1, s * 0.6, s * 0.2, s * 0.06)
    linear_fill(ctx, 0, cy - s * 0.1, 0, cy + s * 0.1, [(0, (64, 68, 72), 1), (1, (18, 19, 21), 1)])
    ctx.fill()
    ctx.rectangle(cx - s * 0.28, cy - s * 0.02, s * 0.56, s * 0.02)
    set_col(ctx, C.GREEN, 0.9)
    ctx.fill()
    # legs
    for sx in (-1, 1):
        ctx.move_to(cx + sx * s * 0.18, cy + s * 0.1)
        ctx.line_to(cx + sx * s * 0.3, cy + s * 0.32)
        ctx.line_to(cx + sx * s * 0.42, cy + s * 0.32)
        set_col(ctx, (24, 25, 27), 1)
        ctx.set_line_width(s * 0.03)
        ctx.stroke()
    glow_spot(ctx, cx + s * 0.3, cy, s * 0.06, C.GREEN, 1.0)


# ================================================================== misc
def solar_panel(ctx, x, y, w, h, skew=0.25):
    ctx.move_to(x, y)
    ctx.line_to(x + w, y - h * skew)
    ctx.line_to(x + w, y + h - h * skew)
    ctx.line_to(x, y + h)
    ctx.close_path()
    linear_fill(ctx, x, y, x + w, y + h, [(0, (40, 60, 90), 1), (1, (14, 20, 34), 1)])
    ctx.fill_preserve()
    set_col(ctx, (180, 186, 190), 1)
    ctx.set_line_width(3)
    ctx.stroke()
    for i in range(1, 6):
        fx = x + w * i / 6
        ctx.move_to(fx, y - h * skew * i / 6)
        ctx.line_to(fx, y + h - h * skew * i / 6)
    for j in range(1, 4):
        ctx.move_to(x, y + h * j / 4)
        ctx.line_to(x + w, y + h * j / 4 - h * skew)
    set_col(ctx, (120, 140, 170), 0.5)
    ctx.set_line_width(1.2)
    ctx.stroke()


def sensor_box(ctx, x, y, w, h, antenna=True, led_on=True):
    rounded_rect(ctx, x, y, w, h, w * 0.08)
    linear_fill(ctx, x, y, x + w, y + h, [(0, (214, 216, 218), 1), (1, (140, 144, 148), 1)])
    ctx.fill()
    ctx.rectangle(x + w * 0.1, y + h * 0.12, w * 0.8, h * 0.04)
    set_col(ctx, C.GREEN, 0.9)
    ctx.fill()
    if led_on:
        glow_spot(ctx, x + w * 0.8, y + h * 0.3, w * 0.12, C.GREEN, 1)
    if antenna:
        ctx.move_to(x + w * 0.2, y)
        ctx.line_to(x + w * 0.2, y - h * 0.9)
        set_col(ctx, (30, 30, 32), 1)
        ctx.set_line_width(w * 0.05)
        ctx.stroke()


def pendant_lamp(ctx, x, y, w, cord_top=0):
    ctx.move_to(x, cord_top)
    ctx.line_to(x, y)
    set_col(ctx, (20, 18, 16), 1)
    ctx.set_line_width(3)
    ctx.stroke()
    ctx.move_to(x - w * 0.12, y)
    ctx.line_to(x + w * 0.12, y)
    ctx.line_to(x + w / 2, y + w * 0.38)
    ctx.line_to(x - w / 2, y + w * 0.38)
    ctx.close_path()
    linear_fill(ctx, x - w / 2, y, x + w / 2, y, [(0, (30, 28, 26), 1), (0.5, (70, 62, 54), 1), (1, (26, 24, 22), 1)])
    ctx.fill()
    ctx.save()
    ctx.translate(x, y + w * 0.38)
    ctx.scale(w / 2, w * 0.05)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    set_col(ctx, (255, 226, 170), 1)
    ctx.fill()


def standing_fan(ctx, x, y, s, col=(30, 30, 32)):
    ctx.arc(x, y, s * 0.45, 0, 2 * math.pi)
    set_col(ctx, col, 1)
    ctx.set_line_width(s * 0.03)
    ctx.stroke()
    for i in range(8):
        a = i / 8 * math.pi * 2
        ctx.move_to(x, y)
        ctx.line_to(x + math.cos(a) * s * 0.45, y + math.sin(a) * s * 0.45)
    ctx.set_line_width(s * 0.008)
    ctx.stroke()
    for i in range(3):
        a = i / 3 * math.pi * 2 + 0.3
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(a)
        ctx.scale(s * 0.3, s * 0.12)
        ctx.arc(0.6, 0, 0.6, 0, 2 * math.pi)
        ctx.restore()
        set_col(ctx, col, 0.8)
        ctx.fill()
    ctx.arc(x, y, s * 0.07, 0, 2 * math.pi)
    set_col(ctx, col, 1)
    ctx.fill()
    ctx.move_to(x, y + s * 0.1)
    ctx.line_to(x, y + s * 1.6)
    ctx.set_line_width(s * 0.05)
    ctx.stroke()
    ctx.save()
    ctx.translate(x, y + s * 1.62)
    ctx.scale(s * 0.35, s * 0.06)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.fill()


def drawer_cabinet(ctx, x, y, cols, rows, cw, ch, col=(58, 60, 64)):
    rounded_rect(ctx, x - 6, y - 6, cols * cw + 12, rows * ch + 12, 6)
    set_col(ctx, col, 1)
    ctx.fill()
    r = rng(int(x + y))
    for i in range(cols):
        for j in range(rows):
            dx, dy = x + i * cw, y + j * ch
            rounded_rect(ctx, dx + 3, dy + 3, cw - 6, ch - 6, 3)
            tint = r.choice([(170, 190, 200), (200, 190, 160), (180, 200, 180)])
            set_col(ctx, tint, 0.28)
            ctx.fill()
            ctx.rectangle(dx + cw * 0.35, dy + ch * 0.62, cw * 0.3, ch * 0.12)
            set_col(ctx, (30, 30, 30), 0.8)
            ctx.fill()


def bokeh(ctx, w, h, n, seed, cols, rmin=10, rmax=60, amin=0.05, amax=0.25, region=None):
    r = rng(seed)
    x0, y0, x1, y1 = region or (0, 0, w, h)
    for _ in range(n):
        x, y = r.uniform(x0, x1), r.uniform(y0, y1)
        rr = r.uniform(rmin, rmax)
        col = r.choice(cols)
        a = r.uniform(amin, amax)
        radial_fill(ctx, x, y, 0, rr, [(0, col, a), (0.8, col, a * 0.8), (1, col, 0)])
        ctx.arc(x, y, rr, 0, 2 * math.pi)
        ctx.fill()


def hand_blob(ctx, x, y, s, ang=0.0, col=C.SKIN):
    """Out-of-focus hand/finger shape (only ever used heavily blurred in the foreground)."""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    radial_fill(ctx, -s * 0.2, -s * 0.1, 0, s * 1.2, [(0, tuple(min(255, c + 30) for c in col), 1), (1, tuple(int(c * 0.55) for c in col), 1)])
    ctx.save()
    ctx.scale(s * 0.9, s * 0.55)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.fill()
    for k in range(2):
        ctx.save()
        ctx.translate(s * (0.8 + k * 0.1), -s * (0.25 - k * 0.3))
        ctx.rotate(-0.25 + k * 0.2)
        ctx.scale(s * 0.75, s * 0.17)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.fill()
    ctx.restore()
