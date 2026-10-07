"""Connection layer for the central PostgreSQL server (psycopg3)."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

# Schema for the central database (created idempotently on first connect).
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    prefix_assembly TEXT NOT NULL,
    prefix_part     TEXT NOT NULL,
    prefix_standard TEXT NOT NULL,
    length          INTEGER NOT NULL DEFAULT 6,
    seq_assembly    BIGINT NOT NULL,
    seq_part        BIGINT NOT NULL,
    seq_standard    BIGINT NOT NULL,
    created_date    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parts (
    id           SERIAL PRIMARY KEY,
    project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    part_number  TEXT NOT NULL,
    part_name    TEXT NOT NULL,
    part_type    TEXT NOT NULL,
    material     TEXT NOT NULL DEFAULT '',
    description  TEXT NOT NULL DEFAULT '',
    created_date TEXT NOT NULL,
    UNIQUE (project_id, part_number)
);

CREATE INDEX IF NOT EXISTS idx_parts_project ON parts(project_id);
CREATE INDEX IF NOT EXISTS idx_parts_number ON parts(project_id, part_number);

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',
    created_date  TEXT NOT NULL
);
"""


class ConnectionManager:
    """Owns the single PostgreSQL connection used by the whole app."""

    def __init__(self) -> None:
        self.conn: psycopg.Connection | None = None
        self.host: str | None = None
        self.port: int | None = None
        self.db: str | None = None
        self.user: str | None = None

    @property
    def connected(self) -> bool:
        try:
            return self.conn is not None and not self.conn.closed
        except Exception:
            return False

    def connect(self, host: str, port: int, dbname: str, user: str,
                password: str) -> None:
        if self.connected:
            self.close()
        self.conn = psycopg.connect(
            host=host, port=port, dbname=dbname, user=user, password=password,
            row_factory=dict_row, connect_timeout=10)
        self.conn.autocommit = False
        self.ensure_schema()
        self.host = host
        self.port = port
        self.db = dbname
        self.user = user

    def ensure_schema(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            # Backwards compatibility: add the per-project length column to any
            # projects table created before V2.0 supported configurable lengths.
            cur.execute("ALTER TABLE projects "
                        "ADD COLUMN IF NOT EXISTS length INTEGER NOT NULL "
                        "DEFAULT 6")
        self.conn.commit()
        self._migrate_legacy_sequences()

    def _migrate_legacy_sequences(self) -> None:
        """Normalise projects to the current numbering model.

        The current model stores, per type: a ``prefix`` (any letters/digits),
        a ``length`` = the width of the zero-padded suffix counter, and a
        ``seq_*`` = the last-assigned counter (starts at 0, first number is
        ``<prefix>00...001``). Older projects stored ``seq_*`` as the full next
        number (e.g. ``800002``) and a total length of 6. This step derives the
        suffix width from the existing parts and converts any full-number
        counters to tails. It is idempotent and safe for new projects too.
        """
        parts = ("assembly", "part", "standard")
        rows = self.execute(
            "SELECT id, prefix_assembly, prefix_part, prefix_standard, "
            "length, seq_assembly, seq_part, seq_standard FROM projects")
        for row in rows:
            prefixes = {t: row[f"prefix_{t}"] for t in parts}
            seqs = {t: row[f"seq_{t}"] for t in parts}

            # Authoritative suffix width = length of a part minus its prefix.
            suffix = None
            for t in parts:
                pfx = prefixes[t]
                if not pfx:
                    continue
                m = self.execute_one(
                    "SELECT MAX(LENGTH(part_number)) AS m FROM parts "
                    "WHERE project_id = %s AND part_number LIKE %s",
                    (row["id"], pfx + "%"))
                if m and m["m"] is not None:
                    s = int(m["m"]) - len(pfx)
                    suffix = s if suffix is None else max(suffix, s)
            if suffix is None:
                # No parts: only migrate when there is clear legacy evidence
                # (a stored full-length counter that spans prefix + old length).
                for t in parts:
                    pfx, seq = prefixes[t], seqs[t]
                    if pfx and seq is not None:
                        s = str(seq)
                        if len(s) == len(pfx) + row["length"] and s.startswith(pfx):
                            suffix = max(row["length"] - len(pfx), 1)
                            break
            if suffix is None:
                # Nothing to normalise (new empty project) - leave untouched.
                continue
            suffix = max(1, min(suffix, 15))

            tails = {}
            for t in parts:
                pfx, seq = prefixes[t], seqs[t]
                if pfx is None or seq is None:
                    continue
                s = str(seq)
                # Full-number form only when it spans prefix + suffix.
                if len(s) == len(pfx) + suffix and s.startswith(pfx):
                    tails[t] = int(s[len(pfx):] or "0")

            if suffix != row["length"] or tails:
                sets = ["length = %s"]
                params = [suffix]
                for t, v in tails.items():
                    sets.append(f"seq_{t} = %s")
                    params.append(v)
                params.append(row["id"])
                self.execute(
                    f"UPDATE projects SET {', '.join(sets)} WHERE id = %s",
                    tuple(params))

    def close(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    # ------------------------------------------------------------------ helpers
    def execute(self, sql: str, params: tuple = ()) -> list:
        """Run a query and return all rows (commits the transaction)."""
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() if cur.description is not None else []
        self.conn.commit()
        return rows

    def execute_one(self, sql: str, params: tuple = ()) -> dict | None:
        """Run a query returning a single row (commits the transaction)."""
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        self.conn.commit()
        return row
