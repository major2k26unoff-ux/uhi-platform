"""Export Landsat 8 Collection 2 Level 2 land-surface temperature in Celsius."""

import ee
import geemap

from config import CITY_DIR
from ee_utils import area_of_interest, initialize


def to_celsius(image: ee.Image) -> ee.Image:
    return (image.select("ST_B10").multiply(0.00341802).add(149.0)
            .subtract(273.15).rename("LST")
            .copyProperties(image, ["system:time_start"]))


def main() -> None:
    initialize()
    CITY_DIR.mkdir(parents=True, exist_ok=True)
    aoi = area_of_interest()
    scenes = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(aoi)
              .filterDate("2024-03-01", "2024-06-15")
              .filter(ee.Filter.lt("CLOUD_COVER", 30)).map(to_celsius))
    print("Landsat scenes found:", scenes.size().getInfo())
    geemap.ee_export_image(scenes.select("LST").median().clip(aoi),
                           filename=str(CITY_DIR / "lst.tif"), scale=30,
                           region=aoi, file_per_band=False)
    print(f"Saved {CITY_DIR / 'lst.tif'}")


if __name__ == "__main__":
    main()
