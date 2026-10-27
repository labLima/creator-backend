# Observabilidade e correlação ponta a ponta

- ADRs primárias: [ADR-006](../adr/0006-versioned-api-envelope.md) e [ADR-008](../adr/0008-api-limits-and-soft-delete.md)
- Tracker: [ADR-006 #39](https://github.com/labLima/creator-backend/issues/39)
- Status: em implementação

## Objetivo

Tornar requests e falhas rastreáveis entre FastAPI, serviços, Unit of Work,
RQ, Gemini e Storage sem registrar credenciais, prompts, payloads ou bytes de
imagem.

## Decisões de implementação

- Logs são JSON com timestamp UTC em todos os ambientes.
- `X-Request-ID` e `meta.request_id` usam o mesmo UUID; entradas inválidas são
  substituídas por um UUID gerado pelo servidor.
- Workers carregam Request ID, job ID e correlation ID em contexto estruturado.
- Métricas HTTP usam somente método, rota normalizada e status como labels.
- `/metrics` não é contabilizado nas próprias métricas HTTP.
- Exceções inesperadas retornam `INTERNAL_ERROR` sem detalhes internos.

## Critérios de aceite

- [x] Request ID é correlacionado na API, envelope, RQ, worker e Generation Job.
- [x] Logging JSON possui redaction recursiva para dados sensíveis.
- [x] Métricas expõem requests, erros e latência sem IDs nas labels.
- [x] Rotas com IDs usam templates FastAPI nas métricas.
- [x] Exceções inesperadas são registradas de forma segura.
- [ ] `make check`, `make security` e `make e2e` passam em Python suportado.
