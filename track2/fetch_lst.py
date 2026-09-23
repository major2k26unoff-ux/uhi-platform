import ee, geemap
from config import BHUBANESWAR_BBOX

ee.Initialize(project='uhi-project-509407')
aoi = ee.Geometry.Rectangle(BHUBANESWAR_BBOX)

def to_celsius(img):
    return (img.select('ST_B10')
               .multiply(0.00341802).add(149.0).subtract(273.15)
               .rename('LST'))

lst = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
       .filterBounds(aoi)
       .filterDate('2024-03-01', '2024-06-15')
       .filter(ee.Filter.lt('CLOUD_COVER', 30))
       .map(to_celsius)
       .select('LST').median().clip(aoi))

geemap.download_ee_image(lst, filename='../data/bhubaneswar/lst_track2.tif',
                          scale=10, region=aoi)
print('Saved lst_track2.tif')

s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
      .filterBounds(aoi)
      .filterDate('2024-03-01', '2024-05-31')
      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
      .median())
ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI').clip(aoi)
geemap.ee_export_image(ndvi, filename='../data/bhubaneswar/ndvi_track2.tif',
                        scale=10, region=aoi, file_per_band=False)
print('Saved ndvi_track2.tif')