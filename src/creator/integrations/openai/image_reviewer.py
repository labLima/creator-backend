from __future__ import annotations

import base64
import json
from typing import Any

from creator.config import Settings
from creator.integrations.openai.client import create_openai_client
from creator.integrations.openai.image_generator import OpenAIImageGenerator
from creator.prompts.agents import build_reviewer_prompt
from creator.services.ai.image_provider import ImageProviderInvalidResponseError
from creator.services.ai.reviewer import ImageReviewRequest, ImageReviewResult


class OpenAIMultimodalImageReviewer:
    def __init__(self, settings: Settings, *, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client if client is not None else create_openai_client(settings)

    def review(self, request: ImageReviewRequest) -> ImageReviewResult:
        rendered = build_reviewer_prompt(
            {
                "briefing": request.briefing,
                "brand_context": dict(request.brand_context),
                "image_prompt": request.prompt,
                "output_instructions": (
                    "Return JSON only with decision (APPROVED, REFINE, or REJECTED), "
                    "score from 0 to 1, feedback (array), and safety_issues (array)."
                ),
            }
        )
        encoded = base64.b64encode(request.image_bytes).decode("ascii")
        image_url = f"data:{request.mime_type};base64,{encoded}"
        try:
            response = self._client.responses.create(
                model=self._settings.openai_reviewer_model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": rendered.text},
                            {"type": "input_image", "image_url": image_url},
                        ],
                    }
                ],
                temperature=0,
            )
        except Exception as error:
            raise OpenAIImageGenerator._classify_error(error) from error

        text = getattr(response, "output_text", None)
        if not isinstance(text, str) or not text.strip():
            raise ImageProviderInvalidResponseError("OpenAI image reviewer returned no text")
        try:
            payload = json.loads(_strip_json_fence(text))
            decision = str(payload["decision"])
            score = float(payload["score"])
            feedback = tuple(str(item) for item in payload.get("feedback", []))
            safety_issues = tuple(str(item) for item in payload.get("safety_issues", []))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ImageProviderInvalidResponseError(
                "OpenAI image reviewer returned invalid JSON"
            ) from error
        if decision not in {"APPROVED", "REFINE", "REJECTED"} or not 0 <= score <= 1:
            raise ImageProviderInvalidResponseError("OpenAI image reviewer returned invalid values")
        return ImageReviewResult(
            decision=decision,
            score=score,
            feedback=feedback,
            safety_issues=safety_issues,
            provider="openai",
            model=self._settings.openai_reviewer_model,
        )


def _strip_json_fence(text: str) -> str:
    normalized = text.strip()
    if normalized.startswith("```"):
        normalized = normalized.split("\n", 1)[-1]
        if normalized.endswith("```"):
            normalized = normalized[:-3]
    return normalized.strip()
