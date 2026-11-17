"""Import an externally produced voice-over (one file, all lines) into the reel.

The file is cut into the five script lines (v0-v4) at the pauses listed in PHRASES,
and approximate word timings are written so build_timeline() can sync the pop-ups.
Phrase times were measured with ffmpeg silencedetect on the uploaded take:

    ffmpeg -i audio/vo/source_voice.mp3 -af silencedetect=noise=-38dB:d=0.12 -f null -

Usage:  python3 insurance_reel/import_vo.py [path/to/voice.mp3]
then:   python3 insurance_reel/reel.py --no-vo
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from src.audio import dsp  # noqa: E402

VO_DIR = HERE / "audio" / "vo"
SOURCE = VO_DIR / "source_voice.mp3"

# segment id -> (cut start, cut end, [(phrase start, phrase end, phrase text), ...])  times in the source file
PHRASES = {
    "v0": (0.15, 3.85, [(0.26, 1.71, "มีประกันสุขภาพแล้ว"), (1.85, 3.71, "ทำไมยังต้องมีประกันโรคร้าย")]),
    "v1": (3.98, 11.38, [(4.31, 5.18, "ประกันสุขภาพ"), (5.36, 6.82, "มีไว้สำหรับค่ารักษา"), (7.03, 7.63, "ค่าห้อง"),
                         (7.78, 8.37, "ค่าหมอ"), (8.60, 9.30, "ค่ายา"), (9.46, 11.24, "และรักษาพยาบาลตามเงื่อนไข")]),
    "v2": (11.48, 23.55, [(11.61, 13.20, "ส่วนประกันโรคร้ายแรง"), (13.34, 14.92, "มีไว้สำหรับค่าใช้จ่ายแฝง"),
                          (15.16, 15.51, "เช่น"), (15.79, 16.70, "ค่าเดินทาง"), (16.87, 17.81, "ค่าปรับปรุงบ้าน"),
                          (18.09, 19.80, "รถเข็นหรืออุปกรณ์ช่วยเหลือ"),
                          (20.12, 23.41, "รายได้ที่หายไปและค่ารักษาบางส่วนที่อยู่นอกสิทธิ์")]),
    "v3": (23.85, 28.15, [(23.98, 25.47, "เพราะเมื่อป่วยหนักหนึ่งครั้ง"), (25.61, 28.09, "ค่าใช้จ่ายไม่ได้จบแค่ที่โรงพยาบาล")]),
    "v4": (28.15, 37.00, [(28.21, 29.21, "อย่ารอให้ป่วยก่อน"), (29.39, 30.56, "แล้วค่อยรู้ว่าไม่พอ"),
                          (30.77, 34.41, "มีทั้งประกันสุขภาพและประกันโรคร้ายถึงจะคุ้มครองครบ"),
                          (34.66, 36.83, "ทักแชทมาเช็กความคุ้มครองของคุณได้วันนี้")]),
}


def main():
    if len(sys.argv) > 1:
        VO_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(sys.argv[1], SOURCE)
    full = VO_DIR / "_source.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(SOURCE), "-ac", "1", "-ar", str(dsp.SR), str(full)],
                   check=True)
    x = dsp.read_wav(full)[:, 0]
    for sid, (c0, c1, phrases) in PHRASES.items():
        seg = x[int(c0 * dsp.SR):int(c1 * dsp.SR)].copy()
        f = int(0.02 * dsp.SR)
        seg[:f] *= [i / f for i in range(f)]
        seg[-f:] *= [1 - i / f for i in range(f)]
        dsp.write_wav(VO_DIR / f"{sid}.wav", seg)
        # character-level timings spread evenly across each phrase (lets build_timeline find any keyword)
        words = []
        for p0, p1, txt in phrases:
            n = len(txt)
            for i, ch in enumerate(txt):
                words.append({"text": ch, "start": round(p0 - c0 + (p1 - p0) * i / n, 3)})
        (VO_DIR / f"{sid}.json").write_text(json.dumps(
            {"text": "".join(p[2] for p in phrases), "voice": "uploaded (Sofia, AI voice)", "duration": len(seg) / dsp.SR,
             "words": words}, ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"{sid}: {len(seg) / dsp.SR:.2f}s")
    full.unlink()
    for old in VO_DIR.glob("v*.mp3"):
        old.unlink()


if __name__ == "__main__":
    main()
