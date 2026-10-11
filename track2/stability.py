"""How stable is the ranking?   python stability.py [--slugs bhubaneswar delhi] [--runs 4] [--per-run 5]

Re-trains the land-cover model several times, each run with its own set of random seeds
(XGBoost samples 80 % of the blocks for each tree, so the seed changes the model a little).
--per-run 1 tests one model per run (the Week 2 setup); --per-run 5 tests the seed-averaged
model priority.py uses now. It compares the runs:
  - spread of the top-300 mean cooling and of the best block
  - how many of the top-300 and top-10 zones stay the same between two runs (overlap)
  - rank correlation of the cooling of every eligible block between two runs (Spearman)
  - near-ties: eligible blocks within 0.05 C of the 300th zone's cooling. When there are many,
    which of them make the top 300 is close to arbitrary, so a low top-300 overlap is expected
Writes nothing into data/<slug>/; prints a Markdown table (save it with > ../data/stability.md).
"""
import argparse
import itertools
import json

import numpy as np
from scipy.stats import spearmanr
import priority as P


def grid_for(slug):
    out = P.DATA / slug
    meta = json.loads((out / "meta.json").read_text())
    lst, transform = P.read_band(out / "lst.tif")
    ndvi, _ = P.read_band(out / "ndvi.tif")
    lc, _ = P.align_landcover(out / "landcover.tif", out / "lst.tif")
    k = max(1, round(P.CELL_M / meta["scale_m"]))
    return P.build_grid(lc, lst, ndvi, transform, k)


def run_seed(df, blocked, seeds):
    model, _ = P.train(df, P.FEATURES_LAND, P.MONOTONE, seeds=seeds)
    scored = P.score_cells(df, model, blocked)
    elig = scored[scored.eligible]
    top = elig.nsmallest(P.TOP_N, "rank")
    keys = list(zip(top.row, top.col))
    cut = float(top.delta_t.min())
    near_ties = int((np.abs(elig.delta_t - cut) <= 0.05).sum())
    return (float(top.delta_t.mean()), float(top.delta_t.max()), set(keys), set(keys[:10]),
            scored.delta_t.where(scored.eligible), near_ties)


def overlap(sets):
    pairs = list(itertools.combinations(sets, 2))
    return float(np.mean([len(a & b) / max(len(a), 1) for a, b in pairs]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slugs", nargs="*")
    ap.add_argument("--runs", type=int, default=4)
    ap.add_argument("--per-run", type=int, default=P.N_SEEDS)
    a = ap.parse_args()
    slugs = a.slugs or sorted(p.parent.name for p in P.DATA.glob("*/priority_summary.json")
                               if not p.parent.name.startswith("custom-"))
    print(f"{a.runs} runs per city, {a.per_run} seed(s) averaged per run, no seed shared between runs. "
          "Overlap = share of zones two runs have in common (1.00 = identical).\n")
    print("| Area | Top-300 mean C (min to max) | Best block C (min to max) | Top-300 overlap | Top-10 overlap | Rank correlation | Near-ties at cut-off |")
    print("|---|---|---|---|---|---|---|")
    for slug in slugs:
        df = grid_for(slug)
        blocked = P.blocked_mask(df, slug)
        runs = [run_seed(df, blocked, range(r * a.per_run, (r + 1) * a.per_run)) for r in range(a.runs)]
        means, bests = [r[0] for r in runs], [r[1] for r in runs]
        print(f"| {slug} | {np.mean(means):.2f} ({min(means):.2f} to {max(means):.2f}) | "
              f"{np.mean(bests):.2f} ({min(bests):.2f} to {max(bests):.2f}) | "
              f"{overlap([r[2] for r in runs]):.2f} | {overlap([r[3] for r in runs]):.2f} | "
              f"{np.mean([spearmanr(x[4], y[4], nan_policy='omit')[0] for x, y in itertools.combinations(runs, 2)]):.3f} | "
              f"{int(np.mean([r[5] for r in runs]))} |", flush=True)


if __name__ == "__main__":
    main()
