"""Cut the official Home Circuit logo (assets/logo/hc_logo_source.jpg, on white)
into transparent PNG parts used by the ending scene:

    hc_logo_official.png   full lock-up (mark + HOME CIRCUIT + STEM LAB)
    hc_logo_mark.png       house/circuit mark
    hc_logo_word.png       HOME CIRCUIT
    hc_logo_sub.png        STEM LAB

White is removed by "un-mixing" it (alpha = how far a pixel is from white), which
keeps the anti-aliased edges and the green gradient exact.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C  # noqa: E402


def unwhite(img):
    a = np.asarray(img.convert("RGB"), np.float32) / 255.0
    alpha = np.clip((1.0 - a.min(-1)) * 1.04, 0, 1)
    alpha[alpha < 0.03] = 0
    safe = np.maximum(alpha, 1e-4)[..., None]
    rgb = np.clip((a - (1 - safe)) / safe, 0, 1)
    out = np.dstack([rgb, alpha]) * 255
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def main():
    src = Image.open(C.LOGO_DIR / "hc_logo_source.jpg")
    full = unwhite(src)
    a = np.asarray(full.getchannel("A")) > 8
    rows = a.any(1)
    runs, start = [], None
    for y, v in enumerate(rows):
        if v and start is None:
            start = y
        if not v and start is not None:
            runs.append((start, y))
            start = None
    if start is not None:
        runs.append((start, len(rows)))
    runs = [r for r in runs if r[1] - r[0] > 10]
    assert len(runs) >= 3, runs
    bb = full.getbbox()
    full.crop(bb).save(C.LOGO_DIR / "hc_logo_official.png")
    for name, (y0, y1) in zip(("mark", "word", "sub"), runs[:3]):
        part = full.crop((0, y0 - 2, full.width, y1 + 2))
        part.crop(part.getbbox()).save(C.LOGO_DIR / f"hc_logo_{name}.png")
        print("wrote", name, part.getbbox())


if __name__ == "__main__":
    main()
