"""06_CAPABILITIES - WHAT CAN HOME CIRCUIT BUILD? fast montage (hard cuts on the beat)."""
import math

from .. import config as C
from ..engine import product
from ..engine import props as P
from ..engine.camera import Plate
from ..engine.canvas import glow_spot, surface, to_pil
from ..engine.pcb import TraceAnim, random_traces, route
from ..engine.scene import VO, SFX, FuncShot, PlateShot, Scene
from ..engine.text import Line, draw_lines
from ..engine.util import progress, rng
from ..plates import CLASS_SCREEN, CX, CY
from .common import Cam, badge, code_layer, hud_corners, label, plate_layer, product_frame
from .s01_hook import HOOK_CODE, code_dyn as hook_code_dyn
from .s03_idea_to_hardware import FW_CODE, pcb_dyn
from .s04_projects import farm_dyn, iot_dyn

HEADLINE = 3.0
ITEM = 2.0            # one bar at 120 BPM
LAST_ITEM = 3.0
ITEMS = ["IoT SOLUTIONS", "GATEWAY", "SMART FARM", "DRONE / UAV", "HARDWARE DEVELOPMENT",
         "FIRMWARE DEVELOPMENT", "CODING TRAINING"]
STARTS = [HEADLINE + i * ITEM for i in range(len(ITEMS))]
DURATION = STARTS[-1] + LAST_ITEM


def _converge():
    r = rng(61)
    items = []
    for i in range(16):
        side = i % 4
        if side == 0:
            a = (-50, r.uniform(80, C.H - 80))
        elif side == 1:
            a = (C.W + 50, r.uniform(80, C.H - 80))
        elif side == 2:
            a = (r.uniform(80, C.W - 80), -50)
        else:
            a = (r.uniform(80, C.W - 80), C.H + 50)
        b = (C.W / 2 + r.uniform(-420, 420), C.H / 2 + r.uniform(-230, 230))
        items.append({"pts": route(a[0], a[1], b[0], b[1], r.uniform(0.3, 0.7)), "t0": r.uniform(0, 1.2),
                      "dur": r.uniform(0.9, 1.5), "width": 2, "alpha": 0.7})
    return TraceAnim(items, glow_radius=7, glow_strength=1.0)


_CONV = _converge()


def headline(t, dur):
    frame = Plate.load("dark_grid").render(Cam(1.12 - 0.08 * t / dur))
    img = _CONV.render(t)
    if img is not None:
        frame.alpha_composite(img)
    draw_lines(frame, [Line("WHAT CAN", "display_black", 112, C.WHITE, -5),
                       Line("HOME CIRCUIT BUILD?", "display_black", 112, C.GREEN, -5)],
               t, 0.25, dur + 1, anim="mask", center=(C.W / 2, C.H / 2), dur_in=0.8, dur_out=0)
    return frame


def gateway_item(t, dur):
    frame, (x, y, sc) = product_frame(product.load("gateway_front"), t, dur, scale0=0.78, scale1=0.86, cy=C.H / 2 + 60)
    s, ctx = surface(C.W, C.H)
    u = (1700 - 100) / 100
    for i in (0, 1, 3):
        lx, ly = 50 + (8 + 9 * i) * u, 50 + (900 - 100) * 0.72
        a = 1.0 if i != 3 else (1.0 if math.sin(t * 19) > -0.2 else 0.25)
        glow_spot(ctx, x + lx * sc, y + ly * sc, 70 * sc, C.GREEN, 0.9 * a)
    frame.alpha_composite(to_pil(s))
    return frame


def drone_hover_dyn(t, dur, plate, cam):
    cx, cy = CX, 640 + math.sin(t * 2.2) * 14

    def fn(ctx):
        P.drone_side(ctx, cx, cy, 700, prop_phase=t * 40)
    return [(plate_layer(fn, (cx - 700, cy - 300, cx + 700, cy + 300)), 0.8)]


def class_dyn(t, dur, plate, cam):
    x, y, w, h = CLASS_SCREEN
    return [(code_layer((x + 40, y + 30, w - 60, h - 40), HOOK_CODE, int(80 + t * 160), t, size=34), 0.0)]


def fw_dyn(t, dur, plate, cam):
    return [(code_layer((300, 330, 1900, 900), FW_CODE[7:], int(40 + t * 260), t, size=50, highlight_line=6), 0.0)]


def build():
    shots = [FuncShot(HEADLINE, headline, "headline", grade="tech")]
    specs = [
        PlateShot(ITEM, "proj_iot", Cam(1.3, -200, -60), Cam(1.42, -180, -70), dyn=iot_dyn, grade="tech", blur_in=0.12),
        FuncShot(ITEM, gateway_item, "gateway", grade="tech"),
        PlateShot(ITEM, "proj_farm", Cam(1.45, 120, -120), Cam(1.58, 140, -140), dyn=farm_dyn, grade="warm", blur_in=0.12),
        PlateShot(ITEM, "drone_sky", Cam(1.05, 0, 40), Cam(1.14, 0, 20), dyn=drone_hover_dyn, grade="tech", blur_in=0.12),
        PlateShot(ITEM, "build_pcb", Cam(1.7, -40, -20, -3), Cam(1.9, 0, -30, 0), dyn=pcb_dyn, grade="tech", blur_in=0.12),
        PlateShot(ITEM, "hook_code", Cam(1.25, -80, -40), Cam(1.35, -40, -40), dyn=fw_dyn, grade="tech", blur_in=0.12),
        PlateShot(LAST_ITEM, "classroom", Cam(1.05, 0, -150), Cam(1.12, 0, -170), dyn=class_dyn, shake=0.4, seed=33, grade="tech", blur_in=0.12),
    ]
    for sp, name in zip(specs, ITEMS):
        sp.name = name.lower().replace(" / ", "_").replace(" ", "_")
    shots += specs
    ov = [badge(HEADLINE, DURATION)]
    for i, (name, t0) in enumerate(zip(ITEMS, STARTS)):
        t1 = STARTS[i + 1] if i + 1 < len(STARTS) else DURATION
        ov.append(label(name, t0 + 0.02, t1, index=i + 1, total=len(ITEMS), y=136, size=66))
    ov.append(hud_corners(HEADLINE, DURATION, "HOME CIRCUIT  ·  CAPABILITIES", "CONCEPT VISUALIZATION"))
    sfx = [SFX(0.25, "whoosh", -16), SFX(0.3, "low_impact", -14)]
    for t0 in STARTS:
        sfx += [SFX(t0 - 0.14, "whoosh", -20), SFX(t0, "tick_hi", -15)]
    sfx += [SFX(STARTS[3] + 0.1, "drone", -18), SFX(STARTS[4] + 0.2, "solder_sizzle", -24), SFX(STARTS[5], "keyboard", -22)]
    return Scene("06_CAPABILITIES", shots, ov, [], sfx, grade="tech",
                 music_marks=[(0.0, "peak_start")] + [(t0, "accent") for t0 in STARTS])
