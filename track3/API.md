# Track 3: Backend API

Base address while developing: `http://localhost:8000`
Interactive docs (auto-generated): `http://localhost:8000/docs`

| Method | Endpoint | Returns |
|---|---|---|
| GET | /health | Server status: `{"status": "ok"}` |
| GET | /api/cities | All preset cities, with a `count` |
| GET | /api/cities/{slug} | One city, for example `/api/cities/titlagarh` |
| GET | /api/results/{slug} | Metadata, statistics and a `layer_urls` map for one city |
| GET | /api/layer/{slug}/{layer}.png | One map layer as a PNG image |
| POST | /api/validate-aoi | Whether a user-drawn box is acceptable |

## POST /api/validate-aoi

Send JSON with four numbers in degrees:

    {"south": 20.20, "west": 85.75, "north": 20.35, "east": 85.90}

A valid box returns `{"valid": true, "area_sq_deg": ...}`.

## Error responses

- **404** for an unknown city, a city with no processed results yet, or a layer that does not exist. The body is `{"detail": "..."}` with a readable message.
- **422** for a bad box: corners the wrong way round, a side longer than 0.5 degrees, or a box outside India. The body is `{"detail": "..."}`.

## Notes for Track 4

- `bounds` is always `[south, west, north, east]`, the order Leaflet expects.
- CORS is enabled, so the website can call this server from a different port.
- Layers listed in a city's `layer_urls` only work if the matching PNG exists. In Week 1 the PNGs available are `rgb`, `ndvi`, `lst`, `landcover` and `priority`.