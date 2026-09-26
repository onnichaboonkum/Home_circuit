"""Mix VO / music / SFX layers into the final stereo track (with VO ducking)."""
import numpy as np

from .. import config as C
from . import sfx as SFXLIB
from .dsp import SR, db, hp, lp, pan_stereo, place, read_wav, soft_limit, write_wav

VO_GAIN = db(-3.0)
MUSIC_GAIN = db(-1.0)
MUSIC_DUCK_DB = -6.5       # music level under narration
SFX_MASTER = db(0.0)


def _smooth_env(active, attack=0.12, release=0.45):
    out = np.zeros_like(active)
    a = 1 - np.exp(-1 / (attack * SR / 64))
    r = 1 - np.exp(-1 / (release * SR / 64))
    # block-wise one-pole for speed
    blocks = active[::64]
    env = np.zeros_like(blocks)
    v = 0.0
    for i, x in enumerate(blocks):
        v += (x - v) * (a if x > v else r)
        env[i] = v
    out = np.repeat(env, 64)[: len(active)]
    return out


def mix(scenes, total, vo_items, music_path):
    n = int(total * SR)
    vo = np.zeros((n, 2))
    fx = np.zeros((n, 2))
    active = np.zeros(n)
    for it in vo_items:
        x = read_wav(it["path"])[:, 0]
        # light "broadcast" polish on the narration bus
        x = hp(x, 80)
        place(vo, x, it["start"], VO_GAIN)
        i0 = int(it["start"] * SR)
        active[i0:i0 + len(x)] = 1.0
    for sc in scenes:
        for s in sc.sfx:
            clip = SFXLIB.load(s.name)
            if clip.shape[1] == 1:
                clip = pan_stereo(clip[:, 0], s.pan)
            place(fx, clip, sc.start + s.t, db(s.gain_db) * SFX_MASTER)
    music = read_wav(music_path)
    if music.shape[1] == 1:
        music = np.repeat(music, 2, 1)
    music = music[:n]
    if len(music) < n:
        music = np.concatenate([music, np.zeros((n - len(music), 2))])
    duck = 1 - (1 - db(MUSIC_DUCK_DB)) * _smooth_env(active)
    music = music * MUSIC_GAIN * duck[:, None]
    out = vo + music + fx
    out = soft_limit(out * 1.0, 0.97)
    peak = np.abs(out).max()
    if peak > 0.97:
        out *= 0.97 / peak
    build = C.BUILD / "stems"
    build.mkdir(parents=True, exist_ok=True)
    write_wav(build / "stem_voiceover.wav", vo)
    write_wav(build / "stem_music_ducked.wav", music)
    write_wav(build / "stem_sfx.wav", fx)
    path = C.BUILD / "mix.wav"
    write_wav(path, out)
    # loudness-normalise to TARGET_LUFS (measured with ffmpeg's EBU R128 meter)
    lufs = measure_lufs(path)
    if lufs is not None:
        g = db(TARGET_LUFS - lufs)
        out = soft_limit(out * g, 0.97)
        pk = np.abs(out).max()
        if pk > db(-1.0):
            out *= db(-1.0) / pk
        write_wav(path, out)
    return path


TARGET_LUFS = -16.0


def measure_lufs(path):
    import re
    import subprocess
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None
