"""Data models for projects and parts (server-side records)."""

from __future__ import annotations

from . import config


class Project:
    """A project (engineering database) stored on the central server."""

    def __init__(self, project_id: int, name: str, prefixes: dict,
                 length: int, created_date: str) -> None:
        self.id = project_id
        self.name = name
        self.prefixes = prefixes
        self.length = length
        self.created_date = created_date

    @classmethod
    def from_row(cls, row: dict) -> "Project":
        return cls(
            project_id=row["id"],
            name=row["name"],
            prefixes={
                "Assembly": row["prefix_assembly"],
                "Part": row["prefix_part"],
                "Standard": row["prefix_standard"],
            },
            length=row.get("length", config.NUMBER_LENGTH),
            created_date=row["created_date"],
        )


class Part:
    """A part inside a project."""

    def __init__(self, part_number: str, part_name: str, part_type: str,
                 material: str, description: str, created_date: str) -> None:
        self.part_number = part_number
        self.part_name = part_name
        self.part_type = part_type
        self.material = material
        self.description = description
        self.created_date = created_date

    @classmethod
    def from_row(cls, row: dict) -> "Part":
        return cls(
            part_number=row["part_number"],
            part_name=row["part_name"],
            part_type=row["part_type"],
            material=row["material"],
            description=row["description"],
            created_date=row["created_date"],
        )
