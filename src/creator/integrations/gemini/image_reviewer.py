from __future__ import annotations

import json
from typing import Any

from google.genai import types

from creator.config import Settings
from creator.integrations.gemini.client import create_gemini_client
from creator.integrations.gemini.exceptions import GeminiInvalidResponseError
from creator.prompts.agents import build_reviewer_prompt
from creator.services.ai.reviewer import ImageReviewRequest, ImageReviewResult


class GeminiMultimodalImageReviewer:
    def __init__(self, settings: Settings, *, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client if client is not None else create_gemini_client(settings)

    def review(self, request: ImageReviewRequest) -> ImageReviewResult:
        rendered = build_reviewer_prompt(
            {
                "briefing": request.briefing,
                "brand_context": dict(request.brand_context),
                "image_prompt": request.prompt,
                "review_criteria": dict(request.metadata),
                "output_instructions": (
                    "Return JSON only with decision (APPROVED, REFINE, or REJECTED), "
                    "score from 0 to 1, feedback (array), and safety_issues (array). "
                    "For REFINE, feedback must contain a concrete correction for the next "
                    "attempt and preserve the original Creative Concept."
                ),
            }
        )
        response = self._client.models.generate_content(
            model=self._settings.agent_reviewer_model,
            contents=[
                rendered.text,
                types.Part.from_bytes(data=request.image_bytes, mime_type=request.mime_type),
            ],
            config=types.GenerateContentConfig(temperature=0),
        )
        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise GeminiInvalidResponseError("Gemini image reviewer returned no text")
        try:
            payload = json.loads(_strip_json_fence(text))
            decision = str(payload["decision"])
            score = float(payload["score"])
            feedback = tuple(str(item) for item in payload.get("feedback", []))
            safety_issues = tuple(str(item) for item in payload.get("safety_issues", []))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise GeminiInvalidResponseError(
                "Gemini image reviewer returned invalid JSON"
            ) from error
        if decision not in {"APPROVED", "REFINE", "REJECTED"} or not 0 <= score <= 1:
            raise GeminiInvalidResponseError("Gemini image reviewer returned invalid values")
        return ImageReviewResult(
            decision=decision,
            score=score,
            feedback=feedback,
            safety_issues=safety_issues,
            provider="gemini",
            model=self._settings.agent_reviewer_model,
        )


def _strip_json_fence(text: str) -> str:
    normalized = text.strip()
    if normalized.startswith("```"):
        normalized = normalized.split("\n", 1)[-1]
        if normalized.endswith("```"):
            normalized = normalized[:-3]
    return normalized.strip()
