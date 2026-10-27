# ADR-018: event-driven agent pipeline with transactional outbox

- Status: accepted
- Tracker: [docs/issues/0040](../issues/0040-event-driven-agent-pipeline.md)

## Decision

The HTTP boundary remains synchronous only for accepting a workflow. Agent stages
are processed asynchronously. In accordance with ADR-021, SQLite is the source
of truth for workflow steps and a transactional `outbox_events` table. Redis/RQ
is the initial transport; the event contract must not depend on that transport
and can later be published to Kafka without changing agent inputs or outputs.

Each stage persists its validated output and the next event in one transaction.
Consumers are idempotent and use the event's run, step, Workspace and hashes to
reject duplicates, stale predecessors, and cross-Workspace data.

Business, Planner, Writer, Artist and Reviewer have independent RQ callables in
the shared Generation queue and worker process. Delivery is at-least-once. The
Outbox row is also the durable consumption record: it owns the consumer lease,
attempt count, retry availability, completion and dead-letter state. A stage has
five total attempts with delays of 30, 60, 120 and 300 seconds. Exhaustion moves
the event to the SQLite dead-letter state and fails the Agent Workflow in the
same transaction; RQ's failed-job registry is not authoritative.

There is one `AgentWorkflowRun` for the whole Generation. Item fan-out and retry
history are represented by steps associated with the source event. Events carry
only typed persistence references and integrity metadata; image bytes, provider
prompts, full outputs and hidden reasoning are forbidden.

Workflow creation and human refinement are accepted after the Agent Workflow
state and Outbox event commit. Redis availability does not affect the HTTP
success response; the publisher retries transport failures from the durable row.
