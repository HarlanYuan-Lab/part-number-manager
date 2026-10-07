"""Application configuration: constants, part-type settings and file paths."""

from __future__ import annotations

import json
import os

APP_NAME = "Part Number Manager"
APP_VERSION = "3.1.0"

# Part numbers are always 6 digits: <leading number><zero-padded sequence>.
NUMBER_LENGTH = 6

# The three supported part types (display order matters).
PART_TYPES = ("Assembly", "Part", "Standard")

# Default leading number for each part type (used as a starting suggestion).
DEFAULT_PREFIXES = {
    "Assembly": "8",
    "Part": "2",
    "Standard": "9",
}


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def data_root() -> str:
    """User-writable base directory for all app data (databases + config)."""
    base = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "PartNumberManager",
    )
    os.makedirs(base, exist_ok=True)
    return base


def databases_dir() -> str:
    """Directory that holds one SQLite file per database."""
    directory = os.path.join(data_root(), "databases")
    os.makedirs(directory, exist_ok=True)
    return directory


def config_path() -> str:
    """Path of the small JSON file that persists the last-opened database."""
    return os.path.join(data_root(), "config.json")


def db_path_for(name: str) -> str:
    """Path of the SQLite file for a named database (in the default folder)."""
    return os.path.join(databases_dir(), f"{name}.db")


# ---------------------------------------------------------------------------
# Persistent config (JSON)
# ---------------------------------------------------------------------------
def load_config() -> dict:
    """Read the small JSON settings file; return an empty dict on any error."""
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    """Write the settings JSON file (best effort)."""
    try:
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False)
    except Exception:
        pass
