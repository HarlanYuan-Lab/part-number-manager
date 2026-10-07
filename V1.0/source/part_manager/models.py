"""Data models shared across layers (plain, UI-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Part:
    """A single part record in a database."""

    part_number: str
    part_name: str
    part_type: str
    material: str = ""
    description: str = ""
    created_date: str = ""

    @classmethod
    def from_row(cls, row) -> "Part":
        """Build a Part from a sqlite3.Row (dictionary-like)."""
        keys = row.keys()
        return cls(
            part_number=row["part_number"],
            part_name=row["part_name"],
            part_type=row["part_type"],
            material=row["material"] if "material" in keys else "",
            description=row["description"] if "description" in keys else "",
            created_date=row["created_date"] if "created_date" in keys else "",
        )


@dataclass
class DatabaseSummary:
    """A lightweight summary of a database, used by the Databases panel."""

    name: str
    path: str
    prefixes: dict
    created_date: str = ""
    part_count: int = 0
