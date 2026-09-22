"""One source of truth for the Week 1 Bhubaneswar run."""

from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CITY_SLUG = "bhubaneswar"
CITY_DIR = DATA_DIR / CITY_SLUG
PREVIEW_DIR = CITY_DIR / "preview"

# Google Earth Engine uses [west, south, east, north].
BHUBANESWAR_BBOX = [85.75, 20.20, 85.90, 20.35]
DATE_START = "2024-03-01"
DATE_END = "2024-05-31"
DISPLAY_NAME = "Bhubaneswar, Odisha"

# Replace this with the Google Cloud project ID approved for Earth Engine, or set
# EARTH_ENGINE_PROJECT in your terminal before running any script.
EARTH_ENGINE_PROJECT = os.getenv("EARTH_ENGINE_PROJECT", "uhi-project-509409")