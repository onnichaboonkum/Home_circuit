"""08_ENDING - temporary logo concept, service line, call to action, power-down."""
import math

from PIL import Image

from .. import config as C
from ..engine import logo
from ..engine.camera import Plate
from ..engine.canvas import glow, glow_spot, solid, surface, to_pil
from ..engine.scene import SFX, FuncShot, Scene
from ..engine.text import Line, draw_lines, text_image
from ..engine.util import clamp, ease_in_out, ease_out, progress
from .common import Cam

DURATION = 7.0
T_LOGO = (0.25, 1.75)      # mark draw-on
T_WORD = 1.25
T_TAGS = 2.2
T_CTA = 3.7                 # logo moves up, CTA appears
T_OFF = 6.3                 # power-down

TAGS = "HARDWARE  •  IoT  •  GATEWAY  •  ROBOTICS"


def _alpha(img, a):
    if a >= 0.999:
        return img
    im = img.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return im


def ending(t, dur):
    frame = Plate.load("dark_grid").render(Cam(1.0 + 0.03 * t / dur))
    frame.alpha_composite(Image.new("RGBA", frame.size, (0, 0, 0, 120)))
    # logo mark (temporary concept)
    p = progress(t, *T_LOGO)
    mv = ease_in_out(progress(t, T_CTA, T_CTA + 0.7))
    size = 230 - 90 * mv
    if logo.USE_LOGO_PNG:
        mark = logo.load_mark(size)
    else:
        mark = logo.draw_mark(size, p)
    cy = 430 - 210 * mv
    frame.alpha_composite(glow(mark, 10, 0.5), dest=(int(C.W / 2 - mark.width / 2), int(cy - mark.height * 0.44)))
    # wordmark
    wa = ease_out(progress(t, T_WORD, T_WORD + 0.8))
    tr = 160 + (1 - wa) * 240
    word = logo.wordmark(int(84 - 30 * mv), tracking=round(tr))
    wy = cy + size * 0.95 + 10
    if wa > 0:
        frame.alpha_composite(_alpha(word, wa), dest=(int(C.W / 2 - word.width / 2), int(wy)))
    # tags
    ta = ease_out(progress(t, T_TAGS, T_TAGS + 0.6)) * (1 - progress(t, T_CTA, T_CTA + 0.35))
    if ta > 0:
        tags = text_image(TAGS, "mono", 28, C.GREEN, 120)
        frame.alpha_composite(_alpha(tags, ta), dest=(int(C.W / 2 - tags.width / 2), int(wy + 130)))
    # call to action
    draw_lines(frame, [Line("HAVE AN IDEA?", "display_bold", 88, C.WHITE, 0),
                       Line("LET’S BUILD IT.", "display_black", 124, C.GREEN, -5)],
               t, T_CTA + 0.35, dur + 1, anim="mask", center=(C.W / 2, 640), dur_in=0.8, stagger=0.35, dur_out=0)
    # footer
    fa = ease_out(progress(t, 0.6, 1.4))
    foot = text_image("CONCEPT VISUALIZATION", "mono", 20, C.GREY, 200)
    frame.alpha_composite(_alpha(foot, fa * 0.9), dest=(int(C.W / 2 - foot.width / 2), C.H - 70))
    # power-down: brief flicker, collapse to a single green node, then black
    if t >= T_OFF:
        k = progress(t, T_OFF, T_OFF + 0.45)
        flick = 0.55 if int((t - T_OFF) * 30) in (1, 3) else 1.0
        black = Image.new("RGBA", frame.size, (0, 0, 0, int(255 * min(1.0, ease_in_out(k) * 1.02) if k < 1 else 255)))
        frame.alpha_composite(black)
        if flick < 1:
            frame.alpha_composite(Image.new("RGBA", frame.size, (0, 0, 0, 110)))
        s, ctx = surface(C.W, C.H)
        dot = 1 - progress(t, T_OFF + 0.35, dur - 0.05)
        if dot > 0:
            glow_spot(ctx, C.W / 2, C.H / 2, 40 * dot + 4, C.GREEN, dot)
        frame.alpha_composite(to_pil(s))
    return frame


def build():
    shots = [FuncShot(DURATION, ending, "logo_and_cta", grade="neutral")]
    sfx = [SFX(0.25, "shimmer", -18), SFX(T_WORD, "tick_hi", -18), SFX(T_TAGS, "beep", -26),
           SFX(T_CTA + 0.35, "whoosh_soft", -20), SFX(T_CTA + 0.7, "low_impact", -14),
           SFX(T_OFF, "power_down", -10), SFX(T_OFF + 0.5, "relay_click", -8)]
    return Scene("08_ENDING", shots, [], [], sfx, grade="neutral", grain=3.0,
                 music_marks=[(0.0, "resolve"), (T_OFF, "end")])
