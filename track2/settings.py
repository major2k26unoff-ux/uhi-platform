"""Reads this machine's own settings from local_config.json at the repo root.
local_config.json is NOT in Git. Every machine has its own copy, because
every person's Earth Engine Cloud project has a different ID.
"""
import json
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "local_config.json"

def ee_project():
    if not CONFIG.exists():
        raise SystemExit(
            "local_config.json is missing at the repo root.\n"
            'Create it with: {"ee_project": "your-cloud-project-id"}'
        )
    return json.loads(CONFIG.read_text())["ee_project"]