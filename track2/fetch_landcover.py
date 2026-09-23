import ee, geemap, os
from config import BHUBANESWAR_BBOX, DATE_START, DATE_END, CITY_SLUG

ee.Initialize(project='uhi-project-509407')
aoi = ee.Geometry.Rectangle(BHUBANESWAR_BBOX)

dw = (ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
      .filterBounds(aoi)
      .filterDate(DATE_START, DATE_END))

print('Images in range:', dw.size().getInfo())

# 'label' holds the winning class per pixel.
# mode() takes the most frequently occurring class across the date range,
# which smooths out one-off misclassifications.
landcover = dw.select('label').mode().clip(aoi)

os.makedirs(f'../data/{CITY_SLUG}', exist_ok=True)
geemap.ee_export_image(
    landcover,
    filename=f'../data/{CITY_SLUG}/landcover.tif',
    scale=10, region=aoi, file_per_band=False
)
print('Saved landcover.tif')