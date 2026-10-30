"""Pagination request parsing."""

from __future__ import annotations

from creator.repositories.common import PageRequest


def page_request(page: int, limit: int, sort: str) -> PageRequest:
    return PageRequest(page=page, limit=limit, sort="asc" if sort == "created_at" else "desc")
