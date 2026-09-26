"""Small math helpers: easing, interpolation, deterministic randomness."""
import math
import random


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(round(lerp(a, b, t))) for a, b in zip(c1, c2))


def progress(t, start, end):
    """0..1 progress of ``t`` inside [start, end]."""
    if end <= start:
        return 1.0 if t >= end else 0.0
    return clamp((t - start) / (end - start))


def ease_in_out(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


def ease_out(t):
    t = clamp(t)
    return 1 - pow(1 - t, 3)


def ease_in(t):
    t = clamp(t)
    return t * t * t


def ease_out_expo(t):
    t = clamp(t)
    return 1.0 if t >= 1 else 1 - pow(2, -10 * t)


def ease_in_out_sine(t):
    t = clamp(t)
    return -(math.cos(math.pi * t) - 1) / 2


def smoothstep(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0)) if e1 != e0 else float(x >= e1)
    return t * t * (3 - 2 * t)


def fade_window(t, t_in, t_out, fade_in=0.3, fade_out=0.3):
    """1 inside [t_in, t_out] with linear fades on both sides."""
    if t < t_in or t > t_out:
        return 0.0
    a = 1.0
    if fade_in > 0:
        a = min(a, (t - t_in) / fade_in)
    if fade_out > 0:
        a = min(a, (t_out - t) / fade_out)
    return clamp(a)


def rng(seed):
    return random.Random(seed)


def flicker(t, seed=0, speed=9.0, depth=0.12):
    """Deterministic organic flicker (lamps, LEDs, solder glow)."""
    s = seed * 1.618
    v = (math.sin(t * speed + s) * 0.5 + math.sin(t * speed * 2.31 + s * 3.1) * 0.3
         + math.sin(t * speed * 5.17 + s * 7.3) * 0.2)
    return 1.0 - depth * (0.5 + 0.5 * v)
