# 0051 — Paridade de operationIds e error responses do OpenAPI

- ADR primária: [ADR-007](../adr/0007-openapi-first.md)
- Issue remota: [#135](https://github.com/labLima/creator-backend/issues/135)
- Status: aberta (Fase 2)
- Owner: backend/platform

## Contexto

`docs/openapi.yaml` é a fonte contratual (ADR-007), mas hoje ele e
`app.openapi()` divergem em **106 operationIds**. Os testes de paridade comparam
apenas paths/methods/security; um cliente gerado a partir do contrato estático
pode receber nomes diferentes dos gerados pelo app.

Além disso, o YAML tem `listAssets` duplicado em `/api/v1/assets` e
`/api/v1/notification-preferences/{id}` (226 ids únicos para 227 operações), e as
respostas de erro (ex.: o novo 404 de Brand Settings) não são comparadas entre
YAML e app.

Exemplo de divergência:

- `docs/openapi.yaml`: `loginWithPassword`
- `app.openapi()`: `login_with_password_api_v1_auth_login_post`

## Objetivo

Definir a fonte autoritativa dos operationIds e das respostas de erro, remover
duplicatas e reconciliar os dois documentos.

## Opções

1. Tornar `docs/openapi.yaml` autoritativo e fixar `operation_id` explícito em
   cada rota FastAPI.
2. Tornar `app.openapi()` autoritativo e atualizar o YAML (breaking change
   documentado).
3. Manter a divergência com justificativa e um teste que a torne explícita.

## Critérios de aceite

- [ ] Decisão registrada em ADR-007 (ou nova ADR).
- [ ] Operação com `operationId` idêntico nos dois documentos, ou divergência
      explicitamente documentada e testada.
- [ ] Nenhum `operationId` duplicado no YAML.
- [ ] Error responses (ao menos 403/404/409/422/429/500) comparadas entre YAML e
      app, ou exceção documentada.
- [ ] `docs/openapi.yaml` sem drift de paths/methods/segurança.
- [ ] `make check` verde.
- [ ] Plano de comunicação se a mudança for breaking.

## Evidência atual

- 106 divergências de operationId (ex.:
  `login_with_password_api_v1_auth_login_post` vs `loginWithPassword`).
- `listAssets` duplicado no YAML.
- `tests/test_openapi_contract.py` compara paths/methods; não compara respostas
  de erro.
- `tests/test_route_table_contract.py` congela os IDs gerados.
