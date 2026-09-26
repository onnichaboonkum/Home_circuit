"""Build 'HC Thai Sans' = Noto Sans (Latin) + Noto Sans Thai merged into one font,
so Thai lines that contain English words / digits / punctuation render with a
single consistent typeface (PIL typography + libass subtitles).

Requires the system Noto fonts (Debian/Ubuntu: fonts-noto-core) and fonttools.
The merged files are committed in assets/fonts, so this only needs re-running
if you want to change the source fonts.
"""
from pathlib import Path

from fontTools.merge import Merger

NOTO = Path("/usr/share/fonts/truetype/noto")
OUT = Path(__file__).resolve().parents[1] / "assets" / "fonts"

for weight in ("Regular", "Medium", "SemiBold"):
    merged = Merger().merge([str(NOTO / f"NotoSans-{weight}.ttf"), str(NOTO / f"NotoSansThai-{weight}.ttf")])
    family = "HC Thai Sans" if weight == "Regular" else f"HC Thai Sans {weight}"
    for rec in merged["name"].names:
        if rec.nameID in (1, 16):
            rec.string = family
        elif rec.nameID == 4:
            rec.string = f"HC Thai Sans {weight}"
        elif rec.nameID == 6:
            rec.string = f"HCThaiSans-{weight}"
    merged.save(str(OUT / f"HCThaiSans-{weight}.ttf"))
    print("wrote", OUT / f"HCThaiSans-{weight}.ttf")
