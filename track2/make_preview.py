import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import rasterio, os

COLOURS = ['#419BDF', '#397D49', '#88B053', '#7A87C6', '#E49635',
           '#DFC35A', '#C4281B', '#A59B8F', '#B39FE1']

with rasterio.open('../data/bhubaneswar/landcover.tif') as src:
    arr = src.read(1)

os.makedirs('../data/bhubaneswar/preview', exist_ok=True)
plt.figure(figsize=(8, 8))
plt.imshow(arr, cmap=ListedColormap(COLOURS), vmin=0, vmax=8)
plt.axis('off')
plt.savefig('../data/bhubaneswar/preview/landcover.png',
            bbox_inches='tight', pad_inches=0, dpi=150, transparent=True)
plt.close()
print('Saved preview PNG.')