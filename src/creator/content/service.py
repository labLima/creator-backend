"""Use cases for the content capability.

The generation and improvement pipelines keep their own focused modules; this
module is the single service entry point for the capability.
"""

from __future__ import annotations

from creator.content.generation_service import (
    GenerateContentCommand,
    generate_content,
)
from creator.content.improvement_service import (
    ImproveContentCommand,
    ImprovedContentPreview,
    improve_content,
)

__all__ = [
    "GenerateContentCommand",
    "ImproveContentCommand",
    "ImprovedContentPreview",
    "generate_content",
    "improve_content",
]
