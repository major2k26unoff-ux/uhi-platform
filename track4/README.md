# Track 4 — Website and Demo

## How to run
1. cd track4
2. python -m http.server 5500
3. Open http://localhost:5500

Make sure Track 3's server is also running at http://localhost:8000
(cd track3, venv\Scripts\activate, uvicorn main:app --reload --port 8000)

## What each button does
- City dropdown: loads a processed city's results, grouped into
  Major cities and Extreme-heat towns. Unprocessed cities are greyed out.
- Five layer buttons: Satellite, Land cover, Heat, Greenery, Plant here.
  A button is disabled if that layer hasn't been produced for the
  selected area yet.
- Draw tool (left map toolbar): draws a rectangle and offers an
  "Analyze this area" button, which sends the box to Track 3's server
  for processing and shows a live progress bar.

## API endpoints used
- GET  /api/cities
- GET  /api/results/{slug}
- GET  /api/layer/{slug}/{layer}.png
- GET  /api/priority/{slug}
- GET  /api/priority/{slug}/summary
- POST /api/analyze
- GET  /api/jobs/{job_id}

## To change the server address
Edit the API constant at the top of app.js.

## What is stubbed vs real
- Preset cities with real data: Bhubaneswar, Titlagarh (more are added
  as Track 1's batch processes them)
- Drawing and analyzing a custom box currently runs through Track 3's
  fake_worker.py, which copies Bhubaneswar's files rather than
  processing the drawn area for real. This will switch to real
  processing once the integration machine's worker.py is running
  (Week 2, Day 5 onward).

## Known limitations
- The city dropdown does not reset its displayed name after a custom
  area finishes analyzing; the map updates correctly but the dropdown
  text can look out of sync.