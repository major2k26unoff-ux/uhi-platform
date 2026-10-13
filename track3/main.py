"""
Urban Heat Island API - Week 3.

Run from the track3 folder:
    uvicorn main:app --reload --port 8000
"""
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = ROOT / "data"          
JOBS = DATA_ROOT / "jobs"
PRESETS = ROOT / "presets.json"

MAX_DEGREES = 0.3                  # about 33 km a side; bigger boxes take too long to process
SLUG_PATTERN = re.compile(r"^[a-z0-9-]{1,40}$")
JOB_PATTERN = re.compile(r"^[a-f0-9]{8}$")

app = FastAPI(
    title="Urban Heat Island API",
    description="Serves satellite heat and greenery layers, and cooling priority zones",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- helpers ----------

def safe_slug(slug: str) -> str:
    """Only lowercase letters, digits and hyphens. Stops requests like '../../secret'."""
    if not SLUG_PATTERN.match(slug):
        raise HTTPException(status_code=400, detail=f"'{slug}' is not a valid area name")
    return slug


def area_dir(slug: str) -> Path:
    return DATA_ROOT / safe_slug(slug)


def check_box(south: float, west: float, north: float, east: float):
    """Shared by /api/validate-aoi and /api/analyze."""
    if south >= north or west >= east:
        raise HTTPException(status_code=422, detail="Box corners are the wrong way round")
    if north - south > MAX_DEGREES or east - west > MAX_DEGREES:
        raise HTTPException(status_code=422,
                            detail=f"Area too large. Maximum {MAX_DEGREES} degrees (about 33 km) per side.")
    if not (6 < south < 38 and 67 < west < 98):
        raise HTTPException(status_code=422, detail="Box is outside India")


def write_json_safely(path: Path, data: dict):
    """Write to a temporary file, then swap it in, so nobody reads a half-written file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)


# ---------- basic ----------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- cities ----------

@app.get("/api/cities")
def list_cities():
    """All preset cities, with whether each has been processed yet."""
    cities = json.loads(PRESETS.read_text())
    for city in cities:
        folder = DATA_ROOT / city["slug"]
        city["ready"] = (folder / "meta.json").exists()
        city["has_priority"] = (folder / "priority.geojson").exists()
    return {"count": len(cities), "cities": cities}


@app.get("/api/cities/{slug}")
def get_city(slug: str):
    for city in list_cities()["cities"]:
        if city["slug"] == slug:
            return city
    raise HTTPException(status_code=404, detail=f"No preset city '{slug}'")


# ---------- results and layers ----------

@app.get("/api/results/{slug}")
def get_results(slug: str):
    """Metadata, statistics, and the address of every layer that exists for this area."""
    folder = area_dir(slug)
    meta_path = folder / "meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404,
                            detail=f"No results for '{slug}'. It may not be processed yet.")
    meta = json.loads(meta_path.read_text())
    previews = sorted((folder / "preview").glob("*.png"))
    meta["layer_urls"] = {p.stem: f"/api/layer/{slug}/{p.name}" for p in previews}
    meta["has_priority"] = (folder / "priority.geojson").exists()
    return meta


@app.get("/api/layer/{slug}/{layer}.png")
def get_layer(slug: str, layer: str):
    """One map layer as a PNG image."""
    path = area_dir(slug) / "preview" / f"{safe_slug(layer)}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Layer '{layer}' not available for '{slug}'")
    return FileResponse(path, media_type="image/png")


# ---------- priority ----------

@app.get("/api/priority/{slug}")
def get_priority(slug: str):
    """The top planting zones, as GeoJSON."""
    path = area_dir(slug) / "priority.geojson"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No priority zones for '{slug}' yet")
    return FileResponse(path, media_type="application/geo+json")


@app.get("/api/priority/{slug}/summary")
def get_priority_summary(slug: str):
    """Headline numbers: expected cooling, model accuracy, the scenario used."""
    path = area_dir(slug) / "priority_summary.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No priority summary for '{slug}' yet")
    return json.loads(path.read_text())


# ---------- analysing a new box ----------

class Box(BaseModel):
    south: float
    west: float
    north: float
    east: float


class AnalyzeRequest(Box):
    name: Optional[str] = None


@app.post("/api/validate-aoi")
def validate_aoi(box: Box):
    """Check a drawn box without starting any work."""
    check_box(box.south, box.west, box.north, box.east)
    return {"valid": True}


@app.post("/api/analyze", status_code=202)
def same_box(a: dict, b: dict) -> bool:
    """Two boxes count as the same if every corner matches to 4 decimals (about 10 m)."""
    return all(round(a[k], 4) == round(b[k], 4) for k in ("south", "west", "north", "east"))


def find_earlier_job(box: dict):
    """An earlier job for the same box that is waiting, running, or done with its files still on disk.
    Failed jobs are ignored, so a failed box can always be tried again."""
    if not JOBS.exists():
        return None
    for request_path in sorted(JOBS.glob("*.request.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            request = json.loads(request_path.read_text())
        except (ValueError, OSError):
            continue                                   # half-written or unreadable: skip it
        bbox = request.get("bbox")
        if not bbox or "job_id" not in request or not same_box(bbox, box):
            continue
        status_path = JOBS / f"{request['job_id']}.status.json"
        try:
            status = json.loads(status_path.read_text()).get("status") if status_path.exists() else "queued"
        except (ValueError, OSError):
            continue
        if status in ("queued", "running"):
            return request, status
        if status == "done" and (DATA_ROOT / request["slug"] / "meta.json").exists():
            return request, status
    return None
@app.post("/api/analyze", status_code=202)
def analyze(req: AnalyzeRequest):
    """Queue a new area for processing. Returns at once; the worker does the slow part.
    If the same box was already done (or is in progress), that job is returned instead."""
    check_box(req.south, req.west, req.north, req.east)
    box = {"south": req.south, "west": req.west, "north": req.north, "east": req.east}
    earlier = find_earlier_job(box)
    if earlier:
        request, status = earlier
        return {"job_id": request["job_id"], "slug": request["slug"], "status": status,
                "status_url": f"/api/jobs/{request['job_id']}", "reused": True}
    job_id = uuid.uuid4().hex[:8]
    slug = f"custom-{job_id}"
    JOBS.mkdir(parents=True, exist_ok=True)
    write_json_safely(JOBS / f"{job_id}.request.json", {
        "job_id": job_id,
        "slug": slug,
        "display_name": req.name or "Custom area",
        "bbox": {"south": req.south, "west": req.west, "north": req.north, "east": req.east},
        "source": "website",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    return {"job_id": job_id, "slug": slug, "status": "queued", "status_url": f"/api/jobs/{job_id}",
            "reused": False}

@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    """How far along a job is. The website asks this every few seconds."""
    if not JOB_PATTERN.match(job_id):
        raise HTTPException(status_code=400, detail="Invalid job id")
    status_path = JOBS / f"{job_id}.status.json"
    request_path = JOBS / f"{job_id}.request.json"
    if status_path.exists():
        return json.loads(status_path.read_text())
    if request_path.exists():
        request = json.loads(request_path.read_text())
        return {"job_id": job_id, "slug": request["slug"], "status": "queued", "progress": 0,
                "stage": "Waiting for the worker to pick this up", "error": None}
    raise HTTPException(status_code=404, detail=f"No job '{job_id}'")