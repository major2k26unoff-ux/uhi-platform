"""Where does the cooling in the top 300 come from: trees, or bare ground disappearing?
    python diag_scenario.py --slug bhubaneswar

Same land-cover model as priority.py. For the top 300 zones it compares three "what if" runs:
  scenario   : the team scenario (trees added, bare ground used up first, then built-up)
  trees only : the same tree increase, but taken from farmland/grass; bare ground untouched
  bare only  : bare ground removed (given to farmland), no new trees
"""
import argparse

import numpy as np
import pandas as pd

from priority import DATA, FEATURES_LAND, MONOTONE, train

parser = argparse.ArgumentParser()
parser.add_argument("--slug", required=True)
slug = parser.parse_args().slug

df = pd.read_csv(DATA / slug / "grid_features.csv")
model, _ = train(df, FEATURES_LAND, MONOTONE)
top = df[df.eligible].nsmallest(300, "rank").copy()


def take_from_farmland(d, amount):
    """Remove `amount` of area from crops and grass, in proportion. Returns the new table and what was taken."""
    d = d.copy()
    farm = (d.crops_frac + d.grass_frac).clip(lower=1e-9)
    taken = np.minimum(amount, farm)
    d["crops_frac"] = d.crops_frac - taken * d.crops_frac / farm
    d["grass_frac"] = d.grass_frac - taken * d.grass_frac / farm
    return d, taken


now = model.predict(top[FEATURES_LAND])

# trees only: add the same tree cover, take it from farmland/grass, leave bare ground alone
trees, taken = take_from_farmland(top, top.added)
trees["tree_frac"] = top.tree_frac + taken
cool_trees = now - model.predict(trees[FEATURES_LAND])

# bare only: bare ground becomes farmland, no new trees
bare = top.copy()
bare["crops_frac"] = top.crops_frac + top.bare_frac
bare["bare_frac"] = 0.0
cool_bare = now - model.predict(bare[FEATURES_LAND])

print(f"Top 300 zones, mean cooling in C")
print(f"  team scenario  : {top.delta_t.mean():.2f}")
print(f"  trees only     : {cool_trees.mean():.2f}   (same tree increase, bare ground untouched)")
print(f"  bare only      : {cool_bare.mean():.2f}   (bare ground removed, no new trees)")
print(f"\nMean bare ground in these zones: {top.bare_frac.mean():.2f}   mean tree cover added: {top.added.mean():.2f}")
print("\nFirst 10 zones:")
out = pd.DataFrame({"rank": top["rank"], "scenario": top.delta_t, "trees_only": cool_trees,
                    "bare_only": cool_bare, "bare_frac": top.bare_frac, "added": top.added})
print(out.head(10).round(2).to_string(index=False))