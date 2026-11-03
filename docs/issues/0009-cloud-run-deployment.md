# Tracker ADR-009: Cloud Run deployment

- ADR: [`0009-cloud-run-deployment`](../adr/0009-cloud-run-deployment.md)
- Labels: `infra`, `deployment`

## Papel

Centralizar o progresso de #3, #7, #24, #30, #31 e #32 sem criar uma tarefa duplicada.

## Encerramento

- Todas as issues vinculadas foram concluídas ou justificadamente substituídas.
- #24 (imagem de produção), #31 (runbooks) e #32 (CD Cloud Run) foram explicitamente dispensadas para a Fase 4.
- A decisão atual é runtime local Docker Compose + SQLite + Redis; a emenda da [ADR-009](../adr/0009-cloud-run-deployment.md) registra a fronteira de deploy.
- Dispensa registrada no [tracker central](../ADR-ISSUE-TRACKER.md).
