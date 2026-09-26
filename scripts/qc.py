"""Quality checks on the rendered video: format, duration, streams, thumbnails."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C  # noqa: E402

out = C.OUTPUT / C.FINAL_NAME
info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(out)],
                                 capture_output=True, text=True, check=True).stdout)
v = next(s for s in info["streams"] if s["codec_type"] == "video")
a = next(s for s in info["streams"] if s["codec_type"] == "audio")
dur = float(info["format"]["duration"])
fps = eval(v["r_frame_rate"])
checks = {
    "file": str(out),
    "size_MB": round(int(info["format"]["size"]) / 1e6, 1),
    "duration_s": round(dur, 3),
    "duration_ok (105-120 s)": 105 <= dur <= 120.5,
    "resolution": f'{v["width"]}x{v["height"]}',
    "resolution_ok": (v["width"], v["height"]) == (1920, 1080),
    "fps": fps, "fps_ok": abs(fps - 30) < 0.01,
    "video_codec": v["codec_name"], "h264_ok": v["codec_name"] == "h264",
    "pix_fmt": v["pix_fmt"],
    "audio_codec": a["codec_name"], "aac_ok": a["codec_name"] == "aac",
    "audio_rate": a["sample_rate"], "audio_channels": a["channels"],
    "av_duration_delta_s": round(abs(float(v.get("duration", dur)) - float(a.get("duration", dur))), 3),
}
for k, val in checks.items():
    print(f"{k:28} {val}")
# contact sheet, one frame every 4 seconds
sheet = C.BUILD / "qc_contact_sheet.jpg"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-vf",
                "fps=1/4,scale=384:216,tile=6x5", "-frames:v", "1", str(sheet)], check=True)
print("contact sheet ->", sheet)
