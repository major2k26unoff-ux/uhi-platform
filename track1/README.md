# Track 1 - Satellite data pipeline

This track creates the five scientific raster layers that the rest of the Urban Heat Island project consumes: true-colour RGB, NDVI (vegetation), NDBI (built-up surface), NDWI (water), and land-surface temperature (LST) in degrees Celsius. It also creates matching PNG previews for the website.

## One-time setup

From the `uhi-project` directory on Windows:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r .\track1\requirements.txt
earthengine authenticate
$env:EARTH_ENGINE_PROJECT = "your-approved-google-cloud-project-id"
python .\track1\test_connection.py
```

`earthengine authenticate` opens a browser; complete it only after Earth Engine has approved your account. The Google Cloud project ID must be the actual approved project ID, not necessarily the display name `uhi-project`.

## Run the pipeline

```powershell
python .\track1\fetch_imagery.py
python .\track1\compute_indices.py
python .\track1\compute_lst.py
python .\track1\make_previews.py
python .\track1\write_meta.py
```

Outputs land in `data/bhubaneswar/`. GeoTIFFs retain the measured values for Tracks 2 and 3; PNGs in `data/bhubaneswar/preview/` are display layers for Track 4. `meta.json` deliberately writes map bounds as `[south, west, north, east]` for Leaflet, while `config.py` keeps Earth Engine bounds as `[west, south, east, north]`.

## Current study area

The configuration is Bhubaneswar, Odisha, from 1 March to 31 May 2024. Change only the constants in `track1/config.py` to use another city.

## Temperature method

The Landsat Collection 2 Level 2 `ST_B10` band is an official USGS surface-temperature product. The pipeline uses the published conversion: `Celsius = ST_B10 * 0.00341802 + 149.0 - 273.15`. It estimates ground-surface temperature, not air temperature.

## Known limitations

- The first export can take several minutes and requires a working Earth Engine account.
- The current Landsat step filters scene-level cloud cover but does not yet mask individual Landsat cloud pixels.
- Generated TIFF and PNG data are intentionally ignored by Git; share the completed `data/bhubaneswar/` folder with the team separately.
