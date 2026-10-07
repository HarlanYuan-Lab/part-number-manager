"""Business-logic layer.

Responsibilities:
  * DatabaseService  - validation + orchestration of database lifecycle.
  * PartNumberService - orchestration of part-number generation and CRUD
                        against the currently active database.
"""

from __future__ import annotations

import re

from . import config
from .models import DatabaseSummary, Part
from .repositories import DatabaseRepository, PartsRepository


class DatabaseService:
    """High-level operations on databases (files + prefixes)."""

    def __init__(self) -> None:
        self._repo = DatabaseRepository

    @staticmethod
    def validate_prefixes(prefixes: dict) -> None:
        """Prefixes must be 1-3 digits, distinct and prefix-free.

        "Prefix-free" means no prefix is an initial segment of another one;
        otherwise two part types could generate colliding 6-digit codes.
        """
        if set(prefixes) != set(config.PART_TYPES):
            raise ValueError("Prefixes must be provided for all three part types.")

        items = []
        for part_type in config.PART_TYPES:
            prefix = str(prefixes[part_type]).strip()
            if not re.fullmatch(r"\d{1,3}", prefix):
                raise ValueError(
                    f"Prefix for '{part_type}' must be a 1-3 digit number.")
            items.append((part_type, prefix))

        distinct = {p for _, p in items}
        if len(distinct) != len(items):
            raise ValueError("The three leading numbers must be different.")

        for first in items:
            for second in items:
                if first is second:
                    continue
                if second[1].startswith(first[1]):
                    raise ValueError(
                        f"'{first[1]}' cannot be a leading part of '{second[1]}' "
                        f"(they would collide). Choose non-overlapping codes.")

    def create(self, name: str, prefixes: dict, folder: str | None = None) -> str:
        name = name.strip()
        if not name:
            raise ValueError("Database name must not be empty.")
        if any(c in name for c in '\\/:*?"<>|'):
            raise ValueError("Database name contains invalid characters.")
        self.validate_prefixes(prefixes)
        return self._repo.create(name, prefixes, folder)

    def import_database(self, path: str) -> str:
        """Open/register an existing database file; returns its name."""
        return self._repo.import_database(path)

    def export_database(self, path: str, dest: str) -> str:
        """Back up a database file to ``dest``."""
        return self._repo.export_database(path, dest)

    def delete(self, path: str) -> None:
        self._repo.delete(path)

    def exists(self, path: str) -> bool:
        return self._repo.exists(path)

    def list_databases(self) -> list[DatabaseSummary]:
        return self._repo.list()

    def get_name(self, path: str) -> str:
        return self._repo.get_db_name(path)

    def get_prefixes(self, path: str) -> dict:
        return self._repo.get_prefixes(path)


class PartNumberService:
    """Orchestrates part creation/management inside a single database."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._repo = PartsRepository(db_path)

    @property
    def db_path(self) -> str:
        return self._db_path

    def next_number(self, part_type: str) -> str:
        return self._repo.next_number(part_type)

    def peek_number(self, part_type: str) -> str:
        """Next number without consuming it (for preview)."""
        return self._repo.peek_number(part_type)

    def create(self, part_name: str, part_type: str, material: str = "",
               description: str = "") -> str:
        return self._repo.create(part_name, part_type, material, description)

    def search(self, keyword: str) -> list[Part]:
        return self._repo.search(keyword)

    def get(self, part_number: str) -> Part | None:
        return self._repo.get(part_number)

    def count(self) -> int:
        return self._repo.count()

    def update(self, part_number: str, new_name: str, new_material: str,
               new_description: str) -> None:
        self._repo.update(part_number, new_name, new_material, new_description)

    def update_part(self, old_number: str, new_number: str, new_name: str,
                    new_material: str, new_description: str,
                    part_type: str) -> str:
        """Update + renumber a part, keeping the number unique; returns final no."""
        return self._repo.update_part(old_number, new_number, new_name,
                                      new_material, new_description, part_type)

    def delete(self, part_number: str) -> None:
        self._repo.delete(part_number)
