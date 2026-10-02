"""The top 10 zones, with links to satellite photos.   python top_zones.py --slug bhubaneswar"""
import argparse
import json

from priority import DATA

parser = argparse.ArgumentParser()
parser.add_argument("--slug", required=True)
slug = parser.parse_args().slug

zones = json.loads((DATA / slug / "priority.geojson").read_text())["features"]
print("| Rank | Cooling C | Now C | Trees now | Built | Satellite photo | What is actually there? |")
print("|---|---|---|---|---|---|---|")
for z in zones[:10]:
    p = z["properties"]
    link = f"https://www.google.com/maps/@{p['lat']},{p['lon']},300m/data=!3m1!1e3"
    print(f"| {p['rank']} | {p['delta_t_c']} | {p['lst_now_c']} | {p['tree_pct_now']}% | "
          f"{p['built_pct']}% | [open]({link}) |  |")