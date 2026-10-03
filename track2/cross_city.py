"""One row per processed area, for the report.    python cross_city.py > ../data/cross_city.md"""
import json

from priority import DATA

print("| Area | Blocks | Top-300 cooling C | Best block C | R2 with greenness | R2 land cover only | Note |")
print("|---|---|---|---|---|---|---|")
for summary_path in sorted(DATA.glob("*/priority_summary.json")):
    if summary_path.parent.name.startswith("custom-"):
        continue  # test jobs from the website or worker, not preset cities
    s = json.loads(summary_path.read_text())
    g, l = s["models"]["with_greenness"], s["models"]["land_cover_only"]
    notes = []
    if s.get("low_data"):
        notes.append("small area - treat with care")
    if l["r2"] < 0.2:
        notes.append("weak scenario model (R2 below 0.2) - cooling numbers uncertain")
    note = "; ".join(notes)
    print(f"| {summary_path.parent.name} | {s['cells_total']} | {s['delta_t']['top_mean_c']} | {s['delta_t']['top_max_c']} | "
          f"{g['r2']} | {l['r2']} | {note} |")