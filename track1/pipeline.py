"""Generate satellite layers for a requested area."""

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import ee
import geemap
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from PIL import Image

from settings import ee_project

import requests
import time


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

S2_START = "2024-03-01"
S2_END = "2024-05-31"

LS_START = "2024-03-01"
LS_END = "2024-06-15"

SCALES = [10, 20, 25, 50]
MAX_PIXELS = 2500

MAX_PNG_SIDE = 1600

PREVIEW_STYLE = {
    "ndvi": ("RdYlGn", -0.2, 0.8),
    "ndbi": ("RdBu_r", -0.5, 0.5),
    "ndwi": ("Blues", -0.3, 0.5),
    "lst": ("inferno", 25, 45),
}

def progress(percent, stage):
    print(f"PROGRESS {percent} {stage}", flush=True)

def pick_scale(south, west, north, east):
    """Choose the smallest pixel size that fits our download budget."""
    height_m = (north - south) * 111_000

    middle_latitude = (north + south) / 2
    width_m = (
        (east - west)
        * 111_000
        * math.cos(math.radians(middle_latitude))
    )

    longest = max(height_m, width_m)

    for scale in SCALES:
        if longest / scale <= MAX_PIXELS:
            return scale

    raise ValueError(
        "Area too large even at 50 m pixels. Draw a smaller box."
    )

def sentinel_composite(aoi):
    """Build a cloud-masked Sentinel-2 median image."""
    cloud_score = ee.ImageCollection(
        "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
    )

    images = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(S2_START, S2_END)
        .linkCollection(cloud_score, ["cs_cdf"])
        .map(
            lambda img: img.updateMask(
                img.select("cs_cdf").gte(0.60)
            ).divide(10000)
        )
    )

    count = images.size().getInfo()

    if count == 0:
        raise RuntimeError(
            "No Sentinel-2 images found for this area and dates."
        )

    return images.median().clip(aoi), count

def land_surface_temperature(aoi):
    """Build a cloud-masked Landsat surface-temperature image."""

    def to_celsius(img):
        qa = img.select("QA_PIXEL")

        clear = (
            qa.bitwiseAnd(1 << 3).eq(0)
            .And(qa.bitwiseAnd(1 << 4).eq(0))
        )

        celsius = (
            img.select("ST_B10")
            .multiply(0.00341802)
            .add(149.0)
            .subtract(273.15)
        )

        return celsius.updateMask(clear).rename("LST")

    scenes = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .merge(ee.ImageCollection("LANDSAT/LC09/C02/T1_L2"))
        .filterBounds(aoi)
        .filterDate(LS_START, LS_END)
        .filter(ee.Filter.eq("PROCESSING_LEVEL", "L2SP"))
        .filter(ee.Filter.lt("CLOUD_COVER", 40))
        .map(to_celsius)
    )

    count = scenes.size().getInfo()

    if count == 0:
        raise RuntimeError(
            "No Landsat surface-temperature scenes found."
        )

    return scenes.median().clip(aoi), count

def export(image, path, aoi, scale):
    """Download and validate a GeoTIFF, with up to three attempts."""
    temporary = path.with_name(path.stem + ".download.tif")

    for attempt in range(1, 4):
        try:
            print(
                f"Downloading {path.name}: attempt {attempt}/3",
                flush=True,
            )

            url = image.getDownloadURL({
                "scale": scale,
                "region": aoi,
                "crs": "EPSG:4326",
                "format": "GEO_TIFF",
            })

            with requests.get(
                url, stream=True, timeout=300
            ) as response:
                if response.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {response.status_code}: "
                        f"{response.text[:1500]}"
                    )

                with temporary.open("wb") as destination:
                    for chunk in response.iter_content(
                        chunk_size=1024 * 1024
                    ):
                        if chunk:
                            destination.write(chunk)

            with rasterio.open(temporary) as src:
                if src.count < 1 or src.width < 1 or src.height < 1:
                    raise RuntimeError("Downloaded raster is empty.")

                src.read(1, window=((0, 1), (0, 1)))

            temporary.replace(path)
            print(f"Saved: {path}", flush=True)
            return

        except (
            requests.RequestException,
            ee.EEException,
            rasterio.errors.RasterioError,
            RuntimeError,
        ) as err:
            temporary.unlink(missing_ok=True)

            if attempt == 3:
                raise RuntimeError(
                    f"{path.name} failed after 3 attempts: {err}"
                ) from err

            delay = attempt * 5
            print(
                f"Attempt failed: {err}\nRetrying in {delay} seconds.",
                flush=True,
            )
            time.sleep(delay)

def read_band(path):
    """Read the first raster band, using NaN for missing pixels."""
    with rasterio.open(path) as src:
        return (
            src.read(1, masked=True)
            .astype("float32")
            .filled(np.nan)
        )

def write_png(rgba, path):
    """Save an image, reducing large previews proportionally."""
    img = Image.fromarray(rgba)

    if max(img.size) > MAX_PNG_SIDE:
        ratio = MAX_PNG_SIDE / max(img.size)
        img = img.resize(
            (
                round(img.width * ratio),
                round(img.height * ratio),
            ),
            Image.Resampling.NEAREST,
        )

    img.save(path, optimize=True)


def save_png(arr, path, cmap, vmin, vmax):
    """Convert raster values into colours and transparency."""
    alpha = np.where(np.isnan(arr), 0, 210).astype(np.uint8)

    norm = np.nan_to_num(
        np.clip((arr - vmin) / (vmax - vmin), 0, 1)
    )

    rgba = (plt.get_cmap(cmap)(norm) * 255).astype(np.uint8)
    rgba[..., 3] = alpha

    write_png(rgba, path)

def make_previews(out):
    """Create RGB and index previews from the downloaded TIFFs."""
    preview = out / "preview"
    preview.mkdir(parents=True, exist_ok=True)

    with rasterio.open(out / "rgb.tif") as src:
        rgb = np.moveaxis(
            src.read([1, 2, 3]), 0, -1
        ).astype(np.uint8)

        alpha = np.where(
            src.dataset_mask() > 0, 255, 0
        ).astype(np.uint8)

    write_png(
        np.dstack([rgb, alpha]),
        preview / "rgb.png",
    )

    for name, (cmap, vmin, vmax) in PREVIEW_STYLE.items():
        arr = read_band(out / f"{name}.tif")
        save_png(
            arr,
            preview / f"{name}.png",
            cmap,
            vmin,
            vmax,
        )

def check_alignment(out):
    """Require all five layers to share the same geographic grid."""
    reference = None
    shapes = {}

    for name in ["rgb", "ndvi", "ndbi", "ndwi", "lst"]:
        with rasterio.open(out / f"{name}.tif") as src:
            grid = (
                src.crs,
                src.transform,
                src.width,
                src.height,
            )

            shapes[name] = (src.height, src.width)

            if reference is None:
                reference = grid
            elif grid != reference:
                raise RuntimeError(
                    f"{name}.tif does not match the RGB grid. "
                    f"Layer dimensions so far: {shapes}"
                )

    return shapes

def write_meta(out, slug, display_name, scale, n_s2, n_ls):
    """Describe the exported area for the other tracks."""
    with rasterio.open(out / "lst.tif") as src:
        left, bottom, right, top = src.bounds
        width = src.width
        height = src.height

    lst = read_band(out / "lst.tif")
    ndvi = read_band(out / "ndvi.tif")

    meta = {
        "contract_version": 2,
        "city": slug,
        "display_name": display_name,
        "bounds": [
            round(bottom, 6),
            round(left, 6),
            round(top, 6),
            round(right, 6),
        ],
        "crs": "EPSG:4326",
        "scale_m": scale,
        "width_px": width,
        "height_px": height,
        "native_resolution_m": {
            "optical": 10,
            "thermal": 100,
        },
        "date_start": S2_START,
        "date_end": S2_END,
        "lst_date_start": LS_START,
        "lst_date_end": LS_END,
        "sentinel_images": n_s2,
        "landsat_scenes": n_ls,
        "layers": ["rgb", "ndvi", "ndbi", "ndwi", "lst"],
        "stats": {
            "lst_min_c": round(float(np.nanmin(lst)), 1),
            "lst_max_c": round(float(np.nanmax(lst)), 1),
            "lst_mean_c": round(float(np.nanmean(lst)), 1),
            "ndvi_mean": round(float(np.nanmean(ndvi)), 2),
        },
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    (out / "meta.json").write_text(
        json.dumps(meta, indent=2),
        encoding="utf-8",
    )

    return meta

def process_aoi(slug, south, west, north, east, display_name):
    """Generate all satellite outputs for one area."""
    progress(2, "Connecting to Earth Engine")
    ee.Initialize(project=ee_project())

    out = DATA / slug
    (out / "preview").mkdir(parents=True, exist_ok=True)

    aoi = ee.Geometry.Rectangle([west, south, east, north])
    scale = pick_scale(south, west, north, east)

    progress(10, f"Fetching Sentinel-2 imagery at {scale} m")
    composite, n_s2 = sentinel_composite(aoi)

    rgb = composite.select(["B4", "B3", "B2"]).visualize(
        min=0,
        max=0.3,
    )
    export(rgb, out / "rgb.tif", aoi, scale)

    progress(30, "Computing vegetation, built-up and water indices")

    for name, bands in [
        ("ndvi", ["B8", "B4"]),
        ("ndbi", ["B11", "B8"]),
        ("ndwi", ["B3", "B8"]),
    ]:
        index = composite.normalizedDifference(bands).rename(
            name.upper()
        )
        export(index, out / f"{name}.tif", aoi, scale)

    progress(55, "Computing ground temperature")
    lst, n_ls = land_surface_temperature(aoi)
    export(lst, out / "lst.tif", aoi, scale)

    progress(80, "Checking layer alignment")
    check_alignment(out)

    progress(90, "Creating previews")
    make_previews(out)

    meta = write_meta(
        out, slug, display_name, scale, n_s2, n_ls
    )

    progress(100, "Satellite layers ready")
    return meta

def main():
    parser = argparse.ArgumentParser(
        description="Generate satellite layers for one area."
    )

    parser.add_argument("--slug", required=True)
    parser.add_argument("--south", type=float, required=True)
    parser.add_argument("--west", type=float, required=True)
    parser.add_argument("--north", type=float, required=True)
    parser.add_argument("--east", type=float, required=True)
    parser.add_argument("--name", default=None)

    args = parser.parse_args()

    process_aoi(
        args.slug,
        args.south,
        args.west,
        args.north,
        args.east,
        args.name or args.slug,
    )


if __name__ == "__main__":
    main()