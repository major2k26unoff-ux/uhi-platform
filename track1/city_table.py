"""Create a Markdown summary of the preset cities."""

import json
from pathlib import Path

from queue_presets import city_ready


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def main():
    cities = json.loads(
        (ROOT / "presets.json").read_text(encoding="utf-8-sig")
    )

    lines = [
        "| City | Status | Mean C | Min C | Max C | NDVI | Pixel m | S2 images | Landsat scenes |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    ready_count = 0

    for city in cities:
        slug = city["slug"]
        meta_path = DATA / slug / "meta.json"

        if not meta_path.is_file():
            lines.append(
                f"| {city['name']} | Not processed | - | - | - | - | - | - | - |"
            )
            continue

        meta = json.loads(
            meta_path.read_text(encoding="utf-8-sig")
        )
        stats = meta["stats"]

        if meta.get("contract_version") == 2 and city_ready(slug):
            status = "Outputs complete"
            ready_count += 1
        else:
            status = "Outputs incomplete"

        lines.append(
            f"| {city['name']} | {status} | "
            f"{stats['lst_mean_c']} | "
            f"{stats['lst_min_c']} | "
            f"{stats['lst_max_c']} | "
            f"{stats['ndvi_mean']} | "
            f"{meta.get('scale_m', 'N/A')} | "
            f"{meta.get('sentinel_images', 'N/A')} | "
            f"{meta.get('landsat_scenes', 'N/A')} |"
        )

    lines.append("")
    lines.append(
        f"Complete output sets: {ready_count} of {len(cities)} preset cities."
    )

    DATA.mkdir(parents=True, exist_ok=True)
    destination = DATA / "city_table.md"
    destination.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("\n".join(lines))
    print(f"\nSaved: {destination}")


if __name__ == "__main__":
    main()