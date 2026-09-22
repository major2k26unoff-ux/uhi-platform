"""Smallest useful proof that Python can access Google Earth Engine."""

import ee

from config import EARTH_ENGINE_PROJECT

ee.Initialize(project=EARTH_ENGINE_PROJECT)
image = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").first()
print("Bands available:", image.bandNames().getInfo()[:6])
print("Earth Engine is working.")
