"""Application configuration: constants, part-type settings and server defaults."""

from __future__ import annotations

import base64
import json
import os

APP_NAME = "Part Number Manager V2"
APP_VERSION = "2.0.0"

# Part number layout is configurable per project:
#   <prefix chars><zero-padded counter>   (prefix may be any letters/digits)
# NUMBER_LENGTH is the default SUFFIX digit count (the counter's width).
NUMBER_LENGTH = 6
MIN_LENGTH = 1
MAX_LENGTH = 15

# The three supported part types (display order matters).
PART_TYPES = ("Assembly", "Part", "Standard")

# Default leading number for each part type (used as a starting suggestion).
DEFAULT_PREFIXES = {
    "Assembly": "8",
    "Part": "2",
    "Standard": "9",
}

# Defaults for connecting to the central PostgreSQL server.
# NOTE (open-source): these are EXAMPLE placeholders. Replace them with your own
# server host/IP, port, database name, role and password before running.
DEFAULT_HOST = "YOUR_SERVER_IP"          # <-- your PostgreSQL host / NAS IP
DEFAULT_PORT = 5432                      # <-- your PostgreSQL port (default 5432)
DEFAULT_DB = "pnmanager"                 # <-- your database name
DEFAULT_USER = "pnmanager"               # <-- your DB role that owns the database
DEFAULT_PASSWORD = "CHANGE_ME_DB_PASSWORD"  # <-- password of the DB role above


# ------------------------------------------------------------------ local config
# Small local file (not on the server) for remembering the login.
def _local_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "PartNumberManagerV2")


def local_config_path() -> str:
    return os.path.join(_local_dir(), "config.json")


def load_local_config() -> dict:
    try:
        with open(local_config_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_local_config(cfg: dict) -> None:
    try:
        os.makedirs(_local_dir(), exist_ok=True)
        with open(local_config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _obfuscate(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _deobfuscate(text: str) -> str:
    try:
        return base64.b64decode(text.encode("ascii")).decode("utf-8")
    except Exception:
        return ""


def get_remembered_login() -> tuple[str, str]:
    """Return (username, password) saved locally, or ("", "")."""
    cfg = load_local_config()
    user = cfg.get("username", "")
    enc = cfg.get("password_enc", "")
    return user, (_deobfuscate(enc) if enc else "")


def set_remembered_login(username: str, password: str) -> None:
    save_local_config({"username": username,
                       "password_enc": _obfuscate(password)})


def clear_remembered_login() -> None:
    save_local_config({})
