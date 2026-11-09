from __future__ import annotations

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image, ImageDraw, ImageFont

from creator.infrastructure.runtime import image_composition as composition
from creator.services.ai.image_provider import ImageGenerationResult
from creator.services.ai.reviewer import ImageReviewResult


def _font_bytes() -> bytes:
    candidates = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate.read_bytes()
    pytest.skip("No TrueType font available for image rendering test")


def _image(width: int, height: int) -> ImageGenerationResult:
    output = BytesIO()
    Image.new("RGB", (width, height), "#8B5A2B").save(output, format="PNG")
    return ImageGenerationResult(
        output.getvalue(), "image/png", width, height, "test-model", "scene prompt", {}
    )


def _setup(monkeypatch: pytest.MonkeyPatch, decision: str = "APPROVED") -> tuple[object, object]:
    workspace_id, brand_id, user_id = uuid4(), uuid4(), uuid4()
    assets = {
        "font": SimpleNamespace(brand_id=brand_id, type="FONT", file_url="storage://assets/font"),
        "logo": SimpleNamespace(brand_id=brand_id, type="LOGO", file_url="storage://assets/logo"),
    }
    logo_buffer = BytesIO()
    Image.new("RGBA", (80, 40), "#FFFFFF").save(logo_buffer, format="PNG")
    settings = SimpleNamespace(storage_max_object_bytes=10_000_000)
    brand_repo = SimpleNamespace(
        brands=SimpleNamespace(
            get_for_user=lambda **kwargs: SimpleNamespace(workspace_id=workspace_id)
        ),
        settings=SimpleNamespace(
            get_for_user=lambda **kwargs: SimpleNamespace(
                visual_settings={
                    "font_asset_id": str(uuid4()),
                    "logo_asset_id": str(uuid4()),
                    "safe_margin": 0.06,
                    "text_color": "#FFFFFF",
                }
            )
        ),
        assets=SimpleNamespace(),
    )
    # The repository is asked for the font first and the logo second.
    calls = iter((assets["font"], assets["logo"]))
    brand_repo.assets.get_for_user = lambda **kwargs: next(calls)

    class Uow:
        brand = brand_repo

        def __enter__(self) -> Uow:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(composition, "SqlAlchemyUnitOfWork", Uow)
    monkeypatch.setattr(
        composition,
        "create_storage_provider",
        lambda settings: SimpleNamespace(
            download=lambda path, **kwargs: (
                _font_bytes() if path.endswith("font") else logo_buffer.getvalue()
            )
        ),
    )
    monkeypatch.setattr(
        composition,
        "create_image_reviewer",
        lambda settings: SimpleNamespace(review=lambda request: ImageReviewResult(decision, 0.99)),
    )
    return settings, (workspace_id, brand_id, user_id)


@pytest.mark.parametrize("dimensions", [(1024, 1024), (1536, 1024), (1024, 1536)])
def test_composition_preserves_scene_dimensions_and_records_inputs(
    monkeypatch: pytest.MonkeyPatch, dimensions: tuple[int, int]
) -> None:
    settings, (workspace_id, brand_id, user_id) = _setup(monkeypatch)
    result = composition.compose_generated_image(
        result=_image(*dimensions),
        approved={
            "headline": "Pão quentinho",
            "supporting_text": "Café da manhã",
            "call_to_action": "Peça já",
        },
        workspace_id=workspace_id,
        brand_id=brand_id,
        user_id=user_id,
        settings=settings,
    )
    assert Image.open(BytesIO(result.image_bytes)).size == dimensions
    assert result.metadata["composition"]["approved_text"]["headline"] == "Pão quentinho"
    assert result.metadata["composition"]["font_sha256"]


def test_composition_rejects_detected_scene_text(monkeypatch: pytest.MonkeyPatch) -> None:
    settings, (workspace_id, brand_id, user_id) = _setup(monkeypatch, "REJECTED")
    with pytest.raises(composition.CompositionError, match="COMPOSITION_SCENE_TEXT_DETECTED"):
        composition.compose_generated_image(
            result=_image(1024, 1024),
            approved={"headline": "Oferta"},
            workspace_id=workspace_id,
            brand_id=brand_id,
            user_id=user_id,
            settings=settings,
        )


def test_composition_rejects_inconclusive_scene_check(monkeypatch: pytest.MonkeyPatch) -> None:
    settings, (workspace_id, brand_id, user_id) = _setup(monkeypatch, "REFINE")
    with pytest.raises(composition.CompositionError, match="COMPOSITION_TEXT_CHECK_INCONCLUSIVE"):
        composition.compose_generated_image(
            result=_image(1024, 1024),
            approved={"headline": "Oferta"},
            workspace_id=workspace_id,
            brand_id=brand_id,
            user_id=user_id,
            settings=settings,
        )


@pytest.mark.parametrize("text", ["  Oferta  ", "Pão   quentinho", "  CTA longo com espaços  "])
def test_wrap_preserves_spaces_exactly(text: str) -> None:
    font = ImageFont.truetype(BytesIO(_font_bytes()), size=24)
    draw = ImageDraw.Draw(Image.new("RGB", (512, 256)))
    lines = composition._wrap_paragraph(text, font=font, draw=draw, max_width=130)
    assert "".join(lines) == text
    assert all(draw.textlength(line, font=font) <= 130 for line in lines)


def test_composition_accepts_explicit_line_breaks_without_passing_them_to_pillow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings, (workspace_id, brand_id, user_id) = _setup(monkeypatch)
    result = composition.compose_generated_image(
        result=_image(1024, 1024),
        approved={"headline": "Pão\nquentinho", "call_to_action": "Peça já"},
        workspace_id=workspace_id,
        brand_id=brand_id,
        user_id=user_id,
        settings=settings,
    )
    assert Image.open(BytesIO(result.image_bytes)).size == (1024, 1024)
    assert result.metadata["composition"]["approved_text"]["headline"] == "Pão\nquentinho"


def test_human_approved_scene_skips_detector_and_is_composed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings, (workspace_id, brand_id, user_id) = _setup(monkeypatch, "REFINE")
    result = composition.compose_generated_image(
        result=_image(1024, 1024),
        approved={"headline": "Pão quentinho"},
        workspace_id=workspace_id,
        brand_id=brand_id,
        user_id=user_id,
        settings=settings,
        scene_review_approved=True,
    )
    assert result.metadata["composition"]["scene_text_check"]["decision"] == "HUMAN_APPROVED"


def test_composition_fails_when_long_text_cannot_fit(monkeypatch: pytest.MonkeyPatch) -> None:
    settings, (workspace_id, brand_id, user_id) = _setup(monkeypatch)
    with pytest.raises(composition.CompositionError, match="COMPOSITION_TEXT_OVERFLOW"):
        composition.compose_generated_image(
            result=_image(256, 256),
            approved={"headline": "Pão " * 300},
            workspace_id=workspace_id,
            brand_id=brand_id,
            user_id=user_id,
            settings=settings,
        )


def test_composition_rejects_invalid_font_asset(monkeypatch: pytest.MonkeyPatch) -> None:
    settings, (workspace_id, brand_id, user_id) = _setup(monkeypatch)
    monkeypatch.setattr(
        composition,
        "create_storage_provider",
        lambda settings: SimpleNamespace(
            download=lambda path, **kwargs: b"invalid font" if path.endswith("font") else b"logo"
        ),
    )
    with pytest.raises(composition.CompositionError, match="COMPOSITION_ASSET_INVALID"):
        composition.compose_generated_image(
            result=_image(1024, 1024),
            approved={"headline": "Oferta"},
            workspace_id=workspace_id,
            brand_id=brand_id,
            user_id=user_id,
            settings=settings,
        )
