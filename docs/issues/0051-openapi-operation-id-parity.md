# 0051 — Paridade de operationIds do OpenAPI

- ADR primária: [ADR-007](../adr/0007-openapi-first.md)
- Issue remota: [#135](https://github.com/labLima/creator-backend/issues/135)
- Status: aberta (Fase 2)
- Owner: backend/platform

## Contexto

`docs/openapi.yaml` é a fonte contratual (ADR-007), mas hoje ele e
`app.openapi()` divergem em **106 operationIds**. Os testes de paridade comparam
apenas paths/methods/security; um cliente gerado a partir do contrato estático
pode receber nomes diferentes dos gerados pelo app.

Exemplo:

- `docs/openapi.yaml`: `loginWithPassword`
- `app.openapi()`: `login_with_password_api_v1_auth_login_post`

## Objetivo

Definir a fonte autoritativa dos operationIds e reconciliar os dois documentos.

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
- [ ] `docs/openapi.yaml` sem drift de paths/methods/segurança.
- [ ] `make check` verde.
- [ ] Plano de comunicação se a mudança for breaking.

## Evidência atual

- 106 divergências (ex.: `login_with_password_api_v1_auth_login_post` vs
  `loginWithPassword`).
- `tests/test_openapi_contract.py` compara paths/methods;
  `tests/test_route_table_contract.py` congela os IDs gerados.
