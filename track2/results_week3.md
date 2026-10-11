# Track 2 - Week 3 results

Week 3 (7 to 14 October 2026). Final numbers for the report. Week 1 and 2 detail stays in
`results_week1.md` and `results_week2.md`.

## Day 1 (7 Oct): water fix, alignment fix, canopy and trees

- **Water.** `landcover.tif` declares 0 as "no data", but Dynamic World class 0 is water. The
  Week 2 `keep_zero` read already handled it. Land cover is now never read through the mask;
  255 means "no data". New Earth Engine downloads use `.unmask(255)`.
- **Alignment.** In 10 of 11 cities the land-cover grid sat one pixel (about 10 m, 20 m in Delhi
  and Mumbai) west and/or north of the heat grid. `align_landcover()` now resamples land cover
  onto `lst.tif`'s exact grid (nearest neighbour). Shift after the fix: 0 m in all 11 cities.
- **Canopy and trees.** Every zone has `canopy_added_m2` (tree cover added x real block area)
  and `trees_est` (canopy / 50 m2). A "100 m" block is about 94 x 99 m in Bhubaneswar.
  Checked by hand on 3 zones; `trees_est` equals canopy / 50 to rounding in all 3,300 zones.

## Day 2 (11 Oct): photo checks, three model fixes, final table

### Photo checks: all 11 cities, top 10 each

Every top-10 zone was opened on satellite imagery (Esri World Imagery) with the block outlined.
Contact sheets: `data/photo_checks_week3/`. Verdicts: **good** = open or farm land where trees
could go; **doubtful** = possible but not a clear planting site (scrub, sports grounds, parks,
village houses, marsh); **wrong** = cannot take trees (water, runway, roofs, highway, riverbed).

| City | Good | Doubtful | Wrong | What the wrong ones were |
|---|---|---|---|---|
| bhubaneswar | 9 | 1 | 0 | - (rank 6: event tents beside the highway, doubtful) |
| titlagarh | 10 | 0 | 0 | - |
| sriganganagar | 9 | 1 | 0 | - (rank 7 is an orchard the labels call treeless) |
| bilaspur | 5 | 3 | 2 | sandy riverbed (Arpa river) |
| banda | 6 | 0 | 4 | dry riverbed, highway interchange, two highway blocks |
| phalodi | 6 | 4 | 0 | - (village edges) |
| churu | 4 | 6 | 0 | - (village houses the labels call 99 % built) |
| bengaluru | 5 | 2 | 3 | pond, earthworks, dense slum roofs |
| hyderabad | 3 | 5 | 2 | housing under construction, bus depot |
| delhi | 2 | 7 | 1 | water body under weeds |
| mumbai | 0 | 7 | 3 | factory sheds, slum roofs |
| **all** | **59** | **36** | **15** | out of 110 |

### No-plant boxes (`no_plant.json`): 10 added this week, 19 in total in 6 cities

| City | Box | Found at |
|---|---|---|
| hyderabad | Begumpet Airport | first top 10: ranks 2 to 9 were runway and taxiway |
| hyderabad | Paved parade ground, Langar Houz area | first top 10: rank 1 |
| hyderabad | Secunderabad parade ground | second top 10: ranks 3, 7, 8 |
| delhi | IGI Airport (main box and southern runway strip) | first and second top 10: ranks 4 to 10 |
| delhi | Ash and soil dump north of the NTPC Eco Park, Badarpur | first top 10: ranks 4 and 7 |
| bengaluru | HAL Airport | first top 10: ranks 1, 3, 4, 6, 8 |
| bengaluru | Bellandur Lake and its marshy bed | second top 10: ranks 2, 3, 7, 8 (open water the labels do not call water) |
| mumbai | Mumbai airport, south-east runway end | rank 2 |
| titlagarh | Stone quarry north-east of the town | rank 4 |

Boxes stop at airports, lakes, quarries and dumps: big, permanent and certainly not plantable.
Single scrub patches, sports grounds and roofs were not boxed (Week 2 rule: boxes for single
places never end).

### Three fixes to the model code

1. **Same result on every machine** (`n_jobs=1`). XGBoost adds its histogram sums in a different
   order for each number of CPU threads. The same Bhubaneswar data gave a best block of 3.21 C on
   one machine and 3.43 C on another. One thread gives one answer everywhere; it costs seconds.
2. **Steadier ranking** (`N_SEEDS = 5`, class `SeedAverage`). Each model is now the average of 5
   XGBoost models with different random seeds. `stability.py` measured the effect (4 runs, no
   seed shared): rank correlation of all eligible blocks rose from 0.977 to 0.989 (Bhubaneswar)
   and 0.971 to 0.991 (Titlagarh); the spread of the best block halved.
3. **No planting zones in blocks that are already half trees** (`MAX_TREE_NOW = 0.5`). A Banda
   block at 93 % trees ranked 3rd with 4.2 C for 7 more points of trees. Almost no training block
   is near 100 % trees, so the model guesses there. It changed one zone in one city.

### How stable is the final ranking? (`data/stability.md`)

4 runs per city, each the average of 5 seeds, no seed shared between runs.

| City | Top-300 mean C (range) | Best block C (range) | Top-300 overlap | Top-10 overlap | Rank correlation | Near-ties at cut-off |
|---|---|---|---|---|---|---|
| banda | 3.66 (3.63 to 3.67) | 4.39 (4.34 to 4.47) | 0.71 | 0.70 | 0.985 | 6237 |
| bengaluru | 3.76 (3.74 to 3.77) | 6.14 (6.08 to 6.24) | 0.93 | 0.92 | 0.979 | 163 |
| bhubaneswar | 2.15 (2.12 to 2.17) | 3.26 (3.20 to 3.28) | 0.37 | 1.00 | 0.989 | 1472 |
| bilaspur | 6.39 (6.38 to 6.40) | 7.04 (7.02 to 7.07) | 0.99 | 0.43 | 0.996 | 13 |
| churu | 3.40 (3.31 to 3.46) | 4.52 (4.36 to 4.65) | 0.24 | 0.80 | 0.971 | 2099 |
| delhi | 4.71 (4.69 to 4.73) | 6.89 (6.74 to 6.97) | 0.98 | 0.78 | 0.977 | 30 |
| hyderabad | 4.34 (4.32 to 4.35) | 6.76 (6.68 to 6.86) | 0.97 | 0.95 | 0.986 | 102 |
| mumbai | 3.65 (3.63 to 3.69) | 6.63 (6.51 to 6.75) | 0.99 | 0.75 | 0.992 | 94 |
| phalodi | 5.19 (5.12 to 5.25) | 5.34 (5.16 to 5.47) | 0.66 | 0.62 | 0.997 | 3251 |
| sriganganagar | 6.15 (6.10 to 6.18) | 7.01 (6.86 to 7.07) | 0.97 | 1.00 | 0.984 | 35 |
| titlagarh | 2.58 (2.57 to 2.61) | 3.07 (3.04 to 3.08) | 0.58 | 0.77 | 0.991 | 1422 |

Reading: the **numbers** are stable (top-300 mean within about 0.15 C in every city, under 0.05 C in 6 of 11). The **order
of all blocks** is stable (rank correlation 0.97 to 1.00). **Which exact 300 blocks** make the
list is not stable in farm-dominated areas (Bhubaneswar, Churu, Titlagarh, Phalodi, Banda),
because 1,400 to 6,200 blocks sit within 0.05 C of the 300th zone. There the top 300 is one
sample from a large group of equally good farmland blocks, and the map should be read as
"this kind of area", not "exactly these blocks".

### Final table (`data/cross_city.md`)

| Area | Blocks | Top-300 cooling C | Best block C | R2 with greenness | R2 land cover only | New canopy m2 | Trees (approx) | Note |
|---|---|---|---|---|---|---|---|---|
| banda | 14763 | 3.66 | 4.37 | 0.513 | 0.262 | 538000 | 10760 |  |
| bengaluru | 49284 | 3.75 | 6.24 | 0.538 | 0.361 | 564800 | 11300 |  |
| bhubaneswar | 27889 | 2.16 | 3.28 | 0.441 | 0.292 | 557000 | 11140 |  |
| bilaspur | 20736 | 6.4 | 7.07 | 0.793 | 0.112 | 552100 | 11040 | weak scenario model |
| churu | 14763 | 3.44 | 4.59 | 0.626 | 0.575 | 524800 | 10500 |  |
| delhi | 92852 | 4.7 | 6.93 | 0.22 | 0.045 | 512700 | 10250 | weak scenario model |
| hyderabad | 49284 | 4.35 | 6.86 | 0.537 | 0.458 | 564700 | 11290 |  |
| mumbai | 55600 | 3.64 | 6.67 | 0.87 | 0.793 | 551200 | 11020 | low confidence (sea, roofs) |
| phalodi | 14763 | 5.15 | 5.34 | 0.436 | 0.357 | 530400 | 10610 |  |
| sriganganagar | 16226 | 6.1 | 6.86 | 0.119 | 0.122 | 472100 | 9440 | weak scenario model |
| titlagarh | 14763 | 2.57 | 3.04 | 0.402 | 0.541 | 558900 | 11180 |  |

Change from the Day 1 table: Hyderabad 4.78 to 4.35 C and Delhi 5.28 to 4.70 C (airports
removed), Bengaluru 3.92 to 3.75 C (airport and lake removed), Churu 3.92 to 3.44 C (seed
averaging; its old number came from one unlucky model), Titlagarh 2.71 to 2.57 C (partly its new
quarry box). Others moved by 0.11 C or less.

### Critical reading

- **Where the model is trustworthy:** farm-dominated towns with a working land-cover model
  (Titlagarh, Bhubaneswar, Phalodi, Churu, Banda). Their top 10 are mostly real farmland.
- **Where it is not:** dense metros. Hot, bare, treeless ground in a metro is often a runway,
  roof, depot, ground or dump. Even with their airport and other boxes, Delhi, Hyderabad and
  Mumbai still have only 0 to 3 good zones in their top 10.
- **Weak models:** Delhi (R2 0.045), Bilaspur (0.112), Sri Ganganagar (0.122). Their cooling
  numbers are mostly the model's average, and many blocks tie (Bilaspur: top 10 all 7.07 C).
- **Churu:** its top 300 is cooler than the town average (47.3 against 51.7 C). The labels call
  village houses 96 % built-up, and the model prefers replacing built-up ground.
- **Dry riverbeds** still reach the top 10 (Banda rank 1, Bilaspur). Known limit since Week 2.
- **Cooling is a statistical association**, not a physical simulation. Treat it as "where to
  look first", then check on the ground.

## How these results were produced and checked

- Code: `priority.py` with `N_SEEDS = 5`, `n_jobs = 1`, `MAX_TREE_NOW = 0.5`. All 11 cities re-run
  with `--skip-fetch` (no Earth Engine calls) on Python 3.12, XGBoost 3.4.1, scikit-learn 1.9.1,
  pandas 3.0.6, NumPy 2.5.3 and rasterio 1.5.1, the same versions as `track2/venv`.
- Checks run: `check_model.py` (monotone: more trees never hotter, passed), `inspect_priority.py`,
  `stability.py`, Track 3 tests (13 passed), Track 1 Week 3 tests (5 passed), `node --check
  track4/app.js`, and the API serving the new files (`/api/priority/<city>` returns canopy and
  trees).
