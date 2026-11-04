# 0051 — Paridade de operationIds e error responses do OpenAPI

- ADR primária: [ADR-007](../adr/0007-openapi-first.md)
- Issue remota: [#135](https://github.com/labLima/creator-backend/issues/135)
- Status: implementação concluída na branch `feat/135-openapi-operation-ids`;
  aguardando revisão/merge (Fase 2)
- Owner: backend/platform
- Decisão: **2026-11-04 — opção 1 aprovada**

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

## Decisão

Adotar a **opção 1**: `docs/openapi.yaml` é autoritativo e cada rota FastAPI
publica explicitamente o mesmo `operationId`. Os nomes camelCase já publicados
são preservados (`loginWithPassword`, `listContents`, `getBrand`); nenhum ID é
derivado do nome do handler.

Política de error responses:

- `403`, `404` e `409`: comparados por operação entre YAML e
  `app.openapi()`, incluindo `x-error-codes` quando presentes.
- `401`, `422`, `429` e `500`: convenções globais. O app exige `401`, `429` e
  `500` em todas as operações `/api/v1`; o YAML documenta `401` por operação,
  `429` em `x-rate-limit` e `500` pelo componente canônico. `422` é gerado pelo
  FastAPI em operações com validação; o YAML o documenta onde aplicável, mas não
  há comparação de presença por operação. O shape canônico continua sendo
  `ErrorResponse`/`ValidationFailed`.
- Exceções: somente com justificativa nesta issue e teste explícito; nenhuma
  exceção silenciosa.

Comunicação: a mudança é breaking apenas para consumidores que geram clientes
diretamente de `app.openapi()`. Consumidores do YAML preservam os nomes. Não há
consumidor conhecido de `app.openapi()` no repositório; a nota deve constar no PR
e no changelog da release.

## Critérios de aceite

- [x] Decisão registrada em ADR-007.
- [x] Operação com `operationId` idêntico nos dois documentos (227/227).
- [x] Nenhum `operationId` duplicado no YAML.
- [x] `403/404/409` comparadas por operação; `401/422/429/500` tratadas como convenções globais.
- [x] `docs/openapi.yaml` sem drift de paths/methods/segurança.
- [x] `make check` verde.
- [x] Plano de comunicação registrado (sem consumidor conhecido de `app.openapi()`).

## Evidência atual

- 106 divergências de operationId (ex.:
  `login_with_password_api_v1_auth_login_post` vs `loginWithPassword`).
- `listAssets` duplicado no YAML; o GET de
  `/api/v1/notification-preferences/{id}` deve ser `getNotificationPreference`,
  tag `Notifications`, parâmetro `ResourceId` e 404.
- `tests/test_openapi_contract.py` compara paths/methods; não compara respostas
  de erro.
- `tests/test_route_table_contract.py` congela os IDs gerados e hoje ignora
  operationIds de propósito.
