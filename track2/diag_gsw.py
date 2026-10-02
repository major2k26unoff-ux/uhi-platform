"""Does the water-history layer (JRC Global Surface Water) flag dry river beds?
    python diag_gsw.py --slug custom-c0ffee01

For the top 10 zones and 300 random blocks, prints how often the ground has been under water
since 1984 (0 = never, 100 = always), averaged over each 100 m block.
Needs Earth Engine (same login as the other scripts). No files are changed.
"""
import argparse

import ee
import pandas as pd

from priority import DATA
from settings import ee_project

parser = argparse.ArgumentParser()
parser.add_argument("--slug", required=True)
slug = parser.parse_args().slug

df = pd.read_csv(DATA / slug / "grid_features.csv")
top = df[df.eligible].nsmallest(10, "rank")
control = df.sample(n=min(300, len(df)), random_state=1)

ee.Initialize(project=ee_project())
occurrence = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence").unmask(0)


def occurrence_for(rows):
    feats = [ee.Feature(ee.Geometry.Rectangle([r.west, r.south, r.east, r.north]), {"i": int(i)})
             for i, r in rows.iterrows()]
    out = occurrence.reduceRegions(collection=ee.FeatureCollection(feats),
                                   reducer=ee.Reducer.mean(), scale=30).getInfo()["features"]
    return pd.Series({f["properties"]["i"]: f["properties"].get("mean") for f in out})


top = top.assign(water_history=occurrence_for(top))
control = control.assign(water_history=occurrence_for(control))

print(f"\n{slug}: top 10 zones, share of time under water since 1984 (0-100)")
print(top[["rank", "lat", "lon", "water_history", "crops_frac", "bare_frac"]].round(2).to_string(index=False))

c = control.water_history
print(f"\n300 random blocks: median {c.median():.1f}   75th pct {c.quantile(.75):.1f}   "
      f"90th pct {c.quantile(.9):.1f}   max {c.max():.1f}")
for cut in (5, 10, 25):
    print(f"  random blocks with water history >= {cut}: {100 * (c >= cut).mean():.0f}%")