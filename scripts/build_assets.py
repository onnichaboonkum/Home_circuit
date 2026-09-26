"""Generate all conceptual still plates, product images and the temporary logo.

Existing files are kept (so replaced / real assets survive) unless --force.
Usage:  python -m scripts.build_assets [--force] [--only name1,name2] [--preview]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config as C          # noqa: E402
from src import plates               # noqa: E402
from src.engine import logo, product  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--preview", action="store_true", help="write flattened previews to output/build/previews")
    a = ap.parse_args()
    only = [x for x in a.only.split(",") if x]
    C.IMAGES.mkdir(parents=True, exist_ok=True)
    prev = C.BUILD / "previews"
    prev.mkdir(parents=True, exist_ok=True)
    for name in plates.REGISTRY:
        if only and name not in only:
            continue
        exists = any(C.IMAGES.glob(f"{name}__*.png"))
        if exists and not a.force:
            print(f"  keep   {name}")
            continue
        for old in C.IMAGES.glob(f"{name}__*.png"):
            old.unlink()
        layers = plates.build(name)
        for lname, im in layers.items():
            im.save(C.IMAGES / f"{name}__{lname}.png", optimize=False, compress_level=3)
        print(f"  built  {name}  ({', '.join(layers)})")
        if a.preview:
            from PIL import Image
            flat = Image.new("RGBA", layers["bg"].size, (0, 0, 0, 255))
            for k in ("bg", "mid", "fx", "fg"):
                if k in layers:
                    flat.alpha_composite(layers[k])
            flat.convert("RGB").resize((960, 540)).save(prev / f"{name}.jpg", quality=85)
    if not only or "products" in only:
        product.build_all(force=a.force)
    if not only or "logo" in only:
        logo.build_logo_files(force=a.force)


if __name__ == "__main__":
    main()
