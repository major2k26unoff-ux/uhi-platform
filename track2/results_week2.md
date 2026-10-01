# Track 2 - Week 2 Results

Area: Bhubaneswar, Odisha (Track 1 grid, 85.75-85.90 E, 20.20-20.35 N).
Layers: Sentinel-2 (Mar-May 2024), Landsat ground temperature (Mar-Jun 2024), Google Dynamic World land cover.

## Day 1 (Thu 1 Oct 2026): first real run

Week 1 and Week 2 numbers are not directly comparable. Week 1 used a wider box
(85.70-85.95 E, 20.15-20.40 N), 77,284 cells. Week 2 uses Track 1's box, 27,590 usable
100 m cells (1671 x 1671 px at 10 m, 10 x 10 pixels per cell).
`priority.py` reads the box and pixel size from `meta.json`.

First run of `python priority.py --slug bhubaneswar`:

| Measure | Result |
|---|---|
| Usable blocks | 27,590 |
| Blocks that can take trees | 19,823 |
| Top-300 mean cooling | 3.43 C |
| Best block | 5.82 C |
| Median eligible block | 1.41 C |

## Day 2 (Thu 1 Oct 2026): the two models

Both models are scored on a geographic split: the west half trains, the east half tests.
Neighbouring blocks look alike, so a random split would leak and flatter the score.

| Model | Features | RMSE (C) | MAE (C) | R2 |
|---|---|---|---|---|
| With greenness (NDVI) | 7 land-cover fractions + NDVI | 1.62 | 1.21 | 0.319 |
| Land cover only (used for the scenario) | 7 land-cover fractions, monotone rules | 1.71 | 1.31 | 0.238 |

Removing NDVI costs 0.09 C of RMSE and 0.081 of R2. This is the ablation: one part
removed, effect measured.

What the land-cover model relies on: tree_frac 0.706, bare_frac 0.216, grass_frac 0.025,
crops_frac 0.019, shrub_frac 0.018, built_frac 0.015, water_frac 0.000.
Built-up area carries little weight in Bhubaneswar. This agrees with the weak
built-up correlation seen in Week 1. The cause has not been tested.

Monotone check (a typical block with more trees, taken from built-up area):

| Tree cover | 0% | 10% | 20% | 30% | 40% | 50% | 60% |
|---|---|---|---|---|---|---|---|
| Predicted C | 40.07 | 38.79 | 38.66 | 38.57 | 38.26 | 38.23 | 38.19 |

Temperature falls and never rises, as the rule requires.

### Why the land-cover model is used for the scenario even though it scores lower

NDVI (greenness) and tree cover move together. In reality, a place with more trees has
higher greenness. The greenness model learned this, and NDVI is its strongest feature.
If we raise tree cover but leave NDVI where it is, we describe a place that cannot exist:
more trees, same greenness. The model would mostly ignore the change and the cooling
would come out near zero, not because trees do not cool but because the question is
contradictory. The land-cover model has no NDVI, so changing tree cover is a fair question
to ask it. It scores a little lower on its own, and that is the price of asking a
consistent question. The greenness model is kept for accuracy reporting.

Monotone constraints: more trees or grass can never make a block hotter, and more
built-up or bare ground can never make it cooler. Without them, noise could make some
blocks appear to warm when trees are added.

Caveat: the scenario converts bare ground first. So part of the cooling it reports comes
from bare ground disappearing, not only from trees arriving.

This is a statistical association learned from the area's own data. It is not a physical
simulation, and the degrees are an estimate, not a promise. 