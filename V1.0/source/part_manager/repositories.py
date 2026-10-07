"""Data access layer (repositories) over SQLite.

Responsibilities:
  * DatabaseRepository  - lifecycle of database files (create anywhere, import,
                          export/backup, delete) plus a persistent registry of
                          known databases, and their metadata.
  * PartsRepository     - CRUD and monotonic number generation for parts inside
                          one active database. Number counters live in the meta
                          table, so deleted numbers are never reused.
"""

from __future__ import annotations

import datetime
import os
import shutil
import sqlite3

from . import config
from .models import DatabaseSummary, Part

# meta keys that hold the last-assigned number per part type (never decrease,
# even when parts are deleted -> deleted numbers are never reused).
SEQ_KEYS = {t: f"seq_{t}" for t in config.PART_TYPES}


class DatabaseRepository:
    """Manages the database files, their metadata and the known-database registry."""

    # ------------------------------------------------------------- registry
    @staticmethod
    def _load_registry() -> list[str]:
        return config.load_config().get("known_databases", [])

    @staticmethod
    def _save_registry(paths: list[str]) -> None:
        cfg = config.load_config()
        cfg["known_databases"] = list(dict.fromkeys(paths))
        config.save_config(cfg)

    @staticmethod
    def _register(path: str) -> None:
        paths = DatabaseRepository._load_registry()
        if path not in paths:
            paths.append(path)
        DatabaseRepository._save_registry(paths)

    @staticmethod
    def _unregister(path: str) -> None:
        paths = [p for p in DatabaseRepository._load_registry() if p != path]
        DatabaseRepository._save_registry(paths)

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _connect(db_path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _schema_sql() -> str:
        return """
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

    @staticmethod
    def _seq_base(prefix: str) -> int:
        """First assignable number for a prefix (e.g. '8' -> 800000)."""
        return int(prefix.ljust(config.NUMBER_LENGTH, "0"))

    @staticmethod
    def _seq_max(prefix: str) -> int:
        """Highest assignable number for a prefix (e.g. '8' -> 899999)."""
        return int(prefix.ljust(config.NUMBER_LENGTH, "9"))

    # ------------------------------------------------------------- create
    @staticmethod
    def create(name: str, prefixes: dict, folder: str | None = None,
               created_date: str | None = None) -> str:
        """Create a new database in ``folder`` (default folder if omitted).

        Returns the absolute path of the created file.
        """
        folder = folder or config.databases_dir()
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{name}.db")
        if os.path.exists(path):
            raise ValueError(f"A database named '{name}' already exists at:\n{path}")

        created_date = created_date or datetime.date.today().isoformat()
        conn = DatabaseRepository._connect(path)
        try:
            conn.executescript(DatabaseRepository._schema_sql())
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("db_name", name))
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("created_date", created_date))
            for part_type in config.PART_TYPES:
                prefix = str(prefixes[part_type])
                conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    (f"prefix_{part_type}", prefix))
                conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    (SEQ_KEYS[part_type],
                     str(DatabaseRepository._seq_base(prefix))))
            conn.commit()
        finally:
            conn.close()
        DatabaseRepository._register(path)
        return path

    # ------------------------------------------------------------- import
    @staticmethod
    def import_database(path: str) -> str:
        """Open/register an existing Part Number Manager database file.

        Initialises the monotonic counters from the existing numbers so that
        creation continues from the last assigned number. Returns the db name.
        """
        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise ValueError(f"File not found: {path}")
        try:
            conn = DatabaseRepository._connect(path)
            try:
                tables = {r["name"] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
            finally:
                conn.close()
        except sqlite3.DatabaseError as exc:
            raise ValueError(f"Not a valid database file:\n{exc}") from exc
        if not {"meta", "parts"} <= tables:
            raise ValueError(
                "This file is not a Part Number Manager database "
                "(missing 'meta'/'parts' tables).")
        DatabaseRepository._ensure_seq(path)
        DatabaseRepository._register(path)
        return DatabaseRepository.get_db_name(path)

    @staticmethod
    def _ensure_seq(db_path: str) -> None:
        """Make sure every part type has a counter >= its max existing number."""
        prefixes = DatabaseRepository.get_prefixes(db_path)
        conn = DatabaseRepository._connect(db_path)
        try:
            for part_type in config.PART_TYPES:
                prefix = str(prefixes[part_type])
                seq_key = SEQ_KEYS[part_type]
                existing = conn.execute(
                    "SELECT value FROM meta WHERE key = ?", (seq_key,)).fetchone()
                if existing is not None:
                    continue
                base = DatabaseRepository._seq_base(prefix)
                max_row = conn.execute(
                    "SELECT part_number FROM parts WHERE part_type = ? "
                    "AND part_number LIKE ? ORDER BY part_number DESC LIMIT 1",
                    (part_type, prefix + "%")).fetchone()
                seq = int(max_row["part_number"]) if max_row else base
                conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    (seq_key, str(seq)))
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------- export
    @staticmethod
    def export_database(path: str, dest: str) -> str:
        """Back up (copy) a database file to ``dest``; returns ``dest``."""
        dest = os.path.abspath(dest)
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        shutil.copy2(path, dest)
        return dest

    # ------------------------------------------------------------- delete
    @staticmethod
    def delete(path: str) -> None:
        if os.path.exists(path):
            os.remove(path)
        DatabaseRepository._unregister(os.path.abspath(path))

    @staticmethod
    def exists(path: str) -> bool:
        return os.path.exists(path)

    # ------------------------------------------------------------- list / read
    @staticmethod
    def list() -> list[DatabaseSummary]:
        """All known databases: those in the default folder plus registered ones."""
        paths = set()
        for fname in os.listdir(config.databases_dir()):
            if fname.endswith(".db"):
                paths.add(os.path.abspath(os.path.join(config.databases_dir(), fname)))
        for path in DatabaseRepository._load_registry():
            if os.path.exists(path):
                paths.add(os.path.abspath(path))
        return [DatabaseRepository.summary(p) for p in sorted(paths)]

    @staticmethod
    def summary(db_path: str) -> DatabaseSummary:
        return DatabaseSummary(
            name=DatabaseRepository.get_db_name(db_path),
            path=db_path,
            prefixes=DatabaseRepository.get_prefixes(db_path),
            created_date=DatabaseRepository.get_created_date(db_path),
            part_count=DatabaseRepository.count_parts(db_path),
        )

    @staticmethod
    def get_db_name(db_path: str) -> str:
        conn = DatabaseRepository._connect(db_path)
        try:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = 'db_name'").fetchone()
        finally:
            conn.close()
        return row["value"] if row else os.path.splitext(os.path.basename(db_path))[0]

    @staticmethod
    def get_prefixes(db_path: str) -> dict:
        conn = DatabaseRepository._connect(db_path)
        try:
            rows = conn.execute(
                "SELECT key, value FROM meta WHERE key LIKE 'prefix_%'").fetchall()
        finally:
            conn.close()
        result = {}
        for row in rows:
            result[row["key"].replace("prefix_", "")] = row["value"]
        for part_type in config.PART_TYPES:
            result.setdefault(part_type, config.DEFAULT_PREFIXES[part_type])
        return result

    @staticmethod
    def get_created_date(db_path: str) -> str:
        conn = DatabaseRepository._connect(db_path)
        try:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = 'created_date'").fetchone()
        finally:
            conn.close()
        return row["value"] if row else ""

    @staticmethod
    def count_parts(db_path: str) -> int:
        conn = DatabaseRepository._connect(db_path)
        try:
            row = conn.execute("SELECT COUNT(*) AS c FROM parts").fetchone()
            return row["c"]
        finally:
            conn.close()


class PartsRepository:
    """CRUD and monotonic number generation for parts inside one database."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    # ------------------------------------------------------------------ helpers
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------ numbering
    def peek_number(self, part_type: str) -> str:
        """Return the next number WITHOUT consuming it (for previews)."""
        prefix = DatabaseRepository.get_prefixes(self.db_path)[part_type]
        seq_key = SEQ_KEYS[part_type]
        base = DatabaseRepository._seq_base(prefix)
        max_full = DatabaseRepository._seq_max(prefix)
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = ?", (seq_key,)).fetchone()
            if row is None:
                max_existing = conn.execute(
                    "SELECT part_number FROM parts WHERE part_type = ? "
                    "AND part_number LIKE ? ORDER BY part_number DESC LIMIT 1",
                    (part_type, prefix + "%")).fetchone()
                seq = int(max_existing["part_number"]) if max_existing else base
            else:
                seq = int(row["value"])
        finally:
            conn.close()
        nxt = seq + 1
        if nxt > max_full:
            raise ValueError(
                f"No more numbers available for '{part_type}' "
                f"(prefix '{prefix}' exhausted).")
        return str(nxt).zfill(config.NUMBER_LENGTH)

    def _read_seq(self, conn, part_type: str, prefix: str) -> int:
        """Current counter for a part type (falls back to max existing number)."""
        seq_key = SEQ_KEYS[part_type]
        row = conn.execute(
            "SELECT value FROM meta WHERE key = ?", (seq_key,)).fetchone()
        if row is None:
            max_existing = conn.execute(
                "SELECT part_number FROM parts WHERE part_type = ? "
                "AND part_number LIKE ? ORDER BY part_number DESC LIMIT 1",
                (part_type, prefix + "%")).fetchone()
            return int(max_existing["part_number"]) if max_existing else \
                DatabaseRepository._seq_base(prefix)
        return int(row["value"])

    def resolve_number(self, part_type: str, desired: str | None = None,
                       exclude: str | None = None) -> str:
        """Return a guaranteed-unique 6-digit number for ``part_type``.

        * ``desired`` given and not taken -> that number (must start with the
          type's leading number).
        * ``desired`` taken by ANOTHER part -> the next free number upwards.
        * no ``desired`` -> the next number from the monotonic counter.

        ``exclude`` is the part's own current number (so keeping it is allowed
        and is not treated as a duplicate). The counter is advanced to the
        assigned number so deleted numbers are never reused.
        """
        prefix = DatabaseRepository.get_prefixes(self.db_path)[part_type]
        seq_key = SEQ_KEYS[part_type]
        base = DatabaseRepository._seq_base(prefix)
        max_full = DatabaseRepository._seq_max(prefix)

        conn = self._connect()
        try:
            seq = self._read_seq(conn, part_type, prefix)
            raw = str(desired).strip() if desired is not None else ""
            if raw:
                if not raw.isdigit() or len(raw) != config.NUMBER_LENGTH:
                    raise ValueError(
                        f"Part number must be a {config.NUMBER_LENGTH}-digit number.")
                if not raw.startswith(prefix):
                    raise ValueError(
                        f"Part number must start with {prefix} "
                        f"(the '{part_type}' leading number).")
                n = int(raw)
            else:
                n = seq + 1

            if n < base:
                n = base

            def _used(x: int) -> bool:
                code = str(x).zfill(config.NUMBER_LENGTH)
                if exclude is not None and code == str(exclude):
                    return False
                return conn.execute(
                    "SELECT 1 FROM parts WHERE part_number = ?",
                    (code,)).fetchone() is not None

            while _used(n):
                n += 1
                if n > max_full:
                    raise ValueError(
                        f"No free number available for '{part_type}' "
                        f"(prefix '{prefix}' exhausted).")

            if n > seq:
                conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    (seq_key, str(n)))
                conn.commit()
        finally:
            conn.close()
        return str(n).zfill(config.NUMBER_LENGTH)

    def next_number(self, part_type: str) -> str:
        """Alias of :meth:`resolve_number` that always picks the next counter."""
        return self.resolve_number(part_type)

    # ------------------------------------------------------------------ create
    def create(self, part_name: str, part_type: str, material: str = "",
               description: str = "") -> str:
        name = part_name.strip()
        if not name:
            raise ValueError("Part name must not be empty.")
        if part_type not in config.PART_TYPES:
            raise ValueError(f"Unknown part type: {part_type}")

        number = self.resolve_number(part_type)
        today = datetime.date.today().isoformat()
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO parts (part_number, part_name, part_type, material, "
                "description, created_date) VALUES (?, ?, ?, ?, ?, ?)",
                (number, name, part_type, material.strip(), description.strip(), today),
            )
            conn.commit()
        finally:
            conn.close()
        return number

    # ------------------------------------------------------------------ read
    def search(self, keyword: str) -> list[Part]:
        keyword = keyword.strip()
        conn = self._connect()
        try:
            if keyword:
                like = f"%{keyword}%"
                rows = conn.execute(
                    "SELECT * FROM parts "
                    "WHERE part_number LIKE ? OR part_name LIKE ? OR material LIKE ? "
                    "ORDER BY part_number ASC",
                    (like, like, like)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM parts ORDER BY part_number ASC").fetchall()
        finally:
            conn.close()
        return [Part.from_row(r) for r in rows]

    def get(self, part_number: str) -> Part | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM parts WHERE part_number = ?", (part_number,)
            ).fetchone()
        finally:
            conn.close()
        return Part.from_row(row) if row else None

    def count(self) -> int:
        return DatabaseRepository.count_parts(self.db_path)

    # ------------------------------------------------------------------ update / delete
    def update(self, part_number: str, new_name: str, new_material: str,
               new_description: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE parts SET part_name = ?, material = ?, description = ? "
                "WHERE part_number = ?",
                (new_name.strip(), new_material.strip(), new_description.strip(),
                 part_number))
            conn.commit()
        finally:
            conn.close()

    def update_part(self, old_number: str, new_number: str, new_name: str,
                    new_material: str, new_description: str,
                    part_type: str) -> str:
        """Update a part and optionally renumber it (keeps numbers unique).

        Returns the final part number: if ``new_number`` was already taken by
        another part, the next free number is used instead.
        """
        final = self.resolve_number(part_type, desired=new_number, exclude=old_number)
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE parts SET part_number = ?, part_name = ?, material = ?, "
                "description = ? WHERE part_number = ?",
                (final, new_name.strip(), new_material.strip(),
                 new_description.strip(), old_number))
            conn.commit()
        finally:
            conn.close()
        return final

    def delete(self, part_number: str) -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM parts WHERE part_number = ?", (part_number,))
            conn.commit()
        finally:
            conn.close()
