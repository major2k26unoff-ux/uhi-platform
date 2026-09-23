import rasterio, numpy as np

NAMES = ['water', 'trees', 'grass', 'flooded_veg', 'crops',
         'shrub', 'built', 'bare', 'snow']

with rasterio.open('../data/bhubaneswar/landcover.tif') as src:
    arr = src.read(1)

values, counts = np.unique(arr[~np.isnan(arr)], return_counts=True)
total = counts.sum()

for v, c in zip(values, counts):
    print('%-14s %6.2f%%' % (NAMES[int(v)], 100 * c / total))