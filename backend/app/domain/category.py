from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CategoryNature(str, Enum):
    NEED = "NEED"
    WANT = "WANT"
    SAVING = "SAVING"


@dataclass(frozen=True, slots=True)
class Category:
    id: str
    name: str
    nature: Optional[CategoryNature] = None

    @staticmethod
    def create(
        *,
        id: str,
        name: str,
        nature: Optional[CategoryNature] = None,
    ) -> "Category":
        if not isinstance(id, str) or id.strip() == "":
            raise ValueError("id cannot be empty")

        if not isinstance(name, str) or name.strip() == "":
            raise ValueError("name cannot be empty")

        if nature is not None and not isinstance(nature, CategoryNature):
            raise ValueError("nature must be a CategoryNature or None")

        return Category(
            id=id.strip(),
            name=name.strip(),
            nature=nature,
        )
