"""Generative score (temporary): minimal electronic documentary music, 120 BPM, no vocals.

Warm keys + pad in the origin story, arps/bass/drums grow with the company,
peak in 06-07 (with the scripted dip), resolve on the logo. Section behaviour is
driven by the scene list and each scene's ``music_marks`` so edits to scene
durations keep the music in sync. Output: ``audio/music/music_score.wav``
(replace that file with licensed music if desired and pass --keep-music).
"""
import numpy as np

from .. import config as C
from .dsp import (SR, bp, convolve_stereo, db, env_adsr, env_exp, hp, lp, midi_hz, noise, pan_stereo,
                  reverb_ir, saw, sine, soft_limit, t_axis, write_wav)

BPM = 120
BEAT = 60 / BPM
BAR = BEAT * 4

# (bass midi, voicing midi) - Am7, Fmaj7, C(add9), G(sus2)
PROG = [(45, [57, 60, 64, 67]), (41, [53, 57, 60, 64]), (48, [55, 60, 64, 74]), (43, [55, 59, 62, 69])]
FINAL = (48, [52, 55, 60, 64, 67, 74])

# per-section settings
P = {
    "intro":   dict(pad=0.40, keys=0.30, arp=0.0, cut=900, bass=0.0, kick=None, hats=None, clap=0.0, bars=2),
    "home":    dict(pad=0.50, keys=0.55, arp=0.0, cut=1100, bass=0.0, kick=None, hats=None, clap=0.0, bars=2),
    "build":   dict(pad=0.45, keys=0.25, arp=0.32, cut=1800, bass=0.45, kick="half", hats="8", clap=0.0, bars=1),
    "projects": dict(pad=0.45, keys=0.10, arp=0.45, cut=2600, bass=0.55, kick="four", hats="8", clap=0.18, bars=1),
    "philo":   dict(pad=0.50, keys=0.20, arp=0.30, cut=1600, bass=0.40, kick="half", hats=None, clap=0.0, bars=1),
    "philo2":  dict(pad=0.50, keys=0.10, arp=0.42, cut=2800, bass=0.50, kick="four", hats="8", clap=0.25, bars=1),
    "rise":    dict(pad=0.55, keys=0.0, arp=0.50, cut=3500, bass=0.35, kick=None, hats="16", clap=0.0, bars=1, roll=True),
    "peak":    dict(pad=0.55, keys=0.0, arp=0.62, cut=5200, bass=0.65, kick="four", hats="16", clap=0.45, bars=1),
    "dip":     dict(pad=0.32, keys=0.35, arp=0.0, cut=650, bass=0.0, kick=None, hats=None, clap=0.0, bars=1),
    "resolve": dict(pad=0.50, keys=0.30, arp=0.20, cut=1400, bass=0.0, kick=None, hats=None, clap=0.0, bars=4, final=True),
    "silent":  dict(pad=0.0, keys=0.0, arp=0.0, cut=500, bass=0.0, kick=None, hats=None, clap=0.0, bars=4),
}


def sections(scenes):
    """Return list of (t0, t1, name) and one-shot events [(t, kind)]."""
    secs, events = [], []
    for sc in scenes:
        s0, s1 = sc.start, sc.start + sc.duration
        marks = sorted((s0 + t, k) for t, k in sc.music_marks)
        events += marks
        n = sc.name
        if n.startswith("01"):
            secs.append((0.6, s1, "intro"))
        elif n.startswith("02"):
            hit = next((t for t, k in marks if k == "hit"), s1)
            secs += [(s0, hit, "home"), (hit, s1, "build")]
        elif n.startswith("03"):
            secs.append((s0, s1, "build"))
        elif n.startswith("04"):
            secs.append((s0, s1, "projects"))
        elif n.startswith("05"):
            drop = next((t for t, k in marks if k == "drop_light"), s1)
            secs += [(s0, drop, "philo"), (drop, s1, "philo2")]
        elif n.startswith("06"):
            first = sc.start + 3.0
            accents = [t for t, k in marks if k == "accent"]
            if accents:
                first = accents[0]
            secs += [(s0, first, "rise"), (first, s1, "peak")]
        elif n.startswith("07"):
            dip = next((t for t, k in marks if k == "dip"), None)
            back = next((t for t, k in marks if k == "hit"), None)
            if dip and back:
                secs += [(s0, dip, "peak"), (dip, back, "dip"), (back, s1, "peak")]
            else:
                secs.append((s0, s1, "peak"))
        elif n.startswith("08"):
            end = next((t for t, k in marks if k == "end"), s1)
            secs += [(s0, end, "resolve"), (end, s1 + 3, "silent")]
    return secs, events


def section_at(secs, t):
    for a, b, n in secs:
        if a <= t < b:
            return n
    return "silent"


# ------------------------------------------------------------------ instruments
def pad_note(freq, dur, cut, gain):
    t = t_axis(dur + 1.2)
    x = (saw(freq, t, -0.004) + saw(freq, t, 0.0) + saw(freq, t, 0.0045)) / 3 + 0.4 * sine(freq / 2, t)
    x = lp(x, cut, 2)
    return x * env_adsr(len(t), 0.5, 0.4, 0.8, 1.1) * gain


def ep_note(freq, gain, dec=0.7):
    t = t_axis(1.4)
    x = sine(freq, t) + 0.25 * sine(freq * 2, t) + 0.06 * sine(freq * 3, t)
    return x * env_exp(len(t), dec) * env_adsr(len(t), 0.004, 0.01, 1, 0.05) * gain


def pluck(freq, gain, cut):
    t = t_axis(0.35)
    x = saw(freq, t) * 0.6 + np.sign(sine(freq, t)) * 0.25
    x = lp(x, cut, 2)
    return x * env_exp(len(t), 0.09) * gain


def bass_note(freq, gain, dur=0.24):
    t = t_axis(dur + 0.05)
    x = lp(saw(freq, t), 260, 2) * 0.7 + sine(freq, t) * 0.6
    return x * env_adsr(len(t), 0.005, 0.08, 0.6, 0.06) * gain


def kick():
    t = t_axis(0.4)
    f = 45 + 80 * np.exp(-t * 28)
    ph = np.cumsum(f) / SR
    x = np.sin(2 * np.pi * ph) * env_exp(len(t), 0.13)
    x[: int(0.004 * SR)] += bp(noise(int(0.004 * SR), 1), 1000, 6000) * 0.3
    return x


def hat(open_=False):
    n = int((0.12 if open_ else 0.045) * SR)
    return hp(noise(n, 7), 7000, 2) * env_exp(n, 0.03 if open_ else 0.012) * 0.6


def clap():
    n = int(0.25 * SR)
    x = np.zeros(n)
    for k, d in enumerate([0, 0.011, 0.022]):
        i = int(d * SR)
        m = int(0.02 * SR)
        x[i:i + m] += bp(noise(m, 10 + k), 900, 3500) * env_exp(m, 0.004)
    x += bp(noise(n, 13), 900, 4000) * env_exp(n, 0.06) * 0.5
    return x * 0.7


def riser(dur):
    n = int(dur * SR)
    t = t_axis(dur)
    x = noise(n, 99)
    out = np.zeros(n)
    seg = 16
    for k in range(seg):
        a, b = k * n // seg, (k + 1) * n // seg
        c = 300 * (1 + k * 1.1)
        out[a:b] = bp(x, c, c * 2.2)[a:b]
    f = 200 + 700 * (t / dur) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15
    return (out * 0.5 + tone) * (t / dur) ** 2


def hit_fx(big=True):
    d = 2.5
    t = t_axis(d)
    f = 36 + 70 * np.exp(-t * 8)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(len(t), 0.45)
    crash = hp(noise(len(t), 5), 3500) * env_exp(len(t), 0.5 if big else 0.25) * (0.35 if big else 0.15)
    return sub * (0.9 if big else 0.5) + crash


# ------------------------------------------------------------------ score
def build(scenes, total, force=True):
    C.MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    out_path = C.MUSIC_DIR / "music_score.wav"
    if out_path.exists() and not force:
        return out_path
    secs, events = sections(scenes)
    n = int((total + 3) * SR)
    dry = np.zeros((n, 2))
    wet_send = np.zeros((n, 2))
    duck = np.zeros(n)  # sidechain amount

    def add(buf, clip, t, gain=1.0, pan=0.0):
        i = int(round(t * SR))
        if i >= len(buf) or i < 0:
            return
        c = pan_stereo(clip, pan) if clip.ndim == 1 else clip
        m = min(len(c), len(buf) - i)
        buf[i:i + m] += c[:m] * gain

    # ---- chords (bar walk) - chord changes forced at section boundaries of big moments
    chord_i = -1
    bar_in_chord = 0
    t = 0.0
    chords = []
    force_change = {round(a / BAR) * BAR for a, b, nm in secs if nm in ("build", "peak", "philo2")}
    while t < total + 0.01:
        sname = section_at(secs, t + 0.01)
        prm = P[sname]
        if prm.get("final"):
            chords.append((t, FINAL, sname))
        else:
            if chord_i < 0 or bar_in_chord >= prm["bars"] or round(t, 3) in {round(x, 3) for x in force_change}:
                chord_i = (chord_i + 1) % len(PROG)
                bar_in_chord = 0
            chords.append((t, PROG[chord_i], sname))
            bar_in_chord += 1
        t += BAR

    # merge consecutive identical chords into spans for the pad
    spans = []
    for (t0, ch, sname) in chords:
        if spans and spans[-1][1] is ch and spans[-1][2] == sname:
            spans[-1][3] = t0 + BAR
        else:
            spans.append([t0, ch, sname, t0 + BAR])

    for t0, ch, sname, t1 in spans:
        prm = P[sname]
        a, b = max(t0, _sec_start(secs, sname, t0)), t1
        if prm["pad"] <= 0:
            continue
        for k, m in enumerate(ch[1]):
            note = pad_note(midi_hz(m), b - a, prm["cut"] * (1.0 + 0.1 * k), prm["pad"] * 0.055)
            add(dry, note, a, 1.0, pan=(k - 1.5) * 0.25)
            add(wet_send, note, a, 0.6, pan=(k - 1.5) * 0.25)

    # ---- per-step instruments
    step = BEAT / 4
    ts = np.arange(0, total, step)
    for si, t in enumerate(ts):
        sname = section_at(secs, t + 1e-4)
        prm = P[sname]
        bar_pos = si % 16
        ch = next((c for (t0, c, s) in reversed(chords) if t0 <= t + 1e-4), PROG[0])
        bass_m, voic = ch
        # keys: 8th notes, gentle broken chord
        if prm["keys"] > 0 and bar_pos % 2 == 0:
            order = [0, 2, 1, 3, 2, 1, 3, 2]
            m = voic[order[(bar_pos // 2) % len(order)] % len(voic)] + 12
            g = prm["keys"] * 0.09 * (1.0 if bar_pos % 8 == 0 else 0.7)
            e = ep_note(midi_hz(m), g)
            add(dry, e, t, 1.0, pan=0.2 if bar_pos % 4 else -0.2)
            add(wet_send, e, t, 0.9)
        # arp: 16ths
        if prm["arp"] > 0:
            order = [0, 1, 2, 3, 2, 1, 3, 1, 0, 2, 3, 2, 1, 3, 2, 3]
            m = voic[order[bar_pos] % len(voic)] + (12 if bar_pos % 8 < 6 else 24)
            if prm.get("final"):
                if bar_pos % 4:
                    continue
            g = prm["arp"] * 0.07 * (1.0 if bar_pos % 4 == 0 else 0.75)
            pl = pluck(midi_hz(m), g, prm["cut"])
            add(dry, pl, t, 1.0, pan=0.35 if bar_pos % 2 else -0.35)
            add(wet_send, pl, t, 0.5)
        # bass: 8ths (skip the downbeat eighth for pump)
        if prm["bass"] > 0 and bar_pos % 2 == 0:
            oct_ = 12 if bar_pos in (6, 14) else 0
            add(dry, bass_note(midi_hz(bass_m + oct_), prm["bass"] * 0.30), t)
        # drums
        if prm["kick"] == "four" and bar_pos % 4 == 0 or prm["kick"] == "half" and bar_pos in (0, 8):
            add(dry, kick(), t, 0.85)
            i = int(t * SR)
            duck[i:i + int(0.25 * SR)] = np.maximum(duck[i:i + int(0.25 * SR)], np.exp(-np.arange(min(int(0.25 * SR), n - i)) / (0.09 * SR)))
        if prm["hats"] == "8" and bar_pos % 4 == 2:
            add(dry, hat(), t, 0.22, pan=0.3)
        if prm["hats"] == "16" and bar_pos % 2 == 0:
            add(dry, hat(bar_pos % 4 == 2), t, 0.16 if bar_pos % 4 else 0.10, pan=0.3)
        if prm["clap"] > 0 and bar_pos in (4, 12):
            c = clap()
            add(dry, c, t, prm["clap"] * 0.6)
            add(wet_send, c, t, prm["clap"] * 0.4)
        if prm.get("roll"):
            # snare/clap roll accelerating into the drop
            sec_end = next(b for a, b, nm in secs if nm == sname and a <= t < b)
            left = sec_end - t
            if left < 2.0 and (bar_pos % 2 == 0 or left < 1.0):
                add(dry, clap(), t, 0.10 + 0.25 * (1 - left / 2.0))

    # ---- one-shot events: risers & hits
    for a, b, nm in secs:
        if nm == "rise":
            r = riser(b - a)
            add(dry, r, a, 0.5)
            add(wet_send, r, a, 0.4)
    for t, kind in events:
        if kind == "hit":
            h = hit_fx(True)
            add(dry, h, t, 0.55)
            add(wet_send, h, t, 0.5)
        elif kind == "hit_soft":
            add(dry, hit_fx(False), t, 0.35)
        elif kind == "riser_short":
            r = riser(1.5)
            add(dry, r, t, 0.35)

    # ---- mix bus: sidechain, reverb, master
    sc = 1 - 0.45 * duck
    dry *= sc[:, None]
    wet = convolve_stereo(wet_send, reverb_ir(2.4))
    mix = dry + wet * 0.35
    mix = hp(mix, 30)
    # fade tail after the power-down
    end_t = next((t for t, k in events if k == "end"), total)
    fade = np.ones(n)
    i0, i1 = int(end_t * SR), int((end_t + 0.6) * SR)
    fade[i0:i1] = np.linspace(1, 0, i1 - i0)
    fade[i1:] = 0
    mix *= fade[:, None]
    mix = mix[: int(total * SR)]
    mix = soft_limit(mix / (np.abs(mix).max() + 1e-9) * 1.1, 0.95) * 0.9
    write_wav(out_path, mix)
    return out_path


def _sec_start(secs, name, t):
    for a, b, n in secs:
        if n == name and a <= t + BAR and t < b:
            return a
    return t
