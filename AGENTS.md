# Creator agent guidelines

## Mission

Build Creator as a multi-tenant, contract-first Python backend. Preserve the domain language in `CONTEXT.md`; do not introduce synonyms for Workspace, Principal, Brand, Content, Generation, or Generation Job.

## Source of truth

- Domain language: `CONTEXT.md`.
- Decisions: `docs/adr/`.
- Work state: GitHub issues (`labLima/creator-backend`) and `docs/ADR-ISSUE-TRACKER.md`.
- HTTP contract: `docs/openapi.yaml`, which must stay in parity with `app.openapi()`.
- `docs/status-do-projeto.md` is a dated snapshot, not authority.

## Commands and gates

- `make check` — Ruff lint, format check, mypy and pytest.
- `make security` — pip-audit and Gitleaks.
- `make e2e` — end-to-end API flows.
- `make dev/start`, `make dev/stop`, `make dev/clean` — local Compose lifecycle.
- Run `make check`, `make security` and `make e2e` before handoff.

## Non-negotiable engineering rules

- Every material architectural decision must have an ADR in `docs/adr/`.
- Every ADR must have one tracker issue and linked implementation issues in `docs/issues/` and in GitHub. Use `docs/ADR-ISSUE-TRACKER.md` as the canonical index.
- Define or update `docs/openapi.yaml` before changing API behavior. Add a parity test when a route is added or removed.
- Keep provider integrations behind interfaces; application code must not import vendor SDKs directly.
- Enforce Workspace isolation at the application boundary and never trust a client-supplied workspace identifier without authorization.
- Treat generated output and uploads as untrusted data. Validate type, size, ownership, and lifecycle.
- Use UTC timestamps, soft delete where the ADR requires it, and structured errors with `request_id`.
- New behavior requires tests. Do not close an issue without code, tests, CI evidence, and checked acceptance criteria.

## Architecture guardrails

- New HTTP routes belong in `src/creator/<entity>/router.py` and must be registered in `src/creator/api/router.py`, never in `main.py`.
- ORM models live only in `<entity>/models.py` and repositories in `<entity>/repository.py`. `router.py`, `schemas.py`, `service.py` and `ports.py` must never import `sqlalchemy` or `creator.infrastructure`.
- Capabilities integrate only through `creator/uow.py` and another module's `ports.py`/`schemas.py`. Importing another module's `service.py`, `router.py` or `adapters/` is forbidden and tested by `tests/test_module_boundaries.py`.
- SQLAlchemy stays in infrastructure; application code depends on repositories and Unit of Work.
- SQLite is the default database. Use portable SQLAlchemy types; do not add PostgreSQL-only constructs to models or migrations.
- Local authentication is Creator-owned. Do not reintroduce Supabase Auth; Supabase Storage remains an optional provider.
- `workers/` module paths are persisted in Redis. Do not rename `creator.workers.*` entrypoints.
- Workers are started through `creator-worker`; the Compose stack must keep API, worker, Redis and SQLite volumes healthy.

## Subagents

Subagents are configured under `~/.agents/skills/*/agents/openai.yaml`. Use them for bounded research or review, never as a substitute for the primary agent reading the repository context and ADRs. A subagent must return evidence (files, commands, and decisions), and its output must be reviewed before it changes the repository.

Recommended delegation:

- `grilling` / `domain-modeling`: expose unresolved domain decisions and update vocabulary.
- `code-review` / `code-review-and-quality`: review a completed increment against standards and the ADR.
- `diagnosing-bugs`: investigate failures before proposing fixes.
- `research` / `source-driven-development`: verify external technical facts against primary documentation.

## Delivery workflow

1. Read `CONTEXT.md`, relevant ADRs, and the issue linked to the task.
2. Make the smallest testable increment on a branch from `dev`.
3. Run focused tests, then `make check`, `make security` and `make e2e`.
4. Update ADR/issue traceability when the decision changes.
5. Report changed files, checks, and unresolved external blockers.

`dev` is the integration branch; `main` is release. Open PRs against `dev` unless explicitly releasing.
