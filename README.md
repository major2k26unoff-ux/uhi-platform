# Urban Heat Island & Green Canopy Analysis Platform

Finds the hottest parts of an Indian city from satellite data, and ranks the 100 m blocks where
planting trees would cool the ground the most. Team ECS_37, KIIT, B.Tech Major Project 2026.

## Run the demo

Double-click `start_demo.bat` (or `python run_all.py` from this folder). It starts the server,
the worker and the website, and opens http://localhost:5500. Press Ctrl+C once to stop.
Logs go to `logs/`.

## How it fits together

| Folder | Track | What it does |
|---|---|---|
| `track1/` | 1 - Satellite data | Sentinel-2 and Landsat through Google Earth Engine: colour image, greenness (NDVI), built-up (NDBI), water (NDWI), surface heat. Also the worker that runs every job. |
| `track2/` | 2 - Cooling model | Dynamic World land cover, 100 m grid, XGBoost model, "add trees" scenario, ranked planting zones, canopy and tree estimate. |
| `track3/` | 3 - Server | FastAPI. Serves the data and turns "Analyze this box" into a job file. |
| `track4/` | 4 - Website | Leaflet map: layers, planting zones, draw a box, progress bar. |
| `data/<city>/` | all | One folder per area. Not in Git (large files); shared on Drive. |
| `presets.json` | all | The 11 preset cities. |

A new box goes: website -> `POST /api/analyze` -> `data/jobs/<id>.request.json` -> worker runs
`track1/pipeline.py` (0 to 55 %), then `track2/priority.py` (55 to 100 %) -> status file ->
the website asks every 3 seconds and loads the result.

Each track's own README explains its part. Results: `track2/results_week3.md`.

Earth Engine needs each person's own sign-in (`earthengine authenticate`). `local_config.json`
and `venv/` folders stay on each machine and are never committed.
