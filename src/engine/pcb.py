"""PCB graphics: trace routing, animated trace drawing, boards, schematic and CAD views."""
import math

import cairo

from .. import config as C
from .canvas import (glow, glow_spot, linear_fill, radial_fill, rounded_rect, set_col,
                     surface, to_pil)
from .util import clamp, ease_in_out, rng


# ================================================================== routing
def route(x0, y0, x1, y1, bend=0.5):
    """PCB-style path: horizontal, 45 degree diagonal, horizontal."""
    dy = y1 - y0
    dx = x1 - x0
    if abs(dy) < 1:
        return [(x0, y0), (x1, y1)]
    sgn = 1 if dx >= 0 else -1
    run = abs(dy)
    xm = x0 + dx * bend
    a = xm - sgn * run / 2
    b = xm + sgn * run / 2
    if sgn * (a - x0) < 0:
        a, b = x0, x0 + sgn * run
    return [(x0, y0), (a, y0), (b, y1), (x1, y1)]


def route_v(x0, y0, x1, y1, bend=0.5):
    """Vertical-first variant."""
    pts = route(y0, x0, y1, x1, bend)
    return [(y, x) for x, y in pts]


def random_traces(seed, w, h, n=40, pitch=18, margin=0, horizontal_bias=0.6):
    """Random bus-like traces for background texture. Returns list of polylines."""
    r = rng(seed)
    lines = []
    for _ in range(n):
        horiz = r.random() < horizontal_bias
        if horiz:
            y = round(r.uniform(margin, h - margin) / pitch) * pitch
            x0 = r.uniform(-50, w * 0.6)
            x1 = x0 + r.uniform(w * 0.15, w * 0.6)
            y1 = y + r.choice([-1, 1]) * pitch * r.randint(1, 6)
            lines.append(route(x0, y, x1, y1, r.uniform(0.25, 0.75)))
        else:
            x = round(r.uniform(margin, w - margin) / pitch) * pitch
            y0 = r.uniform(-50, h * 0.6)
            y1 = y0 + r.uniform(h * 0.15, h * 0.6)
            x1 = x + r.choice([-1, 1]) * pitch * r.randint(1, 6)
            lines.append(route_v(x, y0, x1, y1, r.uniform(0.25, 0.75)))
    return lines


def bus(x0, y0, x1, y1, count=5, pitch=16, bend=0.5):
    """Parallel traces (a data bus) from one point to another."""
    out = []
    for i in range(count):
        o = (i - (count - 1) / 2) * pitch
        out.append(route(x0, y0 + o, x1, y1 + o, bend + (i - count / 2) * 0.02))
    return out


# ================================================================== drawing helpers
def poly_length(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def poly_partial(pts, p):
    """Sub-polyline covering fraction ``p`` of the length; returns (pts, head)."""
    p = clamp(p)
    total = poly_length(pts)
    if total == 0 or p <= 0:
        return [pts[0]], pts[0]
    target = total * p
    out = [pts[0]]
    acc = 0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = math.dist(a, b)
        if acc + seg >= target:
            f = (target - acc) / seg if seg else 0
            head = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            out.append(head)
            return out, head
        out.append(b)
        acc += seg
    return out, pts[-1]


def stroke_poly(ctx, pts, width, col, a=1.0):
    if len(pts) < 2:
        return
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    set_col(ctx, col, a)
    ctx.set_line_width(width)
    ctx.stroke()


def node(ctx, x, y, r, col, a=1.0, ring=True):
    ctx.new_path()
    if ring:
        ctx.arc(x, y, r, 0, 2 * math.pi)
        set_col(ctx, col, a)
        ctx.set_line_width(max(1.0, r * 0.45))
        ctx.stroke()
        ctx.new_sub_path()
        ctx.arc(x, y, r * 0.35, 0, 2 * math.pi)
        ctx.fill()
    else:
        ctx.arc(x, y, r, 0, 2 * math.pi)
        set_col(ctx, col, a)
        ctx.fill()


class TraceAnim:
    """Animated set of traces drawing themselves on (with a bright travelling head).

    items: list of dicts {pts, t0, dur, width, col, end_node}
    """

    def __init__(self, items, glow_radius=10, glow_strength=1.2, head=True):
        self.items = items
        self.glow_radius = glow_radius
        self.glow_strength = glow_strength
        self.head = head

    def render(self, t, size=(C.W, C.H), alpha=1.0):
        s, ctx = surface(*size)
        any_drawn = False
        for it in self.items:
            p = (t - it["t0"]) / it["dur"]
            if p <= 0:
                continue
            any_drawn = True
            p = ease_in_out(clamp(p)) if it.get("ease", True) else clamp(p)
            pts, head = poly_partial(it["pts"], p)
            col = it.get("col", C.GREEN)
            w = it.get("width", 3)
            stroke_poly(ctx, pts, w, col, it.get("alpha", 1.0) * alpha)
            if it.get("start_node", True):
                node(ctx, *it["pts"][0], w * 1.8, col, alpha)
            if p >= 1 and it.get("end_node", True):
                node(ctx, *it["pts"][-1], w * 1.8, col, alpha)
            elif self.head and p < 1:
                node(ctx, *head, w * 1.1, C.WHITE, alpha, ring=False)
        if not any_drawn:
            return None
        img = to_pil(s)
        return glow(img, self.glow_radius, self.glow_strength) if self.glow_radius else img


# ================================================================== boards
def draw_board(ctx, x, y, w, h, seed=1, mask=(18, 44, 30), copper=None, silk=C.WHITE,
               label="HOME CIRCUIT", sub="HC-DEV REV A", density=1.0, leds_on=True,
               terminals=True, ethernet=False, radius=14):
    """Draw a detailed top-view PCB into ``ctx``. Returns dict of feature coordinates."""
    r = rng(seed)
    feats = {"leds": [], "ics": [], "pads": []}
    copper = copper or tuple(min(255, int(c * 1.55 + 10)) for c in mask)
    # board body
    ctx.save()
    rounded_rect(ctx, x, y, w, h, radius)
    ctx.clip_preserve()
    linear_fill(ctx, x, y, x + w * 0.4, y + h, [(0, tuple(int(c * 1.25) for c in mask), 1),
                                                (1, tuple(int(c * 0.8) for c in mask), 1)])
    ctx.fill()
    # background copper routing (under soldermask)
    for pts in random_traces(seed + 11, w, h, n=int(70 * density), pitch=max(8, w / 90), margin=10):
        stroke_poly(ctx, [(x + a, y + b) for a, b in pts], max(1.2, w / 700), copper, 0.55)
    # vias
    for _ in range(int(120 * density)):
        vx, vy = x + r.uniform(10, w - 10), y + r.uniform(10, h - 10)
        node(ctx, vx, vy, max(1.5, w / 480), C.GOLD, 0.8)
    ctx.restore()
    # edge
    rounded_rect(ctx, x, y, w, h, radius)
    set_col(ctx, tuple(min(255, int(c * 2.0)) for c in mask), 0.9)
    ctx.set_line_width(max(1.5, w / 600))
    ctx.stroke()
    u = w / 100.0  # unit
    # mounting holes
    for hx, hy in [(x + 4 * u, y + 4 * u), (x + w - 4 * u, y + 4 * u), (x + 4 * u, y + h - 4 * u), (x + w - 4 * u, y + h - 4 * u)]:
        ctx.arc(hx, hy, 2.2 * u, 0, 2 * math.pi)
        set_col(ctx, C.GOLD, 1)
        ctx.fill()
        ctx.arc(hx, hy, 1.3 * u, 0, 2 * math.pi)
        set_col(ctx, (8, 8, 8), 1)
        ctx.fill()
    # main MCU (QFP)
    cx, cy, s = x + w * 0.46, y + h * 0.48, 15 * u
    qfp(ctx, cx, cy, s, u, "HC32", seed)
    feats["ics"].append((cx, cy, s))
    # fanout traces from the MCU (bright copper on top)
    for i in range(12):
        ang = i / 12 * 2 * math.pi
        sx, sy = cx + math.cos(ang) * s * 0.75, cy + math.sin(ang) * s * 0.75
        ex, ey = x + r.uniform(0.1, 0.9) * w, y + r.uniform(0.1, 0.9) * h
        stroke_poly(ctx, route(sx, sy, ex, ey, r.uniform(0.3, 0.7)), max(1.4, u * 0.35), copper, 0.8)
    # secondary ICs
    for (fx, fy, fs, name) in [(0.74, 0.30, 7.5, "ETH"), (0.22, 0.30, 6.5, "485"), (0.74, 0.70, 6, "PWR"),
                               (0.25, 0.72, 5.5, "MEM")]:
        soic(ctx, x + w * fx, y + h * fy, fs * u, u, name)
        feats["ics"].append((x + w * fx, y + h * fy, fs * u))
    # passives
    for _ in range(int(46 * density)):
        px, py = x + r.uniform(0.08, 0.92) * w, y + r.uniform(0.1, 0.9) * h
        if abs(px - cx) < s * 0.9 and abs(py - cy) < s * 0.9:
            continue
        passive(ctx, px, py, u * r.choice([1.6, 2.0, 2.4]), r.random() < 0.5, r.choice([0, 90]), r)
    # crystal
    ctx.save()
    rounded_rect(ctx, cx + s * 0.95, cy - 2 * u, 5 * u, 2.4 * u, 1.1 * u)
    linear_fill(ctx, 0, cy - 2 * u, 0, cy + 0.4 * u, [(0, (220, 222, 225), 1), (1, (130, 134, 140), 1)])
    ctx.fill()
    ctx.restore()
    # pin header (top edge)
    header(ctx, x + w * 0.30, y + 3.4 * u, 10, u)
    # terminals (bottom edge) - green terminal blocks
    if terminals:
        for k in range(2):
            terminal_block(ctx, x + w * (0.16 + k * 0.34), y + h - 9.5 * u, 4, u)
    if ethernet:
        rj45(ctx, x + w - 17 * u, y + h * 0.36, u)
    # usb connector (left edge)
    rounded_rect(ctx, x - 1.2 * u, y + h * 0.46, 7 * u, 5 * u, 1.2 * u)
    linear_fill(ctx, 0, y + h * 0.46, 0, y + h * 0.46 + 5 * u, [(0, (215, 218, 222), 1), (1, (120, 124, 130), 1)])
    ctx.fill()
    # LEDs
    for i, col in enumerate([C.GREEN, C.GREEN, (255, 170, 60), C.GREEN]):
        lx, ly = x + w * 0.75 + i * 3.4 * u, y + h * 0.80
        rounded_rect(ctx, lx - 1.1 * u, ly - 0.7 * u, 2.2 * u, 1.4 * u, 0.3 * u)
        set_col(ctx, col if leds_on else (70, 74, 70), 1)
        ctx.fill()
        feats["leds"].append((lx, ly, col))
    # silkscreen
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(2.6 * u)
    set_col(ctx, silk, 0.92)
    ctx.move_to(x + w * 0.73, y + h * 0.90)
    ctx.show_text(label)
    ctx.set_font_size(1.6 * u)
    ctx.move_to(x + w * 0.73, y + h * 0.90 + 2.4 * u)
    ctx.show_text(sub)
    # silk outlines / refdes
    ctx.set_font_size(1.2 * u)
    for i in range(18):
        ctx.move_to(x + r.uniform(0.08, 0.9) * w, y + r.uniform(0.1, 0.85) * h)
        ctx.show_text(r.choice("RCUDLQ") + str(r.randint(1, 48)))
    feats["mcu"] = (cx, cy, s)
    return feats


def qfp(ctx, cx, cy, s, u, label="MCU", seed=0):
    n = 12
    pin_l, pin_w = s * 0.14, s * 0.028
    set_col(ctx, (205, 206, 210), 1)
    for side in range(4):
        for i in range(n):
            o = (i - (n - 1) / 2) * (s * 0.8 / n)
            if side == 0:
                ctx.rectangle(cx + o - pin_w / 2, cy - s / 2 - pin_l, pin_w, pin_l)
            elif side == 1:
                ctx.rectangle(cx + o - pin_w / 2, cy + s / 2, pin_w, pin_l)
            elif side == 2:
                ctx.rectangle(cx - s / 2 - pin_l, cy + o - pin_w / 2, pin_l, pin_w)
            else:
                ctx.rectangle(cx + s / 2, cy + o - pin_w / 2, pin_l, pin_w)
    ctx.fill()
    rounded_rect(ctx, cx - s / 2, cy - s / 2, s, s, s * 0.04)
    linear_fill(ctx, cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2, [(0, (44, 46, 50), 1), (1, (16, 17, 19), 1)])
    ctx.fill()
    ctx.arc(cx - s * 0.36, cy - s * 0.36, s * 0.045, 0, 2 * math.pi)
    set_col(ctx, (70, 72, 76), 1)
    ctx.fill()
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(s * 0.16)
    set_col(ctx, (150, 154, 158), 0.8)
    ext = ctx.text_extents(label)
    ctx.move_to(cx - ext.width / 2, cy + s * 0.06)
    ctx.show_text(label)


def soic(ctx, cx, cy, s, u, label=""):
    n = 5
    set_col(ctx, (200, 202, 206), 1)
    for i in range(n):
        o = (i - (n - 1) / 2) * (s * 0.18)
        ctx.rectangle(cx + o - s * 0.035, cy - s * 0.42, s * 0.07, s * 0.84)
    ctx.fill()
    rounded_rect(ctx, cx - s / 2, cy - s * 0.3, s, s * 0.6, s * 0.04)
    linear_fill(ctx, cx, cy - s * 0.3, cx, cy + s * 0.3, [(0, (40, 42, 45), 1), (1, (16, 17, 18), 1)])
    ctx.fill()
    if label:
        ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(s * 0.18)
        set_col(ctx, (140, 144, 148), 0.8)
        ext = ctx.text_extents(label)
        ctx.move_to(cx - ext.width / 2, cy + s * 0.06)
        ctx.show_text(label)


def passive(ctx, x, y, L, is_cap, rot, r):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    w, h = L, L * 0.5
    body = (178, 150, 110) if is_cap else (22, 22, 24)
    set_col(ctx, (210, 210, 214), 1)
    ctx.rectangle(-w / 2, -h / 2, w * 0.22, h)
    ctx.rectangle(w / 2 - w * 0.22, -h / 2, w * 0.22, h)
    ctx.fill()
    set_col(ctx, body, 1)
    ctx.rectangle(-w / 2 + w * 0.22, -h / 2, w * 0.56, h)
    ctx.fill()
    ctx.restore()


def header(ctx, x, y, n, u):
    pitch = 2.54 * u * 0.9
    rounded_rect(ctx, x, y - pitch / 2, pitch * n, pitch, 0.3 * u)
    set_col(ctx, (14, 14, 15), 1)
    ctx.fill()
    for i in range(n):
        px = x + pitch * (i + 0.5)
        ctx.rectangle(px - 0.35 * u, y - 0.35 * u, 0.7 * u, 0.7 * u)
        set_col(ctx, C.GOLD, 1)
        ctx.fill()


def terminal_block(ctx, x, y, n, u, col=(30, 150, 80)):
    pitch = 5 * u
    rounded_rect(ctx, x, y, pitch * n, 7 * u, 0.6 * u)
    linear_fill(ctx, x, y, x, y + 7 * u, [(0, tuple(min(255, int(c * 1.25)) for c in col), 1), (1, tuple(int(c * 0.6) for c in col), 1)])
    ctx.fill()
    for i in range(n):
        px = x + pitch * (i + 0.5)
        ctx.arc(px, y + 2.6 * u, 1.5 * u, 0, 2 * math.pi)
        set_col(ctx, (190, 194, 198), 1)
        ctx.fill()
        ctx.move_to(px - 1.0 * u, y + 2.6 * u)
        ctx.line_to(px + 1.0 * u, y + 2.6 * u)
        set_col(ctx, (80, 84, 88), 1)
        ctx.set_line_width(0.35 * u)
        ctx.stroke()
        rounded_rect(ctx, px - 1.5 * u, y + 4.6 * u, 3 * u, 1.8 * u, 0.3 * u)
        set_col(ctx, (10, 30, 18), 1)
        ctx.fill()


def rj45(ctx, x, y, u):
    rounded_rect(ctx, x, y, 14 * u, 13 * u, 0.8 * u)
    linear_fill(ctx, x, y, x + 14 * u, y + 13 * u, [(0, (212, 214, 218), 1), (1, (120, 124, 128), 1)])
    ctx.fill()
    rounded_rect(ctx, x + 2.5 * u, y + 2.5 * u, 9 * u, 7 * u, 0.5 * u)
    set_col(ctx, (12, 12, 13), 1)
    ctx.fill()


# ================================================================== CAD / schematic (animated)
def draw_cad_layout(ctx, rect, p, seed=3, t=0.0):
    """PCB layout editor look. ``p`` = routing progress 0..1."""
    x, y, w, h = rect
    r = rng(seed)
    # grid dots
    set_col(ctx, (60, 66, 64), 0.6)
    step = 24
    gx0 = int(x - 200)
    for gx in range(gx0, int(x + w + 200), step):
        for gy in range(int(y - 120), int(y + h + 120), step):
            ctx.rectangle(gx, gy, 1.5, 1.5)
    ctx.fill()
    # board outline
    rounded_rect(ctx, x, y, w, h, 16)
    set_col(ctx, (230, 232, 230), 0.9)
    ctx.set_line_width(2)
    ctx.stroke()
    u = w / 100
    # footprints
    comps = [(0.46, 0.48, 16, 16), (0.74, 0.30, 9, 6), (0.22, 0.30, 8, 5), (0.74, 0.70, 7, 5), (0.25, 0.72, 7, 4)]
    pads = []
    for fx, fy, fw, fh in comps:
        cx, cy = x + w * fx, y + h * fy
        set_col(ctx, (235, 235, 235), 0.7)
        ctx.set_line_width(1.2)
        ctx.rectangle(cx - fw * u / 2, cy - fh * u / 2, fw * u, fh * u)
        ctx.stroke()
        n = 6
        for i in range(n):
            o = (i - (n - 1) / 2) * fw * u / n
            for side in (-1, 1):
                px, py = cx + o, cy + side * (fh * u / 2 + 1.2 * u)
                pads.append((px, py))
                set_col(ctx, (170, 176, 178), 0.9)
                ctx.rectangle(px - 0.5 * u, py - 0.8 * u, 1.0 * u, 1.6 * u)
                ctx.fill()
    for _ in range(40):
        px, py = x + r.uniform(0.08, 0.92) * w, y + r.uniform(0.12, 0.88) * h
        set_col(ctx, (170, 176, 178), 0.8)
        ctx.rectangle(px - 1.2 * u, py - 0.5 * u, 0.8 * u, 1.0 * u)
        ctx.rectangle(px + 0.4 * u, py - 0.5 * u, 0.8 * u, 1.0 * u)
        ctx.fill()
    # routes: pad -> nearby pad, manhattan with 45 degree corners
    rr = rng(seed + 5)
    routes = []
    for i in range(60):
        a = pads[rr.randrange(len(pads))]
        near = [b for b in pads if 90 < math.dist(a, b) < w * 0.38]
        if not near:
            continue
        b = near[rr.randrange(len(near))]
        fn = route if abs(b[0] - a[0]) >= abs(b[1] - a[1]) else route_v
        routes.append((fn(a[0], a[1], b[0], b[1], rr.uniform(0.3, 0.7)), rr.random() < 0.7))
        if len(routes) >= 34:
            break
    n = len(routes)
    for i, (pts, top) in enumerate(routes):
        local = clamp(p * n * 1.15 - i * 1.0)
        if local <= 0:
            # ratsnest
            set_col(ctx, (200, 200, 200), 0.18)
            ctx.set_line_width(1)
            ctx.move_to(*pts[0])
            ctx.line_to(*pts[-1])
            ctx.stroke()
            continue
        sub, head = poly_partial(pts, local)
        stroke_poly(ctx, sub, 0.55 * u if top else 0.45 * u, C.GREEN if top else (30, 120, 80), 0.95 if top else 0.7)
        if local < 1:
            node(ctx, *head, 0.7 * u, C.WHITE, 1, ring=False)
    return pads


def draw_schematic(ctx, rect, p, t=0.0):
    """Hand-tidy engineering schematic with a draw-on progress ``p``."""
    x, y, w, h = rect
    u = w / 100
    line_col = (225, 228, 226)

    def seg(pts, t0, t1, col=line_col, width=2.0):
        lp = clamp((p - t0) / max(1e-4, t1 - t0))
        if lp <= 0:
            return
        sub, _ = poly_partial(pts, lp)
        stroke_poly(ctx, sub, width, col, 0.95)

    def label(txt, lx, ly, t0, size=1.8, col=line_col):
        if p < t0:
            return
        a = clamp((p - t0) / 0.05)
        ctx.select_font_face("Noto Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(size * u)
        set_col(ctx, col, a)
        ctx.move_to(lx, ly)
        ctx.show_text(txt)

    # frame / title block
    seg([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], 0.0, 0.12, (110, 116, 114), 1.2)
    seg([(x + w * 0.70, y + h), (x + w * 0.70, y + h * 0.88), (x + w, y + h * 0.88)], 0.08, 0.14, (110, 116, 114), 1.2)
    label("HC-DEV  /  REV A", x + w * 0.72, y + h * 0.955, 0.14, 1.7, (150, 156, 154))
    # MCU block
    mx, my, mw, mh = x + w * 0.38, y + h * 0.22, w * 0.22, h * 0.52
    seg([(mx, my), (mx + mw, my), (mx + mw, my + mh), (mx, my + mh), (mx, my)], 0.1, 0.3, C.GREEN, 2.4)
    label("U1  MCU", mx + mw * 0.2, my + mh * 0.52, 0.28, 2.2, C.GREEN)
    # pins + nets
    nets_l = ["VIN", "SDA", "SCL", "AIN0"]
    nets_r = ["RELAY", "TX", "RX", "LED"]
    for i, nm in enumerate(nets_l):
        py = my + mh * (0.15 + i * 0.23)
        seg([(mx, py), (mx - w * 0.14, py)], 0.3 + i * 0.03, 0.42 + i * 0.03)
        label(nm, mx - w * 0.13, py - 0.8 * u, 0.42 + i * 0.03, 1.5)
    for i, nm in enumerate(nets_r):
        py = my + mh * (0.15 + i * 0.23)
        seg([(mx + mw, py), (mx + mw + w * 0.14, py)], 0.34 + i * 0.03, 0.46 + i * 0.03)
        label(nm, mx + mw + w * 0.02, py - 0.8 * u, 0.46 + i * 0.03, 1.5)
    # resistor (zigzag) on left
    rx0, ry = x + w * 0.10, my + mh * 0.15
    zz = [(rx0, ry)]
    for k in range(7):
        zz.append((rx0 + (k + 0.5) * u * 1.4, ry + (-1.2 * u if k % 2 == 0 else 1.2 * u)))
    zz.append((rx0 + 8 * u * 1.2, ry))
    seg([(x + w * 0.03, ry), (rx0, ry)], 0.45, 0.5)
    seg(zz, 0.5, 0.6)
    seg([(zz[-1][0], ry), (mx - w * 0.14, ry)], 0.58, 0.62)
    label("R1 10k", rx0, ry - 2.4 * u, 0.6, 1.5)
    # capacitor to ground
    cx = x + w * 0.2
    cy = my + mh * 0.84
    seg([(cx, my + mh * 0.61), (cx, cy - 0.6 * u)], 0.55, 0.6)
    seg([(cx - 2.5 * u, cy - 0.6 * u), (cx + 2.5 * u, cy - 0.6 * u)], 0.6, 0.62)
    seg([(cx - 2.5 * u, cy + 0.6 * u), (cx + 2.5 * u, cy + 0.6 * u)], 0.62, 0.64)
    seg([(cx, cy + 0.6 * u), (cx, cy + 4 * u)], 0.64, 0.67)
    for k in range(3):
        seg([(cx - (2.2 - k * 0.7) * u, cy + (4 + k * 0.8) * u), (cx + (2.2 - k * 0.7) * u, cy + (4 + k * 0.8) * u)], 0.67, 0.7)
    seg([(cx, my + mh * 0.61), (mx - w * 0.14, my + mh * 0.61)], 0.6, 0.64)
    label("C3 100n", cx + 3 * u, cy, 0.66, 1.5)
    # relay coil + diode on right
    kx, ky = x + w * 0.80, my + mh * 0.15
    seg([(kx, ky), (kx, ky + 3 * u)], 0.62, 0.65)
    seg([(kx - 3 * u, ky + 3 * u), (kx + 3 * u, ky + 3 * u), (kx + 3 * u, ky + 9 * u), (kx - 3 * u, ky + 9 * u), (kx - 3 * u, ky + 3 * u)], 0.65, 0.75, C.GREEN, 2.2)
    seg([(kx - 3 * u, ky + 9 * u), (kx + 3 * u, ky + 3 * u)], 0.74, 0.78, C.GREEN, 1.6)
    label("K1 RELAY", kx + 4 * u, ky + 6.5 * u, 0.76, 1.5, C.GREEN)
    seg([(mx + mw + w * 0.14, ky), (kx, ky)], 0.6, 0.64)
    # LED
    lx, ly = x + w * 0.80, my + mh * 0.84
    seg([(mx + mw + w * 0.14, ly), (lx - 2 * u, ly)], 0.7, 0.74)
    seg([(lx - 2 * u, ly - 2 * u), (lx - 2 * u, ly + 2 * u), (lx + 1.5 * u, ly), (lx - 2 * u, ly - 2 * u)], 0.74, 0.8)
    seg([(lx + 1.5 * u, ly - 2 * u), (lx + 1.5 * u, ly + 2 * u)], 0.8, 0.82)
    seg([(lx + 0.5 * u, ly - 3 * u), (lx + 2.5 * u, ly - 5 * u)], 0.82, 0.85, C.GREEN, 1.4)
    seg([(lx + 2 * u, ly - 2.5 * u), (lx + 4 * u, ly - 4.5 * u)], 0.83, 0.86, C.GREEN, 1.4)
    label("D2", lx + 3 * u, ly + 3.5 * u, 0.84, 1.5)
    # junction dots
    if p > 0.66:
        for jx, jy in [(cx, my + mh * 0.61)]:
            node(ctx, jx, jy, 0.6 * u, line_col, 1, ring=False)


def circuit_backdrop(w, h, seed=5, col=(40, 70, 52), alpha=0.35, grid=True, bg=C.CHARCOAL):
    """Static subtle PCB/grid background plate (PIL RGBA)."""
    s, ctx = surface(w, h)
    set_col(ctx, bg, 1)
    ctx.paint()
    radial_fill(ctx, w / 2, h / 2, 0, max(w, h) * 0.7, [(0, tuple(min(255, c + 10) for c in bg), 1), (1, tuple(max(0, c - 12) for c in bg), 1)])
    ctx.paint()
    if grid:
        set_col(ctx, (255, 255, 255), 0.035)
        ctx.set_line_width(1)
        for gx in range(0, w, 60):
            ctx.move_to(gx + 0.5, 0)
            ctx.line_to(gx + 0.5, h)
        for gy in range(0, h, 60):
            ctx.move_to(0, gy + 0.5)
            ctx.line_to(w, gy + 0.5)
        ctx.stroke()
    for pts in random_traces(seed, w, h, n=90, pitch=20):
        stroke_poly(ctx, pts, 2, col, alpha)
        node(ctx, *pts[-1], 3.5, col, alpha)
    return to_pil(s)
