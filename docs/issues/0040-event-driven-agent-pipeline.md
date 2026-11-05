# Issue 0040: event-driven agent pipeline

- GitHub: [#107](https://github.com/labLima/creator-backend/issues/107)
- ADR: [`0018-event-driven-agent-pipeline`](../adr/0018-event-driven-agent-pipeline.md)
- Labels: `agents`, `architecture`, `backend`
- Status: **implementado com entrypoint monolítico de compatibilidade (2026-11-04)**

## Scope

Separar as etapas Business, Planner, Writer, Artist e Reviewer em eventos
versionados, com Outbox transacional, consumers idempotentes e Redis/RQ como
transporte inicial.

## O que existe no código

- `PipelineEvent` versionado, `outbox_events` e `OutboxPublisher`.
- Consumers independentes por etapa em `workers/pipeline_events.py`:
  Business, Planner, Writer, Artist, Reviewer e terminal.
- Claim de consumer, lease, retry, deduplicação por `event_id`, dead-letter e
  transição do Agent Workflow para `FAILED` quando o evento esgota tentativas.
- Persistência de step + evento no mesmo commit, coberta por testes de rollback.
- O entrypoint HTTP ainda enfileira `run_image_agent_workflow`, que executa o
  fluxo monolítico e emite os eventos. O dispatch 100% por evento desde o início
  é um follow-up de otimização, não uma regressão funcional.

## Acceptance criteria

- [x] Evento versionado e Outbox persistente.
- [x] Consumer independente para cada etapa.
- [x] Persistência atômica de step + próximo evento.
- [x] Retry, deduplicação e dead-letter queue.
- [ ] Migração do worker monolítico sem regressão da API — parcial: o worker
      monolítico permanece como entrypoint de compatibilidade e o fluxo por
      evento está disponível para consumers; a migração completa do entrypoint
      fica registrada como follow-up.

## Evidência

- `src/creator/workers/pipeline_events.py`
- `src/creator/services/agents/event_publisher.py`
- `tests/test_pipeline_events.py`
- `tests/test_pipeline_event_publisher.py`
- `tests/test_relational_integrity.py` (claim, retry, dead-letter, rollback)
