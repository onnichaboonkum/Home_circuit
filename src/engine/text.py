"""Typography: clean engineering-style titles with restrained animation.

Animations available: ``mask`` (mask reveal, lines rise from a baseline),
``track`` (letter-spacing settle), ``fade``, ``scale`` (gentle 1.05 -> 1.0),
``slam`` (hard cut on the beat with a tiny settle) and ``type`` (typewriter).
"""
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .. import config as C
from .util import clamp, ease_out, ease_out_expo, ease_in, progress


@lru_cache(maxsize=256)
def font(key, size):
    return ImageFont.truetype(str(C.FONT_FILES[key]), int(size),
                              layout_engine=ImageFont.Layout.RAQM)


def _is_thai(s):
    return any("฀" <= ch <= "๿" for ch in s)


@lru_cache(maxsize=1024)
def text_image(text, key="display_bold", size=96, color=C.WHITE, tracking=0.0, alpha=255):
    """Render one line of text to a tight RGBA image. ``tracking`` is in em/1000."""
    f = font(key, size)
    asc, desc = f.getmetrics()
    h = asc + desc
    col = tuple(color[:3]) + (alpha,)
    if tracking == 0 or _is_thai(text):
        w = int(f.getlength(text)) + 4
        im = Image.new("RGBA", (max(1, w), h + 8), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((2, 4), text, font=f, fill=col)
        return im
    sp = tracking / 1000.0 * size
    widths = [f.getlength(ch) for ch in text]
    w = int(sum(widths) + sp * (len(text) - 1)) + 6
    im = Image.new("RGBA", (max(1, w), h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 3.0
    for ch, cw in zip(text, widths):
        d.text((x, 4), ch, font=f, fill=col)
        x += cw + sp
    return im


class Line:
    """One styled line of a title block."""

    def __init__(self, text, key="display_bold", size=110, color=C.WHITE, tracking=-10, gap=None):
        self.text, self.key, self.size = text, key, size
        self.color, self.tracking = color, tracking
        self.gap = gap if gap is not None else int(size * 0.12)

    def image(self, extra_tracking=0.0, alpha=255):
        tr = round(self.tracking + extra_tracking, 0)
        return text_image(self.text, self.key, self.size, tuple(self.color), tr, alpha)


def draw_lines(frame, lines, t, t_in, t_out, anim="mask", center=(C.W / 2, C.H / 2),
               align="center", stagger=0.09, dur_in=0.7, dur_out=0.35, out_anim="fade"):
    """Draw a block of Lines onto ``frame`` at local time ``t``."""
    if t < t_in or t > t_out:
        return frame
    imgs = [ln.image() for ln in lines]
    total_h = sum(im.height for im in imgs) + sum(ln.gap for ln in lines[:-1])
    y = center[1] - total_h / 2
    p_out = progress(t, t_out - dur_out, t_out) if dur_out > 0 else 0.0
    for i, (ln, im) in enumerate(zip(lines, imgs)):
        p = progress(t, t_in + i * stagger, t_in + i * stagger + dur_in)
        alpha_out = 1.0 - ease_in(p_out) if out_anim == "fade" else 1.0
        dx = dy = 0.0
        a = 1.0
        img = im
        if anim == "mask":
            e = ease_out_expo(p)
            dy = (1 - e) * im.height * 0.95
            visible_h = im.height
            crop = img.crop((0, 0, img.width, max(1, int(visible_h - dy)))) if dy > 0 else img
            x = _x(center[0], img.width, align)
            if crop.height > 1:
                frame.alpha_composite(_alpha(crop, alpha_out), dest=(int(x), int(y + dy)))
            y += im.height + ln.gap
            continue
        if anim == "track":
            e = ease_out(p)
            img = ln.image(extra_tracking=(1 - e) * 260)
            a = clamp(p * 1.6)
        elif anim == "fade":
            a = ease_out(p)
        elif anim == "scale":
            e = ease_out(p)
            s = 1.05 - 0.05 * e
            img = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
            dy = (im.height - img.height) / 2
            a = e
        elif anim == "slam":
            e = ease_out_expo(clamp(p * 2.5))
            s = 1.12 - 0.12 * e
            img = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
            dy = (im.height - img.height) / 2
            a = 1.0 if p > 0 else 0
        elif anim == "slide":
            e = ease_out_expo(p)
            dx = (1 - e) * -60
            a = ease_out(p)
        elif anim == "type":
            n = int(len(ln.text) * p + 0.999)
            if n <= 0:
                y += im.height + ln.gap
                continue
            sub = Line(ln.text[:n], ln.key, ln.size, ln.color, ln.tracking)
            img = sub.image()
            x = _x(center[0], im.width, align)
            frame.alpha_composite(_alpha(img, alpha_out), dest=(int(x), int(y)))
            y += im.height + ln.gap
            continue
        if out_anim == "up" and p_out > 0:
            dy -= ease_in(p_out) * 30
            alpha_out = 1 - p_out
        x = _x(center[0], img.width, align) + dx
        a *= alpha_out
        if a > 0.003:
            frame.alpha_composite(_alpha(img, a), dest=(int(x), int(y + dy)))
        y += im.height + ln.gap
    return frame


def _x(cx, w, align):
    if align == "left":
        return cx
    if align == "right":
        return cx - w
    return cx - w / 2


def _alpha(img, a):
    if a >= 0.999:
        return img
    img = img.copy()
    img.putalpha(img.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return img


def measure(lines):
    imgs = [ln.image() for ln in lines]
    return max(im.width for im in imgs), sum(im.height for im in imgs) + sum(l.gap for l in lines[:-1])
