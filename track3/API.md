# Urban Heat Island API: version 2

Run from `track3/`: `uvicorn main:app --reload --port 8000`
Docs page: http://localhost:8000/docs

| Method | Endpoint | Returns |
|---|---|---|
| GET | /health | Server status |
| GET | /api/cities | Preset cities, with `ready` and `has_priority` |
| GET | /api/cities/{slug} | One preset city |
| GET | /api/results/{slug} | Metadata, stats, URL of every available layer |
| GET | /api/layer/{slug}/{layer}.png | One layer image |
| GET | /api/priority/{slug} | Top 300 planting zones, GeoJSON |
| GET | /api/priority/{slug}/summary | Expected cooling, model accuracy, scenario |
| POST | /api/validate-aoi | Whether a drawn box is acceptable |
| POST | /api/analyze | Queue a new area. Replies 202 with `job_id` |
| GET | /api/jobs/{job_id} | `queued`, `running`, `done` or `failed`, with progress |

## How Analyze works
The server never does satellite work. `POST /api/analyze` writes a request file into `data/jobs/` and replies at once. A separate worker (Track 1) picks it up, runs each step, and writes a status file. `GET /api/jobs/{job_id}` reads that file.

## Rules
- Area names: lowercase letters, digits, hyphens only. Anything else gives 400.
- Box limit: 0.3 degrees per side, inside India. Bad boxes give 422.

## Warning
Never run `fake_worker.py` and the real `worker.py` at the same time. Both would grab the same jobs.