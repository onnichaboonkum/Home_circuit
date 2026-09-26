"""05_PHILOSOPHY - conceptual HC GW-01 gateway (DRAFT VISUAL), open hardware for
developers: BUILD. MODIFY. DEVELOP. -> HARDWARE MADE FOR DEVELOPERS."""
import math

from PIL import Image

from .. import config as C
from ..engine import overlays as O
from ..engine import product
from ..engine.camera import Plate, Sprite
from ..engine.canvas import glow, glow_spot, linear_fill, set_col, surface, to_pil
from ..engine.pcb import TraceAnim, node, rj45
from ..engine.scene import VO, SFX, FuncShot, PlateShot, Scene, Overlay
from ..engine.text import Line, draw_lines
from ..engine.util import clamp, ease_in_out, ease_out, progress
from ..plates import CODE_RECT_FW, CX, DEV_GW, DEV_LAPTOP, PH, TERM_RECT_FW
from .common import Cam, badge, code_layer, glow_dot_layer, hud_corners, plate_layer, product_frame, title

# ---- shot table - edit here
SHOTS = [("hero", 4.0), ("pcb", 3.0), ("connect", 3.0), ("code", 2.8), ("words", 3.2), ("tagline", 3.0)]
T = {}
_acc = 0.0
for _n, _d in SHOTS:
    T[_n] = _acc
    _acc += _d
DURATION = _acc

# LED positions inside assets/products/gateway_3q.png (front panel x=180,y=480,w=1100,h=520)
_U = 1100 / 100
GW3Q_LEDS = [(180 + (8 + 9 * i) * _U, 480 + 520 * 0.72) for i in range(4)]

SDK_CODE = [
    "# custom logic on HC GW-01  (concept SDK)",
    "import hcgw",
    "",
    "gw = hcgw.Gateway(\"192.168.1.10\")",
    "",
    "@gw.on_input(\"DI1\")",
    "def pump_control(state):",
    "    level = gw.read(\"AI0\")",
    "    if state and level < 30.0:",
    "        gw.relay(\"DO1\", on=True)",
    "        gw.mqtt.publish(\"farm/pump\", \"ON\")",
    "",
    "gw.run()",
]

TERMINAL = [
    "$ ssh dev@hc-gw01.local",
    "HC GW-01  ·  developer mode (concept)",
    "dev@hc-gw01:~$ hc-io status",
    "DI1=1  DI2=0  AI0=28.4  DO1=OFF",
    "dev@hc-gw01:~$ ",
]


def _led_sprites(frame, x, y, sc, t, which=(0, 1, 3)):
    s, ctx = surface(C.W, C.H)
    for i in which:
        lx, ly = GW3Q_LEDS[i]
        a = 1.0 if i != 3 else (1.0 if math.sin(t * 16) > -0.3 else 0.3)
        glow_spot(ctx, x + lx * sc, y + ly * sc, 60 * sc, C.GREEN, 0.85 * a)
    frame.alpha_composite(to_pil(s))
    return frame


def hero(t, dur):
    frame, (x, y, sc) = product_frame(product.load("gateway_3q"), t, dur, scale0=0.8, scale1=0.87, cy=C.H / 2 + 40)
    return _led_sprites(frame, x, y, sc, t)


def pcb(t, dur):
    img = product.load("gateway_pcb")
    frame, (x, y, sc) = product_frame(img, t, dur, scale0=0.84, scale1=0.9, sweep=False, cy=C.H / 2 + 30)
    feats = list(product.PCB_FEATURES.items())
    for i, (name, (fx, fy)) in enumerate(feats):
        tx, ty = x + fx * img.width * sc, y + fy * img.height * sc
        side = -1 if fx < 0.5 else 1
        lx = tx + side * (160 + (i % 2) * 40)
        ly = ty - 70 - (i % 3) * 16
        O.callout(frame, name, (tx, ty), (lx, ly), t, t0=0.25 + i * 0.32)
    return frame


def connect_dyn(t, dur, plate, cam):
    gx, gy, gw, gh = DEV_GW
    u = gw / 100
    port_x, port_y = gx + 64 * u, gy + gh * 0.2
    pcx, pcy = port_x + 7 * u, port_y + 6 * u
    p = ease_out(progress(t, 0.1, 1.0))
    ox, oy = (1 - p) * -90, (1 - p) * 110

    def cable(ctx):
        hx, hy = pcx + ox, pcy + oy
        ctx.move_to(CX - 300, PH + 60)
        ctx.curve_to(CX - 100, PH - 60, hx - 60, hy + 360, hx, hy + 40)
        set_col(ctx, (40, 90, 200), 1)
        ctx.set_line_width(22)
        ctx.stroke()
        # plug
        ctx.rectangle(hx - 5 * u, hy - 3 * u, 10 * u, 11 * u)
        linear_fill(ctx, hx - 5 * u, 0, hx + 5 * u, 0, [(0, (180, 200, 230), 0.95), (1, (120, 140, 180), 0.95)])
        ctx.fill()
    out = [(plate_layer(cable, (CX - 400, gy - 100, gx + gw + 100, PH)), 0.55)]
    if t > 1.0:
        lx, ly = gx + (8 + 27) * u, gy + gh * 0.72
        out.append((glow_dot_layer([(lx, ly, C.GREEN)], t, radius=4 * u, blink="data"), 0.55))
    n = int(max(0, t - 0.3) * 70) if t < 1.2 else 999
    lines = TERMINAL if t > 1.2 else TERMINAL[:1]
    out.append((code_layer(DEV_LAPTOP, lines, n, t, size=24, gutter=False), 0.5))
    return out


def code_dyn(t, dur, plate, cam):
    chars = int(60 + t * 190)
    return [(code_layer(CODE_RECT_FW, SDK_CODE, chars, t, size=32, highlight_line=9 if chars > 300 else None), 0.5),
            (code_layer(TERM_RECT_FW, ["$ hcgw deploy pump_control.py", "Uploading to hc-gw01 ... OK", "Logic running  ·  DI1 -> DO1"],
                        999 if t > 1.6 else 0, t, size=28, gutter=False, cursor=False), 0.5)]


WORDS = [("BUILD.", 0.15), ("MODIFY.", 1.05), ("DEVELOP.", 1.95)]
WORD_Y = [C.H / 2 - 190, C.H / 2, C.H / 2 + 190]


def _word_traces():
    items = []
    for i in range(2):
        x = C.W / 2
        y0, y1 = WORD_Y[i] + 58, WORD_Y[i + 1] - 58
        items.append({"pts": [(x, y0), (x, y1)], "t0": WORDS[i + 1][1] - 0.3, "dur": 0.3, "width": 3})
        # side branches (circuit look)
        for sgn in (-1, 1):
            items.append({"pts": [(x, (y0 + y1) / 2), (x + sgn * 60, (y0 + y1) / 2 - 30), (x + sgn * 260, (y0 + y1) / 2 - 30)],
                          "t0": WORDS[i + 1][1] - 0.15, "dur": 0.35, "width": 2})
    return TraceAnim(items, glow_radius=8, glow_strength=1.2)


_WT = _word_traces()


def words(t, dur):
    frame = Plate.load("dark_grid").render(Cam(1.02 + 0.04 * t / dur))
    img = _WT.render(t)
    if img is not None:
        frame.alpha_composite(img)
    for (w, t0), y in zip(WORDS, WORD_Y):
        draw_lines(frame, [Line(w, "display_black", 104, C.WHITE if w != "DEVELOP." else C.GREEN, -5)],
                   t, t0, dur + 1, anim="mask", center=(C.W / 2, y), dur_in=0.45, dur_out=0)
    return frame


def tagline(t, dur):
    frame, (x, y, sc) = product_frame(product.load("gateway_3q"), t, dur, scale0=0.44, scale1=0.48, cy=330, sweep=True)
    frame = _led_sprites(frame, x, y, sc, t)
    draw_lines(frame, [Line("HARDWARE", "display_black", 116, C.WHITE, -5),
                       Line("MADE FOR DEVELOPERS.", "display_bold", 66, C.GREEN, 20)],
               t, 0.2, dur + 1, anim="mask", center=(C.W / 2, 740), dur_in=0.7, dur_out=0)
    return frame


def build():
    d = dict(SHOTS)
    shots = [
        FuncShot(d["hero"], hero, "gateway_hero", grade="tech"),
        FuncShot(d["pcb"], pcb, "gateway_pcb_callouts", grade="tech"),
        PlateShot(d["connect"], "dev_desk", Cam(1.04, 30, 30), Cam(1.1, 60, 30), dyn=connect_dyn, shake=0.4, seed=21, grade="tech", name="developer_connect"),
        PlateShot(d["code"], "code_firmware", Cam(1.08, -60, -130), Cam(1.14, -30, -110), dyn=code_dyn, grade="tech", name="developer_code"),
        FuncShot(d["words"], words, "build_modify_develop", grade="tech"),
        FuncShot(d["tagline"], tagline, "made_for_developers", grade="tech"),
    ]
    ov = [badge(0.0, T["words"]), badge(T["tagline"], DURATION),
          hud_corners(T["hero"] + 0.2, T["pcb"] - 0.05, "HC GW-01  ·  EDGE GATEWAY", "CONCEPT  REV 0.9")]
    vo = [
        VO("vo09", 0.4, "แต่สิ่งที่ Home Circuit อยากสร้าง ไม่ใช่แค่อุปกรณ์หนึ่งชิ้นที่ใช้งานได้",
           [["แต่สิ่งที่ Home Circuit อยากสร้าง", "ไม่ใช่แค่อุปกรณ์หนึ่งชิ้นที่ใช้งานได้"]],
           "แต่สิ่งที่โฮมเซอร์กิตอยากสร้าง ไม่ใช่แค่อุปกรณ์หนึ่งชิ้นที่ใช้งานได้", max_dur=4.4),
        VO("vo10", 5.0, "เราอยากสร้าง Hardware ที่นักพัฒนาสามารถนำไปต่อยอด ประยุกต์ใช้ และเขียนโปรแกรมเพิ่มเติมให้เหมาะกับงานของตัวเองได้",
           [["เราอยากสร้าง Hardware", "ที่นักพัฒนาสามารถนำไปต่อยอด ประยุกต์ใช้"],
            ["และเขียนโปรแกรมเพิ่มเติม", "ให้เหมาะกับงานของตัวเองได้"]],
           "เราอยากสร้างฮาร์ดแวร์ ที่นักพัฒนาสามารถนำไปต่อยอด ประยุกต์ใช้ และเขียนโปรแกรมเพิ่มเติมให้เหมาะกับงานของตัวเองได้",
           max_dur=7.6),
    ]
    sfx = [SFX(0.0, "whoosh_soft", -20), SFX(0.4, "shimmer", -22), SFX(T["pcb"], "tick", -18),
           SFX(T["connect"] + 1.0, "plug", -12), SFX(T["connect"] + 1.15, "beep", -22),
           SFX(T["code"], "keyboard", -20), SFX(T["words"], "low_impact", -16)]
    for w, t0 in WORDS:
        sfx.append(SFX(T["words"] + t0, "tick_hi", -14))
    sfx.append(SFX(T["tagline"], "low_impact", -12))
    return Scene("05_PHILOSOPHY", shots, ov, vo, sfx, grade="tech",
                 music_marks=[(T["words"], "drop_light"), (T["tagline"], "hit")])
