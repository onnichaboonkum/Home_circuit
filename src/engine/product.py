"""Conceptual Home Circuit GW-01 gateway renders (DRAFT VISUAL, not a real product).

Written to assets/products/*.png (transparent) so they can be replaced by
real product renders / photos later without touching scene code.
"""
from PIL import Image

from .. import config as C
from . import props as P
from .canvas import fast_blur, glow_spot, linear_fill, radial_fill, rounded_rect, set_col, surface, to_pil
from .pcb import draw_board

FILES = {
    "gateway_3q": (1800, 1250),
    "gateway_front": (1700, 900),
    "gateway_pcb": (1600, 1000),
}


def gateway_3q(leds=(1, 1, 0, 1)):
    w, h = FILES["gateway_3q"]
    s, ctx = surface(w, h)
    P.gateway_3q(ctx, 180, 480, 1100, 520, 470, leds=leds)
    im = to_pil(s)
    # soft contact shadow + reflection
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    s2, c2 = surface(w, h)
    c2.save()
    c2.translate(820, 1020)
    c2.scale(820, 70)
    c2.arc(0, 0, 1, 0, 6.3)
    c2.restore()
    radial_fill(c2, 820, 1020, 0, 820, [(0, (0, 0, 0), 0.7), (1, (0, 0, 0), 0)])
    c2.fill()
    out.alpha_composite(fast_blur(to_pil(s2), 14))
    refl = im.transpose(Image.FLIP_TOP_BOTTOM).crop((0, h - 1000 - 30, w, h))
    refl.putalpha(refl.getchannel("A").point(lambda v: int(v * 0.10)))
    out.alpha_composite(refl.crop((0, 0, w, h - 1000)), dest=(0, 1000))
    out.alpha_composite(im)
    return out


def gateway_front(leds=(1, 1, 0, 1)):
    w, h = FILES["gateway_front"]
    s, ctx = surface(w, h)
    P.gateway_front(ctx, 50, 50, w - 100, h - 100, leds=leds)
    return to_pil(s)


def gateway_pcb():
    w, h = FILES["gateway_pcb"]
    s, ctx = surface(w, h)
    draw_board(ctx, 40, 40, w - 80, h - 80, seed=101, mask=(12, 14, 14), copper=(44, 52, 48), density=1.1,
               label="HOME CIRCUIT", sub="GW-01  REV 0.9  CONCEPT", ethernet=True, radius=20)
    return to_pil(s)


# feature positions in gateway_pcb.png space (for callouts)
PCB_FEATURES = {
    "MCU": (0.46, 0.48),
    "ETHERNET": (0.87, 0.42),
    "RS-485": (0.22, 0.30),
    "I/O TERMINALS": (0.30, 0.86),
    "USB / DEBUG": (0.03, 0.51),
    "STATUS LEDS": (0.80, 0.80),
}


def build_all(force=False):
    C.PRODUCTS.mkdir(parents=True, exist_ok=True)
    for name, fn in (("gateway_3q", gateway_3q), ("gateway_front", gateway_front), ("gateway_pcb", gateway_pcb)):
        p = C.PRODUCTS / f"{name}.png"
        if force or not p.exists():
            fn().save(p)
            print(f"  built  product {name}")


_cache = {}


def load(name):
    if name not in _cache:
        _cache[name] = Image.open(C.PRODUCTS / f"{name}.png").convert("RGBA")
    return _cache[name]
