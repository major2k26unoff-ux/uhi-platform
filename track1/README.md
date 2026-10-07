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

## Week 3 - validation and handover

Run these commands from the repository root with the Track 1 environment active:

```powershell
python .\track1\stress_test.py
python .\track1\stress_test.py --report
python .\track1\quality_table.py
python .\track1\modis_check.py
python .\track1\test_week3.py -v
```

The stress test queues Puri, Jaisalmer, Shimla, Shillong, a tiny Bhubaneswar box and a near-limit Kolkata box. Start exactly one worker first. The script waits up to 90 minutes; `--report` only rebuilds the table without queueing more work. Each invocation retains earlier rounds in `data/stress_test.md`. Its Minutes column measures queue-to-completion time, including time waiting behind other jobs; it is not isolated processing time. `data/week3_run.json` identifies the local validation rounds; status `processing_seconds` records isolated processing time for those runs.

The quality script reads the 11 preset folders and writes `data/quality_table.md`. Valid percentages describe finite saved pixels, not the share of clear scenes or a guarantee of accurate temperatures. Folder sizes include all existing files in each city folder.

The MODIS script writes `data/modis_check.md` using Terra MOD11A2 daytime 8-day composites at 1 km, with the heat dates in each city's metadata. This is a comparison of city averages; the grids, clear-scene sampling and temporal aggregation differ. It is not a pixel-level accuracy test. Correlation is calculated from rounded city means. MODIS dates select composites by their start dates, so a composite can extend beyond the requested end date.

Repeat testing preserves a baseline before re-running the satellite pipeline:

```powershell
python .\track1\repeat_check.py --slug titlagarh --save
Measure-Command { python .\track1\pipeline.py --slug titlagarh --south 20.26 --west 83.09 --north 20.36 --east 83.21 --name "Titlagarh, Odisha" | Out-Default } | Select-Object TotalMinutes
python .\track1\repeat_check.py --slug titlagarh
python .\track1\repeat_check.py --slug phalodi --save
Measure-Command { python .\track1\pipeline.py --slug phalodi --south 27.08 --west 72.30 --north 27.18 --east 72.42 --name "Phalodi, Rajasthan" | Out-Default } | Select-Object TotalMinutes
python .\track1\repeat_check.py --slug phalodi
python .\track1\city_table.py
```

Reports are `data/repeat_titlagarh.md` and `data/repeat_phalodi.md`. Baselines remain under `data/_repeat/<slug>/`; an existing baseline is never silently overwritten. Preserve it before a new test. The checker compares CRS, transform, dimensions, band count and valid-pixel masks. Empty comparisons are `NOT MEASURED`, never `identical`. Small nonzero differences use the supplied 1% of baseline magnitude tolerance.

Failed status files have `error` (plain message for the website) and `error_detail` (last 1500 characters of technical output). Use `python .\track1\job_report.py` to print both, or inspect `data/jobs/<id>.status.json`. Successful retries clear both fields. Full child output is in the worker terminal; this session's validation log is `tmp/pdfs/week3-run.log`.

If Earth Engine explicitly reports expired authorization, activate Track 1 and run `earthengine authenticate`. DNS or connection failures require checking connectivity, not replacing credentials. To change season, edit `S2_START`, `S2_END`, `LS_START`, and `LS_END` near the top of `pipeline.py`, then regenerate the satellite and model files together. End dates are exclusive.

| Limit | Implementation |
|---|---|
| Website maximum box | 0.3 degrees per side in `track3/main.py` |
| Area validation | Existing server checks coordinate order, size, and southwest corner against a broad India bounding rectangle; it does not validate the national boundary |
| Minimum model data | At least 200 usable 100 m cells in `track2/priority.py`; required box size depends on water, clouds and eligibility |
| Export scales | 10, 20, 25, 50 m; `pick_scale()` estimates a 2500-pixel side budget |
| Grid | All five TIFFs must share CRS, transform and dimensions |
| Thermal detail | Approximately 100 m native; smaller export pixels do not add thermal detail |
| Previews | At most 1600 pixels on longest side; LST colours clip to 25-45 C |
| Download retries | Three attempts per TIFF; network/server failures remain possible |

The script-level regression checks are offline; the stress and repeat reports are the real-system evidence. Both local stress rounds use the Week 3 error handling, so they must not be labelled as an observed before/after fix comparison. The first three model runs in round 1 use the older checkout; remaining runs use integration commit `6e09013`. `data/week3_code_versions.json` records this boundary. Round 2 validates the updated integration code throughout.

### Human handover checklist

- Track 2 activates its own Track 1 environment and runs one preset city on its own machine.
- Track 2 starts one worker and draws a new website box, watching it finish.
- Track 2 reads a failed job's `error_detail`, then runs quality and city tables.
- Check the team's launcher and its `logs/` folder on the integration machine. `start_demo.bat` and `run_all.py` are present after the Week 2 integration fast-forward.
- Record the approximately five-minute narrated handover video without showing local credentials.
- Upload the facts PDF to Drive `03_Results/facts/` and Markdown tables/video to `03_Results/track1/`; arrange delivery to Track 2.

The session and recording require the people involved. Their completion is not inferred from local tests. Data, previews, metadata, local config and virtual environments must not be staged with code.

To rebuild the facts PDF from the saved tables and images, use a Python environment with ReportLab installed and run `python .\output\build_week3_facts.py`. The output is `output/pdf/Facts_Track1_Track1.pdf`; the builder also writes `data/run_times.md`. The author label is Track 1, as requested. Regenerate measurement tables before rebuilding; pending tests remain explicitly not measured.
