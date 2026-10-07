"""Print the current status of every requested job."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "data" / "jobs"


def main():
    requests = sorted(
        JOBS.glob("*.request.json"),
        key=lambda path: path.stat().st_mtime,
    )

    if not requests:
        print("No job requests found.")
        return

    for request_path in requests:
        job_id = request_path.name.removesuffix(".request.json")
        request = json.loads(
            request_path.read_text(encoding="utf-8-sig")
        )
        slug = request["slug"]

        status_path = JOBS / f"{job_id}.status.json"

        if not status_path.exists():
            print(f"{job_id}  {slug}  queued")
            continue

        status = json.loads(
            status_path.read_text(encoding="utf-8-sig")
        )

        print(
            f"{job_id}  {slug}  "
            f"{status.get('status', 'unknown')}  "
            f"{status.get('progress', 0)}%  "
            f"{status.get('stage', '')}"
        )

        if status.get("error"):
            print(f"    Error: {status['error']}")
        if status.get("error_detail"):
            print(f"    Technical detail: {status['error_detail']}")


if __name__ == "__main__":
    main()