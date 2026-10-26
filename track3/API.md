# Urban Heat Island API: version 3

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
| GET | /api/priority/{slug}/zones.csv | Top planting zones as a spreadsheet file |
| GET | /api/cell/{slug}?lat=..&lon=.. | The 100 m block under one point: land mix, temperature, rank and cooling, or why it is not a planting zone |
| POST | /api/validate-aoi | Whether a drawn box is acceptable |
| POST | /api/analyze | Queue a new area. Replies 202 with `job_id` and `reused` |
| GET | /api/jobs/{job_id} | `queued`, `running`, `done` or `failed`, with progress |

## How Analyze works
The server never does satellite work. `POST /api/analyze` writes a request file into `data/jobs/` and replies at once. A separate worker (Track 1) picks it up, runs each step, and writes a status file. `GET /api/jobs/{job_id}` reads that file.

## Same box twice
If a box matches an earlier one to 4 decimal places (about 10 m) and that job is waiting, running, or done with its files still on disk, the server returns the old job instead of starting a new one, and the reply says `"reused": true`.
A failed job, or a done job whose folder was deleted, is ignored, so that box simply runs again.
The website needs no change: it watches whatever `job_id` it gets back.

| Earlier job is | What the server does |
|---|---|
| waiting or running | Returns that job. No duplicate work. |
| done, folder still has `meta.json` | Returns that job. The website loads it at once. |
| failed | Starts a new job, so a failed box can be tried again. |
| done, but folder deleted | Starts a new job. |

## Zones as a spreadsheet
`GET /api/priority/{slug}/zones.csv` downloads `<slug>_zones.csv`, one row per zone, with these columns:
`rank, tier_label, lat, lon, delta_t_c, lst_now_c, lst_after_c, tree_pct_now, tree_pct_after, built_pct, canopy_added_m2, trees_est`.
Columns an older priority file does not have stay empty.

## Rules
- Area names: lowercase letters, digits, hyphens only. Anything else gives 400.
- Box limit: 0.3 degrees per side, inside India. Bad boxes give 422.
- A failed job's `error` is a plain sentence for users; `error_detail` holds the technical text.

## Warning
Never run `fake_worker.py` and the real `worker.py` at the same time. Both would grab the same jobs.