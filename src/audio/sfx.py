"""Synthesised sound-effect library (temporary, replaceable).

Every effect is rendered to ``audio/sfx/<name>.wav``. Drop a real recording with
the same name (16-bit WAV) into that folder to replace it - existing files are
never overwritten unless ``build_library(force=True)``.
"""
import numpy as np

from .. import config as C
from .dsp import (SR, bp, db, env_adsr, env_exp, hp, lp, noise, pan_stereo, read_wav, saw, sine,
                  t_axis, write_wav)


def _n(d):
    return int(d * SR)


def relay_click():
    n = _n(0.18)
    out = np.zeros(n)
    for k, (t0, g) in enumerate([(0.0, 1.0), (0.011, 0.55), (0.019, 0.25)]):
        i = int(t0 * SR)
        m = _n(0.03)
        burst = bp(noise(m, k + 1), 1800, 7000) * env_exp(m, 0.0025)
        ping = sine(2100 - k * 300, t_axis(0.03)) * env_exp(m, 0.006) * 0.4
        out[i:i + m] += (burst + ping) * g
    thump = sine(110, t_axis(0.06)) * env_exp(_n(0.06), 0.012)
    out[: len(thump)] += thump * 0.6
    return out / np.abs(out).max()


def tick(freq=4200, dur=0.03):
    n = _n(dur)
    x = sine(freq, t_axis(dur)) * env_exp(n, 0.006) + bp(noise(n, 5), 2000, 9000) * env_exp(n, 0.0015) * 0.5
    return x / np.abs(x).max()


def tick_hi():
    return tick(6200, 0.05) * 0.9 + np.concatenate([np.zeros(_n(0.004)), tick(3100, 0.046)])[: _n(0.05)] * 0.3


def beep(freq=2400, dur=0.09):
    n = _n(dur)
    t = t_axis(dur)
    x = (sine(freq, t) + 0.2 * sine(freq * 2, t)) * env_adsr(n, 0.004, 0.02, 0.8, 0.02)
    return x * 0.8


def keyboard():
    n = _n(1.5)
    out = np.zeros(n)
    r = np.random.default_rng(11)
    t = 0.02
    while t < 1.35:
        i = int(t * SR)
        m = _n(0.03)
        click = bp(noise(m, int(t * 1000)), 1500, 6000) * env_exp(m, 0.003)
        thock = sine(r.uniform(260, 380), t_axis(0.03)) * env_exp(m, 0.008) * 0.5
        out[i:i + m] += (click + thock) * r.uniform(0.5, 1.0)
        t += r.uniform(0.06, 0.17)
    return out / np.abs(out).max() * 0.8


def solder_sizzle():
    n = _n(1.3)
    x = hp(noise(n, 21), 3000) * 0.25
    r = np.random.default_rng(22)
    for _ in range(90):
        i = r.integers(0, n - 200)
        x[i:i + 60] += bp(noise(60, int(i)), 2500, 9000) * r.uniform(0.3, 1.0)
    return x * env_adsr(n, 0.15, 0.2, 0.8, 0.5) * 0.6


def servo():
    d = 0.75
    t = t_axis(d)
    f = 300 + 220 * np.sin(np.pi * t / d) ** 2
    ph = np.cumsum(f) / SR
    x = 2 * (ph - np.floor(ph + 0.5))
    x = bp(x, 250, 2500) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 38 * t)))
    return x * env_adsr(len(t), 0.03, 0.1, 0.9, 0.12) * 0.6


def low_impact():
    d = 1.4
    t = t_axis(d)
    f = 38 + 60 * np.exp(-t * 7)
    ph = np.cumsum(f) / SR
    body = np.sin(2 * np.pi * ph) * env_exp(len(t), 0.35)
    hit = lp(noise(len(t), 31), 300) * env_exp(len(t), 0.05) * 0.8
    x = body + hit
    return x / np.abs(x).max()


def whoosh(d=0.6, f0=300, f1=3200, seed=41):
    n = _n(d)
    x = noise(n, seed)
    out = np.zeros(n)
    seg = 8
    for k in range(seg):
        a, b = k * n // seg, (k + 1) * n // seg
        c = f0 + (f1 - f0) * np.sin(np.pi * (k + 0.5) / seg)
        out[a:b] = bp(x, c * 0.7, c * 1.4)[a:b]
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    out = out * env
    out = out / np.abs(out).max()
    pan = np.linspace(-0.6, 0.6, n)
    a_ = (pan + 1) * np.pi / 4
    return np.stack([out * np.cos(a_), out * np.sin(a_)], -1) * 0.9


def whoosh_soft():
    return whoosh(0.8, 200, 1400, 43) * 0.7


def power_on():
    d = 0.35
    t = t_axis(d)
    f = 200 + 1000 * (t / d) ** 1.5
    ph = np.cumsum(f) / SR
    x = np.sin(2 * np.pi * ph) * env_adsr(len(t), 0.01, 0.05, 0.6, 0.15) * 0.5
    x[: _n(0.02)] += tick(3000, 0.02) * 0.5
    return x


def power_down():
    d = 1.1
    t = t_axis(d)
    f = 60 + 900 * np.exp(-t * 3.2)
    ph = np.cumsum(f) / SR
    x = np.sin(2 * np.pi * ph) * 0.5 + 0.3 * np.sin(2 * np.pi * 50 * t)
    x = lp(x, 1500) * np.linspace(1, 0, len(t)) ** 1.5
    return x / np.abs(x).max() * 0.8


def room_tone():
    d = 4.0
    n = _n(d)
    x = lp(noise(n, 51), 900) * 0.25 + 0.03 * np.sin(2 * np.pi * 50 * t_axis(d))
    return x * env_adsr(n, 0.8, 0.1, 1.0, 1.2)


def pencil():
    d = 2.8
    n = _n(d)
    x = bp(noise(n, 61), 1800, 6500)
    t = t_axis(d)
    strokes = (np.sin(2 * np.pi * 2.3 * t) > 0.1).astype(float)
    strokes = lp(strokes, 30)
    return x * strokes * 0.35 * env_adsr(n, 0.05, 0.1, 1.0, 0.3)


def notify():
    a = sine(880, t_axis(0.16)) * env_exp(_n(0.16), 0.05)
    b = sine(1320, t_axis(0.22)) * env_exp(_n(0.22), 0.07)
    return np.concatenate([a * 0.6, b * 0.6])


def drone():
    d = 2.2
    t = t_axis(d)
    f0 = 185 + 6 * np.sin(2 * np.pi * 0.7 * t)
    ph = np.cumsum(f0) / SR
    x = sum(np.sin(2 * np.pi * k * ph) / k for k in range(1, 9))
    x = x * (0.8 + 0.2 * np.sin(2 * np.pi * 31 * t)) + hp(noise(len(t), 71), 2500) * 0.15
    x = lp(x, 3500)
    return x / np.abs(x).max() * env_adsr(len(t), 0.4, 0.2, 0.9, 0.7) * 0.8


def shimmer():
    d = 1.4
    t = t_axis(d)
    x = sum(np.sin(2 * np.pi * f * t + i) for i, f in enumerate([2093, 3136, 4699, 6272])) / 4
    return x * env_adsr(len(t), 0.35, 0.3, 0.5, 0.7) * 0.35


def plug():
    a = tick(3200, 0.03)
    b = tick(2600, 0.03) * 0.7
    out = np.zeros(_n(0.12))
    out[: len(a)] += a
    i = _n(0.035)
    out[i:i + len(b)] += b
    return out


LIBRARY = {
    "relay_click": relay_click, "tick": tick, "tick_hi": tick_hi, "beep": beep, "keyboard": keyboard,
    "solder_sizzle": solder_sizzle, "servo": servo, "low_impact": low_impact, "whoosh": whoosh,
    "whoosh_soft": whoosh_soft, "power_on": power_on, "power_down": power_down, "room_tone": room_tone,
    "pencil": pencil, "notify": notify, "drone": drone, "shimmer": shimmer, "plug": plug,
}


def build_library(force=False):
    C.SFX_DIR.mkdir(parents=True, exist_ok=True)
    for name, fn in LIBRARY.items():
        p = C.SFX_DIR / f"{name}.wav"
        if force or not p.exists():
            write_wav(p, fn())


_cache = {}


def load(name):
    if name not in _cache:
        _cache[name] = read_wav(C.SFX_DIR / f"{name}.wav")
    return _cache[name]
