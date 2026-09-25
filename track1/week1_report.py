"""Print the Track 1 Week 1 handover answers that can be read from files.

Run from the repository root:
    python .\\track1\\week1_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

from config import (BHUBANESWAR_BBOX, CITY_DIR, CITY_SLUG, DATA_DIR,
                    DISPLAY_NAME, PREVIEW_DIR)


TIFF_LAYERS = ("rgb", "ndvi", "ndbi", "ndwi", "lst")
PNG_LAYERS = TIFF_LAYERS


def readable_size(path: Path) -> str:
    """Return a compact, human-readable file size."""
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    raise AssertionError("unreachable")


def raster_values(source: rasterio.io.DatasetReader) -> np.ndarray:
    """Read all finite, unmasked values across every band."""
    data = source.read(masked=True)
    values = data.compressed()
    return values[np.isfinite(values)]


def report_tiff(path: Path) -> None:
    with rasterio.open(path) as source:
        print(f"\n{path.name} ({readable_size(path)})")
        print(f"  dimensions: {source.width} x {source.height} px; bands: {source.count}")
        print(f"  pixel size: {abs(source.transform.a):g} x {abs(source.transform.e):g}")
        print(f"  CRS: {source.crs}")
        print(
            "  corners [west, south, east, north]: "
            f"[{source.bounds.left:.6f}, {source.bounds.bottom:.6f}, "
            f"{source.bounds.right:.6f}, {source.bounds.top:.6f}]"
        )
        values = raster_values(source)
        if values.size:
            print(
                "  values: "
                f"min={values.min():.4f}, max={values.max():.4f}, "
                f"mean={values.mean():.4f}"
            )
        else:
            print("  values: no valid pixels")


def report_png(path: Path) -> None:
    with Image.open(path) as image:
        print(f"  {path.name}: {image.width} x {image.height} px, {readable_size(path)}")


def report_meta() -> None:
    path = CITY_DIR / "meta.json"
    print("\nmeta.json")
    if not path.exists():
        print("  missing - run write_meta.py after all TIFF files are present")
        return
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"  invalid JSON: {error}")
        return
    print(f"  exists: yes ({readable_size(path)})")
    print(f"  bounds: {metadata.get('bounds')}")
    print("  bounds order: [south, west, north, east] (Leaflet order)")
    print(f"  stats: {metadata.get('stats')}")


def main() -> None:
    west, south, east, north = BHUBANESWAR_BBOX
    print("TRACK 1 - WEEK 1 REPORT")
    print(f"City: {DISPLAY_NAME} ({CITY_SLUG})")
    print(f"Output directory: {CITY_DIR}")
    print(f"Earth Engine bounding box [west, south, east, north]: {BHUBANESWAR_BBOX}")
    print(f"Leaflet bounding box [south, west, north, east]: [{south}, {west}, {north}, {east}]")

    print("\nGeoTIFF files")
    for layer in TIFF_LAYERS:
        path = CITY_DIR / f"{layer}.tif"
        if path.exists():
            report_tiff(path)
        else:
            print(f"\n{path.name}: missing")

    print("\nPNG preview files")
    for layer in PNG_LAYERS:
        path = PREVIEW_DIR / f"{layer}.png"
        if path.exists():
            report_png(path)
        else:
            print(f"  {path.name}: missing")

    report_meta()
    print("\nManual answers still needed: Earth Engine project ID, scene counts, any "
          "date/cloud changes, total duration, errors, RGB scale, laptop/OS/Python, "
          "Drive upload status, and script style.")


if __name__ == "__main__":
    main()
