# Track 2 - Cooling Prediction Model

For any area Track 1 has processed, Track 2 answers two questions:

1. Which 100 m blocks would gain the most from more trees?
2. About how much cooler would they get?

This is a **statistical association learned from each area's own data**, used to rank where
planting would help most. It is **not a physical simulation**, and the degrees are an
estimate, not a promise.

## How to run

Needs Track 1's files in `data/<slug>/` first (`meta.json`, `lst.tif`, `ndvi.tif`).
Use the Track 2 virtual environment (`venv\Scripts\activate`).

```
python priority.py --slug bhubaneswar               # one area
python priority.py --slug bhubaneswar --skip-fetch  # reuse landcover.tif already on disk
python rerun_all.py                                 # every preset city, current code
python cross_city.py > ../data/cross_city.md        # one-row-per-city table
python inspect_priority.py --slug bhubaneswar       # sanity checks and sensitivity
python top_zones.py --slug bhubaneswar              # top 10 with satellite links
python check_model.py --slug bhubaneswar            # ablation and monotone checks
python stability.py > ../data/stability.md          # how much the ranking moves with random seeds
```

Track 1's worker runs `priority.py` by itself after the satellite step.

## What it writes into `data/<slug>/`

`landcover.tif`, `grid_features.csv`, `priority.geojson` (top 300 zones),
`priority_summary.json`, `preview/landcover.png`, `preview/priority.png`.

## How it works

1. **Grid.** Temperature, greenness and land cover are averaged into 100 m blocks.
   Land cover comes from Dynamic World (Google Earth Engine). It is resampled onto the heat
   layer's exact grid (`align_landcover`), and read without the file's "no data" mask,
   because Dynamic World class 0 is water (255 means no data).
2. **Two models** (XGBoost), trained on a geographic split (west trains, east tests). Each
   is the average of 5 XGBoost models with different random seeds (`N_SEEDS`), trained on one
   CPU thread (`n_jobs=1`) so every machine gets the same answer:
   - *With greenness* (land cover + NDVI). Used only to report accuracy.
   - *Land cover only*. Used for the planting scenario. Greenness is left out on purpose:
     if NDVI is an input, "adding trees" has no way to change the answer.
3. **Monotone rules** on the land-cover model: more trees or grass can never make a block
   hotter; more built-up or bare ground can never make it cooler.
4. **Scenario.** Add up to 20 percentage points of tree cover per block, taking the space
   from built-up ground first, then grass, shrub and crops. Bare ground and water are
   not touched.
5. **Cooling** = the model's prediction now, minus its prediction after the scenario
   (model against model, so model error cancels).
6. **Eligibility.** A block must have at least 5 % room to plant, under 5 % water, under
   50 % trees already (`MAX_TREE_NOW`), and not be blocked. Blocked means near a river (water groups of 20+ blocks, 3-block buffer) or
   inside a hand-drawn box in `no_plant.json`.
7. **Ranking.** Eligible blocks are ranked by expected cooling. The top 300 go into
   `priority.geojson`.

## Results

Final numbers: `results_week3.md` (Week 3: photo checks of all 11 cities, stability, final
table). Earlier detail: `results_week1.md`, `results_week2.md`. The one-row-per-city table is
`data/cross_city.md`; the seed-stability table is `data/stability.md`.

Each zone also carries `canopy_added_m2` (new tree canopy, from the scenario and the real
block area) and `trees_est` (canopy / 50 m2, a rough count; real crowns are about 30 to 80 m2).

## Limits (read before using the numbers)

- The model finds places that are hot, look bare and have few trees. It cannot tell
  farmland from airports, landfills, quarries, dry river beds, slum roofs or rail depots.
  Every list needs a satellite photo check. In Week 3 the top 10 of all 11 preset cities
  were checked: 59 good, 36 doubtful, 15 wrong out of 110.
- `no_plant.json` holds 19 hand-drawn exclusion boxes (airports, lakes, quarries, dumps) for
  Bhubaneswar, Titlagarh, Mumbai, Hyderabad, Delhi and Bengaluru only. It cannot cover areas a
  user draws on the website.
- Dry river beds look like crops to the labels, to NDWI and to water history. A real fix
  needs terrain (height above the nearest river). Future work.
- Weak scenario models (land-cover R2 below 0.2): Delhi, Bilaspur, Sri Ganganagar. Their
  cooling numbers are uncertain and flagged in the table.
- Mumbai: half the blocks are sea, which inflates R2. Dense roofs and large sheds read as
  bare ground, so the Mumbai list is low confidence.
- Many blocks share almost the same cooling value. In farm areas 1,400 to 6,200 blocks sit
  within 0.05 C of the 300th zone, so which exact blocks make the top 300 changes between runs
  (see `data/stability.md`). Read the map as "this kind of area", not "exactly these blocks".
- Cooling does not rise smoothly with +10, +20, +30 in every area. Crops have no monotone rule.
- Thresholds (20 points, 5 % room, river buffer) are judgement calls, not fitted values.