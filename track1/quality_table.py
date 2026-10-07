"""Week 3 data quality table: one row per preset city, read straight from the files on disk.
From the repository root, with the Track 1 environment active:
    python .\\track1\\quality_table.py
Writes data/quality_table.md.
"""
import json
from pathlib import Path
import numpy as np
import rasterio
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LAYERS = ["rgb", "ndvi", "ndbi", "ndwi", "lst"]
def valid_percent(path):
    """Share of pixels that hold a real value (not cloud-masked or empty)."""
    with rasterio.open(path) as src:
        band = src.read(1, masked=True).astype("float32").filled(np.nan)
    return round(100 * float(np.isfinite(band).mean()), 1)
def size_mb(folder):
    return round(sum(f.stat().st_size for f in folder.rglob("*") if f.is_file()) / 1e6, 1)
def main():
    cities = json.loads((ROOT / "presets.json").read_text(encoding="utf-8-sig"))
    lines = [
        "| City | Group | Optical dates | Heat dates | S2 images | Landsat scenes | Pixel m | Size px | "
        "LST mean C | LST min C | LST max C | NDVI mean | Valid LST % | Valid NDVI % | Folder MB |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    problems = []
    for city in cities:
        folder = DATA / city["slug"]
        meta_path = folder / "meta.json"
        if not meta_path.is_file():
            lines.append(f"| {city['name']} | {city['group']} | not processed |" + " - |" * 12)
            problems.append(f"{city['name']}: not processed")
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        stats = meta["stats"]
        missing = [name for name in LAYERS if not (folder / f"{name}.tif").is_file()]
        if missing:
            problems.append(f"{city['name']}: missing {', '.join(missing)}")
        lst_ok = valid_percent(folder / "lst.tif") if "lst" not in missing else "-"
        ndvi_ok = valid_percent(folder / "ndvi.tif") if "ndvi" not in missing else "-"
        if isinstance(lst_ok, float) and lst_ok < 80:
            problems.append(f"{city['name']}: only {lst_ok}% of heat pixels are valid (clouds)")
        lines.append(
            f"| {city['name']} | {city['group']} | "
            f"{meta.get('date_start')} to {meta.get('date_end')} | "
            f"{meta.get('lst_date_start')} to {meta.get('lst_date_end')} | "
            f"{meta.get('sentinel_images', '-')} | {meta.get('landsat_scenes', '-')} | "
            f"{meta.get('scale_m', '-')} | {meta.get('width_px', '-')} x {meta.get('height_px', '-')} | "
            f"{stats['lst_mean_c']} | {stats['lst_min_c']} | {stats['lst_max_c']} | {stats['ndvi_mean']} | "
            f"{lst_ok} | {ndvi_ok} | {size_mb(folder)} |"
        )
    lines += ["", "Problems found:" if problems else "Problems found: none."]
    lines += [f"- {p}" for p in problems]
    destination = DATA / "quality_table.md"
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved: {destination}")
if __name__ == "__main__":
    main()
