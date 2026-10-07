"""Week 3 independent check: compare our Landsat heat numbers with NASA MODIS for the same dates.
Landsat (30 m, resampled) and MODIS Terra (1 km) both pass over in the late morning, so their
city averages should move together. MODIS is too coarse to show streets, which is why we do not
use it for the map, but it is a good second opinion on the city-wide numbers.
From the repository root, with the Track 1 environment active:

    python .\\track1\\modis_check.py
Writes data/modis_check.md.
"""
import json
from pathlib import Path
import ee
import numpy as np
from settings import ee_project
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MODIS = "MODIS/061/MOD11A2"     # 8-day land-surface temperature, 1 km, cloudy pixels already removed
BAND = "LST_Day_1km"
SCALE_FACTOR = 0.02             # stored value x 0.02 = kelvin
def modis_mean_c(bounds, start, end):
    """Average MODIS daytime surface temperature over the box, in Celsius."""
    south, west, north, east = bounds
    box = ee.Geometry.Rectangle([west, south, east, north])
    collection = ee.ImageCollection(MODIS).filterDate(start, end).select(BAND)
    count = collection.size().getInfo()
    if count == 0:
        return None, 0
    image = collection.mean().multiply(SCALE_FACTOR).subtract(273.15)
    value = image.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=box, scale=1000, maxPixels=1e9
    ).get(BAND).getInfo()
    return (round(value, 1) if value is not None else None), count
def main():
    ee.Initialize(project=ee_project())
    cities = json.loads((ROOT / "presets.json").read_text(encoding="utf-8-sig"))
    lines = [
        "| City | Landsat mean C (ours) | MODIS mean C | Difference C | MODIS 8-day images |",
        "|---|---|---|---|---|",
    ]
    ours, theirs = [], []
    for city in cities:
        meta_path = DATA / city["slug"] / "meta.json"
        if not meta_path.is_file():
            lines.append(f"| {city['name']} | not processed | - | - | - |")
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        landsat = meta["stats"]["lst_mean_c"]
        modis, count = modis_mean_c(meta["bounds"], meta["lst_date_start"], meta["lst_date_end"])
        if modis is None:
            lines.append(f"| {city['name']} | {landsat} | no data | - | {count} |")
            continue
        ours.append(landsat)
        theirs.append(modis)
        lines.append(f"| {city['name']} | {landsat} | {modis} | {landsat - modis:+.1f} | {count} |")
        print(f"{city['name']}: Landsat {landsat} C, MODIS {modis} C", flush=True)
    if len(ours) >= 3:
        r = float(np.corrcoef(ours, theirs)[0, 1])
        bias = float(np.mean(np.array(ours) - np.array(theirs)))
        mean_abs = float(np.mean(np.abs(np.array(ours) - np.array(theirs))))
        lines += [
            "",
            f"Cities compared: {len(ours)}",
            f"Correlation between the two (r): {r:.2f}",
            f"Average difference, Landsat minus MODIS: {bias:+.1f} C",
            f"Average size of the difference: {mean_abs:.1f} C",
            "",
            "A high r means our numbers rank the cities the same way as MODIS. A steady offset is",
            "expected: Landsat is a median of clear scenes at fine detail, MODIS an average of 1 km",
            "8-day composites.",
        ]
    destination = DATA / "modis_check.md"
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved: {destination}")
if __name__ == "__main__":
    main()
