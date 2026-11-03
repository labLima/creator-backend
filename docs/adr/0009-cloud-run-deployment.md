# ADR-009: Deploy containerizado

- Status: accepted (parcialmente substituída pela ADR-020/021; deploy de produção diferido para Fase 4)
- Fonte: `adr_creator_python.pdf`, seção 11
- Tracker: [#42](https://github.com/labLima/creator-backend/issues/42)

## Decisão

O backend é empacotado em Docker e preparado para Cloud Run, com Supabase como dependência gerenciada e Redis externo. CI valida a imagem; deploy é protegido por ambiente/secrets.

## Emenda 2026-11-03 — runtime atual e fronteira de deploy

A decisão original assumia Supabase/Postgres. As ADR-020 e ADR-021 substituíram
essa base por autenticação própria e SQLite. O runtime efetivamente entregue na
Fase 1 é:

- API FastAPI e worker RQ no mesmo artefato Docker;
- Redis para filas;
- SQLite em volume nomeado;
- migrations Alembic executadas antes da API/worker;
- smoke test de containers no CI;
- usuário não-root e health/live local.

**Deploy de produção** (Cloud Run, CD real, secrets de ambiente, runtime
escalável do worker, persistência SQLite compartilhada e estratégia de
backup/restore) permanece na Fase 4 e é rastreado por #24 e #32. A imagem
multi-stage, readiness e SIGTERM também ficam em #24. Este tracker fecha a
decisão de runtime da Fase 1; não declara produção pronta.

## Issues vinculadas

#3, #7, #24, #30, #31 e #32. Consulte o [tracker central](../ADR-ISSUE-TRACKER.md).
