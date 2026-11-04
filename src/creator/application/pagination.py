from __future__ import annotations

from typing import Any

from creator.core.pagination import Page


def page_payload(page: Page[Any], serializer: Any) -> dict[str, Any]:
    return {
        "items": [serializer(item) for item in page.items],
        "pagination": {"page": page.page, "limit": page.limit, "total": page.total},
    }
