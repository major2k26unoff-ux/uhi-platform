import rasterio, numpy as np, pandas as pd

CELL = 20  # 20 pixels x 10 m = 200 m squares

def load(path):
    with rasterio.open(path) as src:
        return src.read(1), src.transform

lc,  transform = load('../data/bhubaneswar/landcover.tif')
lst, _         = load('../data/bhubaneswar/lst_track2.tif')
ndvi, _        = load('../data/bhubaneswar/ndvi_track2.tif')

rows_n = lc.shape[0] // CELL
cols_n = lc.shape[1] // CELL
records = []

for r in range(rows_n):
    for c in range(cols_n):
        r0, r1 = r * CELL, (r + 1) * CELL
        c0, c1 = c * CELL, (c + 1) * CELL

        lc_block   = lc[r0:r1, c0:c1]
        lst_block  = lst[r0:r1, c0:c1]
        ndvi_block = ndvi[r0:r1, c0:c1]

        n = lc_block.size
        if np.isnan(lst_block).all():
            continue

        records.append({
            'row': r, 'col': c,
            'tree_frac':  float((lc_block == 1).sum()) / n,
            'built_frac': float((lc_block == 6).sum()) / n,
            'water_frac': float((lc_block == 0).sum()) / n,
            'ndvi_mean':  float(np.nanmean(ndvi_block)),
            'lst_mean':   float(np.nanmean(lst_block)),
        })

df = pd.DataFrame(records)
print('Cells:', len(df))
print(df[['tree_frac','built_frac','ndvi_mean','lst_mean']].corr()['lst_mean'])