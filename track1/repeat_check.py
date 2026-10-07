"""Week 3 repeat test: does running the pipeline twice give the same layers?
Step 1, before the second run, keep a copy of the current files:
    python .\\track1\\repeat_check.py --slug titlagarh --save
Step 2, run the pipeline again for the same city (same command as before).
Step 3, compare:
    python .\\track1\\repeat_check.py --slug titlagarh
Writes data/repeat_<slug>.md. The copy is kept in data/_repeat/<slug>/ and can be deleted after.
"""
import argparse
import json
import shutil
from pathlib import Path
import numpy as np
import rasterio
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LAYERS = ["rgb", "ndvi", "ndbi", "ndwi", "lst"]
def read(path):
    with rasterio.open(path) as src:
        return src.read(masked=True).astype("float64").filled(np.nan), (src.crs, src.transform, src.width, src.height)
def compare(slug):
    now_dir, before_dir = DATA / slug, DATA / "_repeat" / slug
    if not before_dir.is_dir():
        raise SystemExit(f"No saved copy in {before_dir}. Run with --save before the second run.")
    lines = [f"Repeat test for {slug}", "",
             "| Layer | Same grid | Pixels compared | Largest difference | Average difference | Verdict |",
             "|---|---|---|---|---|---|"]
    for name in LAYERS:
        a, grid_a = read(before_dir / f"{name}.tif")
        b, grid_b = read(now_dir / f"{name}.tif")
        if grid_a != grid_b or a.shape != b.shape:
            lines.append(f"| {name} | no | - | - | - | DIFFERENT GRID |")
            continue
        if not np.array_equal(np.isfinite(a), np.isfinite(b)):
            lines.append(f"| {name} | yes | - | - | - | CHANGED VALID MASK |")
            continue
        both = np.isfinite(a) & np.isfinite(b)
        if not both.any():
            lines.append(f"| {name} | yes | 0 | - | - | NOT MEASURED |")
            continue
        diff = np.abs(a - b)[both]
        biggest = float(diff.max()) if diff.size else 0.0
        average = float(diff.mean()) if diff.size else 0.0
        verdict = "identical" if biggest == 0 else ("tiny change" if biggest < 0.01 * max(1.0, np.nanmax(np.abs(a))) else
                "CHANGED")
        lines.append(f"| {name} | yes | {int(both.sum())} | {biggest:.4g} | {average:.4g} | {verdict} |")
    meta_a = json.loads((before_dir / "meta.json").read_text(encoding="utf-8-sig"))["stats"]
    meta_b = json.loads((now_dir / "meta.json").read_text(encoding="utf-8-sig"))["stats"]
    lines += ["", "| Statistic | First run | Second run |", "|---|---|---|"]
    lines += [f"| {key} | {meta_a[key]} | {meta_b.get(key)} |" for key in meta_a]
    destination = DATA / f"repeat_{slug}.md"
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved: {destination}")
def main():
    parser = argparse.ArgumentParser(description="Check that a second run gives the same layers.")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--save", action="store_true", help="copy the current files before re-running")
    args = parser.parse_args()
    if not args.slug or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.slug):
        parser.error("slug must contain only lowercase letters, digits and hyphens")
    if args.save:
        source, target = DATA / args.slug, DATA / "_repeat" / args.slug
        if not (source / "meta.json").is_file():
            raise SystemExit(f"{args.slug} has not been processed yet.")
        if target.exists():
            raise SystemExit(f"Saved copy already exists in {target}; preserve or remove it before saving again.")
        target.mkdir(parents=True)
        for name in LAYERS:
            shutil.copy2(source / f"{name}.tif", target / f"{name}.tif")
        shutil.copy2(source / "meta.json", target / "meta.json")
        print(f"Saved a copy in {target}. Now run the pipeline again, then run this without --save.")
    else:
        compare(args.slug)
if __name__ == "__main__":
    main()
