from fastapi import FastAPI
from cities import CITIES

app = FastAPI(
    title="Urban Heat Island API",
    description="Serves satellite-derived heat and greenery layers",
    version="0.1.0"
)

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
