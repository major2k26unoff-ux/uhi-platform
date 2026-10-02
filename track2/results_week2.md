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
| Usable blocks | 27,590 (before the water fix) |
| Blocks that can take trees | 19,823 |
| Top-300 mean cooling | 3.43 C |
| Best block | 5.82 C |
| Median eligible block | 1.41 C |

## Day 2 (Thu 1 Oct 2026, re-run Fri 2 Oct after the water fix): the two models

Both models are scored on a geographic split: the west half trains, the east half tests.
Neighbouring blocks look alike, so a random split would leak and flatter the score.
These numbers are from the corrected data (water included, see Day 4, step 6).

| Model | Features | RMSE (C) | MAE (C) | R2 |
|---|---|---|---|---|
| With greenness (NDVI) | 7 land-cover fractions + NDVI | 1.58 | 1.18 | 0.467 |
| Land cover only (used for the scenario) | 7 land-cover fractions, monotone rules | 1.82 | 1.35 | 0.288 |

Removing NDVI costs 0.24 C of RMSE and 0.179 of R2. This is the ablation: one part
removed, effect measured.

What the land-cover model relies on: tree_frac 0.503, bare_frac 0.268, water_frac 0.160,
grass_frac 0.018, shrub_frac 0.018, crops_frac 0.018, built_frac 0.015.
Built-up area carries little weight in Bhubaneswar. This agrees with the weak
built-up correlation seen in Week 1. The cause has not been tested.
Before the water fix, water_frac was 0.000 and the greenness model scored R2 0.319.
Fixing the water read raised it to 0.467.

Monotone check (a typical block with more trees, taken from built-up area):

| Tree cover | 0% | 10% | 20% | 30% | 40% | 50% | 60% |
|---|---|---|---|---|---|---|---|
| Predicted C | 40.06 | 38.97 | 38.76 | 38.71 | 38.32 | 38.29 | 38.27 |

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

## Day 3 (Fri 2 Oct 2026): scenario sanity checks (final scenario, after Day 4 fixes)

Scenario: add up to 20 points of tree cover to each 100 m block. Trees replace built-up
area first, then grass, shrub and crops. Bare ground and water are left unchanged.
Cooling = the land-cover model's prediction now minus its prediction after. The same model
makes both, so its own error cancels.

Blocks: 27,889 total, 21,559 eligible (77%). A block is eligible if trees can replace at
least 5 points of its land, it has under 5% water, and it is not blocked (3,917 blocks near
a river, 514 inside hand-drawn no-plant boxes; some overlap).

Expected cooling, eligible blocks: median 1.37 C, 90th percentile 1.67 C, maximum 3.21 C.
Top-300 mean cooling: 2.55 C.

Top 300 zones compared with the whole area:

| | Top 300 | All cells |
|---|---|---|
| Ground temperature (C) | 41.14 | 39.65 |
| Tree cover | 0.00 | 0.14 |
| Built-up | 0.01 | 0.60 |
| Bare ground | 0.02 | 0.01 |
| Water | 0.00 | 0.03 |

Sensitivity to the size of the tree-cover change:

| Added tree cover | Top-300 mean cooling (C) |
|---|---|
| +10 points | 1.77 |
| +20 points | 2.55 |
| +30 points | 2.27 |

Cooling rises from +10 to +20, then drops at +30. A drop is not physical. The likely cause:
crops have no monotone rule, so the model can read "less farmland" as "hotter" once many
points are taken from it. Treat +20 as the reference. Not fixed; listed as a limitation.

### Checks

- Median cooling is inside the expected range (0.3 to 2 C): passes.
- Top 300 are hotter and have less tree cover than average: passes (41.1 C against 39.7 C,
  0.00 against 0.14).
- Top 300 have more built-up than average: **does not pass, and it should not.** They have
  almost none (0.01 against 0.60). They are open farmland (Day 4). Built-up carries little
  weight in this model (0.015), so trees "replace" little there. The old expectation came
  from a dense-city picture that does not fit Bhubaneswar's data.
- Shape of the cooling histogram: still a large spike near 1.4 C (earlier run: about 74%
  of eligible blocks tied). Ranking inside that group is weak. Tiers 2, 3 and 4 are rough
  bands, not a precise order. The top-300 list carries the information.

Histogram: `data/bhubaneswar/cooling_histogram.png`.

## Day 4 (Fri 2 Oct 2026): top zones checked against satellite photos

I opened the top-10 zones in Google satellite view and looked at each one.

### What was wrong

1. **First top 10 was mostly not plantable.** Checked ranks showed airport runways/taxiways
   (ranks 5, 6, 9) and river sand (ranks 1, 3, 8, Kuakhai/Kesora). Labels said "crops"
   (84-88%) or "grass" for these, but they were airport grass and river sand.
2. **The planned water rule changed nothing.** Excluding blocks with water >= 5% removed
   no blocks, because these blocks had 0 water in the labels.
3. **Most of the cooling was not from trees.** `diag_scenario.py`, top 300, mean cooling:
   team scenario 3.43 C, trees only 0.55 C, bare-ground removal only 2.87 C. About 85% of
   the cooling came from "bare ground disappears", not from trees arriving.

### What was changed

4. **Scenario now trees only.** Trees replace built-up, grass, shrub and crops (in that
   order). Bare ground and water are untouched. Top-300 mean went 3.43 C to 2.66 C.
5. **No-plant boxes** (`no_plant.json`): airport airfield, airport south-east taxiway/apron,
   Pandra river sand. These are hand-drawn and only cover Bhubaneswar.
6. **Found a real bug: water was missing.** A river buffer rule found 0 river blocks.
   `water_frac` was 0 in every block of a city with a river and lakes. Cause:
   `landcover.tif` marks value 0 as "no data", and Dynamic World's class 0 is water. The
   reader dropped all 81,421 water pixels. Fixed by reading land cover without the mask
   (`read_band(..., keep_zero=True)`). Result: 27,889 usable blocks (299 more), water 3% of
   the area, 3,917 blocks skipped as near a river.
   **Day 1 numbers came from the buggy read. Day 2 was re-run on the fixed data.**

### Result

| | First run | Final |
|---|---|---|
| Top-300 mean cooling | 3.43 C | 2.55 C |
| Best block | 5.82 C | 3.21 C |
| Eligible blocks | 19,823 | 21,559 |
| Top zones are | airport + river sand | farmland |

New top 10: one tight cluster near 20.20 N, 85.77 E. All 0% trees, 0% built-up, 41-43 C.
Checked 3 of 10 by satellite photo (ranks 1, 5, 9): all harvested paddy fields with field
roads, no buildings. All plantable. Ranks 2-4, 6-8, 10 are neighbours of these but were not
opened.

### Limits

- Cooling is a statistical association, not a physical simulation.
- Land-cover labels have errors (airport grass as crops, sand as crops/bare, fallow as grass).
- Hot dry fields in spring may be a seasonal effect. Tree planting there is a
  farmland-use decision, and could mean field edges, not full cover.
- No-plant boxes exist only for Bhubaneswar. A user-drawn area elsewhere only gets the
  generic river rule.
- The river rule thresholds (water >= 20%, groups of 20 blocks, 3-block buffer) are
  judgement calls.
- +30 points gives less cooling than +20 (crops have no monotone rule).
- Built-up has little effect in the model (0.015).

## Day 5 (Fri 2 Oct 2026): second city, Titlagarh

Titlagarh, Odisha (Track 1 v2 files, 83.09-83.21 E, 20.26-20.36 N, 1337 x 1114 px at 10 m).
The Drive folder held Track 2 files made by an older `priority.py`, so all outputs were
regenerated with the current code.

First run (no no-plant boxes): 14,763 blocks, 13,293 eligible (90%), 150 near a river.
Top-300 mean cooling 2.75 C, best block 3.73 C, median 1.63 C, 90th percentile 2.63 C.

### Photo check of the first top 10

| Rank | What is there | Plantable? |
|---|---|---|
| 1 | Stone quarry (rock, pits, "stone crusher") | No |
| 7 | Rocky quarry land | No |
| 8 | Jhardebandh hill, bare granite | No |
| 10 | Village farmland, scrub trees | Yes |

Ranks 1 to 6 sat in one spot, so likely the same quarry. The labels called this rock
"built-up" (53% built in rank 1). Same kind of error as the Bhubaneswar airport. The model
cannot see rock; it only sees "hot, no trees".

### Fix and result

Three hand-drawn no-plant boxes in `no_plant.json` (two quarries, one hill): 58 blocks skipped.

| | Before boxes | After boxes |
|---|---|---|
| Eligible blocks | 13,293 | 13,243 |
| Top-300 mean cooling | 2.75 C | 2.71 C |
| Best block | 3.73 C | 3.23 C |

Top 300 against the whole area (after boxes): ground 44.20 C against 43.55 C, tree cover
0.00 against 0.13, built-up 0.03 against 0.14, bare 0.00 against 0.00, water 0.00 against 0.01.

Sensitivity: +10 points 2.11 C, +20 points 2.71 C, +30 points 2.56 C. Same dip at +30 as in
Bhubaneswar (crops have no monotone rule).

New top 10 checked on satellite photos (ranks 1, 2, 3, 5, 6): all plantable. Village
farmland with houses and roads (rank 1, 3), farmland beside a reservoir (rank 5), town edge
with open dry land (rank 6), village farmland (rank 2). Ranks 4 and 7-10 not opened.

Ranks 1 to 10 are almost tied (3.19 to 3.23 C). The order inside the top 10 means little.

### Lessons from two cities

- The model finds "hot, bare-looking, no trees". It cannot tell farmland from rock, quarry,
  airport or river sand. A photo check is needed per city.
- Bhubaneswar's problems were an airport and river sand. Titlagarh's were quarries and a
  rock hill. Each needed hand-drawn boxes.
- A rock or slope layer would be the generic fix. Not done in Week 2.