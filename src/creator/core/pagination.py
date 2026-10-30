"""Pagination vocabulary shared by routes and repository ports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SortDirection = Literal["asc", "desc"]


@dataclass(frozen=True, slots=True)
class PageRequest:
    page: int = 1
    limit: int = 50
    sort: SortDirection = "desc"

    @property
    def offset(self) -> int:
        normalized_page = max(self.page, 1)
        return (normalized_page - 1) * self.limit


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: list[T]
    total: int
    page: int
    limit: int


def page_request(page: int, limit: int, sort: str) -> PageRequest:
    return PageRequest(page=page, limit=limit, sort="asc" if sort == "created_at" else "desc")
