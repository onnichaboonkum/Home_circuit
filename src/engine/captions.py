"""On-screen Thai story text (the video has no narration - viewers read the story).

Styles
  lower : main story line(s) in the lower third, green rule + soft dark band
  hero  : large centred statement (key emotional lines)
  top   : Thai translation under an English category label
  under : Thai line placed under an English headline at a given y
Timing guideline: keep each caption >= 1.2 s + (characters / 15) s on screen.
"""
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional

from PIL import Image

from .. import config as C
from .canvas import linear_fill, set_col, surface, to_pil, glow
from .text import text_image
from .util import clamp, ease_in, ease_out, ease_out_expo, progress

STYLES = {
    #        font key          size  color      line gap
    "lower": ("thai_semibold", 60, C.WHITE, 14),
    "hero": ("thai_semibold", 80, C.WHITE, 22),
    "top": ("thai_semibold", 44, (228, 232, 230), 8),
    "under": ("thai_semibold", 52, C.WHITE, 12),
}


@dataclass
class Caption:
    t: float                    # scene-local start
    dur: float
    lines: List[str]
    style: str = "lower"
    y: Optional[float] = None   # centre y override
    color: Optional[tuple] = None

    @property
    def t_out(self):
        return self.t + self.dur


@lru_cache(maxsize=4)
def _band(h=420, a=0.72):
    s, ctx = surface(C.W, h)
    linear_fill(ctx, 0, 0, 0, h, [(0, (0, 0, 0), 0), (0.45, (0, 0, 0), a * 0.7), (1, (0, 0, 0), a)])
    ctx.paint()
    return to_pil(s)


@lru_cache(maxsize=64)
def _panel(w, h, a=0.55):
    from .canvas import rounded_rect
    s, ctx = surface(w, h)
    rounded_rect(ctx, 0, 0, w, h, 18)
    set_col(ctx, (8, 10, 10), a)
    ctx.fill()
    return to_pil(s)


@lru_cache(maxsize=512)
def _shadow(key, size, text):
    from PIL import ImageFilter
    im = text_image(text, key, size, (0, 0, 0), 0)
    pad = 24
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    out.alpha_composite(im, dest=(pad, pad))
    return out.filter(ImageFilter.GaussianBlur(9))


def _a(img, a):
    if a >= 0.999:
        return img
    im = img.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return im


def draw_caption(frame, cap: Caption, t):
    """t = scene-local time."""
    if not (cap.t <= t <= cap.t_out):
        return frame
    lt = t - cap.t
    key, size, col, gap = STYLES[cap.style]
    col = cap.color or col
    a_in = clamp(lt / 0.25)
    a_out = 1 - ease_in(progress(lt, cap.dur - 0.3, cap.dur))
    imgs = [text_image(l, key, size, tuple(col), 0) for l in cap.lines]
    total_h = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
    if cap.style == "lower":
        frame.alpha_composite(_a(_band(), min(a_in, a_out)), dest=(0, C.H - 420))
        cy = cap.y or (C.H - 150 - total_h / 2)
        # soft backing panel so the text reads on any background
        pw = max(i.width for i in imgs) + 110
        ph = total_h + 60
        frame.alpha_composite(_a(_panel(int(pw), int(ph)), min(a_in, a_out)),
                              dest=(int(C.W / 2 - pw / 2), int(cy - ph / 2 + 4)))
        # green rule
        rw = int(90 * ease_out(progress(lt, 0.0, 0.5)))
        if rw > 2:
            s, ctx = surface(rw + 10, 10)
            set_col(ctx, C.GREEN, 1)
            ctx.rectangle(0, 3, rw, 4)
            ctx.fill()
            frame.alpha_composite(_a(glow(to_pil(s), 4, 0.6), a_out), dest=(int(C.W / 2 - rw / 2), int(cy - total_h / 2 - 48)))
    elif cap.style == "top":
        cy = cap.y or 238
    else:
        cy = cap.y or C.H / 2
    y = cy - total_h / 2
    for i, (line, im) in enumerate(zip(cap.lines, imgs)):
        p = progress(lt, i * 0.12, i * 0.12 + 0.55)
        e = ease_out_expo(p)
        dy = (1 - e) * 26
        a = clamp(p * 1.8) * a_out
        x = C.W / 2 - im.width / 2
        if a > 0.01:
            sh = _shadow(key, size, line)
            frame.alpha_composite(_a(sh, a * 0.85), dest=(int(x - 24), int(y + dy - 24 + 3)))
            frame.alpha_composite(_a(im, a), dest=(int(x), int(y + dy)))
        y += im.height + gap
    return frame


def reading_time(lines):
    return 1.2 + sum(len(l) for l in lines) / 15.0
