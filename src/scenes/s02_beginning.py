"""02_BEGINNING - small Thai home workshop in the evening; NEED IT? -> BUILD IT."""
import math

from .. import config as C
from ..engine.pcb import TraceAnim, route
from ..engine.captions import Caption
from ..engine.scene import SFX, PlateShot, Scene, Overlay
from ..engine.util import flicker
from ..plates import ENCLOSURE_LED, LAPTOP_RECT_WS, MULTIMETER_DISPLAY_TABLE, SCOPE_RECT_WS
from .common import (Cam, Line, code_layer, glow_dot_layer, scope_in_plate, text_in_plate, title,
                     trace_wipe)

# ---- shot durations - edit here
D = {
    "exterior": 3.7,
    "wide": 4.6,
    "table": 3.0,
    "scope": 2.4,
    "need_it": 2.0,
    "build_it": 2.5,
}
T_BUILD = sum(list(D.values())[:5])   # BUILD IT lands exactly here (music hit)

WS_CODE = ["void loop() {", "  read_sensors();", "  update_relay();", "  log_serial();", "}"]


def table_dyn(t, dur, plate, cam):
    x, y, w, h = MULTIMETER_DISPLAY_TABLE
    v = "3.29" if int(t * 3) % 3 else "3.30"
    return [(text_in_plate(v, (x + w * 0.12, y + h * 0.05), "mono", int(h * 0.72), (20, 30, 24)), 0.5)]


def scope_dyn(t, dur, plate, cam):
    return [(scope_in_plate(SCOPE_RECT_WS, t, "sine"), 0.5),
            (code_layer(LAPTOP_RECT_WS, WS_CODE, 999, t, size=22, cursor=False), 0.5)]


def enclosure_dyn_off(t, dur, plate, cam):
    return None


def enclosure_dyn_on(t, dur, plate, cam):
    x, y = ENCLOSURE_LED
    k = flicker(t, 3, 5, 0.12)
    return [(glow_dot_layer([(x, y, C.GREEN)], t, radius=120 * k), 0.5)]


def wide_dyn(t, dur, plate, cam):
    # warm lamp breathing
    return None


def build_it_traces():
    """Green traces bursting out from the LED position (screen space, centred)."""
    cx, cy = 888, 634   # LED position on screen in the BUILD IT framing
    items = []
    for i, (dx, dy) in enumerate([(-1, -0.4), (1, -0.4), (-1, 0.3), (1, 0.3), (-1, 0.0), (1, 0.0)]):
        ex = cx + dx * (700 + i * 30)
        ey = cy + dy * 500
        items.append({"pts": route(cx + dx * 40, cy, ex, ey, 0.4), "t0": 0.02 * i, "dur": 0.55, "width": 3})
    return TraceAnim(items, glow_radius=10, glow_strength=1.4)


def build():
    t = 0.0
    shots = [
        PlateShot(D["exterior"], "home_exterior", Cam(1.0, 0, -30), Cam(1.14, 0, 40), grade="warm"),
        PlateShot(D["wide"], "workshop_wide", Cam(1.08, -90, 0), Cam(1.12, 70, -10), shake=0.6, seed=3, grade="warm"),
        PlateShot(D["table"], "workshop_table", Cam(1.12, -40, 20, 0), Cam(1.2, 40, 0, 1.4), dyn=table_dyn, grade="warm"),
        PlateShot(D["scope"], "workshop_scope", Cam(1.05, -60, 0), Cam(1.14, -120, -10), dyn=scope_dyn, shake=0.5, seed=4, grade="warm"),
        PlateShot(D["need_it"], "workshop_enclosure", Cam(1.0, 0, 0), Cam(1.06, 0, 10), dyn=enclosure_dyn_off, grade="warm"),
        PlateShot(D["build_it"], "workshop_enclosure", Cam(1.22, 180, 20), Cam(1.28, 190, 24), dyn=enclosure_dyn_on, grade="warm"),
    ]
    t_need = T_BUILD - D["need_it"]
    anim = build_it_traces()

    def burst(frame, tt, dur):
        img = anim.render(tt, alpha=max(0.0, 1 - max(0.0, tt - 1.2) / 1.0))
        if img is not None:
            frame.alpha_composite(img)
        return frame

    ov = [
        title([Line("NEED IT?", "display_bold", 118, C.WHITE, 0)], t_need + 0.25, T_BUILD - 0.02,
              anim="track", dur_in=0.9, dur_out=0.0, center=(C.W / 2, 250)),
        Overlay(T_BUILD, T_BUILD + 2.5, burst, 8),
        title([Line("BUILD IT.", "display_black", 150, C.WHITE, -10)], T_BUILD, T_BUILD + D["build_it"],
              anim="slam", dur_in=0.35, dur_out=0.0, center=(C.W / 2, 250)),
    ]
    caps = [
        Caption(0.3, 3.35, ["Home Circuit เริ่มต้นที่บ้านหลังเล็ก ๆ"]),
        Caption(3.85, 4.35, ["กลุ่มวิศวกรไฟฟ้าและเมคคาทรอนิกส์", "ที่เคยทำงานในบริษัทมาก่อน"]),
        Caption(8.4, 2.8, ["และทุกคนคิดเหมือนกันว่า…"]),
        Caption(11.4, T_BUILD - 11.45, ["“ถ้าอุปกรณ์ที่ต้องการยังไม่มี", "ทำไมไม่สร้างเองล่ะ?”"]),
        Caption(T_BUILD + 0.4, D["build_it"] - 0.4, ["ก็สร้างขึ้นมาเองเลย"]),
    ]
    sfx = [SFX(0.0, "room_tone", -26), SFX(3.7, "solder_sizzle", -26), SFX(6.2, "keyboard", -24),
           SFX(8.6, "beep", -26), SFX(t_need + 0.25, "whoosh_soft", -22),
           SFX(T_BUILD, "relay_click", -10), SFX(T_BUILD, "low_impact", -6), SFX(T_BUILD + 0.05, "power_on", -16)]
    return Scene("02_BEGINNING", shots, ov, [], sfx, grade="warm", captions=caps,
                 music_marks=[(T_BUILD - 1.5, "riser_short"), (T_BUILD, "hit")],
                 flashes=[(T_BUILD, 0.3, C.GREEN, 0.35)])
