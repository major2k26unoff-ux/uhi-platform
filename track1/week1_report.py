"""Print answers 1-6 for the Track 1 Week 1 handover.

Run from the repository root:
    python .\\track1\\week1_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

from config import BHUBANESWAR_BBOX, CITY_DIR, PREVIEW_DIR


TIFF_LAYERS = ("rgb", "ndvi", "ndbi", "ndwi", "lst")


def readable_size(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    raise AssertionError("unreachable")


def tiff_details(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    with rasterio.open(path) as source:
        values = source.read(masked=True).compressed()
        values = values[np.isfinite(values)]
        return {
            "width": source.width,
            "height": source.height,
            "pixel_size": (abs(source.transform.a), abs(source.transform.e)),
            "crs": source.crs,
            "bounds": source.bounds,
            "stats": None if not values.size else (values.min(), values.max(), values.mean()),
        }


def main() -> None:
    files = {layer: CITY_DIR / f"{layer}.tif" for layer in TIFF_LAYERS}
    details = {layer: tiff_details(path) for layer, path in files.items()}

    print("1. Exact bounding box in config.py")
    print("   Earth Engine order [west, south, east, north]:", BHUBANESWAR_BBOX)

    print("\n2. Width x height, pixel size, and CRS of each .tif file")
    for layer, detail in details.items():
        if detail is None:
            print(f"   {layer}.tif: missing")
            continue
        x_size, y_size = detail["pixel_size"]
        print(
            f"   {layer}.tif: {detail['width']} x {detail['height']} px; "
            f"pixel size {x_size:g} x {y_size:g}; CRS {detail['crs']}"
        )

    print("\n3. Actual corners of each .tif file")
    print("   Order: [west, south, east, north]")
    for layer, detail in details.items():
        if detail is None:
            print(f"   {layer}.tif: missing")
            continue
        bounds = detail["bounds"]
        print(
            f"   {layer}.tif: [{bounds.left:.6f}, {bounds.bottom:.6f}, "
            f"{bounds.right:.6f}, {bounds.top:.6f}]"
        )

    print("\n4. Minimum, maximum, and mean of each layer")
    for layer, detail in details.items():
        if detail is None or detail["stats"] is None:
            print(f"   {layer}.tif: missing or has no valid pixels")
            continue
        minimum, maximum, mean = detail["stats"]
        print(f"   {layer}.tif: min {minimum:.4f}; max {maximum:.4f}; mean {mean:.4f}")

    print("\n5. File size of each .tif and PNG")
    for layer, path in files.items():
        print(f"   {path.name}: {readable_size(path) if path.exists() else 'missing'}")
    for layer in TIFF_LAYERS:
        path = PREVIEW_DIR / f"{layer}.png"
        if path.exists():
            with Image.open(path) as image:
                print(f"   {path.name}: {readable_size(path)} ({image.width} x {image.height} px)")
        else:
            print(f"   {path.name}: missing")

    print("\n6. meta.json existence and bounds order")
    meta_path = CITY_DIR / "meta.json"
    if not meta_path.exists():
        print("   meta.json: missing")
    else:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        print("   meta.json: exists")
        print("   bounds:", metadata.get("bounds"))
        print("   bounds order: [south, west, north, east] (Leaflet order)")


if __name__ == "__main__":
    main()
