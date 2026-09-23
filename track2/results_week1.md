# Track 2 — Week 1 Results

## Metrics (geographic split, west trains / east tests)
- RMSE: 1.45 C
- MAE: 1.06 C
- R2: 0.558

## Feature importance
1. ndvi_mean (0.582) — dominant predictor
2. water_frac (0.094)
3. built_frac (0.089)
4. tree_frac (0.088)
5. grass_frac (0.083)
6. bare_frac (0.064)

## Split used, and why
Geographic split (west half trains, east half tests), not random.
Neighbouring 100m cells are nearly identical, so a random split lets
the model see near-duplicates of test cells during training and
inflates accuracy. Geographic split tests on ground the model never saw.

## Exploratory findings (Day 4)
- tree_frac vs lst_mean: r = -0.39
- ndvi_mean vs lst_mean: r = -0.53 (stronger than raw tree fraction)
- built_frac vs lst_mean: r = +0.08 (weak — checked raster alignment
  and water-cell exclusion, both ruled out as causes; likely because
  the built class mixes hot road/roof surfaces with shaded/cooler
  built structures, so it doesn't behave as a uniform "hot" signal)

## What we'd try next
- Bring in Track 1's real ndvi/lst rasters in Week 2 (currently using
  own independently-pulled copies, per Week 1 contract)
- Try NDBI as a built-up proxy instead of raw built_frac
- Test whether built_frac helps more when interacted with tree_frac
  (e.g. built-with-no-shade vs built-with-trees-nearby)