import json
from pathlib import Path

DATA = Path("../data")
KEYS = ["city", "display_name", "bounds", "crs", "date_start", "date_end",
        "width_px", "height_px", "layers", "stats"]
PREVIEWS = ["rgb", "ndvi", "lst", "landcover", "priority"]

for city_dir in DATA.iterdir():
    if not city_dir.is_dir():
        continue
    print("Checking", city_dir.name)
    meta_path = city_dir / "meta.json"
    if not meta_path.exists():
        print("  MISSING meta.json")
    else:
        meta = json.loads(meta_path.read_text())
        for k in KEYS:
            if k not in meta:
                print("  meta.json missing key:", k)
        if "bounds" in meta:
            s, w, n, e = meta["bounds"]
            if not (6 < s < 38 and 67 < w < 98 and s < n and w < e):
                print("  bounds NOT in [south, west, north, east] order:", meta["bounds"])
    for name in PREVIEWS:
        if not (city_dir / "preview" / f"{name}.png").exists():
            print("  missing preview/" + name + ".png")
print("Done")