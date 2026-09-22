"""Shared Earth Engine setup and Sentinel-2 composite construction."""

import ee

from config import BHUBANESWAR_BBOX, DATE_END, DATE_START, EARTH_ENGINE_PROJECT


def initialize() -> None:
    """Authenticate once with `earthengine authenticate`, then initialise EE."""
    ee.Initialize(project=EARTH_ENGINE_PROJECT)


def area_of_interest() -> ee.Geometry:
    return ee.Geometry.Rectangle(BHUBANESWAR_BBOX)


def mask_sentinel2_clouds(image: ee.Image) -> ee.Image:
    """Keep pixels whose QA60 cloud and cirrus flags are both clear."""
    qa = image.select("QA60")
    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11
    clear = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(cirrus_bit).eq(0))
    return image.updateMask(clear).divide(10000).copyProperties(image, ["system:time_start"])


def sentinel2_composite() -> ee.Image:
    aoi = area_of_interest()
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(DATE_START, DATE_END)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        .map(mask_sentinel2_clouds)
    )
    count = collection.size().getInfo()
    if count == 0:
        raise RuntimeError("No Sentinel-2 scenes found. Check dates and bounding box.")
    print(f"Sentinel-2 scenes found: {count}")
    return collection.median().clip(aoi)
