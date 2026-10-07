"""Data access layer (repositories) over the central PostgreSQL server."""

from __future__ import annotations

import datetime

from . import config
from .db import ConnectionManager
from .models import Part, Project

SEQ_COL = {t: f"seq_{t.lower()}" for t in config.PART_TYPES}


class ProjectRepository:
    """Manage projects (engineering databases) on the server."""

    def __init__(self, db: ConnectionManager) -> None:
        self.db = db

    def create(self, name: str, prefixes: dict, length: int,
               created_date: str | None = None) -> Project:
        created = created_date or datetime.date.today().isoformat()
        row = self.db.execute_one(
            "INSERT INTO projects "
            "(name, prefix_assembly, prefix_part, prefix_standard, length, "
            " seq_assembly, seq_part, seq_standard, created_date) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id, name, prefix_assembly, prefix_part, prefix_standard, "
            "length, created_date",
            (name, prefixes["Assembly"], prefixes["Part"], prefixes["Standard"],
             length, 0, 0, 0, created))
        return Project.from_row(row)

    def list(self) -> list[Project]:
        rows = self.db.execute("SELECT * FROM projects ORDER BY name")
        return [Project.from_row(r) for r in rows]

    def get(self, project_id: int) -> Project | None:
        row = self.db.execute_one(
            "SELECT * FROM projects WHERE id = %s", (project_id,))
        return Project.from_row(row) if row else None

    def get_by_name(self, name: str) -> Project | None:
        row = self.db.execute_one(
            "SELECT * FROM projects WHERE name = %s", (name,))
        return Project.from_row(row) if row else None

    def delete(self, project_id: int) -> None:
        self.db.execute("DELETE FROM projects WHERE id = %s", (project_id,))

    def part_count(self, project_id: int) -> int:
        row = self.db.execute_one(
            "SELECT COUNT(*) AS c FROM parts WHERE project_id = %s",
            (project_id,))
        return row["c"]


class PartsRepository:
    """CRUD and monotonic number generation for parts inside one project.

    A part number is ``<leading char><zero-padded counter>`` where the leading
    char may be any single letter or digit, and the counter starts at 1 (so the
    first number is ``<prefix>00...001``). Counters are stored as the numeric
    tail and never reused after a delete.
    """

    def __init__(self, db: ConnectionManager, project: Project) -> None:
        self.db = db
        self.project = project

    # ------------------------------------------------------------------ numbering
    def _prefix(self, part_type: str) -> str:
        return self.project.prefixes[part_type]

    def _suffix_len(self) -> int:
        # project.length = width of the zero-padded suffix counter
        return max(self.project.length, 1)

    def _max_counter(self) -> int:
        return 10 ** self._suffix_len() - 1

    def _format(self, part_type: str, counter: int) -> str:
        return f"{self._prefix(part_type)}{counter:0{self._suffix_len()}d}"

    def _read_seq(self, part_type: str) -> int:
        col = SEQ_COL[part_type]
        row = self.db.execute_one(
            f"SELECT {col} AS seq FROM projects WHERE id = %s",
            (self.project.id,))
        return int(row["seq"])

    def peek_number(self, part_type: str) -> str:
        nxt = self._read_seq(part_type) + 1
        if nxt > self._max_counter():
            raise ValueError(
                f"No more numbers available for '{part_type}' "
                f"(prefix '{self._prefix(part_type)}' exhausted).")
        return self._format(part_type, nxt)

    def _resolve_number(self, part_type: str, desired: str | None = None,
                        exclude: str | None = None) -> str:
        prefix = self._prefix(part_type)
        total = self.project.length
        maxc = self._max_counter()
        seq = self._read_seq(part_type)

        raw = str(desired).strip() if desired is not None else ""
        if raw:
            if (len(raw) != len(prefix) + total
                    or not raw.startswith(prefix)
                    or not raw[len(prefix):].isdigit()):
                raise ValueError(
                    f"Part number must start with '{prefix}' followed by "
                    f"{total} digits.")
            counter = int(raw[len(prefix):] or "0")
        else:
            counter = seq + 1

        if counter < 1:
            counter = 1

        def _used(c: int) -> bool:
            code = self._format(part_type, c)
            if exclude is not None and code == exclude:
                return False
            row = self.db.execute_one(
                "SELECT 1 AS x FROM parts WHERE project_id = %s "
                "AND part_number = %s", (self.project.id, code))
            return row is not None

        while _used(counter):
            counter += 1
            if counter > maxc:
                raise ValueError(
                    f"No free number available for '{part_type}' "
                    f"(prefix '{prefix}' exhausted).")

        if counter > seq:
            col = SEQ_COL[part_type]
            self.db.execute(
                f"UPDATE projects SET {col} = %s WHERE id = %s",
                (counter, self.project.id))
        return self._format(part_type, counter)

    # ------------------------------------------------------------------ create
    def create(self, part_name: str, part_type: str, material: str = "",
               description: str = "") -> str:
        name = part_name.strip()
        if not name:
            raise ValueError("Part name must not be empty.")
        if part_type not in config.PART_TYPES:
            raise ValueError(f"Unknown part type: {part_type}")

        prefix = self._prefix(part_type)
        maxc = self._max_counter()
        col = SEQ_COL[part_type]
        # Atomic per-project counter increment (monotonic, never reuses numbers).
        with self.db.conn.cursor() as cur:
            cur.execute(
                f"UPDATE projects SET {col} = {col} + 1 WHERE id = %s "
                f"RETURNING {col}", (self.project.id,))
            row = cur.fetchone()
        nxt = int(row[col])
        if nxt > maxc:
            raise ValueError(
                f"No more numbers available for '{part_type}' "
                f"(prefix '{prefix}' exhausted).")
        number = self._format(part_type, nxt)
        today = datetime.date.today().isoformat()
        self.db.execute(
            "INSERT INTO parts (project_id, part_number, part_name, part_type, "
            "material, description, created_date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (self.project.id, number, name, part_type, material.strip(),
             description.strip(), today))
        return number

    # ------------------------------------------------------------------ read
    def search(self, keyword: str) -> list[Part]:
        keyword = keyword.strip()
        if keyword:
            like = f"%{keyword}%"
            rows = self.db.execute(
                "SELECT * FROM parts WHERE project_id = %s "
                "AND (part_number ILIKE %s OR part_name ILIKE %s "
                "     OR material ILIKE %s) "
                "ORDER BY part_number ASC",
                (self.project.id, like, like, like))
        else:
            rows = self.db.execute(
                "SELECT * FROM parts WHERE project_id = %s "
                "ORDER BY part_number ASC", (self.project.id,))
        return [Part.from_row(r) for r in rows]

    def get(self, part_number: str) -> Part | None:
        row = self.db.execute_one(
            "SELECT * FROM parts WHERE project_id = %s AND part_number = %s",
            (self.project.id, part_number))
        return Part.from_row(row) if row else None

    def count(self) -> int:
        return ProjectRepository(self.db).part_count(self.project.id)

    # ------------------------------------------------------------------ update / delete
    def update(self, part_number: str, new_name: str, new_material: str,
               new_description: str) -> None:
        self.db.execute(
            "UPDATE parts SET part_name = %s, material = %s, description = %s "
            "WHERE project_id = %s AND part_number = %s",
            (new_name.strip(), new_material.strip(), new_description.strip(),
             self.project.id, part_number))

    def update_part(self, old_number: str, new_number: str, new_name: str,
                    new_material: str, new_description: str,
                    part_type: str) -> str:
        final = self._resolve_number(part_type, desired=new_number,
                                     exclude=old_number)
        self.db.execute(
            "UPDATE parts SET part_number = %s, part_name = %s, material = %s, "
            "description = %s WHERE project_id = %s AND part_number = %s",
            (final, new_name.strip(), new_material.strip(),
             new_description.strip(), self.project.id, old_number))
        return final

    def delete(self, part_number: str) -> None:
        self.db.execute(
            "DELETE FROM parts WHERE project_id = %s AND part_number = %s",
            (self.project.id, part_number))
