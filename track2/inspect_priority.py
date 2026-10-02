"""Sanity checks on the Plant-here result.   python inspect_priority.py --slug bhubaneswar"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from priority import DATA, FEATURES_LAND, MONOTONE, train
import priority

parser = argparse.ArgumentParser()
parser.add_argument("--slug", required=True)
slug = parser.parse_args().slug

df = pd.read_csv(DATA / slug / "grid_features.csv")
elig = df[df.eligible]
top = elig.nsmallest(300, "rank")

print(f"Cells: {len(df)}   eligible: {len(elig)}   ({100 * len(elig) / len(df):.0f}%)")
print(f"Skipped: {int(priority.near_river_mask(df).sum())} near a river, "
      f"{int(priority.no_plant_mask(df, slug).sum())} in no-plant boxes (some overlap)")
print(f"Expected cooling, eligible cells:  median {elig.delta_t.median():.2f} C   "
      f"90th percentile {elig.delta_t.quantile(0.9):.2f} C   max {elig.delta_t.max():.2f} C")

print("\nTop 300 zones compared with the whole area:")
print(f"{'':16s}{'top 300':>10s}{'all cells':>12s}")
for col, label in [("lst_mean", "Temperature C"), ("tree_frac", "Tree cover"),
                   ("built_frac", "Built-up"), ("bare_frac", "Bare ground"), ("water_frac", "Water")]:
    print(f"{label:16s}{top[col].mean():10.2f}{df[col].mean():12.2f}")

plt.figure(figsize=(7, 4))
plt.hist(elig.delta_t, bins=40, color="#cb181d")
plt.xlabel("Expected cooling (C) with up to +20 points of tree cover")
plt.ylabel("Number of 100 m blocks")
plt.title(f"{slug}: expected cooling per block")
plt.tight_layout()
plt.savefig(DATA / slug / "cooling_histogram.png", dpi=150)
print(f"\nSaved {DATA / slug / 'cooling_histogram.png'}")

print("\nSensitivity: how much does the answer depend on the +20 choice?")
model, _ = train(df, FEATURES_LAND, MONOTONE)
for amount in [0.10, 0.20, 0.30]:
    priority.SCENARIO_ADD = amount
    base = df[[c for c in df.columns if c not in ("added", "delta_t", "eligible", "rank", "tier")]]
    scored = priority.score_cells(base, model, priority.blocked_mask(base, slug))
    best = scored[scored.eligible].nsmallest(300, "rank")
    print(f"  +{amount * 100:.0f} points: top-300 mean cooling {best.delta_t.mean():.2f} C")