DEFAULT_OPENAI_IMAGE_MODEL = "gpt-image-2.5-sunburst"

LEGACY_OPENAI_IMAGE_MODELS = frozenset({"gpt-image-2.6-flare"})

LEGACY_IMAGE_MODEL_PREFIXES = ("gemini-", "imagen-")

KNOWN_OPENAI_IMAGE_MODELS = frozenset(
    {
        "gpt-image-1",
        "gpt-image-1-mini",
        "gpt-image-1.5",
        "gpt-image-2",
        "gpt-image-2-2026-04-21",
        "gpt-image-2.5-sunburst",
        "gpt-image-2.5-sunburst-2026-09-08",
        "gpt-image-2.5-flare",
        "gpt-image-2.5-flare-2026-09-08",
        "gpt-image-2.6-sunburst",
        "gpt-image-2.6-flare",
        "chatgpt-image-latest",
        "dall-e-2",
        "dall-e-3",
    }
)


def canonical_image_model(
    requested_model: str | None,
    *,
    default_model: str = DEFAULT_OPENAI_IMAGE_MODEL,
) -> str:
    if requested_model is None:
        return default_model
    requested = requested_model.strip()
    if not requested:
        return default_model
    normalized = requested.lower()
    if normalized in LEGACY_OPENAI_IMAGE_MODELS:
        return default_model
    if normalized.startswith(LEGACY_IMAGE_MODEL_PREFIXES):
        return default_model
    return requested
