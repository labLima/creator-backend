from uuid import uuid4

import pytest
from pydantic import ValidationError

from creator.domain.pipeline_events import (
    PipelineEvent,
    PipelineEventType,
    PipelinePayloadReference,
)
from creator.workers import pipeline_events


def test_pipeline_event_is_transport_neutral_and_reference_based() -> None:
    event = PipelineEvent(
        event_id=uuid4(),
        event_type=PipelineEventType.BUSINESS_COMPLETED,
        event_version="1.0",
        workspace_id=uuid4(),
        run_id=uuid4(),
        step_id=uuid4(),
        correlation_id=uuid4(),
        output_hash="a" * 64,
        payload_ref=PipelinePayloadReference(schema_name="BusinessOutput", schema_version="1.0"),
    )
    assert event.payload_ref.schema_name == "BusinessOutput"
    assert "prompt" not in event.payload_ref.model_dump()


@pytest.mark.parametrize("forbidden", [{"prompt": "secret"}, {"image_bytes": b"png"}])
def test_pipeline_event_rejects_hidden_or_binary_payloads(forbidden: object) -> None:
    with pytest.raises(ValidationError):
        PipelineEvent(
            event_id=uuid4(),
            event_type=PipelineEventType.WRITER_COMPLETED,
            event_version="1.0",
            workspace_id=uuid4(),
            run_id=uuid4(),
            correlation_id=uuid4(),
            payload_ref=forbidden,  # type: ignore[arg-type]
        )


def test_pipeline_event_rejects_unknown_version() -> None:
    with pytest.raises(ValidationError):
        PipelineEvent(
            event_id=uuid4(),
            event_type=PipelineEventType.PLANNER_COMPLETED,
            event_version="2.0",
            workspace_id=uuid4(),
            run_id=uuid4(),
            correlation_id=uuid4(),
        )


def test_stage_events_route_to_the_matching_checkpoint(monkeypatch) -> None:
    calls: list[str] = []

    def fake_consumer(
        payload: dict[str, object], expected: set[PipelineEventType], stage: str
    ) -> None:
        calls.append(stage)

    monkeypatch.setattr(pipeline_events, "_consume_stage", fake_consumer)
    base = {
        "event_id": uuid4(),
        "event_version": "1.0",
        "workspace_id": uuid4(),
        "run_id": uuid4(),
        "correlation_id": uuid4(),
    }
    for event_type, expected in (
        (PipelineEventType.WORKFLOW_STARTED, "BUSINESS"),
        (PipelineEventType.BUSINESS_COMPLETED, "PLANNER"),
        (PipelineEventType.PLANNER_COMPLETED, "WRITER"),
        (PipelineEventType.WRITER_COMPLETED, "ARTIST"),
        (PipelineEventType.ARTIST_COMPLETED, "REVIEWER"),
        (PipelineEventType.WRITER_REFINEMENT_REQUESTED, "WRITER"),
    ):
        handler = {
            PipelineEventType.WORKFLOW_STARTED: pipeline_events.consume_business_event,
            PipelineEventType.BUSINESS_COMPLETED: pipeline_events.consume_planner_event,
            PipelineEventType.PLANNER_COMPLETED: pipeline_events.consume_writer_event,
            PipelineEventType.WRITER_COMPLETED: pipeline_events.consume_artist_event,
            PipelineEventType.ARTIST_COMPLETED: pipeline_events.consume_reviewer_event,
            PipelineEventType.WRITER_REFINEMENT_REQUESTED: pipeline_events.consume_writer_event,
        }[event_type]
        handler({**base, "event_type": event_type})
        assert calls[-1] == expected
