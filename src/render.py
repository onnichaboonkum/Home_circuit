"""Render the Home Circuit company story draft.

    python -m src.render                      # full render (video + audio + subtitles + mux)
    python -m src.render --scenes 03,05       # re-render only some scene clips, then re-mux
    python -m src.render --preview 12.3,40    # write PNG stills at global times (seconds)
    python -m src.render --audio-only         # rebuild VO / music / SFX mix + subtitles, re-mux

Scene clips are cached in output/build/chunks; audio stems in audio/*.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from . import config as C
from .engine.canvas import finish
from .timeline import load_scenes, total_duration

CHUNK = 60  # frames per parallel render job
_SCENES = None


def _scenes():
    global _SCENES
    if _SCENES is None:
        _SCENES = load_scenes()
    return _SCENES


def scene_frames(sc):
    return int(round(sc.duration * C.FPS))


def frame_offsets(scenes):
    offs, acc = [], 0
    for sc in scenes:
        offs.append(acc)
        acc += scene_frames(sc)
    return offs, acc


def render_frame(sc, f_local, f_global):
    t = f_local / C.FPS
    frame, grade = sc.render(t)
    return finish(frame, f_global, grade=grade, grain=sc.grain)


def ffmpeg_writer(path, crf=C.X264_CRF_SCENES):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{C.W}x{C.H}", "-r", str(C.FPS), "-i", "-", "-c:v", "libx264",
           "-preset", C.X264_PRESET, "-crf", str(crf), "-pix_fmt", "yuv420p",
           "-g", str(C.FPS * 2), "-bf", "2", "-r", str(C.FPS), str(path)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def render_chunk(si, f0, f1, out):
    scenes = _scenes()
    sc = scenes[si]
    offs, _ = frame_offsets(scenes)
    p = ffmpeg_writer(out)
    t0 = time.time()
    for f in range(f0, f1):
        arr = render_frame(sc, f, offs[si] + f)
        p.stdin.write(arr.tobytes())
    p.stdin.close()
    p.wait()
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {out}")
    return out, f1 - f0, time.time() - t0


def render_video(scenes, only=None, jobs=4):
    chunks_dir = C.BUILD / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    tasks, all_chunks = [], []
    for si, sc in enumerate(scenes):
        n = scene_frames(sc)
        for f0 in range(0, n, CHUNK):
            f1 = min(n, f0 + CHUNK)
            out = chunks_dir / f"{sc.name}_{f0:05d}_{f1:05d}.mp4"
            all_chunks.append(out)
            if only and not any(sc.name.startswith(o) for o in only) and out.exists():
                continue
            tasks.append((si, f0, f1, out))
    # remove stale chunks of re-rendered scenes (duration changes)
    keep = {c.name for c in all_chunks}
    for c in chunks_dir.glob("*.mp4"):
        if c.name not in keep:
            c.unlink()
    print(f"rendering {len(tasks)} chunks ({sum(t[2] - t[1] for t in tasks)} frames) with {jobs} jobs")
    t0 = time.time()
    done = 0
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        futs = [ex.submit(render_chunk, *t) for t in tasks]
        for fu in as_completed(futs):
            out, nf, dt = fu.result()
            done += nf
            print(f"  {Path(out).name}  {nf} fr  {dt:.1f}s   [{done} frames, {time.time() - t0:.0f}s]", flush=True)
    lst = C.BUILD / "chunks.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in all_chunks))
    video = C.BUILD / "video_nosound.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(video)], check=True)
    return video


def build_audio(scenes, force_vo=False, keep_music=False):
    from .audio import mix, music, sfx, subtitles, voiceover
    total = total_duration(scenes)
    vo_items = voiceover.build(scenes, force=force_vo)
    sfx.build_library()
    music_path = music.build(scenes, total, force=not keep_music)
    mix_path = mix.mix(scenes, total, vo_items, music_path)
    subs = subtitles.build(scenes, vo_items)
    return mix_path, subs


def mux(video, audio, subs_ass, burn=True):
    C.OUTPUT.mkdir(parents=True, exist_ok=True)
    out = C.OUTPUT / C.FINAL_NAME
    vf = []
    if burn:
        vf = ["-vf", f"ass={subs_ass.as_posix()}:fontsdir={C.FONTS.as_posix()}"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio), *vf,
           "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "libx264", "-preset", C.X264_PRESET, "-crf", str(C.X264_CRF_FINAL), "-maxrate", C.FINAL_MAXRATE, "-bufsize", "10M", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-r", str(C.FPS), "-c:a", "aac", "-b:a", C.AUDIO_BITRATE, "-ar", str(C.AUDIO_SR),
           "-movflags", "+faststart", "-shortest", str(out)]
    subprocess.run(cmd, check=True)
    return out


def preview(times, scenes):
    from PIL import Image
    offs, _ = frame_offsets(scenes)
    d = C.BUILD / "stills"
    d.mkdir(parents=True, exist_ok=True)
    for gt in times:
        f = int(round(gt * C.FPS))
        for si, sc in enumerate(scenes):
            n = scene_frames(sc)
            if offs[si] <= f < offs[si] + n:
                arr = render_frame(sc, f - offs[si], f)
                p = d / f"still_{gt:07.2f}_{sc.name}.png"
                Image.fromarray(arr).save(p)
                print(p)
                break


def write_manifest(scenes, vo_items):
    offs, total = frame_offsets(scenes)
    data = {"fps": C.FPS, "size": [C.W, C.H], "total_seconds": total / C.FPS, "scenes": []}
    for sc, o in zip(scenes, offs):
        data["scenes"].append({"name": sc.name, "start": o / C.FPS, "duration": sc.duration,
                               "shots": [{"name": s.name, "start": o / C.FPS + t, "duration": s.dur}
                                         for s, t in zip(sc.shots, sc.cut_times())]})
    data["voiceover"] = [{"id": v["id"], "start": v["start"], "duration": v["dur"], "text": v["text"]} for v in vo_items]
    (C.OUTPUT / "timeline_manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default="", help="comma list of scene prefixes to (re)render, e.g. 03,05")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--preview", default="")
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--force-vo", action="store_true", help="regenerate scratch TTS even if VO files exist")
    ap.add_argument("--no-burn-subs", action="store_true")
    ap.add_argument("--keep-music", action="store_true", help="use existing audio/music/music_score.wav (e.g. licensed track)")
    a = ap.parse_args()
    scenes = _scenes()
    print(f"timeline: {len(scenes)} scenes, {total_duration(scenes):.2f}s")
    for sc in scenes:
        print(f"  {sc.name:<24} start {sc.start:7.2f}  dur {sc.duration:6.2f}")
    if a.preview:
        preview([float(x) for x in a.preview.split(",")], scenes)
        return
    only = [x for x in a.scenes.split(",") if x]
    video = C.BUILD / "video_nosound.mp4"
    if not a.audio_only or not video.exists():
        video = render_video(scenes, only=only, jobs=a.jobs)
    mix_path, subs = build_audio(scenes, force_vo=a.force_vo, keep_music=a.keep_music)
    out = mux(video, mix_path, subs["ass"], burn=not a.no_burn_subs)
    # sidecar subtitles next to the video
    shutil.copy(subs["srt"], C.OUTPUT / C.FINAL_NAME.replace(".mp4", ".th.srt"))
    shutil.copy(subs["ass"], C.OUTPUT / C.FINAL_NAME.replace(".mp4", ".th.ass"))
    write_manifest(scenes, subs["vo_items"])
    print("done ->", out)


if __name__ == "__main__":
    main()
