"""Deterministic rendering of approved copy over a generated scene."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from io import BytesIO
from uuid import UUID

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

from creator.config import Settings
from creator.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from creator.infrastructure.runtime.storage import create_storage_provider
from creator.services.ai.factory import create_image_reviewer
from creator.services.ai.image_provider import ImageGenerationResult
from creator.services.ai.reviewer import ImageReviewRequest

COMPOSITION_VERSION = "1.0"
SCENE_PROMPT_VERSION = "1.0"
SCENE_SUFFIX = (
    " Produce a clean photographic scene with empty space for later typography. "
    "Do not render letters, numbers, signage, logos, watermarks, or promotional text."
)


class CompositionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def compose_generated_image(
    *,
    result: ImageGenerationResult,
    approved: Mapping[str, object],
    workspace_id: UUID,
    brand_id: UUID,
    user_id: UUID,
    settings: Settings,
    scene_review_approved: bool = False,
) -> ImageGenerationResult:
    """Resolve only owned storage assets; fail closed on uncertain scene text."""
    with SqlAlchemyUnitOfWork() as uow:
        brand = uow.brand.brands.get_for_user(user_id=user_id, brand_id=brand_id)
        if brand is None or brand.workspace_id != workspace_id:
            raise CompositionError("COMPOSITION_BRAND_UNAVAILABLE")
        brand_settings = uow.brand.settings.get_for_user(user_id=user_id, brand_id=brand_id)
        visual = brand_settings.visual_settings if brand_settings else {}
        if not isinstance(visual, dict):
            raise CompositionError("COMPOSITION_STYLE_INVALID")
        font_id = visual.get("font_asset_id")
        logo_id = visual.get("logo_asset_id")
        if not isinstance(font_id, str) or not isinstance(logo_id, str):
            raise CompositionError("COMPOSITION_ASSET_MISSING")
        try:
            font_asset = uow.brand.assets.get_for_user(user_id=user_id, asset_id=UUID(font_id))
            logo_asset = uow.brand.assets.get_for_user(user_id=user_id, asset_id=UUID(logo_id))
        except ValueError as error:
            raise CompositionError("COMPOSITION_ASSET_INVALID") from error
        if (
            font_asset is None
            or logo_asset is None
            or font_asset.brand_id != brand_id
            or logo_asset.brand_id != brand_id
            or font_asset.type.upper() != "FONT"
            or logo_asset.type.upper() != "LOGO"
        ):
            raise CompositionError("COMPOSITION_ASSET_INVALID")
        asset_paths = (font_asset.file_url, logo_asset.file_url)
        asset_ids = (font_id, logo_id)
    storage = create_storage_provider(settings)
    assets: list[bytes] = []
    for url in asset_paths:
        if not url.startswith("storage://"):
            raise CompositionError("COMPOSITION_ASSET_INVALID")
        path = url[len("storage://") :]
        if not path or path.startswith("/") or "\\" in path or ".." in path.split("/"):
            raise CompositionError("COMPOSITION_ASSET_INVALID")
        try:
            assets.append(
                storage.download(path, max_bytes=min(settings.storage_max_object_bytes, 10_000_000))
            )
        except Exception as error:
            raise CompositionError("COMPOSITION_ASSET_UNAVAILABLE") from error
    if scene_review_approved:
        review_metadata: dict[str, object] = {"decision": "HUMAN_APPROVED"}
    else:
        try:
            review = create_image_reviewer(settings).review(
                ImageReviewRequest(
                    image_bytes=result.image_bytes,
                    mime_type=result.mime_type,
                    prompt="Inspect for visible letters, numbers, signs, logos or watermarks. "
                    "Return APPROVED only if you are confident none are present; "
                    "otherwise return REJECTED or REFINE.",
                    briefing="Scene must contain no visible text or brand marks.",
                    brand_context={},
                )
            )
        except Exception as error:
            raise CompositionError("COMPOSITION_TEXT_CHECK_INCONCLUSIVE") from error
        if review.decision == "REJECTED":
            raise CompositionError("COMPOSITION_SCENE_TEXT_DETECTED")
        if review.decision != "APPROVED" or review.score < 0.9:
            raise CompositionError("COMPOSITION_TEXT_CHECK_INCONCLUSIVE")
        review_metadata = {
            "decision": review.decision,
            "score": review.score,
            "provider": review.provider,
            "model": review.model,
        }
    try:
        scene = Image.open(BytesIO(result.image_bytes))
        scene.load()
        canvas = scene.convert("RGBA")
        if canvas.size != (result.width, result.height):
            raise CompositionError("COMPOSITION_DIMENSIONS_INVALID")
        logo = Image.open(BytesIO(assets[1])).convert("RGBA")
        if logo.width * logo.height > 4_000_000:
            raise CompositionError("COMPOSITION_ASSET_INVALID")
        font_probe = ImageFont.truetype(BytesIO(assets[0]), size=24)
        if not font_probe.getmask("Áçã ÉÊ Ü").getbbox():
            raise CompositionError("COMPOSITION_FONT_INVALID")
    except (OSError, UnidentifiedImageError, ValueError) as error:
        raise CompositionError("COMPOSITION_ASSET_INVALID") from error
    margin_fraction = visual.get("safe_margin", 0.06)
    if not isinstance(margin_fraction, (float, int)) or not 0.03 <= margin_fraction <= 0.2:
        raise CompositionError("COMPOSITION_STYLE_INVALID")
    margin = round(min(canvas.size) * margin_fraction)
    max_width = canvas.width - 2 * margin
    if max_width <= 0:
        raise CompositionError("COMPOSITION_TEXT_OVERFLOW")
    logo.thumbnail((max_width // 3, max(1, canvas.height // 8)))
    canvas.alpha_composite(logo, (canvas.width - margin - logo.width, margin))
    draw = ImageDraw.Draw(canvas)
    color = visual.get("text_color", "#FFFFFF")
    if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
        raise CompositionError("COMPOSITION_STYLE_INVALID")
    try:
        rgb = tuple(int(color[index : index + 2], 16) for index in (1, 3, 5))
    except ValueError as error:
        raise CompositionError("COMPOSITION_STYLE_INVALID") from error
    alignment = visual.get("text_alignment", "left")
    if alignment not in {"left", "center", "right"}:
        raise CompositionError("COMPOSITION_STYLE_INVALID")
    segments = [
        str(approved[key])
        for key in ("headline", "supporting_text", "call_to_action")
        if isinstance(approved.get(key), str) and approved[key]
    ]
    if not segments:
        raise CompositionError("COMPOSITION_TEXT_MISSING")
    fitted = None
    for size in range(max(18, round(canvas.height * 0.075)), 17, -1):
        font = ImageFont.truetype(BytesIO(assets[0]), size=size)
        lines: list[str] = []
        for segment in segments:
            paragraphs = segment.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            for paragraph in paragraphs:
                lines.extend(_wrap_paragraph(paragraph, font=font, draw=draw, max_width=max_width))
            lines.append("")
        if any(draw.textlength(line, font=font) > max_width for line in lines):
            continue
        line_height = round(size * 1.3)
        if len(lines) * line_height <= canvas.height - 3 * margin - logo.height:
            fitted = (font, lines, line_height, size)
            break
    if fitted is None:
        raise CompositionError("COMPOSITION_TEXT_OVERFLOW")
    font, lines, line_height, size = fitted
    y = canvas.height - margin - len(lines) * line_height
    # A uniform backing plate makes the approved color legible on arbitrary scenes.
    luminance = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255
    backing = (0, 0, 0, 220) if luminance > 0.5 else (255, 255, 255, 220)
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle(
        (0, max(0, y - margin // 2), canvas.width, canvas.height), fill=backing
    )
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)
    for line in lines:
        width = draw.textlength(line, font=font)
        x = (
            margin
            if alignment == "left"
            else (
                (canvas.width - width) / 2
                if alignment == "center"
                else canvas.width - margin - width
            )
        )
        draw.text((x, y), line, font=font, fill=rgb)
        y += line_height
    output = BytesIO()
    canvas.convert("RGB").save(output, format="PNG")
    metadata = {
        **result.metadata,
        "composition": {
            "version": COMPOSITION_VERSION,
            "scene_prompt_version": SCENE_PROMPT_VERSION,
            "scene_prompt": result.prompt,
            "approved_text": dict(approved),
            "font_asset_id": asset_ids[0],
            "logo_asset_id": asset_ids[1],
            "font_sha256": hashlib.sha256(assets[0]).hexdigest(),
            "logo_sha256": hashlib.sha256(assets[1]).hexdigest(),
            "width": canvas.width,
            "height": canvas.height,
            "font_size": size,
            "safe_margin": margin,
            "text_color": color,
            "text_alignment": alignment,
            "scene_text_check": review_metadata,
        },
    }
    return ImageGenerationResult(
        output.getvalue(),
        "image/png",
        canvas.width,
        canvas.height,
        result.model,
        result.prompt,
        metadata,
    )


def _wrap_paragraph(
    text: str, *, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, max_width: int
) -> list[str]:
    """Wrap text without discarding whitespace or passing line breaks to Pillow."""
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    for token in re.findall(r"\s+|\S+", text):
        candidate = current + token
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        if token.isspace():
            # Preserve whitespace runs even when a run itself spans the line width.
            for character in token:
                candidate = current + character
                if current and draw.textlength(candidate, font=font) > max_width:
                    lines.append(current)
                    current = character
                else:
                    current = candidate
            continue
        # Long words are split only when the word cannot fit on an empty line.
        for character in token:
            candidate = current + character
            if current and draw.textlength(candidate, font=font) > max_width:
                lines.append(current)
                current = character
            else:
                current = candidate
    lines.append(current)
    return lines
