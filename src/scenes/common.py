"""Shared building blocks for scenes: overlays, plate-space animation helpers, transitions."""
import math

import cairo
from PIL import Image

from .. import config as C
from ..engine import overlays as O
from ..engine.camera import Cam, Plate, Sprite
from ..engine.canvas import (fast_blur, glow, glow_spot, linear_fill, radial_fill, rounded_rect,
                             set_col, surface, to_pil)
from ..engine.pcb import TraceAnim, node, poly_partial, random_traces, route, stroke_poly
from ..engine.scene import Overlay
from ..engine.text import Line, draw_lines, text_image
from ..engine.util import clamp, ease_in_out, ease_out, ease_out_expo, flicker, progress, rng
from ..plates import PH, PW

__all__ = ["Cam", "Overlay", "Line", "title", "badge", "label", "dim", "trace_wipe", "plate_layer",
           "glow_dot_layer", "code_layer", "scope_in_plate", "hud_corners", "Plate", "PW", "PH"]


# ------------------------------------------------------------------ overlays (screen space)
def title(lines, t_in, t_out, anim="mask", center=(C.W / 2, C.H / 2), z=10, **kw):
    def draw(frame, t, dur):
        return draw_lines(frame, lines, t + t_in, t_in, t_out, anim=anim, center=center, **kw)
    return Overlay(t_in, t_out, draw, z)


def badge(t_in, t_out, fade=0.25):
    def draw(frame, t, dur):
        a = min(1.0, t / fade if fade else 1, (dur - t) / fade if fade else 1)
        return O.draft_badge(frame, max(0.0, a))
    return Overlay(t_in, t_out, draw, 50)


_TOPBAND = {}


def _top_band(h=330, a=0.55):
    if h not in _TOPBAND:
        s, ctx = surface(C.W, h)
        linear_fill(ctx, 0, 0, 0, h, [(0, (0, 0, 0), a), (0.6, (0, 0, 0), a * 0.45), (1, (0, 0, 0), 0)])
        ctx.paint()
        _TOPBAND[h] = to_pil(s)
    return _TOPBAND[h]


def label(text, t_in, t_out, index=None, total=None, sub=None, y=128, size=60, z=20, band=True):
    def draw(frame, t, dur):
        if band:
            k = min(1.0, t / 0.2, (dur - t) / 0.2)
            frame.alpha_composite(_a(_top_band(), max(0.0, k)))
        return O.category_label(frame, text, t, dur, index, total, y=y, size=size, sub=sub)
    return Overlay(t_in, t_out, draw, z)


def caption(text, t_in, t_out, y=200, size=22, color=C.LIGHT_GREY, z=21):
    """Small tracked mono caption, centred (fades)."""
    img = text_image(text, "mono", size, color, 80)

    def draw(frame, t, dur):
        a = min(1.0, t / 0.25, (dur - t) / 0.2)
        if a > 0:
            frame.alpha_composite(_a(img, a), dest=(int(C.W / 2 - img.width / 2), int(y)))
        return frame
    return Overlay(t_in, t_out, draw, z)


def dim(t_in, t_out, amount=0.55, fade=0.3, z=5, color=(0, 0, 0)):
    def draw(frame, t, dur):
        a = amount * min(1.0, t / fade if fade else 1, (dur - t) / fade if fade else 1)
        if a <= 0:
            return frame
        frame.alpha_composite(Image.new("RGBA", frame.size, tuple(color) + (int(255 * a),)))
        return frame
    return Overlay(t_in, t_out, draw, z)


def vignette_band(t_in, t_out, y0=0.55, amount=0.75, z=6):
    """Darken the lower part of the frame (for legible centre/bottom text)."""
    s, ctx = surface(C.W, C.H)
    linear_fill(ctx, 0, C.H * y0, 0, C.H, [(0, (0, 0, 0), 0), (1, (0, 0, 0), amount)])
    ctx.paint()
    band = to_pil(s)

    def draw(frame, t, dur):
        frame.alpha_composite(band)
        return frame
    return Overlay(t_in, t_out, draw, z)


def trace_wipe(t_cut, dur=0.5, seed=1, n=9, z=40, direction=1):
    """Bright green PCB traces sweeping across the frame around a cut (stage linking)."""
    r = rng(seed)
    items = []
    for i in range(n):
        y = C.H * (0.15 + 0.7 * i / (n - 1)) + r.uniform(-20, 20)
        y2 = y + r.choice([-1, 1]) * r.randint(1, 3) * 40
        x0, x1 = (-60, C.W + 60) if direction > 0 else (C.W + 60, -60)
        items.append({"pts": route(x0, y, x1, y2, r.uniform(0.3, 0.7)), "t0": r.uniform(0, 0.08),
                      "dur": dur * r.uniform(0.7, 1.0), "width": r.choice([2, 3, 4]), "ease": False,
                      "start_node": False, "end_node": False})
    anim = TraceAnim(items, glow_radius=8, glow_strength=1.3)
    t0 = t_cut - dur * 0.55

    def draw(frame, t, d):
        tt = t
        # fade out the drawn traces after the head passed
        fade = 1 - progress(tt, dur * 0.7, dur * 1.3)
        img = anim.render(tt, alpha=fade)
        if img is not None:
            frame.alpha_composite(img)
        return frame
    return Overlay(t0, t0 + dur * 1.3, draw, z)


def hud_corners(t_in, t_out, text_tl="", text_br="", z=15, col=C.WHITE, a=0.55):
    """Subtle engineering viewfinder corners + tiny mono readouts."""
    s, ctx = surface(C.W, C.H)
    L_, m = 46, 60
    set_col(ctx, col, a)
    ctx.set_line_width(2)
    for (x, y, dx, dy) in [(m, m, 1, 1), (C.W - m, m, -1, 1), (m, C.H - m, 1, -1), (C.W - m, C.H - m, -1, -1)]:
        ctx.move_to(x, y + dy * L_)
        ctx.line_to(x, y)
        ctx.line_to(x + dx * L_, y)
        ctx.stroke()
    base = to_pil(s)
    tl = text_image(text_tl, "mono", 20, C.LIGHT_GREY, 60) if text_tl else None
    br = text_image(text_br, "mono", 20, C.GREEN, 60) if text_br else None

    def draw(frame, t, dur):
        k = min(1.0, t / 0.2, (dur - t) / 0.2)
        if k <= 0:
            return frame
        frame.alpha_composite(_a(base, k))
        if tl:
            frame.alpha_composite(_a(tl, k), dest=(m + 14, m + 10))
        if br:
            frame.alpha_composite(_a(br, k), dest=(C.W - m - 14 - br.width, C.H - m - 10 - br.height))
        return frame
    return Overlay(t_in, t_out, draw, z)


def _a(img, k):
    if k >= 0.999:
        return img
    im = img.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * k)))
    return im


# ------------------------------------------------------------------ plate-space helpers (dyn)
def plate_layer(draw_fn, bbox=None, blur_r=0, glow_r=0, glow_s=1.0):
    """Run cairo ``draw_fn(ctx, ox, oy)`` on a surface covering bbox (plate coords) and
    return a plate-sized RGBA layer. ox, oy = bbox origin to subtract from coordinates."""
    x0, y0, x1, y1 = bbox or (0, 0, PW, PH)
    x0, y0 = int(max(0, x0)), int(max(0, y0))
    x1, y1 = int(min(PW, x1)), int(min(PH, y1))
    s, ctx = surface(x1 - x0, y1 - y0)
    ctx.translate(-x0, -y0)
    draw_fn(ctx)
    im = to_pil(s)
    if glow_r:
        im = glow(im, glow_r, glow_s)
    if blur_r:
        im = fast_blur(im, blur_r)
    return Sprite(im, x0, y0)


def glow_dot_layer(points, t, radius=40, blink=None, seed=0):
    """LED glows in plate space. points: list of (x, y, col). blink: None | 'blink' | 'flicker'."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    bbox = (min(xs) - radius * 2, min(ys) - radius * 2, max(xs) + radius * 2, max(ys) + radius * 2)

    def fn(ctx):
        for i, (x, y, col) in enumerate(points):
            a = 1.0
            if blink == "blink":
                a = 1.0 if (int(t * 2.5 + i * 0.7) % 2 == 0) else 0.15
            elif blink == "flicker":
                a = flicker(t, seed + i, 7, 0.4)
            elif blink == "data":
                a = 1.0 if math.sin(t * 17 + i * 3) > -0.2 else 0.2
            glow_spot(ctx, x, y, radius, col, 0.9 * a)
            ctx.arc(x, y, radius * 0.12, 0, 2 * math.pi)
            set_col(ctx, (255, 255, 255), 0.9 * a)
            ctx.fill()
    return plate_layer(fn, bbox)


def code_layer(rect, lines, chars, t, size=26, **kw):
    """Code editor text drawn into a plate-sized transparent layer."""
    x, y, w, h = rect
    im = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    O.draw_code(im, (0, 0, w, h), lines, chars, t, size=size, **kw)
    return Sprite(im, int(x), int(y))


def scope_in_plate(rect, t, kind="pwm", **kw):
    x, y, w, h = rect

    def fn(ctx):
        O.draw_scope(ctx, rect, t, kind, **kw)
    return plate_layer(fn, (x - 20, y - 20, x + w + 20, y + h + 20), glow_r=6, glow_s=0.9)


def text_in_plate(text, xy, key="mono", size=64, color=C.GREEN_DEEP, tracking=0):
    im = text_image(text, key, size, color, tracking)
    return Sprite(im, int(xy[0]), int(xy[1]))


def smoke_layer(x, y, t, seed=0, scale=1.0):
    """Soft rising solder smoke wisps."""
    r = rng(seed)

    def fn(ctx):
        for k in range(5):
            ph = r.uniform(0, 6)
            life = (t * 0.6 + k * 0.2) % 1.0
            yy = y - life * 380 * scale
            xx = x + math.sin(life * 5 + ph) * 40 * scale * life
            rad = (30 + life * 120) * scale
            radial_fill(ctx, xx, yy, 0, rad, [(0, (230, 230, 225), 0.18 * (1 - life)), (1, (230, 230, 225), 0)])
            ctx.arc(xx, yy, rad, 0, 2 * math.pi)
            ctx.fill()
    return plate_layer(fn, (x - 300 * scale, y - 560 * scale, x + 300 * scale, y + 60), blur_r=6)


def product_frame(prod_img, t, dur, bg_plate="studio_dark", scale0=0.9, scale1=0.98, cy=None,
                  sweep=True, cam=None, xoff=0, leds=None):
    """Composite a product PNG over a studio plate with a slow push and a light sweep."""
    plate = Plate.load(bg_plate)
    p = ease_in_out(progress(t, 0, dur))
    frame = plate.render(cam or Cam(1.02 + 0.05 * p))
    sc = scale0 + (scale1 - scale0) * p
    im = prod_img.resize((int(prod_img.width * sc), int(prod_img.height * sc)), Image.BICUBIC)
    x = C.W / 2 - im.width / 2 + xoff
    y = (cy or C.H / 2) - im.height / 2
    frame.alpha_composite(im, dest=(int(x), int(y)))
    if sweep:
        sp = progress(t, dur * 0.15, dur * 0.85)
        s, ctx = surface(im.width, im.height)
        bx = -im.width * 0.4 + sp * im.width * 1.8
        linear_fill(ctx, bx - 260, 0, bx + 260, im.height * 0.4,
                    [(0, (255, 255, 255), 0), (0.5, (255, 255, 255), 0.22), (1, (255, 255, 255), 0)])
        ctx.paint()
        light = to_pil(s)
        light.putalpha(Image.fromarray(
            ((__import__("numpy").asarray(light.getchannel("A"), "float32") / 255.0) *
             __import__("numpy").asarray(im.getchannel("A"), "float32")).astype("uint8"), "L"))
        frame.alpha_composite(light, dest=(int(x), int(y)))
    return frame, (x, y, sc)
