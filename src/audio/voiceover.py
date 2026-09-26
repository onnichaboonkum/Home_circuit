"""Thai voice-over: scratch TTS (espeak-ng) fitted to each VO slot.

This environment has no access to neural Thai TTS, so a *temporary* guide
voice is synthesised locally with espeak-ng. Every line lives in
``audio/voiceover/<id>.wav``: record the real narration, export 16-bit WAV with
the same file names, delete ``audio/voiceover/_scratch.json`` (or the ids in
it) and re-run the render - the timeline, ducking and subtitles adapt to the
new durations automatically.
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from .. import config as C
from .dsp import SR, hp, lp, read_wav, write_wav

VOICE = "th+m3"
PITCH = 38
SPEEDS = list(range(165, 281, 10))


def _trim(x, thr=0.012, pad=0.04):
    a = np.abs(x).max(axis=1) if x.ndim > 1 else np.abs(x)
    idx = np.where(a > thr)[0]
    if len(idx) == 0:
        return x
    i0 = max(0, idx[0] - int(pad * SR))
    i1 = min(len(x), idx[-1] + int(pad * SR))
    return x[i0:i1]


def _espeak(text, speed, out):
    subprocess.run(["espeak-ng", "-v", VOICE, "-s", str(speed), "-p", str(PITCH), "-g", "2", "-w", str(out), text],
                   check=True, capture_output=True)


def synth_line(text, max_dur):
    """Return mono float array at SR, spoken as fast as needed to fit max_dur."""
    if not shutil.which("espeak-ng"):
        raise RuntimeError("espeak-ng not installed")
    with tempfile.TemporaryDirectory() as d:
        best = None
        for sp in SPEEDS:
            p = Path(d) / f"v{sp}.wav"
            _espeak(text, sp, p)
            x = _trim(read_wav(p)[:, 0])
            best = x
            if len(x) / SR <= max_dur:
                break
    # warm it up a little: remove rumble, soften the synthetic top end, gentle saturation
    x = hp(best, 90)
    x = lp(x, 6500)
    x = np.tanh(x * 1.6) / np.tanh(1.6)
    return x / (np.abs(x).max() + 1e-9) * 0.9


def build(scenes, force=False):
    """Create / reuse VO clips. Returns list of dicts with global timing."""
    C.VO_DIR.mkdir(parents=True, exist_ok=True)
    scratch_file = C.VO_DIR / "_scratch.json"
    scratch = set(json.loads(scratch_file.read_text())) if scratch_file.exists() else set()
    items = []
    script = []
    for sc in scenes:
        for v in sc.vo:
            path = C.VO_DIR / f"{v.id}.wav"
            if force or not path.exists():
                x = synth_line(v.tts or v.text, v.max_dur)
                write_wav(path, x)
                scratch.add(v.id)
            x = read_wav(path)
            dur = len(x) / SR
            items.append({"id": v.id, "start": sc.start + v.t, "dur": dur, "text": v.text,
                          "sub_lines": v.sub_lines, "path": str(path), "scratch": v.id in scratch,
                          "slot": v.max_dur, "scene": sc.name})
            script.append((sc.name, v, sc.start + v.t))
    scratch_file.write_text(json.dumps(sorted(scratch), indent=1))
    _write_script(script)
    return items


def _write_script(script):
    lines = ["# Home Circuit — Thai voice-over script (for the real narration session)", "",
             "Voice: professional, warm, confident, not aggressive, not overly commercial.", "",
             "| ID | Scene | Starts at | Max length | Line |", "|---|---|---|---|---|"]
    for scn, v, t in script:
        m, s = divmod(t, 60)
        lines.append(f"| {v.id} | {scn} | {int(m)}:{s:05.2f} | {v.max_dur:.1f}s | {v.text} |")
    lines += ["", "Deliver each line as `audio/voiceover/<ID>.wav` (16-bit PCM WAV, any sample rate).",
              "Remove the ID from `_scratch.json` so the renderer knows it is final."]
    (C.VO_DIR / "VO_SCRIPT.md").write_text("\n".join(lines) + "\n")
