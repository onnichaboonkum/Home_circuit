"""Tiny DSP toolkit (numpy/scipy) shared by music, SFX and mixing."""
import wave

import numpy as np
from scipy import signal

from .. import config as C

SR = C.AUDIO_SR


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def env_adsr(n, a=0.01, d=0.1, s=0.7, r=0.2, sr=SR):
    a_n, d_n, r_n = int(a * sr), int(d * sr), int(r * sr)
    s_n = max(0, n - a_n - d_n - r_n)
    e = np.concatenate([np.linspace(0, 1, max(1, a_n)), np.linspace(1, s, max(1, d_n)),
                        np.full(s_n, s), np.linspace(s, 0, max(1, r_n))])
    return _fit(e, n)


def env_exp(n, tau, sr=SR):
    return np.exp(-np.arange(n) / (tau * sr))


def _fit(x, n):
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros(n - len(x))])


def lp(x, f, order=2):
    f = min(f, SR * 0.45)
    return signal.sosfilt(signal.butter(order, f, "low", fs=SR, output="sos"), x, axis=0)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "high", fs=SR, output="sos"), x, axis=0)


def bp(x, f0, f1, order=2):
    f1 = min(f1, SR * 0.45)
    return signal.sosfilt(signal.butter(order, [f0, f1], "band", fs=SR, output="sos"), x, axis=0)


def saw(freq, t, detune=0.0):
    ph = (freq * (1 + detune)) * t
    return 2 * (ph - np.floor(ph + 0.5))


def sine(freq, t, phase=0.0):
    return np.sin(2 * np.pi * freq * t + phase)


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def noise(n, seed=0):
    return np.random.default_rng(seed).standard_normal(n)


def pan_stereo(mono, pan=0.0):
    """Equal-power pan, pan in [-1, 1]."""
    a = (pan + 1) * np.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)], -1)


def db(x):
    return 10 ** (x / 20)


def reverb_ir(dur=2.2, seed=3, damp=3000):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ir = np.stack([noise(n, seed), noise(n, seed + 1)], -1) * np.exp(-t * 3.2)[:, None]
    ir = lp(ir, damp)
    ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))[:, None]
    return ir / np.sqrt((ir ** 2).sum(0, keepdims=True))


def convolve_stereo(x, ir):
    if x.ndim == 1:
        x = np.stack([x, x], -1)
    out = np.stack([signal.fftconvolve(x[:, i], ir[:, i])[: len(x)] for i in range(2)], -1)
    return out


def soft_limit(x, ceiling=0.95):
    return np.tanh(x / ceiling) * ceiling


def write_wav(path, x, sr=SR):
    x = np.asarray(x, np.float64)
    if x.ndim == 1:
        x = x[:, None]
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def read_wav(path):
    """Read 16-bit PCM wav -> float array (n, ch) resampled to SR."""
    with wave.open(str(path), "rb") as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sw != 2:
        raise ValueError(f"{path}: only 16-bit PCM wav supported (convert with ffmpeg)")
    x = np.frombuffer(raw, "<i2").astype(np.float64).reshape(-1, ch) / 32768.0
    if sr != SR:
        from math import gcd
        g = gcd(sr, SR)
        x = signal.resample_poly(x, SR // g, sr // g, axis=0)
    return x


def place(buf, clip, t, gain=1.0):
    """Add clip (n,) or (n,2) into stereo buffer at time t."""
    i = int(round(t * SR))
    if clip.ndim == 1:
        clip = np.stack([clip, clip], -1)
    if i < 0:
        clip = clip[-i:]
        i = 0
    n = min(len(clip), len(buf) - i)
    if n > 0:
        buf[i:i + n] += clip[:n] * gain
