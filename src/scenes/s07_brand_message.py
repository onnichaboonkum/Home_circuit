"""07_BRAND_MESSAGE - emotional engineering montage; music dips on "แต่มันเริ่มจาก…",
returns on "เราจะแก้ปัญหานี้ได้อย่างไร" -> REAL PROBLEMS / ENGINEERING / SOLUTIONS."""
import math

from .. import config as C
from ..engine import props as P
from ..engine.pcb import draw_schematic
from ..engine.scene import VO, SFX, PlateShot, Scene
from ..engine.text import Line
from ..engine.util import ease_in_out, progress
from ..plates import BOARD_RECT, CX, GW_CAB_RECT
from .common import Cam, badge, dim, glow_dot_layer, plate_layer, title
from .s01_hook import code_dyn, solder_dyn
from .s03_idea_to_hardware import pcb_dyn, test_dyn
from .s04_projects import farm_dyn, gateway_dyn
from .s06_capabilities import class_dyn

# ---- shot table - edit here (the long 'thinker' shot carries the pause)
SHOTS = [("schematic", 1.1), ("pcb", 1.1), ("soldering", 1.1), ("programming", 1.2), ("thinker", 4.9),
         ("testing", 0.9), ("gateway", 0.9), ("drone", 0.9), ("farm", 0.9), ("students", 2.0)]
T = {}
_acc = 0.0
for _n, _d in SHOTS:
    T[_n] = _acc
    _acc += _d
DURATION = _acc
T_DIP = T["thinker"] + 0.1          # music drops out
T_BACK = T["testing"]                # music returns (hit)


def schematic_dyn(t, dur, plate, cam):
    x, y, w, h = BOARD_RECT
    return [(plate_layer(lambda ctx: draw_schematic(ctx, BOARD_RECT, 1.0, t), (x - 40, y - 40, x + w + 40, y + h + 40),
                         glow_r=4, glow_s=0.5), 0.0)]


def takeoff_dyn(t, dur, plate, cam):
    lift = ease_in_out(progress(t, 0.05, dur)) * 330
    cx, cy = CX, 1010 - lift

    def fn(ctx):
        P.drone_side(ctx, cx, cy, 520, prop_phase=t * 45)
    return [(plate_layer(fn, (cx - 520, cy - 250, cx + 520, cy + 250)), 0.8)]


def build():
    d = dict(SHOTS)
    shots = [
        PlateShot(d["schematic"], "cad_dark", Cam(1.4, 0, 0), Cam(1.55, 20, 0), dyn=schematic_dyn, grade="tech", name="schematic"),
        PlateShot(d["pcb"], "build_pcb", Cam(1.3, 0, 0, -2), Cam(1.45, 20, -10, 0), dyn=pcb_dyn, grade="neutral", name="pcb"),
        PlateShot(d["soldering"], "hook_solder", Cam(1.25, 20, 10), Cam(1.35, 40, 20), dyn=solder_dyn, shake=0.6, seed=4, grade="warm", name="soldering"),
        PlateShot(d["programming"], "hook_code", Cam(1.3, -100, -60), Cam(1.36, -60, -60), dyn=code_dyn, grade="tech", name="programming"),
        PlateShot(d["thinker"], "brand_thinker", Cam(1.0, 60, 0), Cam(1.16, 140, -30), grade="warm", name="engineer_thinking"),
        PlateShot(d["testing"], "test_bench", Cam(1.3, -200, -60), Cam(1.38, -180, -60), dyn=test_dyn, grade="neutral", name="hardware_testing", blur_in=0.08),
        PlateShot(d["gateway"], "proj_gateway_cabinet", Cam(1.5, 280, -340), Cam(1.6, 290, -340), dyn=gateway_dyn, grade="tech", name="gateway_operating"),
        PlateShot(d["drone"], "drone_sky", Cam(1.0, 0, 0), Cam(1.06, 0, -20), dyn=takeoff_dyn, grade="tech", name="drone_takeoff"),
        PlateShot(d["farm"], "proj_farm", Cam(1.5, 120, -140), Cam(1.6, 130, -150), dyn=farm_dyn, grade="warm", name="smart_farm_sensor"),
        PlateShot(d["students"], "classroom", Cam(1.05, 0, -150), Cam(1.12, 0, -170), dyn=class_dyn, grade="tech", name="students_coding"),
    ]
    t1, t2, t3 = T_BACK, T["drone"], T["students"]
    ov = [
        dim(t1, DURATION, amount=0.42, fade=0.15),
        title([Line("REAL PROBLEMS.", "display_black", 104, C.WHITE, -5)], t1 + 0.05, t2, anim="mask", center=(C.W / 2, 470), dur_in=0.5, dur_out=0.12),
        title([Line("REAL ENGINEERING.", "display_black", 104, C.WHITE, -5)], t2, t3, anim="mask", center=(C.W / 2, 470), dur_in=0.5, dur_out=0.12),
        title([Line("REAL SOLUTIONS.", "display_black", 104, C.GREEN, -5)], t3, DURATION, anim="mask", center=(C.W / 2, 470), dur_in=0.5, dur_out=0.0),
        badge(T["gateway"], T["students"]),
    ]
    vo = [
        VO("vo11", 0.3, "เพราะสำหรับ Home Circuit เทคโนโลยีไม่ได้เริ่มจากคำว่า “ขายอะไร”",
           [["เพราะสำหรับ Home Circuit", "เทคโนโลยีไม่ได้เริ่มจากคำว่า “ขายอะไร”"]],
           "เพราะสำหรับโฮมเซอร์กิต เทคโนโลยีไม่ได้เริ่มจากคำว่า ขายอะไร", max_dur=4.2),
        VO("vo12", T["thinker"] + 0.45, "แต่มันเริ่มจาก…", [["แต่มันเริ่มจาก…"]], "แต่มันเริ่มจาก", max_dur=1.4),
        VO("vo13", T["thinker"] + 2.4, "“เราจะแก้ปัญหานี้ได้อย่างไร”", [["“เราจะแก้ปัญหานี้ได้อย่างไร”"]],
           "เราจะแก้ปัญหานี้ได้อย่างไร", max_dur=2.2),
        VO("vo14", T_BACK + 0.2, "และเปลี่ยนคำตอบนั้น ให้กลายเป็น Hardware ที่ใช้งานได้จริง",
           [["และเปลี่ยนคำตอบนั้น", "ให้กลายเป็น Hardware ที่ใช้งานได้จริง"]],
           "และเปลี่ยนคำตอบนั้น ให้กลายเป็นฮาร์ดแวร์ที่ใช้งานได้จริง", max_dur=4.0),
    ]
    sfx = [SFX(T["soldering"], "solder_sizzle", -22), SFX(T["programming"], "keyboard", -20),
           SFX(T_DIP, "room_tone", -24), SFX(T_BACK, "low_impact", -8), SFX(T_BACK, "relay_click", -14),
           SFX(T["gateway"], "beep", -22), SFX(T["drone"], "drone", -16), SFX(T["farm"], "tick", -20),
           SFX(t2, "tick_hi", -16), SFX(t3, "tick_hi", -14)]
    return Scene("07_BRAND_MESSAGE", shots, ov, vo, sfx, grade="neutral",
                 music_marks=[(T_DIP, "dip"), (T_BACK - 0.8, "riser_short"), (T_BACK, "hit")],
                 flashes=[(T_BACK, 0.2, C.WHITE, 0.25)])
