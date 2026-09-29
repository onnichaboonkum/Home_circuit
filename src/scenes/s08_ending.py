"""08_ENDING - official Home Circuit logo (assets/logo/hc_logo_*.png), service line,
call to action, power-down.

The supplied logo is designed for a light background (black "HOME" / "STEM LAB"),
so the end card switches to a clean light background and shows it unmodified.
"""
from functools import lru_cache

from PIL import Image

from .. import config as C
from ..engine.canvas import glow_spot, surface, to_pil
from ..engine.captions import Caption
from ..engine.pcb import circuit_backdrop
from ..engine.scene import SFX, FuncShot, Scene
from ..engine.text import Line, draw_lines, text_image
from ..engine.util import clamp, ease_in_out, ease_out, ease_out_expo, progress

DURATION = 7.6
T_LIGHT = 0.35             # black -> light end card
T_MARK = (0.3, 1.1)        # mark rises in
T_WORD = (0.95, 1.7)       # HOME CIRCUIT wipes in
T_SUB = (1.55, 2.2)        # STEM LAB
T_TAGS = 2.3
T_CTA = 3.9                # logo moves up, CTA appears
T_OFF = 6.9                # power-down

PAPER = (246, 247, 245)
INK = (24, 26, 28)
BRAND_GREEN = (32, 176, 72)        # darker end of the logo gradient (reads on light bg)
TAGS = "HARDWARE  •  IoT  •  GATEWAY  •  ROBOTICS"


@lru_cache(maxsize=1)
def _parts():
    return {n: Image.open(C.LOGO_DIR / f"hc_logo_{n}.png").convert("RGBA") for n in ("mark", "word", "sub")}


@lru_cache(maxsize=1)
def _background():
    bg = circuit_backdrop(C.W, C.H, seed=23, col=(200, 206, 202), alpha=0.22, grid=False, bg=PAPER)
    return bg


def _alpha(img, a):
    if a >= 0.999:
        return img
    im = img.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return im


def _scaled(img, s):
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)


def _lockup(t):
    """Compose mark + wordmark + STEM LAB with their reveal animations. Returns RGBA."""
    P = _parts()
    mark_h = 330
    ks = mark_h / P["mark"].height
    word = _scaled(P["word"], 900 / P["word"].width)
    sub = _scaled(P["sub"], word.width * (P["sub"].width / P["word"].width) / P["sub"].width)
    mark = _scaled(P["mark"], ks)
    gap1, gap2 = 70, 42
    W_ = max(mark.width, word.width) + 20
    H_ = mark.height + gap1 + word.height + gap2 + sub.height + 40
    out = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    # mark: rise + fade + slight scale
    pm = ease_out_expo(progress(t, *T_MARK))
    if pm > 0:
        m = _scaled(mark, 0.9 + 0.1 * pm)
        out.alpha_composite(_alpha(m, clamp(pm * 1.4)),
                            dest=(int(W_ / 2 - m.width / 2), int(mark.height - m.height + (1 - pm) * 40)))
    # wordmark: left-to-right wipe
    pw = ease_out(progress(t, *T_WORD))
    if pw > 0:
        cw = max(1, int(word.width * pw))
        out.alpha_composite(word.crop((0, 0, cw, word.height)), dest=(int(W_ / 2 - word.width / 2), mark.height + gap1))
    # STEM LAB: fade
    ps = ease_out(progress(t, *T_SUB))
    if ps > 0:
        out.alpha_composite(_alpha(sub, ps), dest=(int(W_ / 2 - sub.width / 2),
                                                   int(mark.height + gap1 + word.height + gap2 + (1 - ps) * 12)))
    return out


def ending(t, dur):
    frame = _background().copy()
    # logo lock-up, later scaled down and moved up for the call to action
    mv = ease_in_out(progress(t, T_CTA, T_CTA + 0.7))
    lock = _lockup(t)
    sc = 1.0 - 0.52 * mv
    lk = _scaled(lock, sc) if sc < 0.999 else lock
    cy = 500 - 250 * mv
    frame.alpha_composite(lk, dest=(int(C.W / 2 - lk.width / 2), int(cy - lk.height / 2)))
    # service line
    ta = ease_out(progress(t, T_TAGS, T_TAGS + 0.6)) * (1 - progress(t, T_CTA, T_CTA + 0.3))
    if ta > 0:
        tags = text_image(TAGS, "mono", 30, BRAND_GREEN, 120)
        frame.alpha_composite(_alpha(tags, ta), dest=(int(C.W / 2 - tags.width / 2), int(cy + lock.height / 2 + 30)))
    # call to action
    draw_lines(frame, [Line("HAVE AN IDEA?", "display_bold", 84, INK, 0),
                       Line("LET’S BUILD IT.", "display_black", 120, BRAND_GREEN, -5)],
               t, T_CTA + 0.45, dur + 1, anim="mask", center=(C.W / 2, 650), dur_in=0.8, stagger=0.35, dur_out=0)
    # footer
    fa = ease_out(progress(t, 0.8, 1.6))
    foot = text_image("CONCEPT VISUALIZATION", "mono", 20, (130, 136, 134), 200)
    frame.alpha_composite(_alpha(foot, fa), dest=(int(C.W / 2 - foot.width / 2), C.H - 70))
    # lights on: fade up from black at the start
    if t < T_LIGHT:
        k = 1 - ease_out(t / T_LIGHT)
        frame.alpha_composite(Image.new("RGBA", frame.size, (0, 0, 0, int(255 * k))))
    # power-down: fade to black, a last green node, then nothing
    if t >= T_OFF:
        k = progress(t, T_OFF, T_OFF + 0.45)
        frame.alpha_composite(Image.new("RGBA", frame.size, (0, 0, 0, int(255 * min(1.0, ease_in_out(k))))))
        if int((t - T_OFF) * 30) in (1, 3):
            frame.alpha_composite(Image.new("RGBA", frame.size, (0, 0, 0, 110)))
        dot = 1 - progress(t, T_OFF + 0.35, dur - 0.05)
        if dot > 0:
            s, ctx = surface(C.W, C.H)
            glow_spot(ctx, C.W / 2, C.H / 2, 40 * dot + 4, C.GREEN, dot)
            frame.alpha_composite(to_pil(s))
    return frame


def build():
    shots = [FuncShot(DURATION, ending, "logo_and_cta", grade="neutral")]
    sfx = [SFX(0.05, "power_on", -16), SFX(0.3, "shimmer", -18), SFX(T_WORD[0], "whoosh_soft", -24),
           SFX(T_SUB[0], "tick_hi", -20), SFX(T_TAGS, "beep", -26),
           SFX(T_CTA + 0.45, "whoosh_soft", -20), SFX(T_CTA + 0.8, "low_impact", -14),
           SFX(T_OFF, "power_down", -10), SFX(T_OFF + 0.5, "relay_click", -8)]
    caps = [Caption(T_CTA + 0.9, T_OFF - T_CTA - 0.9, ["มีไอเดีย? มาสร้างมันด้วยกัน"], style="under", y=850,
                    color=(52, 56, 58), shadow=False)]
    return Scene("08_ENDING", shots, [], [], sfx, grade="neutral", grain=2.0, vignette=0.12, captions=caps,
                 music_marks=[(0.0, "resolve"), (T_OFF, "end")])
