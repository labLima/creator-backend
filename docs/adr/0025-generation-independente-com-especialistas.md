# ADR-025: Independent Generation through shared specialists

- Status: accepted
- Tracker: [#140](https://github.com/labLima/creator-backend/issues/140)
- Implementation: [#141](https://github.com/labLima/creator-backend/issues/141)
- Related: ADR-014, ADR-016 and ADR-017

## Context

Creator must support creating or transforming one Content component without
running the complete image Agent Workflow. The existing Generation Job model
already distinguishes IMAGE, COPY and CAPTION, but execution and persistence
are still image-specific and text Content has no immutable versions.

## Decision

Independent Generation uses the same server-owned specialist responsibilities
as the complete workflow: WRITER produces COPY or CAPTION, and ARTIST produces
IMAGE from an existing visual direction. REVIEWER may assess an independent
image when requested. Independent Generation is asynchronous, requires an
authorized Brand, records idempotency and audit metadata, and persists each
result as a new immutable Content Version. CREATE creates Content; REGENERATE
and TRANSFORM append a version to authorized source Content.

The complete Business → Planner → Writer → Artist → Reviewer Agent Workflow
remains available. Existing direct endpoints remain compatible during migration;
their prompt implementations are removed only after consumers and queued jobs
no longer depend on them. Text improvement remains a synchronous preview and
must use WRITER constraints without mutating Content.

The legacy `POST /api/v1/images/generate` accepts only `content_id` and an
optional style; `POST /api/v1/images/{id}/regenerate` accepts an image ID and
optional style. Neither contract supplies an approved visual direction. These
endpoints therefore retain their existing prompt builder and worker path, which
also preserves already-enqueued jobs. Requests that need ARTIST execution must
use Generation Jobs and provide `brand_id` and `direction`. The legacy routes
can migrate after their consumers can supply that direction without changing
their established request/response contracts.

## Consequences

Generation Jobs and workers must dispatch by Artifact Type. Image-only recovery
and claim paths must never claim or fail text jobs. Text Content Version
persistence, specialist output contracts, API schemas and OpenAPI parity tests
are required. Workspace and Brand authorization is checked at the application
boundary for both source Content and requested Brand.
