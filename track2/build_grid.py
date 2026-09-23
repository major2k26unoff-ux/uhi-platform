import rasterio, numpy as np, pandas as pd

CELL = 10  # 10 pixels x 10 m = 100 m squares

def load(path):
    with rasterio.open(path) as src:
        return src.read(1), src.transform

lc,  transform = load('../data/bhubaneswar/landcover.tif')
lst, _  = load('../data/bhubaneswar/lst_track2.tif')
ndvi, _ = load('../data/bhubaneswar/ndvi_track2.tif')
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
            continue  # no temperature data here

        lon, lat = rasterio.transform.xy(transform, (r0 + r1) // 2, (c0 + c1) // 2)
        records.append({
            'row': r, 'col': c, 'lat': lat, 'lon': lon,
            'tree_frac':  float((lc_block == 1).sum()) / n,
            'grass_frac': float((lc_block == 2).sum()) / n,
            'built_frac': float((lc_block == 6).sum()) / n,
            'water_frac': float((lc_block == 0).sum()) / n,
            'bare_frac':  float((lc_block == 7).sum()) / n,
            'ndvi_mean':  float(np.nanmean(ndvi_block)),
            'lst_mean':   float(np.nanmean(lst_block)),
        })

df = pd.DataFrame(records)
df.to_csv('../data/bhubaneswar/grid_features.csv', index=False)

print('Cells:', len(df))
print(df.describe())