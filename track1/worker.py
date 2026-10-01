"""Process area requests from the shared job folder."""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "data" / "jobs"
POLL_SECONDS = 3


def now():
    """Return a timestamp for job status updates."""
    return datetime.now().isoformat(timespec="seconds")


def venv_python(track):
    """Find the Python executable for one track."""
    candidates = [
        ROOT / track / "venv" / "Scripts" / "python.exe",
        ROOT / track / "venv" / "bin" / "python",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return None

def write_status(job_id, **fields):
    """Update a status file using an atomic replacement."""
    JOBS.mkdir(parents=True, exist_ok=True)

    path = JOBS / f"{job_id}.status.json"

    if path.exists():
        status = json.loads(path.read_text(encoding="utf-8"))
    else:
        status = {"job_id": job_id}

    status.update(fields)
    status["updated_at"] = now()

    temporary = JOBS / f"{job_id}.status.tmp"
    temporary.write_text(
        json.dumps(status, indent=2),
        encoding="utf-8",
    )

    os.replace(temporary, path)

def run_step(track, script, args, job_id, low, high):
    """Run a track's script and report its progress."""
    python = venv_python(track)
    script_path = ROOT / track / script

    if python is None:
        raise RuntimeError(
            f"{track}'s virtual environment is missing."
        )

    if not script_path.is_file():
        raise RuntimeError(
            f"Required script is missing: {track}/{script}"
        )

    proc = subprocess.Popen(
        [python, "-u", script] + args,
        cwd=ROOT / track,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    last_lines = []

    for line in proc.stdout:
        line = line.rstrip()
        print(f"[{track}] {line}", flush=True)
        last_lines = (last_lines + [line])[-15:]

        if line.startswith("PROGRESS "):
            parts = line.split(" ", 2)
            percent = int(parts[1])
            stage = parts[2] if len(parts) > 2 else ""

            overall = round(
                low + (high - low) * percent / 100
            )

            write_status(
                job_id,
                progress=overall,
                stage=stage,
            )

    if proc.wait() != 0:
        raise RuntimeError(
            f"{track}/{script} failed:\n"
            + "\n".join(last_lines)
        )

def process(request_path):
    """Run both tracks for one request and record the outcome."""
    job_id = request_path.name.removesuffix(".request.json")

    try:
        req = json.loads(
            request_path.read_text(encoding="utf-8-sig")
        )

        if req["job_id"] != job_id:
            raise ValueError(
                "Request job_id does not match its filename."
            )

        slug = req["slug"]
        box = req["bbox"]

        write_status(
            job_id,
            slug=slug,
            status="running",
            progress=0,
            stage="Starting",
            error=None,
        )

        for track, script in [
            ("track1", "pipeline.py"),
            ("track2", "priority.py"),
        ]:
            if venv_python(track) is None:
                raise RuntimeError(
                    f"{track}'s virtual environment is missing."
                )

            if not (ROOT / track / script).is_file():
                raise RuntimeError(
                    f"Required script is missing: {track}/{script}"
                )

        run_step(
            "track1",
            "pipeline.py",
            [
                "--slug", slug,
                "--south", str(box["south"]),
                "--west", str(box["west"]),
                "--north", str(box["north"]),
                "--east", str(box["east"]),
                "--name", req.get("display_name") or slug,
            ],
            job_id,
            0,
            55,
        )

        run_step(
            "track2",
            "priority.py",
            ["--slug", slug],
            job_id,
            55,
            100,
        )

        write_status(
            job_id,
            status="done",
            progress=100,
            stage="Done",
            error=None,
        )

        print(f"Job {job_id}: done", flush=True)

    except Exception as err:
        write_status(
            job_id,
            status="failed",
            stage="Failed",
            error=str(err)[-1500:],
        )

        print(f"Job {job_id}: FAILED\n{err}", flush=True)

def waiting_requests():
    """Find requests with no status file, oldest first."""
    requests = sorted(
        JOBS.glob("*.request.json"),
        key=lambda path: path.stat().st_mtime,
    )

    return [
        request
        for request in requests
        if not (
            JOBS
            / (
                request.name.removesuffix(".request.json")
                + ".status.json"
            )
        ).exists()
    ]

def requeue_interrupted():
    """Allow interrupted jobs to run again after a restart."""
    for status_path in JOBS.glob("*.status.json"):
        status = json.loads(
            status_path.read_text(encoding="utf-8")
        )

        job_id = status_path.name.removesuffix(".status.json")
        request_path = JOBS / f"{job_id}.request.json"

        if (
            status.get("status") == "running"
            and request_path.is_file()
        ):
            status_path.unlink()
            print(
                f"Re-queued interrupted job {job_id}",
                flush=True,
            )


def main():
    JOBS.mkdir(parents=True, exist_ok=True)
    requeue_interrupted()

    print(
        f"Worker watching {JOBS} (Ctrl+C to stop)",
        flush=True,
    )

    try:
        while True:
            for request_path in waiting_requests():
                process(request_path)

            time.sleep(POLL_SECONDS)

    except KeyboardInterrupt:
        print("\nWorker stopped.", flush=True)


if __name__ == "__main__":
    main()