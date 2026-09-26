"""2.5D camera: Ken Burns, push-in, pan and multi-layer parallax on still plates.

A *plate* is a stack of RGBA layers of identical size (larger than the frame)
with a depth value each (0 = far background, 1 = near foreground).  Plates are
stored on disk as ``assets/images/<name>__<layer>.png`` so any layer can be
replaced by real photography later (a single ``__bg.png`` is enough).
"""
import math
from dataclasses import dataclass

from PIL import Image

from .. import config as C
from .util import ease_in_out, lerp

LAYER_DEPTHS = {"bg": 0.0, "mid": 0.5, "fg": 1.0, "fx": 0.75}
LAYER_ORDER = ["bg", "mid", "fx", "fg"]
_PLATE_CACHE = {}


@dataclass
class Cam:
    zoom: float = 1.0      # 1.0 shows the full plate
    x: float = 0.0         # pan offset of the view centre, in plate pixels
    y: float = 0.0
    rot: float = 0.0       # degrees (used sparingly)


class Plate:
    def __init__(self, layers, name="plate"):
        # layers: list of (PIL RGBA, depth)
        self.layers = sorted(layers, key=lambda l: l[1])
        self.w, self.h = self.layers[0][0].size
        self.name = name

    @classmethod
    def load(cls, name, folder=None):
        key = (name, str(folder))
        if key in _PLATE_CACHE:
            return _PLATE_CACHE[key]
        folder = folder or C.IMAGES
        layers = []
        for lname in LAYER_ORDER:
            p = folder / f"{name}__{lname}.png"
            if p.exists():
                layers.append((Image.open(p).convert("RGBA"), LAYER_DEPTHS[lname]))
        if not layers:
            raise FileNotFoundError(f"plate '{name}' not found in {folder} - run scripts/build_assets.py")
        # a replaced background photo may have any size: normalise to 16:9 cover
        bw, bh = layers[0][0].size
        fixed = []
        for img, d in layers:
            if img.size != (bw, bh):
                img = img.resize((bw, bh), Image.LANCZOS)
            fixed.append((img, d))
        if abs(bw / bh - 16 / 9) > 0.01:
            from .canvas import fit_cover
            nw, nh = bw, int(bw * 9 / 16)
            if nh > bh:
                nw, nh = int(bh * 16 / 9), bh
            fixed = [(fit_cover(img, nw, nh), d) for img, d in fixed]
        plate = cls(fixed, name)
        _PLATE_CACHE[key] = plate
        return plate

    # --------------------------------------------------------------
    def view_box(self, cam, depth):
        """Source rectangle (in plate px) seen by the camera for a given layer depth."""
        k = 0.45 + depth * 1.1
        z = max(1e-3, 1.0 + (cam.zoom - 1.0) * k)
        bw, bh = self.w / z, self.h / z
        cx = self.w / 2 + cam.x * k
        cy = self.h / 2 + cam.y * k
        if depth <= 0.01:  # background never shows its edges
            cx = min(max(cx, bw / 2), self.w - bw / 2)
            cy = min(max(cy, bh / 2), self.h - bh / 2)
        return (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)

    def render(self, cam, extra=None, size=(C.W, C.H), resample=Image.BILINEAR):
        """Composite all layers for a camera.

        ``extra`` items are (img, depth) with a plate-sized RGBA image, or
        (Sprite, depth) for small animated elements positioned in plate space.
        """
        self._prepare()
        layers = list(self._prepared) + list(extra or [])
        layers.sort(key=lambda l: l[1])
        out = None
        for img, depth in layers:
            box = self.view_box(cam, depth)
            if isinstance(img, Sprite):
                if out is None:
                    out = Image.new("RGBA", size, (0, 0, 0, 255))
                _composite_sprite(out, img, box, size, resample, cam.rot * (0.6 + depth * 0.6))
                continue
            if out is None and img.mode == "RGB":
                out = _view(img, box, size, resample).convert("RGBA")
            else:
                if out is None:
                    out = Image.new("RGBA", size, (0, 0, 0, 255))
                v = _view(img, box, size, resample)
                if cam.rot:
                    v = v.rotate(cam.rot * (0.6 + depth * 0.6), resample=Image.BILINEAR)
                out.alpha_composite(v)
                continue
            if cam.rot:
                out = out.rotate(cam.rot * (0.6 + depth * 0.6), resample=Image.BILINEAR, fillcolor=(0, 0, 0, 255))
        return out

    def _prepare(self):
        """Opaque background -> RGB, other layers -> cropped sprites (big speed-up)."""
        if getattr(self, "_prepared", None) is not None:
            return
        prep = []
        for i, (img, depth) in enumerate(self.layers):
            if i == 0 and img.getchannel("A").getextrema()[0] == 255:
                prep.append((img.convert("RGB"), depth))
                continue
            bb = img.getchannel("A").getbbox()
            if bb is None:
                continue
            prep.append((Sprite(img.crop(bb), bb[0], bb[1]), depth))
        self._prepared = prep

    def to_frame_xy(self, cam, depth, px, py, size=(C.W, C.H)):
        """Map a plate-pixel position to frame coordinates (for tracked overlays)."""
        x0, y0, x1, y1 = self.view_box(cam, depth)
        return ((px - x0) / (x1 - x0) * size[0], (py - y0) / (y1 - y0) * size[1])


class Sprite:
    """Small RGBA image placed at (x, y) in plate coordinates."""
    __slots__ = ("img", "x", "y")

    def __init__(self, img, x, y):
        self.img, self.x, self.y = img, x, y


def _composite_sprite(out, sp, box, size, resample, rot=0.0):
    x0, y0, x1, y1 = box
    sx, sy = size[0] / (x1 - x0), size[1] / (y1 - y0)
    dx, dy = (sp.x - x0) * sx, (sp.y - y0) * sy
    w, h = sp.img.width * sx, sp.img.height * sy
    # clip to the visible frame before scaling
    cx0, cy0 = max(0.0, -dx / sx), max(0.0, -dy / sy)
    cx1 = min(float(sp.img.width), (size[0] - dx) / sx)
    cy1 = min(float(sp.img.height), (size[1] - dy) / sy)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    tw, th = int(round((cx1 - cx0) * sx)), int(round((cy1 - cy0) * sy))
    if tw < 1 or th < 1:
        return
    part = sp.img.resize((tw, th), resample, box=(cx0, cy0, cx1, cy1))
    px, py = int(round(dx + cx0 * sx)), int(round(dy + cy0 * sy))
    if rot:
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        layer.paste(part, (px, py))
        out.alpha_composite(layer.rotate(rot, resample=Image.BILINEAR))
        return
    out.alpha_composite(part, dest=(max(0, px), max(0, py)))


def _view(img, box, size, resample):
    """Crop+scale a (possibly out-of-bounds) box of ``img`` to ``size`` quickly."""
    x0, y0, x1, y1 = box
    if x0 >= 0 and y0 >= 0 and x1 <= img.width and y1 <= img.height:
        return img.resize(size, resample, box=box)
    # partially outside: resize the valid part and paste it at the right place
    sx, sy = size[0] / (x1 - x0), size[1] / (y1 - y0)
    vx0, vy0 = max(0.0, x0), max(0.0, y0)
    vx1, vy1 = min(float(img.width), x1), min(float(img.height), y1)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    if vx1 <= vx0 or vy1 <= vy0:
        return out
    dx0, dy0 = (vx0 - x0) * sx, (vy0 - y0) * sy
    dw, dh = max(1, int(round((vx1 - vx0) * sx))), max(1, int(round((vy1 - vy0) * sy)))
    part = img.resize((dw, dh), resample, box=(vx0, vy0, vx1, vy1))
    out.paste(part, (int(round(dx0)), int(round(dy0))))
    return out


def cam_at(cam0, cam1, p, ease=ease_in_out):
    e = ease(p)
    return Cam(lerp(cam0.zoom, cam1.zoom, e), lerp(cam0.x, cam1.x, e),
               lerp(cam0.y, cam1.y, e), lerp(cam0.rot, cam1.rot, e))


def handheld(t, amount=1.0, seed=0):
    """Subtle organic camera float (documentary feel)."""
    s = seed * 3.7
    dx = (math.sin(t * 0.9 + s) * 0.6 + math.sin(t * 2.3 + s * 2) * 0.3 + math.sin(t * 5.1 + s) * 0.1)
    dy = (math.cos(t * 0.7 + s * 1.3) * 0.6 + math.sin(t * 1.9 + s * 0.5) * 0.3 + math.cos(t * 4.3 + s) * 0.1)
    return dx * 6 * amount, dy * 4 * amount
