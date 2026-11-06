# Todo — Fix PR #144

## Phase 0
- [x] T1 mypy `_error_code` narrowing
- [x] T2 update stale tests (api/queue/openapi)
- [x] T3 default image model `gpt-image-2` + env/README

## Checkpoint A
- [x] mypy + ruff clean; targeted tests green

## Phase 1
- [x] T4 `brand_id` on ImageGenerationWorkItem + repository + worker
- [x] T5 persist/consume `resolved_input`
- [x] T6 best-effort Automated Review
- [x] Task A specialist executor (`create_specialist_executor`) for CREWAI_ENABLED=false

## Checkpoint B
- [x] Planning-only job reaches persistence
- [x] Review failure does not fail image

## Phase 2
- [x] T7 legacy `gemini-*` model normalization
- [x] T8 ProviderNotConfiguredError classification
- [x] T9 image max-size bound
- [x] T10 stable `GENERATION_INPUT_NOT_FOUND`

## Checkpoint C
- [x] legacy regeneration, auth failure, size bound, 404 tested

## Phase 3
- [x] T11 dev compose secret fix + test
- [x] T12 Gemini reviewer fallback + env/ADR/README
- [x] T13 docs/issue/ADR, gitlink cleanup, RQ drain note

## Checkpoint D
- [x] `make check` green; dev compose uses `.env` secret

## Phase 4
- [x] T14 OpenAI adapter tests
- [x] T15 Planning/worker tests
- [x] T16 `make check`, `make security`, `make e2e`, coverage >=73%

## Final
- [x] Reviewer + security sign-off (see reports)
- [x] Working tree reviewed; no push

## Evidence
- `make check`: 572 passed; coverage 74.95% (gate 73%); mypy/ruff clean.
- `make security`: pip-audit no known vulnerabilities (4 ignored); Gitleaks no leaks.
- `make e2e`: 18 passed (Playwright browsers via PLAYWRIGHT_BROWSERS_PATH).
- Red evidence: new tests on pre-fix `dev` worktree -> 7 failed, 51 passed; branch -> 58 passed.
- Env workarounds: `HOME=/tmp/creator-home XDG_DATA_HOME=/tmp/creator-data` (CrewAI data dir),
  `PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright`, `make PYTHON=.venv/bin/python`.
