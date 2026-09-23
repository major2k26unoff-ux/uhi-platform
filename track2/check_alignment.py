import rasterio, matplotlib.pyplot as plt
import numpy as np

with rasterio.open('../data/bhubaneswar/landcover.tif') as src:
    lc = src.read(1)
with rasterio.open('../data/bhubaneswar/lst_track2.tif') as src:
    lst = src.read(1)

print('landcover shape:', lc.shape)
print('lst shape:', lst.shape)

fig, axes = plt.subplots(1, 2, figsize=(10,5))
axes[0].imshow(lc); axes[0].set_title('landcover')
axes[1].imshow(lst); axes[1].set_title('lst')
plt.savefig('../data/bhubaneswar/align_check.png', dpi=100)
print('saved align_check.png')