"""01_HOOK - black, relay click, rapid macro montage, "IT STARTED FROM A HOME." (no logo)."""
import math

from PIL import Image

from .. import config as C
from ..engine import props as P
from ..engine.canvas import set_col, solid
from ..engine.pcb import qfp
from ..engine.captions import Caption
from ..engine.scene import SFX, FuncShot, PlateShot, Scene
from ..engine.util import ease_out, flicker, progress
from ..plates import CX, CY, SCOPE_RECT_HOOK
from .common import (Cam, Line, code_layer, glow_dot_layer, plate_layer, scope_in_plate,
                     smoke_layer, title)

# ---- shot durations (seconds) - edit here
D_BLACK = 0.5
D_MACRO = [0.8, 0.7, 0.8, 0.75, 0.85, 0.75]   # solder, components, code, scope, hands, drone
D_TITLE = 8.3 - D_BLACK - sum(D_MACRO)        # remainder -> typography card

HOOK_CODE = [
    "#include \"hc_io.h\"",
    "",
    "void setup() {",
    "  hc_gpio_init(RELAY_PIN, OUTPUT);",
    "  hc_adc_begin(AIN0, 12);",
    "}",
    "",
    "void loop() {",
    "  float v = hc_adc_read_volt(AIN0);",
    "  if (v > THRESHOLD) relay_on();",
    "}",
]


def solder_dyn(t, dur, plate, cam, tip=(CX + 40, CY + 22)):
    k = flicker(t, 1, 14, 0.35)
    return [(glow_dot_layer([(tip[0] + 6, tip[1] + 14, (255, 190, 110))], t, radius=90 * k), 0.8),
            (smoke_layer(tip[0], tip[1], t + 3.0, seed=2), 0.9)]


def code_dyn(t, dur, plate, cam):
    n = int(120 + t * 300)
    return [(code_layer((300, 110, 1900, 1100), HOOK_CODE, n, t, size=54, highlight_line=9), 0.0)]


def scope_dyn(t, dur, plate, cam):
    return [(scope_in_plate(SCOPE_RECT_HOOK, t + 1.2, "pwm", bg=False, grid=True, speed=1.4), 0.0)]


def hands_dyn(t, dur, plate, cam):
    p = ease_out(progress(t, 0, dur * 0.85))
    cy = CY - 20 - (1 - p) * 140

    def fn(ctx):
        qfp(ctx, CX - 10, cy, 300, 3)
        P.tweezers(ctx, CX + 1000, CY - 760, CX + 60, cy - 40, width=70, gap=30)
    return [(plate_layer(fn, (CX - 400, 0, CX + 1100, CY + 300)), 0.6)]


def drone_dyn(t, dur, plate, cam):
    # spinning motor highlight
    return [(glow_dot_layer([(CX - 520 + 840 * 0.75 + 34 * 0.4 * i, CY - 420 + 840 * 0.8, C.GREEN) for i in range(3)],
                            t, radius=26, blink="data"), 0.5)]


def black(t, dur):
    return solid(C.BLACK)


def build():
    shots = [FuncShot(D_BLACK, black, "black")]
    shots.append(PlateShot(D_MACRO[0], "hook_solder", Cam(1.18, 20, 10), Cam(1.3, 40, 18), dyn=solder_dyn, shake=0.6, seed=1, grade="warm"))
    shots.append(PlateShot(D_MACRO[1], "hook_components", Cam(1.2, -90, 0), Cam(1.26, 60, -10), shake=0.4, seed=2, grade="warm"))
    shots.append(PlateShot(D_MACRO[2], "hook_code", Cam(1.35, -120, -60), Cam(1.42, -40, -50), dyn=code_dyn, grade="tech"))
    shots.append(PlateShot(D_MACRO[3], "hook_scope", Cam(1.12, 0, 20), Cam(1.22, 30, 20), dyn=scope_dyn, grade="tech"))
    shots.append(PlateShot(D_MACRO[4], "hook_hands", Cam(1.15, 0, -30), Cam(1.25, 0, -10), dyn=hands_dyn, shake=0.8, seed=5, grade="warm"))
    shots.append(PlateShot(D_MACRO[5], "hook_drone", Cam(1.5, 120, 60, -1.5), Cam(1.7, 160, 60, 1.0), dyn=drone_dyn, grade="tech"))
    shots.append(PlateShot(D_TITLE, "dark_grid_warm", Cam(1.0), Cam(1.08), name="title_card"))
    t_title = D_BLACK + sum(D_MACRO)
    ov = [title([Line("IT STARTED", "display_black", 124, C.WHITE, -5),
                 Line("FROM A HOME.", "display_black", 124, C.WHITE, -5)],
                t_title + 0.15, 8.3, anim="mask", dur_in=0.8, dur_out=0.0, center=(C.W / 2, 450))]
    caps = [Caption(0.6, t_title - 0.65, ["เทคโนโลยีหลายชิ้นของเรา", "ไม่ได้เริ่มต้นจากโรงงานใหญ่"]),
            Caption(t_title + 0.55, 8.3 - t_title - 0.55, ["แต่มันเริ่มจาก “บ้านหลังหนึ่ง”"], style="under", y=700)]
    cuts = [D_BLACK + sum(D_MACRO[:i]) for i in range(len(D_MACRO))]
    sfx = [SFX(0.2, "relay_click", -6)]
    sfx += [SFX(cuts[0], "solder_sizzle", -20), SFX(cuts[2], "keyboard", -18), SFX(cuts[3], "beep", -22),
            SFX(cuts[5], "servo", -22), SFX(t_title, "low_impact", -10)]
    for c in cuts:
        sfx.append(SFX(c, "tick", -24))
    return Scene("01_HOOK", shots, ov, [], sfx, grade="neutral", captions=caps,
                 music_marks=[(t_title, "hit_soft")], flashes=[(t_title, 0.25, C.WARM, 0.25)])
