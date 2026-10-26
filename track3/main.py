"""
Urban Heat Island API - Week 3 (version 3).

Run from the track3 folder:
    uvicorn main:app --reload --port 8000
"""
import csv
import io
import json
import math
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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
    version="0.3.0",
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


ZONE_COLUMNS = ["rank", "tier_label", "lat", "lon", "delta_t_c", "lst_now_c", "lst_after_c",
                "tree_pct_now", "tree_pct_after", "built_pct", "canopy_added_m2", "trees_est"]


@app.get("/api/priority/{slug}/zones.csv")
def get_zones_csv(slug: str):
    """The top planting zones as a spreadsheet file, one row per zone."""
    path = area_dir(slug) / "priority.geojson"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No priority zones for '{slug}' yet")
    features = json.loads(path.read_text()).get("features", [])
    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=ZONE_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for feature in features:
        writer.writerow(feature.get("properties", {}))   # columns a file does not have stay empty
    return Response(content=text.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{slug}_zones.csv"'})


# ---------- one 100 m block, anywhere in an area ----------
# The map draws only the top 300 zones. Every other block can still be clicked: the website asks
# this endpoint, which reads Track 2's grid_features.csv (one row per 100 m block).
# Same rules as track2/priority.py score_cells(); kept here only to explain a "no".
MIN_ROOM = 0.05           # at least 5 points of tree cover can be added
MAX_WATER = 0.05          # under 5% water
MAX_TREE_NOW = 0.5        # under 50% trees already
_grid_cache = {}          # slug -> (file mtime, grid)


def load_grid(slug: str):
    path = area_dir(slug) / "grid_features.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No block data for '{slug}' yet")
    mtime = path.stat().st_mtime
    cached = _grid_cache.get(slug)
    if cached and cached[0] == mtime:
        return cached[1]
    cells = {}
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            cells[(int(r["row"]), int(r["col"]))] = r
    any_cell = next(iter(cells.values()))
    cell_w = float(any_cell["east"]) - float(any_cell["west"])       # degrees, positive
    cell_h = float(any_cell["south"]) - float(any_cell["north"])     # degrees, negative
    grid = {
        "cells": cells, "cell_w": cell_w, "cell_h": cell_h,
        "west0": float(any_cell["west"]) - int(any_cell["col"]) * cell_w,
        "north0": float(any_cell["north"]) - int(any_cell["row"]) * cell_h,
        "ranked": sum(1 for r in cells.values() if r["eligible"] == "True"),
    }
    _grid_cache[slug] = (mtime, grid)
    return grid


def why_not(r) -> str:
    if float(r["water_frac"]) >= MAX_WATER:
        return "Mostly water"
    if float(r["tree_frac"]) >= MAX_TREE_NOW:
        return "Already half or more trees"
    if float(r["added"]) < MIN_ROOM:
        return "No room for trees (bare ground or water is never replaced)"
    return "Near a river or big lake, or inside a no-plant area (airport, quarry, parade ground)"


def pct(x) -> int:
    return int(round(100 * float(x)))


@app.get("/api/cell/{slug}")
def get_cell(slug: str, lat: float, lon: float):
    """The 100 m block under one point: its land mix, temperature, and expected cooling."""
    grid = load_grid(slug)
    row = math.floor((lat - grid["north0"]) / grid["cell_h"])
    col = math.floor((lon - grid["west0"]) / grid["cell_w"])
    r = grid["cells"].get((row, col))
    if r is None:
        raise HTTPException(status_code=404, detail="No data for this block (outside the area, or cloud)")
    eligible = r["eligible"] == "True"
    return {
        "row": row, "col": col,
        "bounds": [float(r["south"]), float(r["west"]), float(r["north"]), float(r["east"])],
        "lst_now_c": round(float(r["lst_mean"]), 1),
        "ndvi": round(float(r["ndvi_mean"]), 2),
        "land_pct": {"trees": pct(r["tree_frac"]), "built": pct(r["built_frac"]), "crops": pct(r["crops_frac"]),
                     "grass": pct(r["grass_frac"]), "shrub": pct(r["shrub_frac"]), "bare": pct(r["bare_frac"]),
                     "water": pct(r["water_frac"])},
        "eligible": eligible,
        "reason": None if eligible else why_not(r),
        "rank": int(r["rank"]) if eligible else None,
        "ranked_blocks": grid["ranked"],
        "tier": int(r["tier"]),
        "delta_t_c": round(float(r["delta_t"]), 2) if eligible else None,
        "lst_after_c": round(float(r["lst_mean"]) - float(r["delta_t"]), 1) if eligible else None,
        "tree_pct_after": pct(float(r["tree_frac"]) + float(r["added"])) if eligible else None,
        "canopy_added_m2": int(round(float(r["canopy_added_m2"]))) if eligible and r.get("canopy_added_m2") else None,
        "trees_est": int(round(float(r["trees_est"]))) if eligible and r.get("trees_est") else None,
    }


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