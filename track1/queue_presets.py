"""Create worker requests for preset cities."""

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
JOBS = DATA / "jobs"
PRESETS = ROOT / "presets.json"


def city_ready(slug):
    """Check whether both tracks' expected outputs exist."""
    folder = DATA / slug

    meta_path = folder / "meta.json"

    if not meta_path.is_file():
        return False

    try:
        meta = json.loads(
            meta_path.read_text(encoding="utf-8-sig")
        )
    except (ValueError, OSError):
        return False

    if meta.get("contract_version") != 2:
        return False

    required = [
        "meta.json",
        "rgb.tif",
        "ndvi.tif",
        "ndbi.tif",
        "ndwi.tif",
        "lst.tif",
        "landcover.tif",
        "priority.geojson",
        "priority_summary.json",
        "preview/rgb.png",
        "preview/ndvi.png",
        "preview/ndbi.png",
        "preview/ndwi.png",
        "preview/lst.png",
        "preview/landcover.png",
        "preview/priority.png",
    ]

    return all(
        (folder / name).is_file()
        for name in required
    )

def existing_request(slug):
    """Find an existing request for this city."""
    for path in JOBS.glob("*.request.json"):
        request = json.loads(
            path.read_text(encoding="utf-8-sig")
        )

        if request.get("slug") == slug:
            return path

    return None


def queue_city(city):
    """Write one request for the worker."""
    slug = city["slug"]

    if city_ready(slug):
        print(f"skip {slug}: all expected outputs exist")
        return

    previous = existing_request(slug)

    if previous is not None:
        print(f"skip {slug}: request already exists ({previous.name})")
        return

    south, west, north, east = city["bounds"]
    job_id = uuid.uuid4().hex[:8]

    request = {
        "job_id": job_id,
        "slug": slug,
        "display_name": city["name"],
        "bbox": {
            "south": south,
            "west": west,
            "north": north,
            "east": east,
        },
        "source": "preset-batch",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    JOBS.mkdir(parents=True, exist_ok=True)

    destination = JOBS / f"{job_id}.request.json"
    temporary = JOBS / f"{job_id}.request.tmp"

    temporary.write_text(
        json.dumps(request, indent=2),
        encoding="utf-8",
    )
    temporary.replace(destination)

    print(f"queued {slug}: job {job_id}")

def main():
    parser = argparse.ArgumentParser(
        description="Queue preset cities for the worker."
    )
    parser.add_argument(
        "--slugs",
        nargs="+",
        help="Queue only these city slugs; default: all presets.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned requests without writing files.",
    )
    args = parser.parse_args()

    cities = json.loads(
        PRESETS.read_text(encoding="utf-8-sig")
    )

    if args.slugs:
        available = {city["slug"] for city in cities}
        unknown = set(args.slugs) - available

        if unknown:
            parser.error(
                "Unknown city slugs: " + ", ".join(sorted(unknown))
            )

        cities = [
            city for city in cities
            if city["slug"] in args.slugs
        ]

    for city in cities:
        if args.dry_run:
            slug = city["slug"]

            if city_ready(slug):
                print(f"skip {slug}: all expected outputs exist")
            elif existing_request(slug) is not None:
                print(f"skip {slug}: request already exists")
            else:
                print(f"would queue {slug}: {city['bounds']}")
        else:
            queue_city(city)


if __name__ == "__main__":
    main()