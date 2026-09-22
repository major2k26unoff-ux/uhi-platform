"""Write the exact cross-track metadata contract after all GeoTIFFs exist."""

import json

import numpy as np
import rasterio

from config import (BHUBANESWAR_BBOX, CITY_DIR, CITY_SLUG, DATE_END, DATE_START,
                    DISPLAY_NAME)


def raster_stats(path):
    with rasterio.open(path) as source:
        values = source.read(1, masked=True).compressed()
        width, height = source.width, source.height
    if values.size == 0:
        raise RuntimeError(f"{path} has no valid pixels")
    return float(values.min()), float(values.max()), float(values.mean()), width, height


def main() -> None:
    lst_min, lst_max, lst_mean, width, height = raster_stats(CITY_DIR / "lst.tif")
    _, _, ndvi_mean, _, _ = raster_stats(CITY_DIR / "ndvi.tif")
    west, south, east, north = BHUBANESWAR_BBOX
    metadata = {
        "city": CITY_SLUG,
        "display_name": DISPLAY_NAME,
        "bounds": [south, west, north, east],
        "crs": "EPSG:4326",
        "date_start": DATE_START,
        "date_end": DATE_END,
        "width_px": width,
        "height_px": height,
        "layers": ["rgb", "ndvi", "ndbi", "ndwi", "lst"],
        "stats": {"lst_min_c": round(lst_min, 1), "lst_max_c": round(lst_max, 1),
                  "lst_mean_c": round(lst_mean, 1), "ndvi_mean": round(ndvi_mean, 2)},
    }
    destination = CITY_DIR / "meta.json"
    destination.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(destination.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
