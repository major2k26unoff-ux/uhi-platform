"""Re-run priority.py on every city folder in data/, with the current code.
    python rerun_all.py

Skips custom-* test jobs. Reuses landcover.tif when it is already there.
One city failing does not stop the others. Prints a short table at the end.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

results = []
for meta_path in sorted(DATA.glob("*/meta.json")):
    folder = meta_path.parent
    slug = folder.name
    if slug.startswith("custom-"):
        continue
    meta = json.loads(meta_path.read_text())
    if meta.get("contract_version") != 2:
        results.append((slug, "SKIPPED: meta.json is not contract v2", ""))
        continue

    cmd = [sys.executable, str(HERE / "priority.py"), "--slug", slug]
    if (folder / "landcover.tif").exists():
        cmd.append("--skip-fetch")
    print(f"\n===== {slug} =====", flush=True)
    t0 = time.time()
    run = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    mins = f"{(time.time() - t0) / 60:.1f} min"
    if run.returncode != 0:
        last = (run.stderr.strip().splitlines() or ["no error text"])[-1]
        print(run.stderr[-1500:])
        results.append((slug, f"FAILED: {last}", mins))
        continue
    s = json.loads((folder / "priority_summary.json").read_text())
    note = "low data" if s.get("low_data") else ""
    results.append((slug, f"ok  blocks {s['cells_total']}  top-300 {s['delta_t']['top_mean_c']} C  "
                          f"best {s['delta_t']['top_max_c']} C  {note}", mins))
    print(results[-1][1], flush=True)

print("\n===== Summary =====")
for slug, msg, mins in results:
    print(f"{slug:16s} {mins:>8s}  {msg}")