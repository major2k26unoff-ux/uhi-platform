"""Export a cloud-masked Sentinel-2 RGB composite as the contract's rgb.tif."""

import geemap

from config import CITY_DIR
from ee_utils import area_of_interest, initialize, sentinel2_composite


def main() -> None:
    initialize()
    CITY_DIR.mkdir(parents=True, exist_ok=True)
    rgb = sentinel2_composite().select(["B4", "B3", "B2"])
    geemap.ee_export_image(
        rgb, filename=str(CITY_DIR / "rgb.tif"), scale=10,
        region=area_of_interest(), file_per_band=False,
    )
    print(f"Saved {CITY_DIR / 'rgb.tif'}")


if __name__ == "__main__":
    main()
