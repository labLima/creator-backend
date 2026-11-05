from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from creator.api.serializers import _generation_data
from creator.generation.ports import GenerationRecord

NOW = datetime(2026, 11, 5, tzinfo=UTC)


def test_generation_serializer_does_not_expose_resolved_input() -> None:
    generation = GenerationRecord(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        workspace_id=UUID("20000000-0000-0000-0000-000000000001"),
        content_id=UUID("30000000-0000-0000-0000-000000000001"),
        brand_id=None,
        project_id=None,
        requested_by_user_id=None,
        generation_type="IMAGE",
        model="gpt-image-2",
        prompt="prompt",
        parameters={
            "resolved_input": {"briefing": "internal", "direction": "internal"},
            "request_input": {"artifact_type": "IMAGE"},
        },
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )

    serialized = _generation_data(generation)

    assert "resolved_input" not in serialized["parameters"]
    assert serialized["parameters"]["request_input"] == {"artifact_type": "IMAGE"}
