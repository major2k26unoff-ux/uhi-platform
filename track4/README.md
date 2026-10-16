# Track 4 — Website and Demo

## How to run
1. `cd track4`
2. `python -m http.server 5500`
3. Open http://localhost:5500

Or start everything at once with `start_demo.bat` from the repository root.

## What each control does
- City dropdown (top left): moves the map to a preset city
- Layer buttons (top centre): switch between Satellite, Land cover, Heat, Greenery and Plant here. The app starts on Satellite and only changes layer when you click one.
- Legend card (bottom right): shows the active layer, its colour key and an opacity slider (default 60%)
- Info card (bottom left): area statistics, expected cooling for Plant here, and messages such as "Server not reachable"
- Square tool (top right): draw a box, then press "Analyze this area". A small progress card shows the stage and percentage.
- Click a Plant here zone for its expected cooling in °C

Both cards collapse. On a phone only one is open at a time.

## API dependency
Depends on Track 3's server at http://localhost:8000 (see `track3/API.md`).
If the server is down, the info card says "Server not reachable".

## To change the server address
Edit the `API` constant at the top of `app.js`.

## Notes
- Plain HTML, CSS and JS. Leaflet and leaflet-draw load from unpkg; the page uses the system font, no web fonts.
- Analyze needs the Track 1 worker running.
