# Increment — migrate image model to gpt-image-2.5-sunburst

## Evidence (OpenAI docs, fetched 2026-11-06)
- Model ID: `gpt-image-2.5-sunburst`; snapshot `gpt-image-2.5-sunburst-2026-09-08`.
- Images API (`POST /v1/images/generations`) supported; quality: `low|medium|high|xhigh|max|auto`;
  output formats `png|webp|jpeg`; arbitrary `WIDTHxHEIGHT`, both edges divisible by 16,
  aspect 1:3–3:1, max 3840x2160 (above 2560x1440 experimental).
- Docs also list `gpt-image-2.6-flare` as supported, but it is the legacy value shipped by
  PR #144 and the reviewer reports it fails for the account; the product wants
  `gpt-image-2.5-sunburst` as the new default.
- Installed `openai` 2.54.0 `ImageModel` literal predates 2.5 Sunburst; the API accepts `str`.
  Do not assert the default against `ImageModel`; use an explicit docs-sourced allowlist.

## Design (architect)
- New leaf module `src/creator/image_models.py` (no imports):
  `DEFAULT_OPENAI_IMAGE_MODEL`, `LEGACY_OPENAI_IMAGE_MODELS = {"gpt-image-2.6-flare"}`,
  `LEGACY_IMAGE_MODEL_PREFIXES = ("gemini-", "imagen-")`,
  `KNOWN_OPENAI_IMAGE_MODELS` (docs-sourced), and
  `canonical_image_model(requested, *, default_model)`:
  blank/None -> default; gemini-/imagen- prefix -> default; legacy exact -> default;
  otherwise return the stripped requested value.
- `Settings.openai_image_model` default is `DEFAULT_OPENAI_IMAGE_MODEL`; add
  `@field_validator("openai_image_model", mode="after")` delegating to
  `canonical_image_model`, so an existing `.env` with `gpt-image-2.6-flare` is migrated at load.
- `services/ai/image_provider.normalize_image_model` delegates to `canonical_image_model`
  (same signature), covering queued jobs (worker) and existing images (regeneration).
- No DB backfill; historical generation/image model stays as audit. Normalize only at use.
- `.env.example` and README use the new default; document the snapshot variant in a comment.
- Update issue 0053 evidence and ADR/README only where the model identity is stated.
- Tests: config default + legacy `.env` + blank; normalize legacy/gemini/imagen/valid;
  service regeneration; worker queued job; adapter default; keep explicit `gpt-image-2`
  overrides valid. Remove the SDK `ImageModel` membership assertion (SDK lags docs).

## Constraints
- No new routes, no SQLAlchemy/infrastructure imports, no worker entrypoint renames.
- TDD: red test per behavior first; then minimal implementation.
- Gates: `make check` (coverage >=73), `make security`, `make e2e`; then push/PR #145 update.
