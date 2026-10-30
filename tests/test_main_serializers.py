from datetime import UTC, datetime
from uuid import UUID

import creator.api.serializers as serializers
import creator.core.pagination as pagination
from creator.api.responses import page_payload as main_page_payload


class _Record:
    """Small structural fixture for exercising the response contract mappers."""

    def __getattr__(self, name: str) -> object:
        if name in {"status", "human_review", "role", "type", "channel", "provider"}:
            return _EnumValue()
        if name.endswith("_at") or name.endswith("_period"):
            return datetime(2026, 1, 1, tzinfo=UTC)
        if name.endswith("_id") or name == "id":
            return UUID("11111111-1111-1111-1111-111111111111")
        if name in {"metadata", "payload", "objectives", "info", "price_brackets"}:
            return {"fixture": True}
        if name in {"is_active", "is_enabled", "closed", "delinquent", "signature_verified"}:
            return True
        if name in {"amount", "amount_cents", "price_cents", "quantity", "cycles", "attempts"}:
            return 1
        return f"fixture-{name}"


class _EnumValue:
    value = "fixture"


def test_all_response_contract_mappers_return_structured_data() -> None:
    record = _Record()
    mapper_names = [
        name for name in dir(serializers) if name.endswith("_data") and name.startswith("_")
    ]

    # These are intentionally tested as a group: every mapper is a public response
    # contract boundary, even though its implementation is private to main.py.
    for name in mapper_names:
        mapper = getattr(serializers, name)
        if name in {
            "_content_detail_data",
            "_content_page_data",
            "_image_generation_status_data",
        }:
            continue
        if name == "_page_data":
            continue
        result = mapper(record)
        assert isinstance(result, dict), name
        assert result, name


def test_page_and_request_helpers_preserve_contract_values() -> None:
    page = serializers.Page(items=[_Record()], total=1, page=2, limit=10)
    result = main_page_payload(page, lambda item: {"id": str(item.id)})

    assert result == {
        "items": [{"id": "11111111-1111-1111-1111-111111111111"}],
        "pagination": {"total": 1, "page": 2, "limit": 10},
    }
    request = pagination.page_request(2, 10, "-created_at")
    assert request.page == 2
    assert request.limit == 10
    assert request.sort == "desc"
