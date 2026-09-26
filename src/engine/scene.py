"""Scene / Shot / Cue model.

A Scene is an ordered list of Shots (hard cuts by default) plus overlays
(typography, labels, HUD) and audio cues (VO, SFX). All times inside a scene
are *local* seconds; ``src/timeline.py`` places scenes on the global timeline.
"""
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from PIL import Image

from .. import config as C
from .camera import Cam, Plate, cam_at, handheld
from .util import ease_in_out, progress


# ------------------------------------------------------------------ shots
class Shot:
    dur: float = 1.0
    grade: Optional[str] = None
    name: str = "shot"

    def render(self, t: float) -> Image.Image:  # t: 0..dur
        raise NotImplementedError


class FuncShot(Shot):
    """Shot drawn by a function ``fn(t, dur) -> RGBA frame``."""

    def __init__(self, dur, fn, name="func", grade=None):
        self.dur, self.fn, self.name, self.grade = dur, fn, name, grade

    def render(self, t):
        return self.fn(t, self.dur)


class PlateShot(Shot):
    """Ken Burns / parallax move over a still plate.

    dyn(t, dur, plate, cam) may return a list of (RGBA plate-sized layer, depth)
    for animated elements living *inside* the picture (LED blink, smoke, screens).
    post(frame, t, dur, plate, cam) draws screen-space overlays that track nothing.
    """

    def __init__(self, dur, plate, cam0=Cam(), cam1=Cam(1.08), ease=ease_in_out, dyn=None,
                 post=None, shake=0.0, seed=0, name=None, grade=None, blur_in=0.0):
        self.dur = dur
        self.plate_name = plate
        self.cam0, self.cam1, self.ease = cam0, cam1, ease
        self.dyn, self.post = dyn, post
        self.shake, self.seed = shake, seed
        self.name = name or plate
        self.grade = grade
        self.blur_in = blur_in

    @property
    def plate(self):
        return Plate.load(self.plate_name)

    def cam(self, t):
        c = cam_at(self.cam0, self.cam1, progress(t, 0, self.dur), self.ease)
        if self.shake:
            dx, dy = handheld(t, self.shake, self.seed)
            c = Cam(c.zoom, c.x + dx, c.y + dy, c.rot)
        return c

    def render(self, t):
        plate = self.plate
        cam = self.cam(t)
        extra = self.dyn(t, self.dur, plate, cam) if self.dyn else None
        frame = plate.render(cam, extra)
        if self.blur_in and t < self.blur_in:
            from .canvas import motion_blur
            k = 1 - t / self.blur_in
            frame = motion_blur(frame, 90 * k * k, 0)
        if self.post:
            frame = self.post(frame, t, self.dur, plate, cam) or frame
        return frame


# ------------------------------------------------------------------ overlays
@dataclass
class Overlay:
    """Screen-space element drawn on top of shots between t_in and t_out (scene-local)."""
    t_in: float
    t_out: float
    draw: Callable  # draw(frame, t_rel, dur) -> frame | None ; t_rel = t - t_in
    z: int = 0

    def apply(self, frame, t):
        if self.t_in <= t <= self.t_out:
            out = self.draw(frame, t - self.t_in, self.t_out - self.t_in)
            return out if out is not None else frame
        return frame


# ------------------------------------------------------------------ audio cues
@dataclass
class VO:
    """Voice-over line. ``text`` is shown as subtitle; ``tts`` is what the scratch TTS speaks."""
    id: str
    t: float
    text: str
    sub_lines: List[str]
    tts: str = ""
    max_dur: float = 6.0


@dataclass
class SFX:
    t: float
    name: str
    gain_db: float = -12.0
    pan: float = 0.0


# ------------------------------------------------------------------ scene
@dataclass
class Scene:
    name: str
    shots: List[Shot]
    overlays: List[Overlay] = field(default_factory=list)
    vo: List[VO] = field(default_factory=list)
    sfx: List[SFX] = field(default_factory=list)
    grade: str = "neutral"
    grain: Optional[float] = None
    # music intent markers (scene-local): list of (t, kind) e.g. (15.0, "hit"), (4.5, "dip")
    music_marks: list = field(default_factory=list)
    flashes: list = field(default_factory=list)   # (t, dur, color, strength)

    @property
    def duration(self):
        return sum(s.dur for s in self.shots)

    def shot_at(self, t):
        acc = 0.0
        for s in self.shots:
            if t < acc + s.dur:
                return s, t - acc, acc
            acc += s.dur
        last = self.shots[-1]
        return last, last.dur - 1e-4, acc - last.dur

    def cut_times(self):
        out, acc = [], 0.0
        for s in self.shots:
            out.append(acc)
            acc += s.dur
        return out

    def render(self, t):
        shot, lt, _ = self.shot_at(t)
        frame = shot.render(lt)
        if frame.mode != "RGBA":
            frame = frame.convert("RGBA")
        for ov in sorted(self.overlays, key=lambda o: o.z):
            frame = ov.apply(frame, t)
        for (ft, fd, col, strength) in self.flashes:
            if ft <= t <= ft + fd:
                k = (1 - (t - ft) / fd) ** 2 * strength
                flash = Image.new("RGBA", frame.size, tuple(col) + (int(255 * min(1, k)),))
                frame.alpha_composite(flash)
        return frame, (shot.grade or self.grade)
