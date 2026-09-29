"""Logo helpers. The ending now uses the OFFICIAL logo (assets/logo/hc_logo_*.png,
cut from hc_logo_source.jpg by scripts/extract_logo.py). The procedural
TEMPORARY Home Circuit logo concept below is kept only for reference:: house geometry drawn as a PCB trace,
with a green circuit 'trident' growing from the door.  Replace
``assets/logo/hc_logo_mark.png`` / ``hc_logo_full.png`` with the real logo later
(the ending scene uses the PNGs when ``USE_LOGO_PNG`` is True).
"""
import math

from PIL import Image

from .. import config as C
from .canvas import glow, set_col, surface, to_pil
from .pcb import node, poly_partial, stroke_poly
from .text import text_image
from .util import clamp, ease_in_out, ease_out

USE_LOGO_PNG = False  # set True to use a replaced logo file instead of the procedural mark

HOUSE = [(-0.12, 0.45), (-0.42, 0.45), (-0.42, -0.08), (0.0, -0.46), (0.42, -0.08), (0.42, 0.45), (0.12, 0.45)]
TRUNK = [(0.0, 0.66), (0.0, 0.16)]
BRANCHES = [[(0.0, 0.16), (-0.19, -0.03)], [(0.0, 0.16), (0.19, -0.03)], [(0.0, 0.16), (0.0, -0.13)]]


def draw_mark(size, p=1.0, stroke=0.062, white=C.WHITE, green=C.GREEN):
    """Return RGBA image (size x size*1.25) of the mark at draw-progress p (0..1)."""
    w, h = int(size * 1.1), int(size * 1.3)
    s, ctx = surface(w, h)
    ox, oy = w / 2, h * 0.44

    def pts(lst):
        return [(ox + x * size, oy + y * size) for x, y in lst]

    lw = stroke * size
    ph = clamp(p / 0.6)
    sub, _ = poly_partial(pts(HOUSE), ease_in_out(ph))
    stroke_poly(ctx, sub, lw, white, 1)
    pt = clamp((p - 0.35) / 0.3)
    if pt > 0:
        sub, head = poly_partial(pts(TRUNK), ease_out(pt))
        stroke_poly(ctx, sub, lw * 0.8, green, 1)
        node(ctx, *pts(TRUNK)[0], lw * 0.75, green, 1)
    pb = clamp((p - 0.6) / 0.3)
    if pb > 0:
        for br in BRANCHES:
            sub, head = poly_partial(pts(br), ease_out(pb))
            stroke_poly(ctx, sub, lw * 0.8, green, 1)
            if pb >= 1:
                node(ctx, *pts(br)[-1], lw * 0.9, green, 1)
    pn = clamp((p - 0.9) / 0.1)
    if pn > 0:
        node(ctx, *pts(HOUSE)[3], lw * 0.0 + 0.001, white, 0)
    return to_pil(s)


def wordmark(size=96, tracking=160, color=C.WHITE):
    return text_image("HOME CIRCUIT", "display_bold", size, color, tracking)


def full_logo(mark_size=260, word_size=92, p=1.0, word_alpha=1.0):
    mark = draw_mark(mark_size, p)
    word = wordmark(word_size)
    W_ = max(mark.width, word.width) + 40
    H_ = mark.height + word.height + 40
    out = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    out.alpha_composite(mark, dest=((W_ - mark.width) // 2, 0))
    if word_alpha > 0:
        wd = word.copy()
        wd.putalpha(wd.getchannel("A").point(lambda v: int(v * word_alpha)))
        out.alpha_composite(wd, dest=((W_ - word.width) // 2, mark.height + 20))
    return out


def load_mark(size):
    f = C.LOGO_DIR / "hc_logo_mark.png"
    im = Image.open(f).convert("RGBA")
    k = size * 1.3 / im.height
    return im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)


def build_logo_files(force=False):
    """The official logo lives in assets/logo/hc_logo_source.jpg; cut its transparent parts."""
    C.LOGO_DIR.mkdir(parents=True, exist_ok=True)
    src = C.LOGO_DIR / "hc_logo_source.jpg"
    needed = [C.LOGO_DIR / f"hc_logo_{n}.png" for n in ("official", "mark", "word", "sub")]
    if src.exists() and (force or not all(p.exists() for p in needed)):
        from scripts.extract_logo import main as extract
        extract()
        print("  built  official logo parts")
