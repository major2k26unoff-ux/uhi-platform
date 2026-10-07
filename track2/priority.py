"""
Track 2: where to plant trees, and how much cooler it would get.

Needs Track 1's files in data/<slug>/ first (meta.json, lst.tif, ndvi.tif).

    python priority.py --slug bhubaneswar
    python priority.py --slug bhubaneswar --skip-fetch   # reuse landcover.tif already on disk

Writes into data/<slug>/:
    landcover.tif  grid_features.csv  priority.geojson  priority_summary.json
    preview/landcover.png  preview/priority.png
"""
import argparse
import json
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import Resampling, reproject
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from scipy import ndimage
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

DATA = Path(__file__).resolve().parent.parent / "data"
NO_PLANT = Path(__file__).resolve().parent / "no_plant.json"   # hand-drawn no-plant boxes per area

CELL_M = 100          # grid cell size in metres
SCENARIO_ADD = 0.20   # add up to 20 percentage points of tree cover per cell
MIN_ROOM = 0.05       # a cell needs at least 5 % of TREE_SOURCES to plant on
TREE_SOURCES = ["built_frac", "grass_frac", "shrub_frac", "crops_frac"]   # trees replace these, in order
WET_BLOCK = 0.2           # a block at least 20 % water counts as wet
RIVER_MIN_CELLS = 20      # wet blocks joined together, at least this many = river or big lake (0.2 km2)
RIVER_BUFFER_CELLS = 3    # skip blocks within 3 blocks (about 300 m) of a river: riverbeds, sandbanks
TOP_N = 300           # zones written to priority.geojson
MAX_PNG_SIDE = 1600
DW_START, DW_END = "2024-03-01", "2024-05-31"
LC_NODATA = 255       # "no data" for land cover; 0 is a real class (water)

CLASSES = [("water_frac", 0), ("tree_frac", 1), ("grass_frac", 2), ("crops_frac", 4),
           ("shrub_frac", 5), ("built_frac", 6), ("bare_frac", 7)]
FEATURES_LAND = ["tree_frac", "grass_frac", "crops_frac", "shrub_frac",
                 "built_frac", "water_frac", "bare_frac"]
FEATURES_GREEN = FEATURES_LAND + ["ndvi_mean"]

# Physically sensible rules the land-cover model must obey:
#   more trees or grass -> never hotter (-1)
#   more built or bare  -> never cooler (+1)
MONOTONE = {"tree_frac": -1, "grass_frac": -1, "built_frac": 1, "bare_frac": 1}

DW_COLOURS = ["#419BDF", "#397D49", "#88B053", "#7A87C6", "#E49635",
              "#DFC35A", "#C4281B", "#A59B8F", "#B39FE1"]
TIERS = {1: "Highest", 2: "High", 3: "Medium", 4: "Low"}


def progress(pct, stage):
    print(f"PROGRESS {pct} {stage}", flush=True)


# ---------- reading and writing ----------

def read_band(path):
    """For continuous layers (lst, ndvi). Land cover must use align_landcover, never this."""
    with rasterio.open(path) as src:
        return src.read(1, masked=True).astype("float32").filled(np.nan), src.transform


def align_landcover(lc_path, ref_path):
    """Land cover resampled onto the reference (lst.tif) pixel grid, as float32 with NaN = no data.

    Two traps. (1) landcover.tif declares nodata=0, but Dynamic World class 0 is water, so the
    file is read as a plain array and never through the nodata mask; LC_NODATA (255) marks
    'no data' instead. (2) Earth Engine exports land cover with its origin one pixel off from
    lst.tif, so trimming sizes is not enough: it is reprojected onto lst.tif's exact grid.
    """
    with rasterio.open(ref_path) as ref:
        dst_transform, dst_crs, dst_shape = ref.transform, ref.crs, ref.shape
    with rasterio.open(lc_path) as src:
        lc_raw = src.read(1)
        src_transform, src_crs = src.transform, src.crs
    dst = np.full(dst_shape, LC_NODATA, dtype=lc_raw.dtype)
    reproject(lc_raw, dst, src_transform=src_transform, src_crs=src_crs, src_nodata=None,
              dst_transform=dst_transform, dst_crs=dst_crs, dst_nodata=LC_NODATA,
              resampling=Resampling.nearest)
    lc = dst.astype("float32")
    lc[dst == LC_NODATA] = np.nan
    return lc, dst_transform


def write_png(rgba, path):
    img = Image.fromarray(rgba)
    if max(img.size) > MAX_PNG_SIDE:
        ratio = MAX_PNG_SIDE / max(img.size)
        img = img.resize((round(img.width * ratio), round(img.height * ratio)), Image.NEAREST)
    img.save(path, optimize=True)


def landcover_png(lc, path):
    table = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] + [220] for c in DW_COLOURS], dtype=np.uint8)
    idx = np.nan_to_num(lc, nan=0).astype(int).clip(0, 8)
    rgba = table[idx]
    rgba[np.isnan(lc), 3] = 0
    write_png(rgba, path)


def priority_png(canvas, path, vmax):
    alpha = np.where(np.isnan(canvas), 0, 215).astype(np.uint8)
    norm = np.nan_to_num(np.clip(canvas / vmax, 0, 1))
    rgba = (plt.get_cmap("Reds")(0.15 + 0.85 * norm) * 255).astype(np.uint8)
    rgba[..., 3] = alpha
    write_png(rgba, path)


# ---------- step 1: land cover from Dynamic World ----------

def fetch_landcover(out, meta):
    import ee
    import geemap
    from settings import ee_project

    ee.Initialize(project=ee_project())
    south, west, north, east = meta["bounds"]
    aoi = ee.Geometry.Rectangle([west, south, east, north])
    landcover = (ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
                 .filterBounds(aoi)
                 .filterDate(DW_START, DW_END)
                 .select("label")
                 .mode()
                 .unmask(LC_NODATA)   # no observations -> 255, not the export's masked 0 (= water)
                 .clip(aoi))
    path = out / "landcover.tif"
    geemap.ee_export_image(landcover, filename=str(path), scale=meta["scale_m"],
                           region=aoi, crs="EPSG:4326", file_per_band=False)
    if not path.exists():
        raise RuntimeError("Earth Engine did not return landcover.tif")


# ---------- step 2: the 100 m grid ----------

def crop_to_common(*arrays):
    """Layers can differ by a pixel at the edge. Trim them to the same size, but refuse bigger gaps."""
    h = min(a.shape[0] for a in arrays)
    w = min(a.shape[1] for a in arrays)
    if max(a.shape[0] for a in arrays) - h > 2 or max(a.shape[1] for a in arrays) - w > 2:
        raise RuntimeError(f"Layers do not line up: {[a.shape for a in arrays]}")
    return [a[:h, :w] for a in arrays]


def block_mean(arr, k):
    """Average every k x k block of pixels into one value."""
    h, w = (arr.shape[0] // k) * k, (arr.shape[1] // k) * k
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)  # all-empty blocks give NaN, which we want
        return np.nanmean(arr[:h, :w].reshape(h // k, k, w // k, k), axis=(1, 3))


def build_grid(lc, lst, ndvi, transform, k):
    features = {}
    for name, code in CLASSES:
        is_class = np.where(np.isnan(lc), np.nan, (lc == code).astype("float32"))
        features[name] = block_mean(is_class, k)

    rows, cols = features["tree_frac"].shape
    rr, cc = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    cell_w = transform.a * k   # degrees, positive
    cell_h = transform.e * k   # degrees, negative (rows go south)
    west = transform.c + cc * cell_w
    north = transform.f + rr * cell_h

    df = pd.DataFrame({
        "row": rr.ravel(), "col": cc.ravel(),
        "west": west.ravel(), "east": (west + cell_w).ravel(),
        "north": north.ravel(), "south": (north + cell_h).ravel(),
        **{name: arr.ravel() for name, arr in features.items()},
        "ndvi_mean": block_mean(ndvi, k).ravel(),
        "lst_mean": block_mean(lst, k).ravel(),
    })
    df["lon"] = (df.west + df.east) / 2
    df["lat"] = (df.north + df.south) / 2
    return df.dropna(subset=["lst_mean", "ndvi_mean", "tree_frac"]).reset_index(drop=True)


# ---------- step 3: two models ----------

def train(df, features, monotone=None):
    """Score on a GEOGRAPHIC split (west trains, east tests), then refit on every cell for the scenario."""
    params = dict(n_estimators=300, max_depth=5, learning_rate=0.05,
                  subsample=0.8, random_state=42, n_jobs=-1)
    if monotone:
        params["monotone_constraints"] = "(" + ",".join(str(monotone.get(f, 0)) for f in features) + ")"

    split = df.lon.median()
    train_part, test_part = df[df.lon <= split], df[df.lon > split]
    scorer = XGBRegressor(**params).fit(train_part[features], train_part.lst_mean)
    pred = scorer.predict(test_part[features])
    metrics = {
        "features": features,
        "rmse_c": round(float(np.sqrt(mean_squared_error(test_part.lst_mean, pred))), 3),
        "mae_c": round(float(mean_absolute_error(test_part.lst_mean, pred)), 3),
        "r2": round(float(r2_score(test_part.lst_mean, pred)), 3),
        "train_cells": int(len(train_part)),
        "test_cells": int(len(test_part)),
    }
    if monotone:
        metrics["monotone"] = monotone
    final = XGBRegressor(**params).fit(df[features], df.lst_mean)
    return final, metrics


# ---------- step 4: the "what if" ----------

def add_trees(df):
    """Scenario: add up to 20 points of tree cover, taken from built-up first, then grass, shrub, crops.

    Bare ground is never touched. In Bhubaneswar the land-cover labels call airport strips and
    riverbeds "bare", and the model treats bare ground as a heat marker. Removing it credited
    trees with cooling they do not cause (Week 2, Day 4 check: 2.87 of 3.43 C came from bare
    ground disappearing). Now the predicted change comes from the trees.
    """
    s = df.copy()
    room = s[TREE_SOURCES].sum(axis=1)
    added = np.minimum(SCENARIO_ADD, room)
    left = added.copy()
    for col in TREE_SOURCES:
        take = np.minimum(left, s[col])
        s[col] = s[col] - take
        left = left - take
    s["tree_frac"] = s.tree_frac + added
    return s, added


def near_river_mask(df):
    """True for blocks within RIVER_BUFFER_CELLS blocks of a large water body (river, big lake).

    Dry riverbeds and sandbanks sit beside river channels, and the land-cover labels call them
    crops or bare ground, so no land-cover rule can spot them. Distance to the river can.
    Small ponds (fewer than RIVER_MIN_CELLS wet blocks joined together) are ignored, so a city
    tank does not knock out a whole neighbourhood.
    """
    rows, cols = int(df.row.max()) + 1, int(df.col.max()) + 1
    wet = np.zeros((rows, cols), dtype=bool)
    w = df[df.water_frac >= WET_BLOCK]
    wet[w.row.values, w.col.values] = True
    labels, _ = ndimage.label(wet, structure=np.ones((3, 3)))
    sizes = np.bincount(labels.ravel())
    keep = np.nonzero(sizes >= RIVER_MIN_CELLS)[0]
    keep = keep[keep != 0]                                   # label 0 is "not water"
    river = np.isin(labels, keep)
    near = ndimage.binary_dilation(river, structure=np.ones((3, 3)), iterations=RIVER_BUFFER_CELLS)
    return near[df.row.values, df.col.values]


def blocked_mask(df, slug):
    """Blocks nobody can plant on: near a river, or inside a hand-drawn no-plant box."""
    return near_river_mask(df) | no_plant_mask(df, slug)


def no_plant_mask(df, slug):
    """True for blocks inside a hand-drawn no-plant box (airport, riverbed) listed for this area
    in track2/no_plant.json. Areas not listed there get no boxes: the rule cannot see them."""
    mask = np.zeros(len(df), dtype=bool)
    if not NO_PLANT.exists():
        return mask
    for box in json.loads(NO_PLANT.read_text()).get(slug, []):
        south, west, north, east = box["bounds"]
        mask |= ((df.lat >= south) & (df.lat <= north) & (df.lon >= west) & (df.lon <= east)).to_numpy()
    return mask


def score_cells(df, model, blocked=None):
    after, added = add_trees(df)
    df = df.copy()
    df["added"] = added
    # Model versus model: the same model predicts both, so its own bias cancels out.
    df["delta_t"] = model.predict(df[FEATURES_LAND]) - model.predict(after[FEATURES_LAND])
    df["eligible"] = (df.added >= MIN_ROOM) & (df.water_frac < 0.05)
    if blocked is not None:
        df["eligible"] = df.eligible & ~blocked

    ranked = df[df.eligible].sort_values("delta_t", ascending=False)
    df["rank"] = 0
    df.loc[ranked.index, "rank"] = np.arange(1, len(ranked) + 1)
    share = df["rank"] / max(len(ranked), 1)
    df["tier"] = np.select([share <= 0.10, share <= 0.30, share <= 0.60], [1, 2, 3], default=4)
    df.loc[~df.eligible, "tier"] = 0
    return df


# ---------- step 5: outputs ----------

def zone_feature(r):
    ring = [[r.west, r.south], [r.east, r.south], [r.east, r.north], [r.west, r.north], [r.west, r.south]]
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[[round(x, 6), round(y, 6)] for x, y in ring]]},
        "properties": {
            "rank": int(r["rank"]),
            "tier": int(r.tier),
            "tier_label": TIERS[int(r.tier)],
            "delta_t_c": round(float(r.delta_t), 2),
            "lst_now_c": round(float(r.lst_mean), 1),
            "lst_after_c": round(float(r.lst_mean - r.delta_t), 1),
            "tree_pct_now": int(round(100 * r.tree_frac)),
            "tree_pct_after": int(round(100 * (r.tree_frac + r.added))),
            "built_pct": int(round(100 * r.built_frac)),
            "lat": round(float(r.lat), 5),
            "lon": round(float(r.lon), 5),
        },
    }


def write_outputs(out, slug, df, shape, k, metrics_green, metrics_land):
    df.to_csv(out / "grid_features.csv", index=False)

    top = df[df.eligible].nsmallest(TOP_N, "rank")
    geojson = {"type": "FeatureCollection", "features": [zone_feature(r) for _, r in top.iterrows()]}
    (out / "priority.geojson").write_text(json.dumps(geojson))

    # Picture: one value per cell, stretched back to the full image size so it lines up with the other layers
    rows, cols = int(df.row.max()) + 1, int(df.col.max()) + 1
    cells = np.full((rows, cols), np.nan, dtype="float32")
    elig = df[df.eligible]
    cells[elig.row.values, elig.col.values] = np.clip(elig.delta_t.values, 0, None)
    stretched = np.repeat(np.repeat(cells, k, axis=0), k, axis=1)
    canvas = np.full(shape, np.nan, dtype="float32")
    h, w = min(shape[0], stretched.shape[0]), min(shape[1], stretched.shape[1])
    canvas[:h, :w] = stretched[:h, :w]
    vmax = max(float(np.nanpercentile(elig.delta_t, 95)), 0.1) if len(elig) else 1.0
    priority_png(canvas, out / "preview" / "priority.png", vmax)

    summary = {
        "contract_version": 2,
        "slug": slug,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "scenario": {
            "description": "Add up to 20 percentage points of tree cover in each 100 m cell, "
                           "replacing built-up area first, then grass, shrub and crops; "
                           "bare ground and water are left unchanged",
            "max_added_tree_frac": SCENARIO_ADD,
        },
        "cells_total": int(len(df)),
        "cells_eligible": int(df.eligible.sum()),
        "top_zones": int(len(top)),
        "low_data": bool(len(df) < 2000),
        "delta_t": {
            "top_mean_c": round(float(top.delta_t.mean()), 2) if len(top) else 0.0,
            "top_max_c": round(float(top.delta_t.max()), 2) if len(top) else 0.0,
            "eligible_median_c": round(float(elig.delta_t.median()), 2) if len(elig) else 0.0,
        },
        "models": {"with_greenness": metrics_green, "land_cover_only": metrics_land},
        "note": "Estimated from this area's own data. A statistical association, not a physical simulation.",
    }
    (out / "priority_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


# ---------- the whole thing ----------

def compute_priority(slug, skip_fetch=False):
    out = DATA / slug
    meta_path = out / "meta.json"
    if not meta_path.exists():
        raise SystemExit(f"No meta.json for '{slug}'. Track 1's pipeline must run first.")
    meta = json.loads(meta_path.read_text())
    (out / "preview").mkdir(exist_ok=True)

    if skip_fetch and (out / "landcover.tif").exists():
        progress(5, "Using land cover already on disk")
    else:
        progress(5, "Fetching Dynamic World land cover")
        fetch_landcover(out, meta)

    progress(30, "Building 100 m grid")
    lst, transform = read_band(out / "lst.tif")
    ndvi, ndvi_transform = read_band(out / "ndvi.tif")
    lc, lc_transform = align_landcover(out / "landcover.tif", out / "lst.tif")
    if not (lc.shape == lst.shape == ndvi.shape and lc_transform == transform == ndvi_transform):
        raise RuntimeError(f"Layers not on one grid after alignment: shapes {lc.shape} {lst.shape} {ndvi.shape}, "
                           f"transforms {lc_transform} {transform} {ndvi_transform}")
    lc, lst, ndvi = crop_to_common(lc, lst, ndvi)   # final guard; a no-op once aligned
    landcover_png(lc, out / "preview" / "landcover.png")

    k = max(1, round(CELL_M / meta["scale_m"]))
    df = build_grid(lc, lst, ndvi, transform, k)
    if len(df) < 200:
        raise RuntimeError(f"Only {len(df)} usable grid cells - area too small or too cloudy.")

    progress(50, "Training model with greenness (for accuracy report)")
    _, metrics_green = train(df, FEATURES_GREEN)

    progress(70, "Training land-cover model (for the planting scenario)")
    model_land, metrics_land = train(df, FEATURES_LAND, MONOTONE)

    progress(85, "Ranking zones by expected cooling")
    df = score_cells(df, model_land, blocked_mask(df, slug))

    progress(95, "Writing priority map")
    summary = write_outputs(out, slug, df, lst.shape, k, metrics_green, metrics_land)
    progress(100, "Priority map ready")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Cooling priority for one processed area")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--skip-fetch", action="store_true",
                        help="reuse landcover.tif already on disk instead of downloading it")
    args = parser.parse_args()
    summary = compute_priority(args.slug, args.skip_fetch)
    print(json.dumps(summary["delta_t"], indent=2))


if __name__ == "__main__":
    main()