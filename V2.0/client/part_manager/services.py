"""Application services: validation plus higher-level operations."""

from __future__ import annotations

from . import config
from .db import ConnectionManager
from .models import Project
from .repositories import PartsRepository, ProjectRepository


class ProjectService:
    """Business rules for projects (engineering databases)."""

    def __init__(self, db: ConnectionManager) -> None:
        self.db = db
        self._repo = ProjectRepository(db)

    @staticmethod
    def validate_name(name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("Project name must not be empty.")
        return name

    @staticmethod
    def validate_prefixes(prefixes: dict) -> dict:
        out = {}
        for t in config.PART_TYPES:
            value = str(prefixes.get(t, "")).strip()
            if not value or not value.isalnum():
                raise ValueError(
                    f"The '{t}' prefix must contain only letters and digits.")
            out[t] = value
        values = list(out.values())
        if len(set(values)) != len(values):
            raise ValueError(
                "The three prefixes (Assembly, Part, Standard) "
                "must be different from each other.")
        return out

    @staticmethod
    def validate_length(length: object) -> int:
        try:
            n = int(str(length).strip())
        except (TypeError, ValueError):
            raise ValueError(
                f"Suffix length must be a whole number between "
                f"{config.MIN_LENGTH} and {config.MAX_LENGTH}.") from None
        if not (config.MIN_LENGTH <= n <= config.MAX_LENGTH):
            raise ValueError(
                f"Suffix length must be between {config.MIN_LENGTH} and "
                f"{config.MAX_LENGTH}.")
        return n

    def create(self, name: str, prefixes: dict, length: int = config.NUMBER_LENGTH,
               created_date: str | None = None) -> Project:
        name = self.validate_name(name)
        prefixes = self.validate_prefixes(prefixes)
        length = self.validate_length(length)
        if self._repo.get_by_name(name):
            raise ValueError(f"A project named '{name}' already exists.")
        return self._repo.create(name, prefixes, length, created_date)

    def delete(self, project_id: int) -> None:
        self._repo.delete(project_id)

    def list_projects(self) -> list[Project]:
        return self._repo.list()

    def get(self, project_id: int) -> Project | None:
        return self._repo.get(project_id)

    def get_by_name(self, name: str) -> Project | None:
        return self._repo.get_by_name(name)

    def part_count(self, project_id: int) -> int:
        return self._repo.part_count(project_id)


class PartNumberService:
    """Business rules for part numbers inside one project."""

    def __init__(self, db: ConnectionManager, project: Project) -> None:
        self._repo = PartsRepository(db, project)
        self.project = project

    def peek_number(self, part_type: str) -> str:
        return self._repo.peek_number(part_type)

    def create(self, part_name: str, part_type: str, material: str = "",
               description: str = "") -> str:
        return self._repo.create(part_name, part_type, material, description)

    def search(self, keyword: str = ""):
        return self._repo.search(keyword)

    def get(self, part_number: str):
        return self._repo.get(part_number)

    def count(self) -> int:
        return self._repo.count()

    def update(self, part_number: str, new_name: str, new_material: str,
               new_description: str) -> None:
        self._repo.update(part_number, new_name, new_material, new_description)

    def update_part(self, old_number: str, new_number: str, new_name: str,
                    new_material: str, new_description: str,
                    part_type: str) -> str:
        return self._repo.update_part(old_number, new_number, new_name,
                                      new_material, new_description, part_type)

    def delete(self, part_number: str) -> None:
        self._repo.delete(part_number)
