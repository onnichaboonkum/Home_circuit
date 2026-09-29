"""05_PHILOSOPHY - the real product: Arduino HcEee Gateway V1.0 (images supplied by
Home Circuit, assets/products/hceee/). Open hardware for developers:
BUILD. MODIFY. DEVELOP. -> HARDWARE MADE FOR DEVELOPERS."""
import math

from PIL import Image

from .. import config as C
from ..engine import hceee
from ..engine.camera import Plate
from ..engine.canvas import rounded_rect, set_col, surface, to_pil
from ..engine.captions import Caption
from ..engine.pcb import TraceAnim
from ..engine.scene import SFX, FuncShot, PlateShot, Scene
from ..engine.text import Line, draw_lines, text_image
from ..engine.util import clamp, ease_out, ease_out_expo, progress
from ..plates import CODE_RECT_FW, TERM_RECT_FW
from .common import Cam, code_layer, label

# ---- shot table - edit here
SHOTS = [("hero", 3.8), ("specs", 4.8), ("inside", 3.4), ("connect", 3.6), ("code", 2.9),
         ("words", 3.0), ("tagline", 3.9)]
T = {}
_acc = 0.0
for _n, _d in SHOTS:
    T[_n] = _acc
    _acc += _d
DURATION = _acc

ARDUINO_CODE = [
    "// HcEee Gateway V1.0 - example sketch (ESP32)",
    "#include <Ethernet.h>       // W5500",
    "#include <PubSubClient.h>   // MQTT",
    "#include <ModbusMaster.h>   // RS-485",
    "",
    "void loop() {",
    "  float soil = readSoilSensor();      // Modbus RTU",
    "  if (digitalRead(X0) && soil < 30.0) {",
    "    digitalWrite(Y0, HIGH);           // pump relay",
    "    mqtt.publish(\"farm/pump\", \"ON\");",
    "  }",
    "  delay(1000);",
    "}",
]
UPLOAD = ["Arduino IDE  ·  Board: ESP32 Dev Module", "Uploading sketch ........ 100%", "HcEee Gateway running  ·  MQTT connected"]


def _bg(t, dur, z0=1.02, z1=1.07):
    return Plate.load("dark_grid").render(Cam(z0 + (z1 - z0) * t / dur))


def hero(t, dur):
    frame = _bg(t, dur)
    a = clamp(t / 0.35)
    hceee.card(frame, "views", t, dur, (C.W / 2, 430), 1120, zoom=(1.0, 1.1), focus=(0.62, 0.45),
               alpha=a, rise=(1 - ease_out(clamp(t / 0.6))) * 30)
    return frame


def _spec_rows():
    rows = []
    for cnt, txt in hceee.SPECS:
        chip = text_image(cnt, "ui_semibold", 28, C.WHITE, 20)
        body = text_image(txt, "ui_medium", 33, (232, 236, 234), 0)
        rows.append((chip, body))
    return rows


_ROWS = None


def specs(t, dur):
    global _ROWS
    if _ROWS is None:
        _ROWS = _spec_rows()
    frame = _bg(t, dur, 1.06, 1.1)
    hceee.card(frame, "enclosed", t, dur, (520, 520), 560, zoom=(1.0, 1.08), focus=(0.5, 0.5))
    x0, y0, step = 880, 290, 68
    for i, (chip, body) in enumerate(_ROWS):
        p = ease_out_expo(progress(t, 0.35 + i * 0.28, 0.35 + i * 0.28 + 0.5))
        if p <= 0:
            continue
        y = y0 + i * step
        dx = (1 - p) * 40
        cw = max(64, chip.width + 26)
        s, ctx = surface(cw, 46)
        rounded_rect(ctx, 0, 0, cw, 46, 10)
        set_col(ctx, C.GREEN_DIM if i else (18, 70, 44), 1)
        ctx.fill()
        pill = to_pil(s)
        pill.alpha_composite(chip, dest=(int(cw / 2 - chip.width / 2), int(23 - chip.height / 2)))
        a = clamp(p * 1.5)
        for im, xx in ((pill, x0 + dx), (body, x0 + cw + 22 + dx)):
            im2 = im
            if a < 0.999:
                im2 = im.copy()
                im2.putalpha(im2.getchannel("A").point(lambda v: int(v * a)))
            frame.alpha_composite(im2, dest=(int(xx), int(y - im.height / 2 + (0 if im is body else 0))))
    return frame


def inside(t, dur):
    frame = _bg(t, dur)
    hceee.card(frame, "block", t, dur, (C.W / 2, 470), 1000, zoom=(1.0, 1.35), focus=(0.34, 0.45))
    return frame


def connect(t, dur):
    frame = _bg(t, dur)
    hceee.card(frame, "application", t, dur, (C.W / 2, 470), 1000, zoom=(1.3, 1.02), focus=(0.4, 0.5))
    return frame


def code_dyn(t, dur, plate, cam):
    chars = int(60 + t * 210)
    return [(code_layer(CODE_RECT_FW, ARDUINO_CODE, chars, t, size=32, highlight_line=8 if chars > 330 else None), 0.5),
            (code_layer(TERM_RECT_FW, UPLOAD, 999 if t > 1.5 else 0, t, size=28, gutter=False, cursor=False), 0.5)]


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
    frame = _bg(t, dur)
    hceee.card(frame, "views", t, dur, (C.W / 2, 290), 760, zoom=(1.0, 1.06), focus=(0.5, 0.5),
               alpha=clamp(t / 0.3))
    draw_lines(frame, [Line("HARDWARE", "display_black", 112, C.WHITE, -5),
                       Line("MADE FOR DEVELOPERS.", "display_bold", 64, C.GREEN, 20)],
               t, 0.2, dur + 1, anim="mask", center=(C.W / 2, 640), dur_in=0.7, dur_out=0)
    return frame


def build():
    d = dict(SHOTS)
    shots = [
        FuncShot(d["hero"], hero, "hceee_hero", grade="tech"),
        FuncShot(d["specs"], specs, "hceee_specs", grade="tech"),
        FuncShot(d["inside"], inside, "hceee_block_diagram", grade="tech"),
        FuncShot(d["connect"], connect, "hceee_application", grade="tech"),
        PlateShot(d["code"], "code_firmware", Cam(1.08, -60, -130), Cam(1.14, -30, -110), dyn=code_dyn, grade="tech", name="arduino_code"),
        FuncShot(d["words"], words, "build_modify_develop", grade="tech"),
        FuncShot(d["tagline"], tagline, "made_for_developers", grade="tech"),
    ]
    ov = [label("ARDUINO HcEee GATEWAY V1.0", T["hero"] + 0.2, T["specs"], size=52, y=56, band=False),
          label("ARDUINO HcEee GATEWAY V1.0", T["specs"], T["inside"], size=52, y=130),
          label("INSIDE THE GATEWAY", T["inside"], T["connect"], size=40, y=46, band=False),
          label("CONNECT EVERYTHING", T["connect"], T["code"], size=40, y=46, band=False)]
    d_ = dict(SHOTS)

    def cap(name, lines, **kw):
        return Caption(T[name] + 0.3, d_[name] - 0.45, lines, **kw)

    caps = [
        cap("hero", ["สิ่งที่ Home Circuit อยากสร้าง", "ไม่ใช่แค่อุปกรณ์ที่ใช้งานได้"]),
        cap("specs", ["แต่เป็น Hardware ที่ต่อยอดได้"]),
        cap("inside", ["หัวใจคือ ESP32 พร้อม I/O ครบในตัว"]),
        cap("connect", ["ต่อเซนเซอร์ อุปกรณ์ และระบบคลาวด์ได้ในตัวเดียว"]),
        cap("code", ["เขียนโปรแกรมเพิ่มได้ด้วย Arduino"]),
        cap("words", ["สร้าง  •  ปรับแต่ง  •  พัฒนาต่อ"]),
        cap("tagline", ["“E” สามตัวใน HcEee = Electrical · Electronic · Embedded"]),
    ]
    sfx = [SFX(0.0, "whoosh_soft", -20), SFX(0.3, "shimmer", -22)]
    for i in range(len(hceee.SPECS)):
        sfx.append(SFX(T["specs"] + 0.35 + i * 0.28, "tick", -22))
    sfx += [SFX(T["inside"], "whoosh_soft", -22), SFX(T["connect"], "whoosh_soft", -22),
            SFX(T["connect"] + 1.2, "beep", -24), SFX(T["code"], "keyboard", -20), SFX(T["words"], "low_impact", -16)]
    for w, t0 in WORDS:
        sfx.append(SFX(T["words"] + t0, "tick_hi", -14))
    sfx.append(SFX(T["tagline"], "low_impact", -12))
    return Scene("05_PHILOSOPHY", shots, ov, [], sfx, grade="tech", captions=caps,
                 music_marks=[(T["words"], "drop_light"), (T["tagline"], "hit")])
