"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.content.ports import ImageMetadata, ImageRecord
from creator.generation.ports import (
    GenerationHistoryFilters,
    GenerationJobRecord,
    GenerationJobStatusEventRecord,
    ImageGenerationRepository,
    ImageGenerationStatusRecord,
    ImageGenerationWorkItem,
)

__all__ = [
    "GenerationHistoryFilters",
    "GenerationJobRecord",
    "GenerationJobStatusEventRecord",
    "ImageGenerationRepository",
    "ImageGenerationStatusRecord",
    "ImageGenerationWorkItem",
    "ImageMetadata",
    "ImageRecord",
]
