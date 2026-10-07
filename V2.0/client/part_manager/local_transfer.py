"""Bridge between V1.0 SQLite database files and the V2 central server.

* ``read_v1_db``            - read a V1.0 Part Number Manager ``.db`` (SQLite).
* ``import_v1_to_server``   - create a server project from a V1.0 file, keeping
                              the parts and continuing numbering from the last
                              assigned number.
* ``export_project_to_v1``  - write a server project back to a V1.0-compatible
                              SQLite ``.db`` file (for backup / V1.0 reuse).
"""

from __future__ import annotations

import datetime
import os
import sqlite3

from . import config
from .db import ConnectionManager
from .services import ProjectService

V1_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS parts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number  TEXT    NOT NULL UNIQUE,
    part_name    TEXT    NOT NULL,
    part_type    TEXT    NOT NULL,
    material     TEXT    NOT NULL DEFAULT '',
    description  TEXT    NOT NULL DEFAULT '',
    created_date TEXT    NOT NULL
);
"""


def _tail(full: object, prefix: str) -> int:
    """Extract the numeric tail of a full part number for a given prefix."""
    s = str(full)
    if s.startswith(prefix) and s[len(prefix):].isdigit():
        return int(s[len(prefix):] or "0")
    return 0


def read_v1_db(path: str) -> dict:
    """Read a V1.0 database file into a plain dictionary."""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise ValueError(f"File not found: {path}")
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"meta", "parts"} <= tables:
                raise ValueError(
                    "This file is not a Part Number Manager database "
                    "(missing 'meta'/'parts' tables).")
            meta = {r["key"]: r["value"] for r in conn.execute(
                "SELECT key, value FROM meta")}
            prefixes = {t: meta.get(f"prefix_{t}", config.DEFAULT_PREFIXES[t])
                        for t in config.PART_TYPES}
            seqs = {t: meta.get(f"seq_{t}") for t in config.PART_TYPES}
            parts = [dict(r) for r in conn.execute(
                "SELECT part_number, part_name, part_type, material, "
                "description, created_date FROM parts ORDER BY part_number")]
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"Not a valid database file:\n{exc}") from exc
    return {
        "name": meta.get("db_name")
                or os.path.splitext(os.path.basename(path))[0],
        "created_date": meta.get("created_date")
                        or datetime.date.today().isoformat(),
        "prefixes": prefixes,
        "seqs": seqs,
        "parts": parts,
    }


def import_v1_to_server(db: ConnectionManager,
                        project_service: ProjectService, path: str,
                        project_name: str | None = None):
    """Import a V1.0 file as a new server project.

    Returns ``(project, part_count, nexts)`` where ``nexts`` are the next full
    part numbers per type, so numbering continues from the last assigned number.
    """
    data = read_v1_db(path)
    name = (project_name or data["name"]).strip()
    if project_service.get_by_name(name):
        raise ValueError(
            f"A project named '{name}' already exists on the server. "
            f"Choose a different name to import.")
    prefixes = project_service.validate_prefixes(data["prefixes"])

    # V1 numbers were 6 characters total with single-char prefixes, so derive
    # the suffix width from the actual part numbers.
    suffix = 1
    for p in data["parts"]:
        pfx = prefixes.get(p["part_type"], "")
        if pfx and p["part_number"].startswith(pfx):
            suffix = max(suffix, len(p["part_number"]) - len(pfx))
    suffix = max(1, min(suffix, 15))

    proj = project_service.create(
        name, prefixes, length=suffix, created_date=data["created_date"])

    tails = {}  # stored "last-assigned" suffix counters
    nexts = {}  # next full part numbers (for display)
    for t in config.PART_TYPES:
        prefix = prefixes[t]
        max_part_tail = max(
            [_tail(p["part_number"], prefix) for p in data["parts"]
             if p["part_type"] == t], default=0)
        file_seq = data["seqs"].get(t)
        file_tail = _tail(file_seq, prefix) if file_seq else 0
        next_tail = max(max_part_tail + 1, file_tail)
        tails[t] = max(next_tail - 1, 0)
        nexts[t] = f"{prefix}{next_tail:0{suffix}d}"

    with db.conn.cursor() as cur:
        for p in data["parts"]:
            cur.execute(
                "INSERT INTO parts (project_id, part_number, part_name, "
                "part_type, material, description, created_date) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (proj.id, p["part_number"], p["part_name"], p["part_type"],
                 p["material"], p["description"], p["created_date"]))
        cur.execute(
            "UPDATE projects SET seq_assembly = %s, seq_part = %s, "
            "seq_standard = %s WHERE id = %s",
            (tails["Assembly"], tails["Part"], tails["Standard"], proj.id))
    db.conn.commit()
    return proj, len(data["parts"]), nexts


def export_project_to_v1(db: ConnectionManager, project, parts: list,
                         dest: str) -> str:
    """Write a server project to a V1.0-compatible SQLite ``.db`` file."""
    dest = os.path.abspath(dest)
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    row = db.execute_one(
        "SELECT length, seq_assembly, seq_part, seq_standard, created_date "
        "FROM projects WHERE id = %s", (project.id,))
    length = row["length"] or config.NUMBER_LENGTH
    tails = {"Assembly": row["seq_assembly"], "Part": row["seq_part"],
             "Standard": row["seq_standard"]}
    # V1.0 stores the next full number to assign, so rebuild it as prefix+tail+1.
    seqs = {}
    for t in config.PART_TYPES:
        prefix = project.prefixes[t]
        seqs[t] = f"{prefix}{int(tails[t]) + 1:0{length - 1}d}"
    created = row["created_date"] or project.created_date

    conn = sqlite3.connect(dest)
    try:
        conn.executescript(V1_SCHEMA_SQL)
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                     ("db_name", project.name))
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                     ("created_date", created))
        for t in config.PART_TYPES:
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                         (f"prefix_{t}", project.prefixes[t]))
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                         (f"seq_{t}", seqs[t]))
        for p in parts:
            conn.execute(
                "INSERT INTO parts (part_number, part_name, part_type, "
                "material, description, created_date) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (p.part_number, p.part_name, p.part_type, p.material,
                 p.description, p.created_date))
        conn.commit()
    finally:
        conn.close()
    return dest
