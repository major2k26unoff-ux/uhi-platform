"""Does the land-cover model behave sensibly?   python check_model.py --slug bhubaneswar

1. Compares the two models (the ablation table for the report).
2. Takes a typical block and slowly adds trees: predicted temperature must never go up.
"""
import argparse

import pandas as pd

from priority import DATA, FEATURES_GREEN, FEATURES_LAND, MONOTONE, train

parser = argparse.ArgumentParser()
parser.add_argument("--slug", required=True)
slug = parser.parse_args().slug

df = pd.read_csv(DATA / slug / "grid_features.csv")

model_green, m_green = train(df, FEATURES_GREEN)
model_land, m_land = train(df, FEATURES_LAND, MONOTONE)

print("Model comparison (geographic split: west trains, east tests)")
print(f"{'':28s}{'RMSE C':>8s}{'MAE C':>8s}{'R2':>8s}")
for name, m in [("With greenness (Week 1)", m_green), ("Land cover only (scenario)", m_land)]:
    print(f"{name:28s}{m['rmse_c']:8.2f}{m['mae_c']:8.2f}{m['r2']:8.3f}")

print("\nWhat the land-cover model relies on:")
for feature, weight in sorted(zip(FEATURES_LAND, model_land.feature_importances_), key=lambda x: -x[1]):
    print(f"  {feature:12s} {weight:.3f}")

typical = df[FEATURES_LAND].median().to_frame().T
print("\nA typical block, with more and more trees (taken from built-up area):")
print("  tree %   predicted C")
for tree in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]:
    cell = typical.copy()
    extra = tree - float(cell.tree_frac.iloc[0])
    cell["tree_frac"] = tree
    cell["built_frac"] = max(0.0, float(cell.built_frac.iloc[0]) - extra)
    print(f"  {tree * 100:5.0f}    {model_land.predict(cell[FEATURES_LAND])[0]:8.2f}")