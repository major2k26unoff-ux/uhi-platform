"""Compute Sentinel-2 vegetation, built-up, and water index GeoTIFFs."""

import geemap

from config import CITY_DIR
from ee_utils import area_of_interest, initialize, sentinel2_composite


def main() -> None:
    initialize()
    CITY_DIR.mkdir(parents=True, exist_ok=True)
    composite = sentinel2_composite()
    layers = {
        "ndvi": composite.normalizedDifference(["B8", "B4"]).rename("NDVI"),
        "ndbi": composite.normalizedDifference(["B11", "B8"]).rename("NDBI"),
        "ndwi": composite.normalizedDifference(["B3", "B8"]).rename("NDWI"),
    }
    for name, image in layers.items():
        destination = CITY_DIR / f"{name}.tif"
        geemap.ee_export_image(image, filename=str(destination), scale=10,
                               region=area_of_interest(), file_per_band=False)
        print(f"Saved {destination}")


if __name__ == "__main__":
    main()
