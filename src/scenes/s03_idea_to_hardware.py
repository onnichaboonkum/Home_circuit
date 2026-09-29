"""03_IDEA_TO_HARDWARE - IDEA > DESIGN > BUILD > CODE > TEST > REAL SOLUTION.

All stage plates share BOARD_RECT (plate space) so sketch -> schematic -> layout ->
physical PCB read as match cuts. Stages are linked by green trace wipes and a
pipeline bar whose trace grows from node to node.
"""
import math

import cairo

from .. import config as C
from ..engine.canvas import linear_fill, rounded_rect, set_col, surface, to_pil
from ..engine.overlays import draw_scope
from ..engine.pcb import draw_cad_layout, draw_schematic, node, poly_partial, stroke_poly
from ..engine.captions import Caption
from ..engine.scene import SFX, PlateShot, Scene, Overlay
from ..engine.text import text_image
from ..engine.util import clamp, ease_in_out, ease_out, progress, rng
from ..plates import (BOARD_RECT, CODE_RECT_FW, CX, CY, METER_RECT_TB, PROTO_LEDS, SCOPE_RECT_TB,
                      TERM_RECT_FW)
from .common import (Cam, badge, code_layer, glow_dot_layer, hud_corners, label, plate_layer,
                     scope_in_plate, smoke_layer, text_in_plate, trace_wipe)
from .s01_hook import solder_dyn

# ---- stage timing (scene-local seconds) - edit here
STAGES = [("IDEA", 0.0), ("DESIGN", 3.0), ("BUILD", 6.0), ("CODE", 9.0), ("TEST", 11.8), ("REAL SOLUTION", 14.6)]
DURATION = 19.2
SPLIT_DESIGN = 4.5   # schematic -> PCB layout
SPLIT_BUILD = 7.5    # bare PCB -> soldering

FW_CODE = [
    "// hc-firmware / main.c",
    "#include \"hc_board.h\"",
    "#include \"hc_relay.h\"",
    "",
    "#define PUMP_RELAY   DO1",
    "#define MOISTURE_IN  AIN0",
    "",
    "void app_main(void) {",
    "    hc_board_init();",
    "    hc_uart_log(\"HC-DEV boot OK\");",
    "",
    "    while (1) {",
    "        float m = hc_adc_read(MOISTURE_IN);",
    "        hc_relay_set(PUMP_RELAY, m < 35.0f);",
    "        hc_delay_ms(500);",
    "    }",
    "}",
]

# ------------------------------------------------------------------ sketch (pencil draw-on)
def _jitter_line(r, pts, amp=2.5, steps=14):
    out = []
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        for k in range(steps):
            f = k / steps
            out.append((x0 + (x1 - x0) * f + r.uniform(-amp, amp), y0 + (y1 - y0) * f + r.uniform(-amp, amp)))
    out.append(pts[-1])
    return out


def _sketch_strokes():
    r = rng(33)
    x, y, w, h = BOARD_RECT

    def R(u0, v0, u1, v1):
        return [(x + u0 * w, y + v0 * h), (x + u1 * w, y + v0 * h), (x + u1 * w, y + v1 * h), (x + u0 * w, y + v1 * h), (x + u0 * w, y + v0 * h)]

    def Ln(u0, v0, u1, v1):
        return [(x + u0 * w, y + v0 * h), (x + u1 * w, y + v1 * h)]

    strokes = [R(0.0, 0.0, 1.0, 1.0), R(0.08, 0.34, 0.28, 0.62), R(0.40, 0.26, 0.60, 0.70), R(0.72, 0.34, 0.92, 0.62),
               Ln(0.28, 0.48, 0.40, 0.48), Ln(0.37, 0.45, 0.40, 0.48), Ln(0.37, 0.51, 0.40, 0.48),
               Ln(0.60, 0.48, 0.72, 0.48), Ln(0.69, 0.45, 0.72, 0.48), Ln(0.69, 0.51, 0.72, 0.48),
               Ln(0.50, 0.70, 0.50, 0.86), R(0.43, 0.86, 0.57, 0.96)]
    js = [_jitter_line(r, s) for s in strokes]
    texts = [("SENSOR", 0.105, 0.50, 0.17), ("MCU", 0.465, 0.51, 0.3), ("RELAY", 0.755, 0.50, 0.47),
             ("12V", 0.455, 0.935, 0.62), ("IDEA: auto pump controller?", 0.0, -0.05, 0.05),
             ("log data -> cloud?", 0.63, 0.22, 0.8)]
    return js, texts


SKETCH_STROKES, SKETCH_TEXTS = _sketch_strokes()


def sketch_dyn(t, dur, plate, cam):
    p = ease_in_out(progress(t, 0.0, dur * 0.95))
    total = sum(len(s) for s in SKETCH_STROKES)
    x, y, w, h = BOARD_RECT
    head = None

    def fn(ctx):
        nonlocal head
        budget = p * total
        for s in SKETCH_STROKES:
            if budget <= 0:
                break
            n = min(len(s), int(budget) + 1)
            ctx.move_to(*s[0])
            for pt in s[1:n]:
                ctx.line_to(*pt)
            set_col(ctx, (58, 58, 64), 0.85)
            ctx.set_line_width(4.5)
            ctx.stroke()
            head = s[n - 1]
            budget -= len(s)
        ctx.select_font_face("Inter", cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
        for txt, u, v, t0 in SKETCH_TEXTS:
            if p > t0:
                ctx.set_font_size(40 if "IDEA" not in txt else 46)
                set_col(ctx, (50, 50, 58), 0.85 * clamp((p - t0) / 0.06))
                ctx.move_to(x + u * w + 10, y + v * h)
                ctx.show_text(txt)
        if head is not None and p < 0.999:
            hx, hy = head
            ctx.save()
            ctx.translate(hx, hy)
            ctx.rotate(-0.75)
            rounded_rect(ctx, 20, -16, 620, 32, 6)
            set_col(ctx, (40, 42, 44), 1)
            ctx.fill()
            ctx.rectangle(20, -16, 620, 7)
            set_col(ctx, C.GREEN_DIM, 1)
            ctx.fill()
            ctx.move_to(20, -16)
            ctx.line_to(-50, 0)
            ctx.line_to(20, 16)
            set_col(ctx, (220, 190, 150), 1)
            ctx.fill()
            ctx.move_to(-28, -6)
            ctx.line_to(-50, 0)
            ctx.line_to(-28, 6)
            set_col(ctx, (40, 40, 40), 1)
            ctx.fill()
            ctx.restore()
    return [(plate_layer(fn, (x - 80, y - 120, x + w + 900, y + h + 900)), 0.0)]


def schematic_dyn(t, dur, plate, cam):
    p = 0.2 + 0.8 * ease_out(progress(t, 0, dur * 0.95))
    return [(plate_layer(lambda ctx: draw_schematic(ctx, BOARD_RECT, p, t),
                         (BOARD_RECT[0] - 40, BOARD_RECT[1] - 40, BOARD_RECT[0] + BOARD_RECT[2] + 40, BOARD_RECT[1] + BOARD_RECT[3] + 40),
                         glow_r=4, glow_s=0.5), 0.0)]


def layout_dyn(t, dur, plate, cam):
    p = ease_in_out(progress(t, 0, dur * 0.95))
    x, y, w, h = BOARD_RECT
    return [(plate_layer(lambda ctx: draw_cad_layout(ctx, BOARD_RECT, p, t=t),
                         (x - 220, y - 140, x + w + 220, y + h + 140), glow_r=5, glow_s=0.6), 0.0)]


def pcb_dyn(t, dur, plate, cam):
    x, y, w, h = BOARD_RECT
    sp = progress(t, 0, dur)

    def fn(ctx):
        bx = x - 300 + sp * (w + 600)
        ctx.save()
        rounded_rect(ctx, x, y, w, h, 14)
        ctx.clip()
        linear_fill(ctx, bx - 220, y, bx + 220, y + h * 0.3, [(0, (255, 255, 255), 0), (0.5, (255, 255, 255), 0.16), (1, (255, 255, 255), 0)])
        ctx.paint()
        ctx.restore()
    return [(plate_layer(fn, (x, y, x + w, y + h)), 0.6)]


def firmware_dyn(t, dur, plate, cam):
    chars = int(40 + t * 190)
    x, y, w, h = TERM_RECT_FW
    p = progress(t, 1.2, dur - 0.3)
    term = ["$ make flash PORT=/dev/ttyUSB0", "Building hc-firmware ........ OK"]
    if p > 0:
        bar = int(p * 28)
        term.append("Flashing  [" + "#" * bar + "." * (28 - bar) + f"]  {int(p * 100):3d}%")
    if p >= 1:
        term.append("Verify OK  ·  HC-DEV running")
    return [(code_layer(CODE_RECT_FW, FW_CODE, chars, t, size=30, highlight_line=13 if chars > 400 else None), 0.5),
            (code_layer((x, y, w, h), term, 999 if t > 0.6 else int(t * 60), t, size=28, gutter=False, cursor=False), 0.5)]


def test_dyn(t, dur, plate, cam):
    x, y, w, h = METER_RECT_TB
    v = "3.30" if t > 0.5 else "0.00"
    return [(scope_in_plate(SCOPE_RECT_TB, t + 0.4, "pwm"), 0.5),
            (text_in_plate(v, (x + w * 0.1, y + h * 0.04), "mono", int(h * 0.66), (18, 30, 22)), 0.5)]


def proto_dyn(t, dur, plate, cam):
    pts = [(px, py, C.GREEN if i != 2 else (255, 170, 60)) for i, (px, py) in enumerate(PROTO_LEDS)]
    return [(glow_dot_layer(pts, t, radius=46, blink="data"), 0.5)]


# ------------------------------------------------------------------ pipeline bar
def pipeline_overlay():
    names = [s[0] for s in STAGES]
    starts = [s[1] for s in STAGES]
    x0, x1, y = 470, 1450, 86
    xs = [x0 + (x1 - x0) * i / (len(names) - 1) for i in range(len(names))]
    lbls = {(n, a): (text_image(n, "display_bold", 30, C.WHITE, 60) if a else text_image(n, "mono", 19, C.GREY, 80))
            for n in names for a in (0, 1)}

    def draw(frame, t, dur):
        k = min(1.0, t / 0.4, (dur - t) / 0.3)
        s, ctx = surface(C.W, 140)
        # base line
        ctx.move_to(x0, y)
        ctx.line_to(x1, y)
        set_col(ctx, C.WHITE, 0.18 * k)
        ctx.set_line_width(2)
        ctx.stroke()
        # progress trace
        idx = max(i for i, st in enumerate(starts) if t >= st)
        seg_p = ease_in_out(progress(t, starts[idx], starts[idx] + 0.6))
        xe = xs[idx - 1] + (xs[idx] - xs[idx - 1]) * seg_p if idx > 0 else xs[0]
        ctx.move_to(x0, y)
        ctx.line_to(xe, y)
        set_col(ctx, C.GREEN, k)
        ctx.set_line_width(3)
        ctx.stroke()
        for i, xx in enumerate(xs):
            active = i < idx or (i == idx and seg_p >= 1) or i == 0
            node(ctx, xx, y, 7 if i == idx else 5, C.GREEN if active else C.GREY, k)
        if seg_p < 1 and idx > 0:
            node(ctx, xe, y, 4, C.WHITE, k, ring=False)
        bar = to_pil(s)
        from ..engine.canvas import glow
        frame.alpha_composite(glow(bar, 6, 0.8), dest=(0, 0))
        for i, (n, xx) in enumerate(zip(names, xs)):
            im = lbls[(n, int(i == idx))]
            a = k * (1.0 if i <= idx else 0.55)
            if a < 0.999:
                im = im.copy()
                im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
            frame.alpha_composite(im, dest=(int(xx - im.width / 2), y + 16))
        return frame
    return Overlay(0.0, DURATION, draw, 30)


def top_band(t_in, t_out, h=260, a=0.55):
    s, ctx = surface(C.W, h)
    linear_fill(ctx, 0, 0, 0, h, [(0, (0, 0, 0), a), (1, (0, 0, 0), 0)])
    ctx.paint()
    band = to_pil(s)

    def draw(frame, t, dur):
        frame.alpha_composite(band)
        return frame
    return Overlay(t_in, t_out, draw, 4)


def build():
    st = dict(STAGES)
    shots = [
        PlateShot(st["DESIGN"] - st["IDEA"], "paper", Cam(1.02, 0, 0), Cam(1.1, 0, 10), dyn=sketch_dyn, grade="warm", name="idea_sketch"),
        PlateShot(SPLIT_DESIGN - st["DESIGN"], "cad_dark", Cam(1.1, 0, 0), Cam(1.1, 0, 0), dyn=schematic_dyn, grade="tech", name="schematic"),
        PlateShot(st["BUILD"] - SPLIT_DESIGN, "cad_dark", Cam(1.1, 0, 0), Cam(1.16, 0, 0), dyn=layout_dyn, grade="tech", name="pcb_layout"),
        PlateShot(SPLIT_BUILD - st["BUILD"], "build_pcb", Cam(1.16, 0, 0), Cam(1.3, 40, -20, 2.0), dyn=pcb_dyn, grade="neutral", name="physical_pcb"),
        PlateShot(st["CODE"] - SPLIT_BUILD, "hook_solder", Cam(1.05, 0, 0), Cam(1.16, 30, 10), dyn=solder_dyn, shake=0.6, seed=7, grade="warm", name="soldering"),
        PlateShot(st["TEST"] - st["CODE"], "code_firmware", Cam(1.08, -60, -130), Cam(1.16, -20, -100), dyn=firmware_dyn, grade="tech", name="firmware"),
        PlateShot(st["REAL SOLUTION"] - st["TEST"], "test_bench", Cam(1.12, -120, -40), Cam(1.2, -60, -30), dyn=test_dyn, shake=0.4, seed=9, grade="neutral", name="testing"),
        PlateShot(DURATION - st["REAL SOLUTION"], "prototype_working", Cam(1.0, 0, 0), Cam(1.1, 0, -20), dyn=proto_dyn, grade="neutral", name="working_prototype"),
    ]
    ov = [pipeline_overlay(), top_band(0.0, DURATION)]
    for i, (name, t0) in enumerate(STAGES):
        t1 = STAGES[i + 1][1] if i + 1 < len(STAGES) else DURATION
        if i > 0:
            ov.append(trace_wipe(t0, 0.5, seed=10 + i))
    ov.append(badge(st["BUILD"], DURATION))
    ov.append(hud_corners(st["REAL SOLUTION"] + 0.3, DURATION, "PROTO-02  ·  BENCH TEST", "● SYSTEM RUNNING"))
    st_t = [t0 for _, t0 in STAGES] + [DURATION]
    texts = [["เริ่มจากปัญหาที่เจอจริง"],
             ["ออกแบบวงจร และลายวงจร (PCB)"],
             ["ประกอบและบัดกรีบอร์ดต้นแบบ"],
             ["เขียนโปรแกรมควบคุม (Firmware)"],
             ["ทดสอบจนใช้งานได้จริง"],
             ["จากของที่ทำไว้ใช้เอง", "สู่งานพัฒนา Hardware และ Firmware"]]
    caps = [Caption(st_t[i] + 0.25, st_t[i + 1] - st_t[i] - 0.4, texts[i]) for i in range(len(texts))]
    sfx = [SFX(0.1, "pencil", -18)]
    for name, t0 in STAGES[1:]:
        sfx.append(SFX(t0 - 0.25, "whoosh_soft", -22))
        sfx.append(SFX(t0, "tick", -18))
    sfx += [SFX(SPLIT_BUILD, "solder_sizzle", -20), SFX(st["CODE"] + 0.2, "keyboard", -20),
            SFX(st["CODE"] + 2.4, "beep", -20), SFX(st["TEST"] + 0.5, "beep", -18),
            SFX(st["REAL SOLUTION"], "relay_click", -14), SFX(st["REAL SOLUTION"] + 0.1, "power_on", -18)]
    return Scene("03_IDEA_TO_HARDWARE", shots, ov, [], sfx, grade="neutral", captions=caps,
                 music_marks=[(t0, "accent") for _, t0 in STAGES[1:]])
