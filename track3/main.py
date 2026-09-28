import json
from functools import lru_cache
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cities import CITIES

app = FastAPI(
    title="Urban Heat Island API",
    description="Serves satellite-derived heat and greenery layers",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for a student project; tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Week 1 points at stubs. In Week 2 change this ONE line to ../data
DATA_ROOT = Path("stub_data")
MAX_DEGREES = 0.5  # about 55 km, our processing limit


@app.get("/")
def root():
    return {"message": "UHI API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/cities")
def list_cities():
    """Return all preset cities available for analysis."""
    return {"count": len(CITIES), "cities": CITIES}


@app.get("/api/cities/{slug}")
def get_city(slug: str):
    """Return one city by its slug, for example 'bhubaneswar'."""
    for city in CITIES:
        if city["slug"] == slug:
            return city
    raise HTTPException(status_code=404, detail=f"City '{slug}' not found")


@lru_cache(maxsize=32)
def load_meta_cached(slug: str) -> str:
    path = DATA_ROOT / slug / "meta.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No results for '{slug}'. It may not be processed yet."
        )
    return path.read_text()


@app.get("/api/results/{slug}")
def get_results(slug: str):
    """Return the analysis metadata and statistics for one city."""
    meta = json.loads(load_meta_cached(slug))
    meta["layer_urls"] = {
        layer: f"/api/layer/{slug}/{layer}.png" for layer in meta["layers"]
    }
    return meta


@app.get("/api/layer/{slug}/{layer}.png")
def get_layer(slug: str, layer: str):
    """Return one map layer as a PNG image."""
    path = DATA_ROOT / slug / "preview" / f"{layer}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Layer '{layer}' not available")
    return FileResponse(path, media_type="image/png")


class AOIRequest(BaseModel):
    south: float
    west: float
    north: float
    east: float


@app.post("/api/validate-aoi")
def validate_aoi(aoi: AOIRequest):
    """Check a user-drawn box before we try to process it."""
    if aoi.south >= aoi.north or aoi.west >= aoi.east:
        raise HTTPException(status_code=422, detail="Box corners are the wrong way round")

    height = aoi.north - aoi.south
    width = aoi.east - aoi.west
    if height > MAX_DEGREES or width > MAX_DEGREES:
        raise HTTPException(
            status_code=422,
            detail=f"Area too large. Maximum {MAX_DEGREES} degrees per side."
        )

    if not (6 < aoi.south < 38 and 67 < aoi.west < 98):
        raise HTTPException(status_code=422, detail="Box is outside India")

    return {"valid": True, "area_sq_deg": round(height * width, 4)}