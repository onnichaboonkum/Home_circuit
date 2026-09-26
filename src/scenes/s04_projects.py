"""04_PROJECTS - from small freelance jobs to IoT, gateways, drones, public-sector and
university projects. All project visuals are generic concepts (no real logos,
no insignia, no named organisations) and carry the DRAFT VISUAL badge."""
import math

from PIL import Image, ImageDraw

from .. import config as C
from ..engine import props as P
from ..engine.camera import Sprite
from ..engine.canvas import fast_blur, glow_spot, set_col
from ..engine.pcb import node, poly_partial, route, route_v, stroke_poly
from ..engine.scene import VO, SFX, PlateShot, Scene
from ..engine.text import font
from ..engine.util import clamp, ease_out, progress
from ..plates import CX, CY, FARM_SENSOR_LED, FREELANCE_SCREEN, GW_CAB_RECT, PUBLIC_BEACON, network_nodes
from .common import Cam, badge, caption, glow_dot_layer, label, plate_layer

# ---- shot table (name, duration) - edit here
SHOTS = [
    ("freelance", 2.6),
    ("network", 2.2),
    ("iot", 2.0),
    ("gateway", 1.8),
    ("drone", 1.8),
    ("public", 1.8),
    ("university", 2.0),
    ("farm", 2.2),
    ("embedded", 2.6),
]
T = {}
_acc = 0.0
for _n, _d in SHOTS:
    T[_n] = _acc
    _acc += _d
DURATION = _acc

CHAT = [
    (0.15, "in", "สวัสดีครับ อยากให้ช่วยทำบอร์ดควบคุมปั๊มน้ำ"),
    (0.75, "in", "อ่านเซนเซอร์ 4 จุด แล้วส่งข้อมูลขึ้นระบบได้ไหมครับ?"),
    (1.45, "out", "ได้ครับ เริ่มจากทำต้นแบบกันก่อน"),
]


def freelance_dyn(t, dur, plate, cam):
    x, y, w, h = FREELANCE_SCREEN
    im = Image.new("RGBA", (int(w), int(h)), (16, 19, 21, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 70), fill=(24, 29, 30, 255))
    d.text((34, 16), "PROJECT REQUEST", font=font("ui_semibold", 30), fill=C.WHITE + (255,))
    d.ellipse((w - 60, 24, w - 36, 48), fill=C.GREEN + (255,))
    fy = 110
    f = font("thai", 34)
    for t0, side, msg in CHAT:
        a = clamp((t - t0) / 0.2)
        if a <= 0:
            continue
        tw = f.getlength(msg) + 56
        bx = 40 if side == "in" else w - 40 - tw
        rise = (1 - ease_out(a)) * 20
        col = (38, 44, 46) if side == "in" else (22, 110, 62)
        d.rounded_rectangle((bx, fy + rise, bx + tw, fy + 78 + rise), 22, fill=col + (int(255 * a),))
        d.text((bx + 28, fy + 14 + rise), msg, font=f, fill=C.WHITE + (int(255 * a),))
        fy += 104
    if t > 1.0 and t < 1.45:
        d.text((w - 190, fy + 10), "typing…", font=font("ui_regular", 26), fill=(150, 156, 156, 255))
    return [(Sprite(im, int(x), int(y)), 0.5)]


NODES = network_nodes()


def network_dyn(t, dur, plate, cam):
    p = ease_out(progress(t, 0.0, dur * 0.85))

    def fn(ctx):
        n = len(NODES)
        for i, (x, y, lab, dist) in enumerate(NODES):
            lp = clamp(p * n * 0.6 - i * 0.45)
            if lp <= 0:
                continue
            pts = route(CX, CY, x, y, 0.5) if abs(x - CX) > abs(y - CY) else route_v(CX, CY, x, y, 0.5)
            sub, head = poly_partial(pts, lp)
            stroke_poly(ctx, sub, 3, C.GREEN, 0.8)
            if lp >= 1:
                node(ctx, x, y, 9, C.GREEN, 1)
                ctx.select_font_face("Noto Sans Mono")
                ctx.set_font_size(22)
                set_col(ctx, C.LIGHT_GREY, 0.8 * clamp((lp - 1) + 1))
                ctx.move_to(x + 16, y - 12)
                ctx.show_text(lab)
        # home node
        node(ctx, CX, CY, 18, C.WHITE, 1)
        glow_spot(ctx, CX, CY, 70, C.GREEN, 0.6)
    return [(plate_layer(fn, (0, 0, 2304, 1296), glow_r=6, glow_s=0.7), 0.4)]


IOT_SENSORS = [(CX - 710, 590), (CX - 250, 370), (CX + 220, 510), (CX + 670, 690), (CX - 820, 900), (CX - 330, 800),
               (CX + 120, 860), (CX + 560, 980), (CX - 600, 1110), (CX + 300, 1150)]
IOT_HUB = (CX - 60, 1210)


def iot_dyn(t, dur, plate, cam):
    def fn(ctx):
        for i, (sx, sy) in enumerate(IOT_SENSORS):
            pts = route_v(sx, sy, IOT_HUB[0], IOT_HUB[1], 0.6)
            lp = clamp(t * 1.6 - i * 0.06)
            sub, _ = poly_partial(pts, lp)
            stroke_poly(ctx, sub, 2.2, C.GREEN, 0.55)
            # packet travelling to the hub
            pk = ((t * 0.9 + i * 0.13) % 1.0)
            if lp >= 1:
                _, head = poly_partial(pts, pk)
                node(ctx, *head, 5, C.WHITE, 1, ring=False)
            ring = ((t * 1.2 + i * 0.3) % 1.0)
            ctx.arc(sx, sy, 10 + ring * 46, 0, 2 * math.pi)
            set_col(ctx, C.GREEN, 0.7 * (1 - ring))
            ctx.set_line_width(2)
            ctx.stroke()
            node(ctx, sx, sy, 8, C.GREEN, 1)
        node(ctx, IOT_HUB[0], IOT_HUB[1], 16, C.WHITE, 1)
    return [(plate_layer(fn, (0, 0, 2304, 1296), glow_r=6, glow_s=0.8), 0.5)]


def gateway_leds(rect, t, link_on=True):
    x, y, w, h = rect
    u = w / 100
    pts = []
    for i in range(4):
        lx, ly = x + (8 + i * 9) * u, y + h * 0.72
        if i == 2:
            continue
        if i == 3 and not link_on:
            continue
        pts.append((lx, ly, C.GREEN))
    return glow_dot_layer(pts, t, radius=u * 4, blink="data")


def gateway_dyn(t, dur, plate, cam):
    return [(gateway_leds(GW_CAB_RECT, t), 0.5)]


def drone_dyn(t, dur, plate, cam):
    dx = math.sin(t * 1.3) * 18
    dy = math.cos(t * 1.1) * 12
    s = 560

    def shadow(ctx):
        P.drone_top(ctx, CX + 150 + dx * 0.4, CY + 190 + dy * 0.4, s, arm_col=(0, 0, 0), leds=False)

    def body(ctx):
        P.drone_top(ctx, CX + dx, CY + 70 + dy, s, prop_phase=t * 38)
    sh = plate_layer(shadow, (CX - 500, CY - 300, CX + 800, CY + 700), blur_r=16)
    sh.img.putalpha(sh.img.getchannel("A").point(lambda v: int(v * 0.45)))
    return [(sh, 0.05), (plate_layer(body, (CX - 620, CY - 560, CX + 620, CY + 700)), 1.0)]


def public_dyn(t, dur, plate, cam):
    x, y = PUBLIC_BEACON
    px, py = CX + 300 - 425, 482

    def waves(ctx):
        for k in range(3):
            ph = ((t * 0.9 + k / 3) % 1.0)
            r = 30 + ph * 260
            ctx.arc(px, py, r, math.pi * 0.3, math.pi * 0.7)
            set_col(ctx, C.GREEN, 0.8 * (1 - ph))
            ctx.set_line_width(3)
            ctx.stroke()
    return [(glow_dot_layer([(x, y, C.GREEN)], t, radius=40, blink="blink"), 0.5),
            (plate_layer(waves, (px - 320, py - 20, px + 320, py + 320), glow_r=5), 0.5)]


def farm_dyn(t, dur, plate, cam):
    ax, ay = CX + 152, 431

    def rings(ctx):
        for k in range(3):
            ph = ((t * 0.8 + k / 3) % 1.0)
            ctx.arc(ax, ay, 16 + ph * 220, 0, 2 * math.pi)
            set_col(ctx, C.GREEN, 0.6 * (1 - ph))
            ctx.set_line_width(3)
            ctx.stroke()
    x, y = FARM_SENSOR_LED
    return [(glow_dot_layer([(x, y, C.GREEN)], t, radius=36, blink="blink"), 0.5),
            (plate_layer(rings, (ax - 260, ay - 260, ax + 260, ay + 260), glow_r=5), 0.5)]


def embedded_dyn(t, dur, plate, cam):
    pts = [(1828 + i * 92, 1127, C.GREEN if i != 2 else (255, 170, 60)) for i in range(4)]
    return [(glow_dot_layer(pts, t, radius=70, blink="data"), 0.0)]


def university_dyn(t, dur, plate, cam):
    rx, ry = CX - 330, 800
    return [(glow_dot_layer([(rx + 600, ry + 40, C.GREEN), (rx + 560, ry + 40, (255, 90, 60))], t, radius=26, blink="blink"), 0.5)]


def build():
    d = dict(SHOTS)
    shots = [
        PlateShot(d["freelance"], "proj_freelance", Cam(1.1, -40, -120), Cam(1.18, 0, -110), dyn=freelance_dyn, grade="warm", name="freelance_chat"),
        PlateShot(d["network"], "proj_network", Cam(1.35, 0, 0), Cam(1.0, 0, 0), dyn=network_dyn, grade="tech", name="project_network"),
        PlateShot(d["iot"], "proj_iot", Cam(1.04, 0, 20), Cam(1.12, 0, 0), dyn=iot_dyn, grade="tech", name="iot", blur_in=0.1),
        PlateShot(d["gateway"], "proj_gateway_cabinet", Cam(1.3, 250, -330), Cam(1.4, 260, -340), dyn=gateway_dyn, grade="tech", name="gateway_cabinet", blur_in=0.1),
        PlateShot(d["drone"], "proj_drone", Cam(1.05, 0, 0, -2), Cam(1.16, 0, 0, 2), dyn=drone_dyn, grade="tech", name="drone_uav"),
        PlateShot(d["public"], "proj_public", Cam(1.08, 60, -60), Cam(1.16, 90, -60), dyn=public_dyn, grade="tech", name="public_sector_generic"),
        PlateShot(d["university"], "proj_university", Cam(1.06, -40, 0), Cam(1.12, 40, 0), dyn=university_dyn, shake=0.5, seed=12, grade="neutral", name="university"),
        PlateShot(d["farm"], "proj_farm", Cam(1.1, 80, -40), Cam(1.2, 110, -60), dyn=farm_dyn, grade="warm", name="smart_farm"),
        PlateShot(d["embedded"], "proj_embedded", Cam(1.1, -60, 0), Cam(1.22, 60, 20), dyn=embedded_dyn, grade="tech", name="embedded", blur_in=0.1),
    ]
    ov = [
        badge(T["network"] + 0.1, DURATION),
        label("IoT", T["iot"], T["gateway"]),
        label("GATEWAY", T["gateway"], T["drone"]),
        label("DRONE / UAV", T["drone"], T["public"]),
        label("ENGINEERING PROJECTS", T["public"], T["farm"], size=54),
        caption("PUBLIC-SECTOR TECHNOLOGY  ·  GENERIC CONCEPT", T["public"] + 0.2, T["university"], y=196),
        caption("UNIVERSITY ENGINEERING PROJECTS", T["university"] + 0.05, T["farm"], y=196),
        label("IoT", T["farm"], T["embedded"], sub="SMART AGRICULTURE"),
        label("EMBEDDED SYSTEMS", T["embedded"], DURATION),
    ]
    vo = [
        VO("vo07", 0.3, "จากงาน Freelance เล็ก ๆ โปรเจกต์เริ่มเดินทางไปไกลขึ้น",
           [["จากงาน Freelance เล็ก ๆ", "โปรเจกต์เริ่มเดินทางไปไกลขึ้น"]],
           "จากงานฟรีแลนซ์เล็กเล็ก โปรเจกต์เริ่มเดินทางไปไกลขึ้น", max_dur=3.9),
        VO("vo08", 4.7, "ตั้งแต่งาน IoT และระบบควบคุม งานพัฒนาโดรน เทคโนโลยีสำหรับหน่วยงานภาครัฐ ไปจนถึงโปรเจกต์ของนักศึกษามหาวิทยาลัย",
           [["ตั้งแต่งาน IoT และระบบควบคุม", "งานพัฒนาโดรน"],
            ["เทคโนโลยีสำหรับหน่วยงานภาครัฐ", "ไปจนถึงโปรเจกต์ของนักศึกษามหาวิทยาลัย"]],
           "ตั้งแต่งานไอโอทีและระบบควบคุม งานพัฒนาโดรน เทคโนโลยีสำหรับหน่วยงานภาครัฐ ไปจนถึงโปรเจกต์ของนักศึกษามหาวิทยาลัย",
           max_dur=9.2),
    ]
    sfx = [SFX(0.15, "notify", -20), SFX(0.75, "notify", -22), SFX(1.45, "notify", -20),
           SFX(T["network"], "whoosh", -18), SFX(T["drone"], "drone", -14), SFX(T["university"], "servo", -18)]
    for n, t0 in T.items():
        if n not in ("freelance",):
            sfx.append(SFX(t0, "tick", -18))
        if n in ("iot", "gateway", "embedded"):
            sfx.append(SFX(t0 - 0.12, "whoosh_soft", -20))
    for t0 in (T["iot"] + 0.3, T["gateway"] + 0.4, T["farm"] + 0.5):
        sfx.append(SFX(t0, "beep", -24))
    return Scene("04_PROJECTS", shots, ov, vo, sfx, grade="tech",
                 music_marks=[(t0, "accent") for n, t0 in T.items() if n != "freelance"])
