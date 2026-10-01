"""Read this machine's Earth Engine project settings."""

import json
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "local_config.json"


def ee_project():
    if not CONFIG.exists():
        raise SystemExit(
            "local_config.json is missing at the repository root."
        )

    settings = json.loads(CONFIG.read_text(encoding="utf-8"))
    return settings["ee_project"]