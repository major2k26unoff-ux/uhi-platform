# Track 1 - Satellite pipeline and job worker

Track 1 generates RGB, NDVI, NDBI, NDWI, and land-surface temperature (LST) GeoTIFFs, matching PNG previews, and version 2 metadata.

The worker runs Track 1's pipeline followed by Track 2's priority analysis. Tracks communicate through files rather than importing each other's code.

## Setup on Windows

Run these commands from the `uhi-platform` repository root:

```powershell
py -m venv .\track1\venv
.\track1\venv\Scripts\Activate.ps1
python -m pip install -r .\track1\requirements.txt
earthengine authenticate
```

Create `local_config.json` at the repository root:

```json
{
  "ee_project": "your-approved-google-cloud-project-id"
}
```

Use the actual approved Google Cloud project ID. Each machine uses its own Earth Engine account and settings file. `local_config.json` and virtual environments are ignored by Git.

For worker processing, also set up Track 2:

```powershell
python -m venv .\track2\venv
.\track2\venv\Scripts\python.exe -m pip install -r .\track2\requirements.txt
```

For later sessions, activate the existing environment without recreating it:

```powershell
.\track1\venv\Scripts\Activate.ps1
```

## Process one area

From the repository root:

```powershell
python .\track1\pipeline.py --slug titlagarh --south 20.26 --west 83.09 --north 20.36 --east 83.21 --name "Titlagarh, Odisha"
```

The slug determines the output folder. Keep slugs lowercase; display names may use capitals.

Outputs in `data/<slug>/`:

- `rgb.tif`, `ndvi.tif`, `ndbi.tif`, `ndwi.tif`, and `lst.tif`
- `meta.json` with `contract_version: 2`
- Five matching PNGs inside `preview/`

The pipeline selects an export scale from 10, 20, 25, or 50 metres, checks that all layers share a grid, and creates previews up to 1600 pixels on their longest side.

Downloads use temporary files, basic raster validation, and up to three attempts. A failed download does not replace an existing TIFF.

## Changes from Week 1

- Command-line coordinates replace a fixed Bhubaneswar configuration.
- Sentinel-2 uses Cloud Score+ with a 0.60 threshold.
- Landsat 8 and 9 are combined.
- Landsat cloud and cloud-shadow pixels are masked using QA_PIXEL.
- Landsat processing selects L2SP surface-temperature scenes.
- Pillow saves previews directly without chart borders.
- Metadata bounds come from the exported raster footprint.

Sentinel-2 dates are 2024-03-01 to 2024-05-31. Landsat dates are 2024-03-01 to 2024-06-15. Earth Engine treats the end date as exclusive.

## Worker and job files

Start one worker from the repository root:

```powershell
python .\track1\worker.py
```

The worker checks `data/jobs/` every three seconds. It processes requests sequentially, oldest first. It runs each track using that track's own virtual environment. It converts PROGRESS messages into status updates written atomically. It records completion or failure; startup requeues interrupted jobs whose saved status is `running` and whose request file still exists.

Track 1 occupies 0-55% of overall progress; Track 2 occupies 55-100%. Both tracks must succeed before the job is marked `done`. Stop the worker with Ctrl+C.

Files use matching job IDs:

```text
data/jobs/<id>.request.json
data/jobs/<id>.status.json
```

To retry a failed job, remove only its matching status file. Keep the request file. The worker will pick it up again.

## Preset queue and reports

Track 3 supplies `presets.json` at the repository root.

Preview a two-town trial:

```powershell
python .\track1\queue_presets.py --slugs churu phalodi --dry-run
```

Create those requests:

```powershell
python .\track1\queue_presets.py --slugs churu phalodi
```

Queue all remaining presets:

```powershell
python .\track1\queue_presets.py
```

The queue skips cities with complete version 2 output sets and cities with existing requests. It creates requests; the worker does the processing.

Inspect jobs and regenerate the city table:

```powershell
python .\track1\job_report.py
python .\track1\city_table.py
```

The table is saved to `data/city_table.md`. Output completeness does not establish model accuracy or scientific validity.

## Recorded results

All 11 preset cities produced complete output sets.

- Titlagarh's standalone satellite run: approximately 1.70 minutes.
- Two-town worker trial: approximately 6.30 minutes total.
- Initial nine-city batch: approximately 21.28 minutes, with three failures.
- Delhi, Mumbai, and Hyderabad subsequently completed after retries.

These timings exclude later retries from the initial batch duration and depend on area size, network conditions, and server response time.

City folders were shared under Drive's `02_Data`, and the city table under `03_Results`. TIFFs are ignored by Git. Some PNGs and JSON files are tracked or untracked under the team's current ignore rules.

## Temperature method and limitations

Landsat Collection 2 Level 2 ST_B10 is converted using:

```text
Celsius = ST_B10 * 0.00341802 + 149.0 - 273.15
```

- LST measures ground-surface temperature, not air temperature.
- Native thermal resolution is approximately 100 m. Exporting at 10 m does not create additional thermal detail.
- Results represent the configured 2024 date windows.
- Cloud masking can leave missing pixels and does not guarantee removal of every contaminated pixel.
- Large-area downloads and network or server errors can still fail.
- Temperature previews use a fixed 25-45 C display range; hotter pixels share the maximum colour while TIFF values are retained.
- Phalodi and Churu's high temperatures need scientific review.
- Track 2's cooling estimates are statistical scenarios, not guaranteed cooling. Review model scores and low-data flags.

Metadata bounds use `[south, west, north, east]`. Earth Engine rectangles use `[west, south, east, north]`.

## Week 1 reference

The original fixed-area scripts remain available:

```powershell
python .\track1\fetch_imagery.py
python .\track1\compute_indices.py
python .\track1\compute_lst.py
python .\track1\make_previews.py
python .\track1\write_meta.py
```

They use the Week 1 configuration and workflow. The Week 2 pipeline is the current entry point for processing new areas.

The Week 1 file-based handover report remains available:

```powershell
python .\track1\week1_report.py
```

The local Week 1 Bhubaneswar backup is `data/bhubaneswar_week1/`.
