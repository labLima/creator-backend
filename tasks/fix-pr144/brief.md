# Brief — Fix PR #144 (OpenAI provider + Planning image generation)

Branch: `fix/openai-provider-ci-recovery` (already checked out from `dev` @ c7a7839).
Goal: local CI green (`make check`, `make security`, `make e2e`) and the Planning→image
flow functional, respecting `AGENTS.md` and `CONTEXT.md`. Do not push. Do not commit
from subagents. Preserve historical `tasks/plan.md` and `tasks/todo.md`.

## Decisions already made (architect to validate, planner to sequence)

1. **CI mypy**: in `src/creator/integrations/openai/image_generator.py::_error_code`,
   bind `code = detail.get("code")` and return only after `isinstance(code, str)`.
2. **Stale tests**: update `tests/test_api.py` model expectations to OpenAI defaults,
   `tests/test_queue.py` job IDs to `creator-rq-*`, and make
   `tests/test_openapi_contract.py` assert conditions semantically (no positional
   `allOf` indices).
3. **Coverage**: add tests for the new OpenAI adapters, Planning service/worker path,
   legacy model mapping, provider-not-configured, size bounds and dev compose secret;
   keep `--cov-fail-under=73` (target >=75).
4. **Worker brand tenancy**: add `brand_id: UUID | None` to `ImageGenerationWorkItem`
   and populate it from `Generation.brand_id` in
   `generation/repository.py::claim_pending_by_id` (query already joins `Generation`).
   Worker uses `work_item.brand_id` for the Artist/review Brand lookup; never
   `UUID(str(request_input["brand_id"]))`. Fail closed if missing.
5. **Resolved prompt inputs**: service persists
   `parameters["resolved_input"] = {"briefing": briefing, "direction": direction}`
   (derived by `_generation_input_from_planning`). Worker prefers
   `work_item.parameters["resolved_input"]` over raw `request_input` for the Artist
   inputs and Automated Review briefing. `request_input` remains the client payload.
6. **Automated Review**: use resolved briefing and `work_item.brand_id`; run review
   best-effort in its own try/except (provider/config errors log and add
   `review_error` metadata); a review failure must not fail an already-generated image.
7. **Legacy model compatibility**: add a provider-neutral helper (suggest
   `services/ai/image_provider.py::normalize_image_model(settings, requested_model)`)
   mapping legacy `gemini-*` model names to `settings.openai_image_model`, preserving
   other names. Use it in `submit_image_regeneration` and in the worker before the
   provider call (old queued jobs).
8. **Default image model**: change `OPENAI_IMAGE_MODEL` default from the non-existent
   `gpt-image-2.6-flare` to `gpt-image-2` in `config.py`, `.env.example`, `README.md`.
9. **Unconfigured provider**: worker catches `ProviderNotConfiguredError` and settles
   `PROVIDER_AUTHENTICATION_FAILED` (non-retryable) instead of generic
   `IMAGE_GENERATION_FAILED`.
10. **Image size bound**: before base64 decode, reject encoded payloads above
    `settings.storage_max_object_bytes` (base64-safe bound); re-check decoded length.
11. **Stable 404**: `generation/router.py` uses `not_found("Generation input")`
    yielding `GENERATION_INPUT_NOT_FOUND`; update any test/docs expectation.
12. **Dev compose secret**: `scripts/dev_compose.py` must not inject
    `AUTH_JWT_SECRET=unused-for-local-compose-command` for `start`; use placeholder only
    for `stop`/`clean`/`logs`, and ensure `.env` provisioning happens before building
    the start environment. Add a regression test (import module via importlib).
13. **Gemini alignment**: keep OpenAI as active text/image provider; restore optional
    Gemini reviewer fallback in `create_image_reviewer` (OpenAI key first, else
    `gemini_api_key` → `GeminiMultimodalImageReviewer`, else unconfigured), matching
    ADR-001. Re-add legacy Gemini env vars (`GEMINI_API_KEY`,
    `GEMINI_EMBEDDING_MODEL`, `AGENT_REVIEWER_MODEL`, plus legacy text/image model
    vars) to `.env.example` with comments that they are legacy/optional and not
    selected for text/image generation. Update ADR-001/README only if wording is
    inaccurate.
14. **Hygiene/low**: remove the accidental `.worktrees/workflow-only-generation`
    gitlink from the index without deleting the directory (`.gitignore` `.worktrees/`);
    update `docs/issues/0053` acceptance criteria only after green; document the RQ
    drain-before-deploy note; optionally simplify dead `_classify_error` branches and
    `_image_request_size`. Do not delete Postman files or pre-existing worktrees.

## Hard constraints
- No new routes; no renames of `creator.workers.*` entrypoints; keep `creator-rq-*`.
- `router/schemas/service/ports` must not import SQLAlchemy or `creator.infrastructure`.
- SQLAlchemy only in `models.py`/`repository.py`; cross-capability only via `uow.py` and
  the other capability's `ports.py`/`schemas.py`.
- Tests must be added for every behavior change (TDD: red first).
- No live OpenAI calls; fake/injected clients only.
- Each task <=5 files; vertical slices; checkpoints with exact commands.

## Suggested task skeleton (planner may refine)
Phase 0: unblock static gate (mypy) + baseline tests.
Phase 1: stale tests + default model + config/env.
Phase 2: tenant-safe worker brand + resolved inputs + review best-effort.
Phase 3: legacy model mapping + provider-not-configured + size bound + 404 code.
Phase 4: dev compose secret + Gemini reviewer fallback + docs/ADR/hygiene.
Phase 5: new tests, coverage, full gates, reviewer/security evidence.
