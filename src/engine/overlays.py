"""Screen-space overlays & in-picture animated screens.

* draft_badge      - "DRAFT VISUAL" label for conceptual products/projects
* category_label   - project / capability label (green rule + tracked caps)
* callout          - engineering callout with leader line
* draw_scope       - oscilloscope graticule + live waveform (cairo)
* draw_code        - code editor with typing animation (PIL, mono font)
* draw_meter       - multimeter 7-seg style readout
"""
import math

from PIL import Image, ImageDraw

from .. import config as C
from .canvas import glow, set_col, surface, to_pil, rounded_rect
from .text import font, text_image
from .util import clamp, ease_out, ease_out_expo, progress


# ------------------------------------------------------------------ labels
def draft_badge(frame, alpha=1.0, corner="tr"):
    if alpha <= 0.01:
        return frame
    txt = text_image(C.DRAFT_LABEL, "mono", 20, C.WHITE, 120)
    pad_x, pad_y = 16, 8
    w, h = txt.width + pad_x * 2 + 18, txt.height + pad_y * 2 - 6
    s, ctx = surface(w, h)
    rounded_rect(ctx, 1, 1, w - 2, h - 2, 4)
    set_col(ctx, C.BLACK, 0.55)
    ctx.fill_preserve()
    set_col(ctx, C.WHITE, 0.55)
    ctx.set_line_width(1.2)
    ctx.stroke()
    ctx.arc(pad_x + 3, h / 2, 4, 0, 2 * math.pi)
    set_col(ctx, C.GREEN, 1)
    ctx.fill()
    badge = to_pil(s)
    badge.alpha_composite(txt, dest=(pad_x + 16, pad_y - 5))
    x = C.W - w - 56 if corner == "tr" else 56
    y = 48
    if alpha < 1:
        badge.putalpha(badge.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(badge, dest=(x, y))
    return frame


def category_label(frame, text, t, dur, index=None, total=None, y=150, size=64,
                   sub=None, align="center", x=None, fade_out=0.25):
    """Tracked caps label with a drawing green rule. Centred in the 9:16-safe column."""
    p = progress(t, 0, 0.55)
    a_out = 1 - progress(t, dur - fade_out, dur) if fade_out else 1
    e = ease_out_expo(p)
    img = text_image(text, "display_bold", size, C.WHITE, 40)
    cx = C.W / 2 if x is None else x
    tx = cx - img.width / 2 if align == "center" else cx
    # soft shadow for legibility on bright plates, then mask reveal
    dy = (1 - e) * img.height
    if img.height - dy > 1:
        crop = img.crop((0, 0, img.width, int(img.height - dy)))
        _paste_a(frame, _shadow(crop), (tx - 20, y + dy - 20 + 3), a_out * 0.7)
        _paste_a(frame, crop, (tx, y + dy), a_out)
    # rule
    rw = int(min(img.width, 420) * ease_out(progress(t, 0.1, 0.7)))
    if rw > 2:
        s, ctx = surface(rw + 12, 12)
        set_col(ctx, C.GREEN, 1)
        ctx.rectangle(0, 4, rw, 3)
        ctx.fill()
        ctx.arc(rw + 2, 5.5, 4, 0, 2 * math.pi)
        ctx.fill()
        rule = glow(to_pil(s), 5, 0.8)
        rx = cx - rw / 2 if align == "center" else cx
        _paste_a(frame, rule, (rx, y - 18), a_out)
    if index is not None:
        idx = text_image(f"{index:02d} / {total:02d}", "mono", 22, C.GREEN, 80)
        ix = cx - idx.width / 2 if align == "center" else cx
        _paste_a(frame, idx, (ix, y - 58), a_out * clamp(p * 2))
    if sub:
        sb = text_image(sub, "mono", 22, C.LIGHT_GREY, 60)
        sx = cx - sb.width / 2 if align == "center" else cx
        _paste_a(frame, sb, (sx, y + img.height + 10), a_out * clamp(progress(t, 0.25, 0.7)))
    return frame


def _shadow(img, r=10):
    from PIL import Image as _I, ImageFilter
    sh = _I.new("RGBA", (img.width + 40, img.height + 40), (0, 0, 0, 0))
    blk = _I.new("RGBA", img.size, (0, 0, 0, 255))
    blk.putalpha(img.getchannel("A"))
    sh.alpha_composite(blk, dest=(20, 20))
    return sh.filter(ImageFilter.GaussianBlur(r))


def callout(frame, text, target, label_pos, t, t0=0.0, col=C.GREEN, size=22, alpha=1.0):
    """Engineering callout: dot at target, leader line, mono label."""
    p = progress(t, t0, t0 + 0.6)
    if p <= 0:
        return frame
    e = ease_out(p)
    tx, ty = target
    lx, ly = label_pos
    s, ctx = surface(C.W, C.H)
    ctx.arc(tx, ty, 7, 0, 2 * math.pi)
    set_col(ctx, col, alpha)
    ctx.set_line_width(2)
    ctx.stroke()
    ctx.arc(tx, ty, 2.5, 0, 2 * math.pi)
    ctx.fill()
    mx, my = lx, ty + (ly - ty) * 1.0
    ex = tx + (mx - tx) * e
    ey = ty + (my - ty) * e
    ctx.move_to(tx, ty)
    ctx.line_to(ex, ey)
    ctx.set_line_width(1.6)
    ctx.stroke()
    frame.alpha_composite(to_pil(s))
    if p > 0.6:
        img = text_image(text, "mono", size, C.WHITE, 60)
        a = clamp((p - 0.6) / 0.4) * alpha
        dx = 12 if lx >= tx else -img.width - 12
        _paste_a(frame, img, (lx + dx, ly - img.height / 2 - 2), a)
    return frame


def _paste_a(frame, img, xy, a):
    if a <= 0.01:
        return
    if a < 0.999:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    x, y = int(xy[0]), int(xy[1])
    if x >= frame.width or y >= frame.height:
        return
    frame.alpha_composite(img, dest=(max(0, x), max(0, y)),
                          source=(max(0, -x), max(0, -y)))


# ------------------------------------------------------------------ oscilloscope
def draw_scope(ctx, rect, t, kind="pwm", col=C.GREEN, amp=1.0, grid=True, bg=True, speed=1.0):
    x, y, w, h = rect
    if bg:
        set_col(ctx, (6, 12, 9), 1)
        ctx.rectangle(x, y, w, h)
        ctx.fill()
    if grid:
        set_col(ctx, (120, 140, 130), 0.22)
        ctx.set_line_width(1)
        for i in range(1, 10):
            gx = x + w * i / 10
            ctx.move_to(gx, y)
            ctx.line_to(gx, y + h)
        for j in range(1, 8):
            gy = y + h * j / 8
            ctx.move_to(x, gy)
            ctx.line_to(x + w, gy)
        ctx.stroke()
        set_col(ctx, (140, 160, 150), 0.35)
        ctx.move_to(x + w / 2, y)
        ctx.line_to(x + w / 2, y + h)
        ctx.move_to(x, y + h / 2)
        ctx.line_to(x + w, y + h / 2)
        ctx.stroke()
    n = int(w / 2)
    ctx.move_to(x, y + h / 2)
    for i in range(n + 1):
        u = i / n
        ph = u * 4 * math.pi * 2 - t * 6 * speed
        if kind == "pwm":
            duty = 0.35 + 0.2 * math.sin(t * 1.3)
            v = 0.6 if (ph / (2 * math.pi)) % 1 < duty else -0.6
            v += 0.05 * math.sin(ph * 23)
        elif kind == "sine":
            v = 0.7 * math.sin(ph) + 0.05 * math.sin(ph * 7 + t)
        elif kind == "data":
            bit = int((u * 32 + t * 12 * speed)) * 2654435761 % 7 > 3
            v = 0.55 if bit else -0.55
        else:  # "ecg"-like sensor burst
            v = 0.6 * math.exp(-((ph % (2 * math.pi)) - 1) ** 2 * 6) * math.sin(ph * 9)
        ctx.line_to(x + u * w, y + h / 2 - v * h * 0.4 * amp)
    set_col(ctx, col, 1)
    ctx.set_line_width(2.2)
    ctx.stroke()


def scope_layer(size, rect, t, kind="pwm", glow_r=8, **kw):
    """Plate-space RGBA layer with a glowing scope trace inside rect."""
    s, ctx = surface(*size)
    draw_scope(ctx, rect, t, kind, **kw)
    return glow(to_pil(s), glow_r, 1.0)


# ------------------------------------------------------------------ code editor
SYNTAX = {
    "kw": (86, 214, 140), "fn": (240, 240, 236), "num": (230, 190, 110),
    "str": (160, 200, 170), "com": (110, 118, 120), "txt": (200, 206, 204),
}
KEYWORDS = {"void", "int", "uint8_t", "uint16_t", "float", "return", "if", "else", "while", "for",
            "const", "static", "bool", "true", "false", "#include", "#define", "def", "import",
            "from", "async", "await", "class", "self", "None", "struct"}


def _tokens(line):
    out, word = [], ""
    stripped = line.lstrip()
    if stripped.startswith("//") or stripped.startswith("#") and not stripped.startswith(("#include", "#define")):
        return [(line, "com")]
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            j = line.find('"', i + 1)
            j = len(line) - 1 if j < 0 else j
            if word:
                out.append((word, "kw" if word in KEYWORDS else "txt"))
                word = ""
            out.append((line[i:j + 1], "str"))
            i = j + 1
            continue
        if ch.isalnum() or ch in "_#.":
            word += ch
        else:
            if word:
                kind = "kw" if word in KEYWORDS else "num" if word.replace(".", "").replace("x", "").isdigit() else "txt"
                out.append((word, kind))
                word = ""
            out.append((ch, "fn" if ch == "(" else "txt"))
        i += 1
    if word:
        out.append((word, "kw" if word in KEYWORDS else "txt"))
    return out


def draw_code(img, rect, lines, chars, t=0.0, size=26, line_h=None, cursor=True, gutter=True,
              highlight_line=None, alpha=255):
    """Draw code into PIL image ``img`` inside rect with the first ``chars`` characters visible."""
    x, y, w, h = rect
    d = ImageDraw.Draw(img)
    f = font("mono", size)
    lh = line_h or int(size * 1.5)
    shown = 0
    cur = None
    for li, line in enumerate(lines):
        ly = y + li * lh
        if ly + lh > y + h:
            break
        if gutter:
            d.text((x, ly), f"{li + 1:>3}", font=f, fill=(80, 88, 88, alpha))
        cx = x + (int(size * 2.6) if gutter else 0)
        if highlight_line == li:
            d.rectangle((x, ly - 2, x + w, ly + lh - 4), fill=(46, 214, 115, 28))
        remaining = chars - shown
        if remaining <= 0:
            break
        visible = line[:max(0, remaining)]
        shown += len(line) + 1
        for tok, kind in _tokens(visible):
            d.text((cx, ly), tok, font=f, fill=SYNTAX[kind] + (alpha,))
            cx += f.getlength(tok)
        cur = (cx, ly)
        if remaining <= len(line):
            break
    if cursor and cur and (int(t * 2.2) % 2 == 0):
        d.rectangle((cur[0] + 2, cur[1] + 2, cur[0] + size * 0.55, cur[1] + size * 1.2), fill=C.GREEN + (alpha,))
    return img


def total_chars(lines):
    return sum(len(l) + 1 for l in lines)


# ------------------------------------------------------------------ meter
def draw_meter_text(img, xy, value, size=64, col=(20, 26, 22)):
    d = ImageDraw.Draw(img)
    d.text(xy, value, font=font("mono", size), fill=col + (255,))
    return img
