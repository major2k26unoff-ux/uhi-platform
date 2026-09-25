"""Create consistently coloured PNG previews for the website layer overlays."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from PIL import Image

from config import CITY_DIR, PREVIEW_DIR

STYLE = {
    "ndvi": ("RdYlGn", -0.2, 0.8),
    "ndbi": ("RdBu_r", -0.5, 0.5),
    "ndwi": ("Blues", -0.3, 0.5),
    "lst": ("inferno", 25, 45),
}


def read_first_band(path: Path) -> np.ndarray:
    with rasterio.open(path) as source:
        return source.read(1, masked=True)


def optimise_png(path: Path) -> None:
    """Keep website previews compact without changing their displayed colours."""
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        rgb.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
        indexed = rgb.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
        indexed.save(path, optimize=True, compress_level=9)


def save_index_preview(name: str, cmap: str, vmin: float, vmax: float) -> None:
    image = read_first_band(CITY_DIR / f"{name}.tif")
    destination = PREVIEW_DIR / f"{name}.png"
    plt.imsave(destination, image, cmap=cmap, vmin=vmin, vmax=vmax)
    optimise_png(destination)


def save_rgb_preview() -> None:
    with rasterio.open(CITY_DIR / "rgb.tif") as source:
        rgb = source.read([1, 2, 3]).astype("float32")
    # Sentinel reflectance is normally 0-1 after the export pipeline.
    rgb = np.clip(rgb, 0, 1).transpose(1, 2, 0)
    destination = PREVIEW_DIR / "rgb.png"
    plt.imsave(destination, rgb)
    optimise_png(destination)


def main() -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    save_rgb_preview()
    for name, (cmap, vmin, vmax) in STYLE.items():
        save_index_preview(name, cmap, vmin, vmax)
    print(f"Saved previews to {PREVIEW_DIR}")


if __name__ == "__main__":
    main()
