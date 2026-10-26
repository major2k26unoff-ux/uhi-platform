"""Redraw preview/lst.png for areas already on disk with the per-area colour range.

No Earth Engine needed: it reads data/<slug>/lst.tif and rewrites only
preview/lst.png and the lst_preview_c field in meta.json.
From the repository root:
    python .\\track1\\refresh_lst_previews.py            (all areas)
    python .\\track1\\refresh_lst_previews.py phalodi    (one area)
"""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from PIL import Image

from lst_scale import lst_range

DATA = Path(__file__).resolve().parent.parent / "data"
MAX_PNG_SIDE = 1600          # same as pipeline.py


def save_png(arr, path, vmin, vmax):
    """Same colours, transparency and size rule as pipeline.save_png()."""
    alpha = np.where(np.isnan(arr), 0, 210).astype(np.uint8)
    norm = np.nan_to_num(np.clip((arr - vmin) / (vmax - vmin), 0, 1))
    rgba = (plt.get_cmap("inferno")(norm) * 255).astype(np.uint8)
    rgba[..., 3] = alpha
    img = Image.fromarray(rgba)
    if max(img.size) > MAX_PNG_SIDE:
        ratio = MAX_PNG_SIDE / max(img.size)
        img = img.resize((round(img.width * ratio), round(img.height * ratio)), Image.Resampling.NEAREST)
    img.save(path, optimize=True)


def refresh(folder):
    with rasterio.open(folder / "lst.tif") as src:
        arr = src.read(1, masked=True).astype("float32").filled(np.nan)
    low, high = lst_range(arr)
    save_png(arr, folder / "preview" / "lst.png", low, high)
    meta_path = folder / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    meta["lst_preview_c"] = [low, high]
    tmp = meta_path.with_name("meta.json.tmp")
    tmp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    tmp.replace(meta_path)
    print(f"{folder.name:16s} {low}-{high} C")


def main():
    names = sys.argv[1:]
    folders = [DATA / n for n in names] if names else sorted(DATA.iterdir())
    for folder in folders:
        if (folder / "lst.tif").exists() and (folder / "meta.json").exists():
            refresh(folder)


if __name__ == "__main__":
    main()
