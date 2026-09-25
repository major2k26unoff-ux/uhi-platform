import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from cities import CITIES

app = FastAPI(
    title="Urban Heat Island API",
    description="Serves satellite-derived heat and greenery layers",
    version="0.1.0"
)

# Week 1 points at stubs. In Week 2 change this ONE line to ../data
DATA_ROOT = Path("stub_data")

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
    return {"error": "city not found", "slug": slug}

@app.get("/api/results/{slug}")
def get_results(slug: str):
    """Return the analysis metadata and statistics for one city."""
    meta_path = DATA_ROOT / slug / "meta.json"
    if not meta_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No results for '{slug}'. It may not be processed yet."
        )
    with open(meta_path) as f:
        meta = json.load(f)
    meta["layer_urls"] = {
        layer: f"/api/layer/{slug}/{layer}.png" for layer in meta["layers"]
    }
    return meta
