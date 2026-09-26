"""Low-level raster helpers.

* cairo is used for anti-aliased vector drawing (plates, traces, logo, UI).
* PIL / numpy are used for compositing, blur, grading and grain.
"""
import math
from functools import lru_cache

import cairo
import numpy as np
from PIL import Image, ImageFilter

from .. import config as C


# ------------------------------------------------------------------ cairo bridge
def surface(w, h):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(w), int(h))
    ctx = cairo.Context(s)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    return s, ctx


def to_pil(s):
    """cairo ARGB32 (premultiplied BGRA) -> PIL RGBA (straight alpha)."""
    s.flush()
    w, h = s.get_width(), s.get_height()
    buf = np.frombuffer(s.get_data(), np.uint8).reshape(h, s.get_stride() // 4, 4)[:, :w]
    b, g, r, a = [buf[..., i].astype(np.float32) for i in range(4)]
    alpha = np.maximum(a, 1) / 255.0
    rgba = np.stack([np.clip(r / alpha, 0, 255), np.clip(g / alpha, 0, 255),
                     np.clip(b / alpha, 0, 255), a], -1).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def rgb(c, a=1.0):
    """Palette tuple (0-255) -> cairo floats."""
    return (c[0] / 255.0, c[1] / 255.0, c[2] / 255.0, a)


def set_col(ctx, c, a=1.0):
    ctx.set_source_rgba(*rgb(c, a))


def rounded_rect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def linear_fill(ctx, x0, y0, x1, y1, stops):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for off, col, a in stops:
        g.add_color_stop_rgba(off, *rgb(col, a)[:3], a)
    ctx.set_source(g)


def radial_fill(ctx, cx, cy, r0, r1, stops):
    g = cairo.RadialGradient(cx, cy, r0, cx, cy, r1)
    for off, col, a in stops:
        g.add_color_stop_rgba(off, *rgb(col, a)[:3], a)
    ctx.set_source(g)


def glow_spot(ctx, cx, cy, r, col, a=1.0):
    ctx.new_path()
    radial_fill(ctx, cx, cy, 0, r, [(0, col, a), (0.35, col, a * 0.35), (1, col, 0)])
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.fill()


# ------------------------------------------------------------------ PIL helpers
def blank(w=C.W, h=C.H, color=(0, 0, 0, 0)):
    return Image.new("RGBA", (int(w), int(h)), color)


def solid(color, w=C.W, h=C.H):
    return Image.new("RGBA", (int(w), int(h)), tuple(color) + (255,))


def blur(img, radius):
    return img.filter(ImageFilter.GaussianBlur(radius)) if radius > 0.3 else img


def fast_blur(img, radius):
    """Cheap wide blur: downscale, blur, upscale."""
    if radius < 4:
        return blur(img, radius)
    f = max(2, int(radius // 3))
    small = img.resize((max(1, img.width // f), max(1, img.height // f)), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(radius / f))
    return small.resize(img.size, Image.BILINEAR)


def with_alpha(img, a):
    if a >= 0.999:
        return img
    img = img.copy()
    al = img.getchannel("A").point(lambda v: int(v * max(0.0, a)))
    img.putalpha(al)
    return img


def paste(dst, src, xy, alpha=1.0):
    """Alpha-composite ``src`` onto ``dst`` at integer ``xy`` (clips safely)."""
    if alpha <= 0.003:
        return dst
    src = with_alpha(src, alpha)
    x, y = int(round(xy[0])), int(round(xy[1]))
    dst.alpha_composite(src, dest=(max(0, x), max(0, y)),
                        source=(max(0, -x), max(0, -y)))
    return dst


def add_light(dst, light, amount=1.0):
    """Additive blend (screen-like) of an RGBA light layer onto an RGB(A) frame."""
    if amount <= 0.003:
        return dst
    a = np.asarray(dst.convert("RGB"), np.float32)
    l = np.asarray(light, np.float32)
    lum = l[..., :3] * (l[..., 3:4] / 255.0) * amount
    out = 255 - (255 - a) * (255 - lum) / 255.0
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def glow(img, radius=18, strength=1.0):
    """Return ``img`` with a soft bloom of itself added (for LEDs, traces)."""
    halo = fast_blur(img, radius)
    base = img.copy()
    base.alpha_composite(with_alpha(halo, min(1.0, strength)))
    if strength > 1:
        base.alpha_composite(with_alpha(halo, strength - 1))
    return base


def fit_cover(img, w, h):
    s = max(w / img.width, h / img.height)
    im = img.resize((int(img.width * s + 0.5), int(img.height * s + 0.5)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


# ------------------------------------------------------------------ finishing
@lru_cache(maxsize=4)
def _vignette(w, h, amount):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = (x - w / 2) / (w / 2), (y - h / 2) / (h / 2)
    d = np.sqrt(nx * nx * 0.8 + ny * ny)
    v = 1.0 - amount * np.clip((d - 0.45) / 0.9, 0, 1) ** 1.6
    g = (v * 255).astype(np.uint8)
    return Image.fromarray(np.stack([g, g, g], -1), "RGB")


@lru_cache(maxsize=2)
def _grain_bank(w, h, amp):
    r = np.random.default_rng(7)
    out = []
    for _ in range(8):
        n = r.normal(0, 1, (h // 2, w // 2)).astype(np.float32) * amp
        n = np.repeat(np.repeat(n, 2, 0), 2, 1)[:h, :w]
        g = np.clip(128 + n, 0, 255).astype(np.uint8)
        out.append(Image.fromarray(np.stack([g, g, g], -1), "RGB"))
    return out


GRADES = {
    # name: (shadow tint, highlight tint, saturation)
    "neutral": ((0, 0, 0), (0, 0, 0), 1.0),
    "warm": ((6, 2, -4), (10, 2, -10), 1.05),
    "tech": ((-2, 2, 3), (-4, 2, 2), 0.95),
    "cool": ((-3, 0, 5), (-6, 0, 6), 0.9),
}


@lru_cache(maxsize=16)
def _grade_lut(grade, exposure):
    sh, hi, _ = GRADES.get(grade, GRADES["neutral"])
    lut = []
    for c in range(3):
        for v in range(256):
            k = v / 255.0
            o = v * exposure + (1 - k) * sh[c] + k * hi[c]
            lut.append(int(max(0, min(255, round(o)))))
    return lut


def finish(frame, frame_index=0, grade="neutral", grain=None, vignette=None, exposure=1.0):
    """Final per-frame look: grade, vignette, grain. Returns RGB uint8 ndarray."""
    from PIL import ImageChops, ImageEnhance
    grain = C.GRAIN_AMOUNT if grain is None else grain
    vignette = C.VIGNETTE_AMOUNT if vignette is None else vignette
    im = frame.convert("RGB")
    if grade != "neutral" or exposure != 1.0:
        im = im.point(_grade_lut(grade, round(exposure, 3)))
        sat = GRADES.get(grade, GRADES["neutral"])[2]
        if sat != 1.0:
            im = ImageEnhance.Color(im).enhance(sat)
    if vignette > 0:
        im = ImageChops.multiply(im, _vignette(im.width, im.height, round(vignette, 3)))
    if grain > 0:
        bank = _grain_bank(im.width, im.height, round(grain, 2))
        im = ImageChops.add(im, bank[(frame_index // 2) % len(bank)], 1.0, -128)
    return np.asarray(im)


def motion_blur(img, dx, dy, samples=7):
    """Directional blur used for whip/push transitions."""
    if abs(dx) + abs(dy) < 1:
        return img
    a = np.asarray(img.convert("RGB"), np.float32)
    acc = np.zeros_like(a)
    for i in range(samples):
        f = (i / (samples - 1) - 0.5)
        acc += np.roll(np.roll(a, int(dx * f), 1), int(dy * f), 0)
    return Image.fromarray((acc / samples).astype(np.uint8), "RGB").convert("RGBA")
