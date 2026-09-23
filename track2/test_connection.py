import ee
ee.Initialize(project='uhi-project-509407')

dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
print('Dynamic World images available:', dw.size().getInfo())
print('Earth Engine is working.')