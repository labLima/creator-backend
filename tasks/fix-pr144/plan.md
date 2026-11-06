# Implementation Plan: Fix PR #144 — OpenAI provider + Planning image Generation

## Overview
Recover the merged-but-red PR #144 on branch `fix/openai-provider-ci-recovery`.
The work restores local CI (`make check`, `make security`, `make e2e`), fixes the
Planning → image Generation path end-to-end, removes the invalid OpenAI image model
default, preserves tenant isolation in the worker, and adds the tests that were
missing. Decisions are recorded in `tasks/fix-pr144/brief.md`; `AGENTS.md` and
`CONTEXT.md` are the authority.

## Architecture Decisions
- Authorized Brand comes from persistence (`Generation.brand_id` exposed on
  `ImageGenerationWorkItem`), never from client-supplied `request_input` in the worker.
- Resolved prompt inputs are derived in the application service and persisted under
  `generation.parameters["resolved_input"]`; the worker prefers them and keeps the raw
  client payload untouched.
- Automated Review is best-effort: a reviewer/provider failure is recorded in image
  metadata and does not fail an image that was generated successfully.
- Legacy `gemini-*` model names are normalized to the configured OpenAI image model in
  the application/worker boundary; the historical Generation record keeps its model.
- OpenAI remains the active text/image provider; Gemini remains an optional reviewer
  fallback (ADR-001), with legacy env vars documented.
- No new routes, no SQLAlchemy outside models/repository, no cross-capability service
  imports, no `creator.workers.*` renames, no push.

## Task List

### Phase 0 — Static gate and stale tests
- [ ] **T1 mypy fix** — `image_generator._error_code` narrows `detail["code"]` to `str`.
  Files: `src/creator/integrations/openai/image_generator.py`. Size XS.
  Verify: `.venv/bin/python -m mypy src`.
- [ ] **T2 stale tests** — update OpenAI model expectations (`tests/test_api.py:1382,1949`),
  RQ job ids (`tests/test_queue.py:72,129`), and make
  `tests/test_openapi_contract.py` assert conditions semantically. Size M.
  Verify: targeted pytest.
- [ ] **T3 default image model** — `gpt-image-2` in `config.py`, `.env.example`, README.
  Size XS. Verify: config unit test + `Settings(_env_file=None)`.

### Checkpoint A
- [ ] mypy clean; targeted stale tests green; `ruff check` clean.

### Phase 1 — Tenant-safe worker and resolved inputs
- [ ] **T4 brand on work item** — add `brand_id` to `ImageGenerationWorkItem`, populate from
  `Generation.brand_id` in `claim_pending_by_id`, use it for Artist/review; fail closed.
  Files: `generation/ports.py`, `generation/repository.py`, `workers/image_generation.py`.
  Size M. Verify: worker/service tests.
- [ ] **T5 resolved inputs** — persist `resolved_input` in `submit_independent_generation`;
  worker uses it for Artist briefing/direction. Files: `generation/service.py`,
  `workers/image_generation.py`. Size M.
- [ ] **T6 review best-effort** — use resolved briefing + work-item brand; catch reviewer
  provider/config errors, persist `review_error`, continue. Size M.

### Checkpoint B
- [ ] Planning-only job test reaches image persistence with resolved brief/direction.
- [ ] Reviewer failure does not fail a successful image.

### Phase 2 — Provider robustness
- [ ] **T7 legacy model normalization** — helper maps `gemini-*` to
  `settings.openai_image_model`; use in regeneration and worker. Size S.
- [ ] **T8 unconfigured provider** — catch `ProviderNotConfiguredError` in worker →
  `PROVIDER_AUTHENTICATION_FAILED`. Size S.
- [ ] **T9 image size bound** — reject base64 payloads above
  `storage_max_object_bytes` before decode and decoded bytes after. Size S.
- [ ] **T10 stable 404** — `not_found("Generation input")` →
  `GENERATION_INPUT_NOT_FOUND`; update expectations/docs. Size XS.

### Checkpoint C
- [ ] Legacy regeneration uses OpenAI model; unconfigured job settles auth failure;
  oversized payload rejected; 404 code stable.

### Phase 3 — Ops, compatibility, docs
- [ ] **T11 dev compose** — placeholder only for stop/clean/logs; start uses `.env`
  secret; regression test. Size S.
- [ ] **T12 Gemini reviewer fallback + env/ADR** — OpenAI first, Gemini fallback;
  re-add legacy env vars; align ADR-001/README. Size M.
- [ ] **T13 hygiene/docs** — remove accidental `.worktrees/workflow-only-generation`
  gitlink from index, ignore `.worktrees/`, update `docs/issues/0053` criteria after
  green, document RQ drain-before-deploy. Size S.

### Checkpoint D
- [ ] `make check` green; dev compose start resolves the `.env` secret.

### Phase 4 — Test coverage and final gates
- [ ] **T14 OpenAI adapter tests** — image generator (success/invalid/error/size),
  text provider (success/error), reviewer (JSON/decision), config default. Size M.
- [ ] **T15 Planning/worker tests** — authorization, brand derivation, resolved inputs,
  review best-effort, legacy model, unconfigured provider. Size M.
- [ ] **T16 full gates** — unit with coverage >=73% (target 75), `make check`,
  `make security`, `make e2e`; reviewer/security sign-off. Size M.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| Work-item brand missing for some job path | High | Fail closed; only independent jobs use Artist/review; tests cover both |
| Review best-effort hides real defects | Med | Catch only known provider/config errors; log + persist `review_error` |
| Legacy model mapping hides provider mismatch | Med | Normalize only known `gemini-*`; keep historical model in record |
| Gemini fallback contradicts migration intent | Med | OpenAI preferred; fallback only for review per ADR-001 |
| Coverage gate still short | High | Add adapter/planning/worker tests; verify 72.87% -> >=73 |
| E2E environment (Playwright/server) | Med | Use `HOME`/`XDG_DATA_HOME` workdirs; document if blocked |

## Open Questions
- Should Gemini text fallback be restored too? Plan: no; OpenAI is active, migration note only.

## Task tracking
Checklist: `tasks/fix-pr144/todo.md`.
