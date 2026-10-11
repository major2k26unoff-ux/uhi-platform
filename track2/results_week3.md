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
The table is for the official results made on the demo PC (Windows); 25 blocks that were new in
the Windows top 10 were checked separately.
Contact sheets: `data/photo_checks_week3/`. Verdicts: **good** = open or farm land where trees
could go; **doubtful** = possible but not a clear planting site (scrub, sports grounds, parks,
village houses, marsh); **wrong** = cannot take trees (water, runway, roofs, highway, riverbed).

| City | Good | Doubtful | Wrong | What the wrong ones were |
|---|---|---|---|---|
| bhubaneswar | 9 | 1 | 0 | - (one doubtful: event tents beside the highway) |
| titlagarh | 10 | 0 | 0 | - |
| sriganganagar | 9 | 1 | 0 | - (one orchard the labels call treeless) |
| bilaspur | 3 | 4 | 3 | sandy riverbed (twice), quarry pond |
| banda | 7 | 0 | 3 | dry riverbed, highway interchange, highway |
| phalodi | 6 | 4 | 0 | - (village edges) |
| churu | 5 | 5 | 0 | - (village houses the labels call 99 % built) |
| bengaluru | 4 | 3 | 3 | pond, construction site, dense slum roofs |
| hyderabad | 3 | 4 | 3 | housing under construction (twice), bus depot |
| delhi | 2 | 6 | 2 | water bodies under weeds |
| mumbai | 0 | 6 | 4 | factory sheds, slum roofs |
| **all** | **58** | **34** | **18** | out of 110 |

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

1. **Same result every run** (`n_jobs=1`). With several threads XGBoost adds its sums in a
   varying order. One thread makes every run on one machine identical (checked on the demo PC).
   Linux and Windows builds can still differ slightly; see "Same answer on another machine?".
2. **Steadier ranking** (`N_SEEDS = 5`, class `SeedAverage`). Each model is now the average of 5
   XGBoost models with different random seeds. `stability.py` measured the effect (4 runs, no
   seed shared): rank correlation of all eligible blocks rose from 0.977 to 0.989 (Bhubaneswar)
   and 0.971 to 0.991 (Titlagarh); the spread of the best block halved.
3. **No planting zones in blocks that are already half trees** (`MAX_TREE_NOW = 0.5`). A Banda
   block at 93 % trees ranked 3rd with 4.2 C for 7 more points of trees. Almost no training block
   is near 100 % trees, so the model guesses there. It changed one zone in one city.

### How stable is the final ranking? (`data/stability.md`, demo PC)

4 runs per city, each the average of 5 seeds, no seed shared between runs.

| City | Top-300 mean C (range) | Best block C (range) | Top-300 overlap | Top-10 overlap | Rank correlation | Near-ties at cut-off |
|---|---|---|---|---|---|---|
| banda | 3.66 (3.63 to 3.70) | 4.47 (4.41 to 4.55) | 0.88 | 0.67 | 0.986 | 6235 |
| bengaluru | 3.76 (3.72 to 3.79) | 6.17 (6.13 to 6.24) | 0.92 | 0.83 | 0.975 | 164 |
| bhubaneswar | 2.15 (2.13 to 2.18) | 3.22 (3.15 to 3.32) | 0.59 | 1.00 | 0.985 | 1466 |
| bilaspur | 6.39 (6.37 to 6.43) | 7.04 (7.01 to 7.09) | 0.99 | 0.37 | 0.995 | 15 |
| churu | 3.47 (3.41 to 3.55) | 4.61 (4.52 to 4.69) | 0.24 | 0.78 | 0.966 | 1548 |
| delhi | 4.69 (4.63 to 4.79) | 6.84 (6.81 to 6.89) | 0.97 | 0.85 | 0.953 | 32 |
| hyderabad | 4.31 (4.31 to 4.33) | 6.76 (6.71 to 6.82) | 0.98 | 0.88 | 0.985 | 106 |
| mumbai | 3.66 (3.59 to 3.72) | 6.68 (6.52 to 6.78) | 0.98 | 0.83 | 0.989 | 92 |
| phalodi | 5.17 (5.11 to 5.27) | 5.38 (5.33 to 5.44) | 0.73 | 0.65 | 0.994 | 3250 |
| sriganganagar | 6.15 (6.07 to 6.19) | 7.05 (7.00 to 7.11) | 0.94 | 0.95 | 0.982 | 50 |
| titlagarh | 2.60 (2.59 to 2.61) | 3.07 (3.05 to 3.09) | 0.67 | 0.83 | 0.990 | 1423 |

Reading: the **numbers** are stable (top-300 mean within 0.16 C in every city). The **order of
all blocks** is stable (rank correlation 0.95 to 1.00). **Which exact 300 blocks** make the list
is not stable in farm-dominated areas (Churu 24 %, Bhubaneswar 59 %, Titlagarh 67 % overlap),
because 1,400 to 6,200 blocks sit within 0.05 C of the 300th zone. There the top 300 is one
sample from a large group of equally good farmland blocks, and the map should be read as
"this kind of area", not "exactly these blocks".

### Same answer on another machine?

- Two runs on the demo PC (Windows) are identical (Titlagarh and Phalodi re-run and compared).
- A Linux run with the same package versions gave slightly different models: top-300 mean
  within 0.08 C, best block within 0.18 C. In metros 270 to 297 of the 300 zones were the same;
  in farm towns far fewer (Phalodi 6), for the near-tie reason above.
- So the **official numbers are the ones made on the demo PC**. Re-running there gives the same
  files every time.

### Final table (`data/cross_city.md`, demo PC)

| Area | Blocks | Top-300 cooling C | Best block C | R2 with greenness | R2 land cover only | New canopy m2 | Trees (approx) | Note |
|---|---|---|---|---|---|---|---|---|
| banda | 14763 | 3.69 | 4.55 | 0.514 | 0.262 | 537900 | 10760 |  |
| bengaluru | 49284 | 3.78 | 6.13 | 0.538 | 0.36 | 569600 | 11390 |  |
| bhubaneswar | 27889 | 2.16 | 3.27 | 0.44 | 0.293 | 557000 | 11140 |  |
| bilaspur | 20736 | 6.37 | 7.01 | 0.793 | 0.113 | 552100 | 11040 | weak scenario model |
| churu | 14763 | 3.41 | 4.57 | 0.627 | 0.576 | 524800 | 10500 |  |
| delhi | 92852 | 4.7 | 6.85 | 0.214 | 0.045 | 513000 | 10260 | weak scenario model |
| hyderabad | 49284 | 4.31 | 6.77 | 0.537 | 0.458 | 565600 | 11310 |  |
| mumbai | 55600 | 3.72 | 6.7 | 0.87 | 0.793 | 554300 | 11090 | low confidence (sea, roofs) |
| phalodi | 14763 | 5.13 | 5.33 | 0.436 | 0.358 | 530400 | 10610 |  |
| sriganganagar | 16226 | 6.18 | 7.02 | 0.119 | 0.12 | 484100 | 9680 | weak scenario model |
| titlagarh | 14763 | 2.59 | 3.08 | 0.396 | 0.543 | 558900 | 11180 |  |

Change from the Day 1 table: Hyderabad 4.78 to 4.31 C and Delhi 5.28 to 4.70 C (airports
removed), Bengaluru 3.92 to 3.78 C (airport and lake removed), Churu 3.92 to 3.41 C (seed
averaging; its old number came from one unlucky model). Others moved by 0.2 C or less.

### Critical reading

- **Where the model is trustworthy:** farm-dominated towns with a working land-cover model
  (Titlagarh, Bhubaneswar, Phalodi, Churu, Banda). Their top 10 are mostly real farmland.
- **Where it is not:** dense metros. Hot, bare, treeless ground in a metro is often a runway,
  roof, depot, ground or dump. Even with their airport and other boxes, Delhi, Hyderabad and
  Mumbai still have only 0 to 3 good zones in their top 10.
- **User-drawn boxes have no hand-drawn boxes.** The Visakhapatnam test box (Day 3) put a solar
  farm and an industrial ash yard at the top: 0 of 10 good.
- **Weak models:** Delhi (R2 0.045), Bilaspur (0.113), Sri Ganganagar (0.120). Their cooling
  numbers are mostly the model's average, and many blocks tie (Bilaspur: top 10 all 7.01 C).
- **Churu:** its top 300 is cooler than the town average (48.4 against 51.7 C). The labels call
  village houses 96 % built-up, and the model prefers replacing built-up ground.
- **Dry riverbeds** still reach the top 10 (Banda rank 1, Bilaspur). Known limit since Week 2.
- **Cooling is a statistical association**, not a physical simulation. Treat it as "where to
  look first", then check on the ground.

## How these results were produced and checked

- Code: `priority.py` with `N_SEEDS = 5`, `n_jobs = 1`, `MAX_TREE_NOW = 0.5`. Official run: all 11
  cities with `rerun_all.py` (`--skip-fetch`, no Earth Engine calls) on the demo PC, 11 October
  2026; every city ok, no retries. Full log: `data/week3_windows_check.md`.
- Checks run: `check_model.py` (monotone: 40.06 to 38.25 C, only falls, passed), `inspect_priority.py`,
  `stability.py`, Track 3 tests (13 passed), Track 1 Week 3 tests (5 passed), `node --check
  track4/app.js`, and the API serving the new files (`/api/priority/<city>` returns canopy and
  trees).

## Day 3 (11 Oct): three new boxes through the real system (demo PC)

| Box | Result | Minutes from request |
|---|---|---|
| Bhuj, Gujarat (new state, normal size) | done: 9,879 blocks, top-300 3.83 C, best 4.65 C, R2 0.342 / 0.163, about 10,930 trees | 2.4 |
| Visakhapatnam coast (part sea) | done: 9,879 blocks, 4,570 eligible, top-300 2.41 C, best 7.52 C, R2 0.374 / 0.628, water 26 % | 4.2 |
| Tiny box in Patna | failed with: "This area is too small or too cloudy to rank planting zones. Draw a bigger box." | 4.9 |

Jobs run one at a time, so the second and third waited for the first.

Photo check of the two new top 10s:
- **Bhuj:** 7 good (dry fields, scrub), 1 doubtful (plotted layout), 2 wrong (road, highway).
  Its scenario model is weak (R2 0.163), so treat the numbers with care.
- **Visakhapatnam:** 0 good. The top 10 is one industrial compound: solar panels, an ash or soil
  yard and its embankments. The 7.52 C best block sits on that yard. This is the clearest example
  of the main limit: a drawn box gets no hand-drawn exclusions.
- `.unmask(255)` (new land-cover downloads) did not change anything: both boxes had land cover
  everywhere (no 255 pixels). Class 0 (water) was kept: 0.8 % of Bhuj, 26 % of Visakhapatnam.
