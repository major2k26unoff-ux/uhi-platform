"""
A PRETEND worker, for testing /api/analyze before the real one exists.

It does no satellite work. For each new job it walks the progress bar
from 0 to 100 over about 25 seconds, then copies Bhubaneswar's finished
files into the new job's folder.

    python fake_worker.py

NEVER run this at the same time as Track 1's real worker.py -
both would grab the same jobs.
"""
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
JOBS = DATA / "jobs"
SOURCE = DATA / "bhubaneswar"        # any finished area works

STAGES = [
    (5, "Fetching Sentinel-2 imagery"),
    (25, "Computing greenery, built-up and water scores"),
    (45, "Computing ground temperature"),
    (60, "Fetching Dynamic World land cover"),
    (75, "Building 100 m grid"),
    (90, "Ranking zones by expected cooling"),
]


def write_status(job_id, **fields):
    path = JOBS / f"{job_id}.status.json"
    status = json.loads(path.read_text()) if path.exists() else {"job_id": job_id}
    status.update(fields)
    status["updated_at"] = datetime.now().isoformat(timespec="seconds")
    tmp = JOBS / f"{job_id}.status.tmp"
    tmp.write_text(json.dumps(status, indent=2))
    os.replace(tmp, path)


def main():
    JOBS.mkdir(parents=True, exist_ok=True)
    print(f"FAKE worker watching {JOBS}   (Ctrl+C to stop)")
    while True:
        for request_path in sorted(JOBS.glob("*.request.json")):
            job_id = request_path.name.split(".")[0]
            if (JOBS / f"{job_id}.status.json").exists():
                continue
            slug = json.loads(request_path.read_text())["slug"]
            print(f"Pretending to process {job_id} -> {slug}")
            for pct, stage in STAGES:
                write_status(job_id, slug=slug, status="running", progress=pct, stage=stage, error=None)
                time.sleep(4)
            shutil.copytree(SOURCE, DATA / slug, dirs_exist_ok=True)
            write_status(job_id, status="done", progress=100, stage="Done")
            print(f"  done")
        time.sleep(2)


if __name__ == "__main__":
    main()