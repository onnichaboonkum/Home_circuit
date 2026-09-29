"""Real product: Arduino HcEee Gateway V1.0 (Home Circuit).

Source images supplied by the client live in ``assets/products/hceee/``.
They are shown as framed image cards with a slow Ken Burns move inside the
card (crop animation). Replace the *_source.jpg files with higher-resolution
versions to sharpen every product shot (crop rectangles are relative).
"""
from functools import lru_cache

from PIL import Image, ImageFilter

from .. import config as C
from .canvas import fast_blur, rounded_rect, set_col, surface, to_pil
from .util import ease_in_out, lerp

DIR = C.PRODUCTS / "hceee"
SOURCES = {
    "overview": "hceee_overview_source.jpg",        # product sheet (2 views, dimensions, feature icons)
    "block": "hceee_block_diagram_source.jpg",      # Base Board / Master Board / Plug-in module
    "application": "hceee_application_source.jpg",  # wiring / application example
}
# crops as fractions of the source image (x0, y0, x1, y1)
CROPS = {
    "views": ("overview", (40 / 900, 86 / 629, 622 / 900, 348 / 629)),
    "enclosed": ("overview", (42 / 900, 86 / 629, 318 / 900, 348 / 629)),
    "transparent": ("overview", (338 / 900, 86 / 629, 622 / 900, 348 / 629)),
    "dimensions": ("overview", (118 / 900, 388 / 629, 602 / 900, 578 / 629)),
    "sheet": ("overview", (0, 0, 1, 1)),
    "block": ("block", (0, 0, 1, 1)),
    "application": ("application", (0, 0, 1, 1)),
}

NAME = "Arduino HcEee Gateway V1.0"
SPECS = [
    ("MCU", "ESP32-WROOM-32U"),
    ("1×", "Ethernet W5500  ·  MQTT / HTTP / Modbus TCP"),
    ("2×", "RS-485   +   1× RS-232  ·  Modbus RTU"),
    ("4×", "Digital Input (Source) 12–24 VDC"),
    ("2×", "Open Collector Output (Relay / Alarm)"),
    ("1×", "RTC DS3231 ±2 ppm  ·  microSD (FAT32)"),
    ("1×", "External Watchdog  ·  I²C  ·  Buzzer"),
]


@lru_cache(maxsize=8)
def source(name):
    return Image.open(DIR / SOURCES[name]).convert("RGB")


@lru_cache(maxsize=16)
def crop(name):
    src_name, (a, b, c, d) = CROPS[name]
    im = source(src_name)
    return im.crop((int(a * im.width), int(b * im.height), int(c * im.width), int(d * im.height)))


@lru_cache(maxsize=32)
def _mask(w, h, r):
    s, ctx = surface(w, h)
    rounded_rect(ctx, 0, 0, w, h, r)
    set_col(ctx, (255, 255, 255), 1)
    ctx.fill()
    return to_pil(s).getchannel("A")


@lru_cache(maxsize=32)
def _shadow(w, h, r, pad=60):
    s, ctx = surface(w + pad * 2, h + pad * 2)
    rounded_rect(ctx, pad, pad + 14, w, h, r)
    set_col(ctx, (0, 0, 0), 0.75)
    ctx.fill()
    return fast_blur(to_pil(s), 26)


@lru_cache(maxsize=32)
def _border(w, h, r):
    s, ctx = surface(w, h)
    rounded_rect(ctx, 1, 1, w - 2, h - 2, r)
    set_col(ctx, (255, 255, 255), 0.22)
    ctx.set_line_width(2)
    ctx.stroke()
    return to_pil(s)


def card(frame, name, t, dur, center, width, zoom=(1.0, 1.12), focus=(0.5, 0.5), alpha=1.0, radius=18,
         rise=0.0, ease=ease_in_out):
    """Draw a product image card; the picture pushes in from ``zoom[0]`` to ``zoom[1]`` towards ``focus``."""
    img = crop(name)
    w = int(width)
    h = int(width * img.height / img.width)
    p = ease(min(1.0, max(0.0, t / dur))) if dur > 0 else 1.0
    z = lerp(zoom[0], zoom[1], p)
    sw, sh = img.width / z, img.height / z
    fx, fy = focus
    cx = min(max(img.width * fx, sw / 2), img.width - sw / 2)
    cy = min(max(img.height * fy, sh / 2), img.height - sh / 2)
    # blend centre from image centre (zoom 1) to focus
    k = (z - 1) / max(1e-6, (max(zoom) - 1)) if max(zoom) > 1 else 0
    cx = lerp(img.width / 2, cx, k)
    cy = lerp(img.height / 2, cy, k)
    box = (cx - sw / 2, cy - sh / 2, cx + sw / 2, cy + sh / 2)
    pic = img.resize((w, h), Image.LANCZOS, box=box).filter(ImageFilter.UnsharpMask(1.6, 70, 2))
    pic = pic.convert("RGBA")
    m = _mask(w, h, radius)
    if alpha < 0.999:
        m = m.point(lambda v: int(v * alpha))
    pic.putalpha(m)
    x = int(center[0] - w / 2)
    y = int(center[1] - h / 2 + rise)
    sh_img = _shadow(w, h, radius)
    if alpha < 0.999:
        sh_img = sh_img.copy()
        sh_img.putalpha(sh_img.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(sh_img, dest=(x - 60, y - 60))
    frame.alpha_composite(pic, dest=(x, y))
    bd = _border(w, h, radius)
    if alpha < 0.999:
        bd = bd.copy()
        bd.putalpha(bd.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(bd, dest=(x, y))
    return (x, y, w, h)
