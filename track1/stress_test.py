"""Week 3 stress test: send six very different boxes through the real worker and time each one.
Start the worker first, in another window:
    python .\\track1\\worker.py
Then, from the repository root:
    python .\\track1\\stress_test.py            # queue the six boxes and wait for them
    python .\\track1\\stress_test.py --report   # only rebuild the table from finished jobs
Writes data/stress_test.md. Every box gets a slug starting with "custom-stress-". Track 2's
rerun_all.py and cross_city.py already skip "custom-" folders, so these never mix with the
preset cities.
"""
import argparse
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "data" / "jobs"
REPORT = ROOT / "data" / "stress_test.md"
WAIT_LIMIT_MIN = 90          # give up waiting after this long; the table still records what finished
# kind, display name, south, west, north, east  (each side is at most 0.3 degrees)
BOXES = [
    ("coastal",    "Puri, Odisha",             19.78, 85.78, 19.86, 85.88),
    ("desert",     "Jaisalmer, Rajasthan",     26.88, 70.87, 26.96, 70.97),
    ("hilly",      "Shimla, Himachal Pradesh", 31.07, 77.13, 31.13, 77.21),
    ("cloudy",     "Shillong, Meghalaya",      25.54, 91.84, 25.61, 91.92),
    ("tiny",       "Bhubaneswar (tiny box)",   20.295, 85.82, 20.307, 85.832),
    ("near-limit", "Kolkata, West Bengal",     22.45, 88.25, 22.74, 88.54),
]
def now():
    return datetime.now().isoformat(timespec="seconds")
def queue(kind, name, south, west, north, east):
    """Write one request file, exactly as the website's Analyze button would."""
    job_id = uuid.uuid4().hex[:8]
    request = {
        "job_id": job_id,
        "slug": f"custom-stress-{kind}-{job_id}",
        "display_name": f"{name} [{kind}]",
        "bbox": {"south": south, "west": west, "north": north, "east": east},
        "source": "stress-test",

        "kind": kind,
        "created_at": now(),
    }
    JOBS.mkdir(parents=True, exist_ok=True)
    temporary = JOBS / f"{job_id}.request.tmp"
    temporary.write_text(json.dumps(request, indent=2), encoding="utf-8")
    os.replace(temporary, JOBS / f"{job_id}.request.json")
    return job_id
def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
def stress_jobs():
    """Every stress-test request with its status (None while still queued)."""
    jobs = []
    for request_path in sorted(JOBS.glob("*.request.json"), key=lambda p: p.stat().st_mtime):
        request = read_json(request_path)
        if not request or request.get("source") != "stress-test":
            continue
        status = read_json(JOBS / f"{request['job_id']}.status.json")
        jobs.append((request, status))
    return jobs
def minutes(request, status):
    """Minutes from queueing to the worker's last update."""
    if not status or status.get("status") not in ("done", "failed"):
        return None
    start = datetime.fromisoformat(request["created_at"])
    end = datetime.fromisoformat(status["updated_at"])
    return round((end - start).total_seconds() / 60, 1)
def box_km(bbox):
    import math
    lat = (bbox["north"] + bbox["south"]) / 2
    height = (bbox["north"] - bbox["south"]) * 111
    width = (bbox["east"] - bbox["west"]) * 111 * math.cos(math.radians(lat))
    return f"{width:.1f} x {height:.1f}"
def write_report():
    lines = [
        "| Kind | Area | Box (km) | Result | Minutes | Pixel m | Message |",
        "|---|---|---|---|---|---|---|",
    ]
    for request, status in stress_jobs():
        kind = request.get("kind", "-")
        result = status.get("status") if status else "queued"
        meta = read_json(ROOT / "data" / request["slug"] / "meta.json") or {}
        message = (status or {}).get("error") or ""
        took = minutes(request, status)
        lines.append(
            f"| {kind} | {request['display_name']} | {box_km(request['bbox'])} | {result} | "
            f"{'-' if took is None else took} | {meta.get('scale_m', '-')} | {message} |"
        )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved: {REPORT}")
def main():
    parser = argparse.ArgumentParser(description="Stress-test the worker with six different boxes.")
    parser.add_argument("--report", action="store_true", help="only rebuild the table")
    args = parser.parse_args()
    if not args.report:
        ids = [queue(*box) for box in BOXES]
        print(f"Queued {len(ids)} boxes. The worker runs them one at a time.")
        deadline = time.time() + WAIT_LIMIT_MIN * 60
        while time.time() < deadline:
            finished = [s for r, s in stress_jobs()
                        if r["job_id"] in ids and s and s.get("status") in ("done", "failed")]
            print(f"{now()}  finished {len(finished)} of {len(ids)}", flush=True)
            if len(finished) == len(ids):
                break
            time.sleep(30)
    write_report()
if __name__ == "__main__":
    main()
