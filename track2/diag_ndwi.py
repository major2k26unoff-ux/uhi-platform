"""Is wetness (NDWI) a good signal for dry river beds?   python diag_ndwi.py --slug custom-c0ffee01

Prints the block-average NDWI for the top 10 zones and compares it with all blocks.
"""
import argparse
import json

import numpy as np
import pandas as pd

from priority import DATA, block_mean, read_band

parser = argparse.ArgumentParser()
parser.add_argument("--slug", required=True)
slug = parser.parse_args().slug

meta = json.loads((DATA / slug / "meta.json").read_text())
k = int(round(100 / meta["scale_m"]))
ndwi, _ = read_band(DATA / slug / "ndwi.tif")
blocks = block_mean(ndwi, k)

df = pd.read_csv(DATA / slug / "grid_features.csv")
df["ndwi_mean"] = [blocks[r, c] if r < blocks.shape[0] and c < blocks.shape[1] else np.nan
                   for r, c in zip(df.row, df.col)]

print(f"{slug}: NDWI per 100 m block, all blocks")
print(df.ndwi_mean.describe(percentiles=[.5, .75, .9, .95, .99]).round(3).to_string())

top = df[df.eligible].nsmallest(10, "rank")
print("\nTop 10 zones:")
print(top[["rank", "lat", "lon", "ndwi_mean", "built_frac", "bare_frac", "crops_frac", "grass_frac"]]
      .round(3).to_string(index=False))

pct = (df.ndwi_mean.rank(pct=True).loc[top.index] * 100).round(0)
print("\nTop 10 NDWI percentile among all blocks (100 = wettest):", pct.astype(int).tolist())