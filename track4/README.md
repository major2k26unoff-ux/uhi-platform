# Track 4 — Website and Demo

## How to run
1. `cd track4`
2. `python -m http.server 5500`
3. Open http://localhost:5500

## What each button does
- City dropdown: moves the map to a preset city
- Five layer buttons: switch between satellite, land cover, heat, greenery, and priority overlays
- Draw tool (left toolbar): draws a box and shows its coordinates

## API dependency
Depends on Track 3's server at http://localhost:8000 for `/api/cities` and `/api/layer/{slug}/{layer}.png`.
If the server is down, the page falls back to a built-in city list and a placeholder image.

## To change the server address
Edit the `API` constant at the top of `app.js`.

## What is stubbed vs real
All layer images are currently placeholders until Track 1 and Track 2 supply real PNGs (Week 2/3).