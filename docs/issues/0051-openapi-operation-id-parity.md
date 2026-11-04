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

## Exceções explícitas (2026-11-04)

A #135 garante paridade **documento-vs-documento** para `operationId`,
`403/404/409` e shape canônico de `422`. Ela não é uma auditoria completa de
todo erro de runtime. As exceções abaixo são deliberadas e rastreadas:

| Exceção | Motivo | Destino |
| --- | --- | --- |
| `429`/`500` com componentes específicos no YAML (`AuthRateLimited`, `LlmProviderRateLimited`, `SignupFailed`, etc.) e componentes globais no app (`RateLimitExceeded`, `InternalServerError`) | Ambos usam o envelope `ErrorResponse`; o app aplica a convenção global e o YAML distingue a causa do provider. | Comparação por componente fica fora da #135; união de `x-error-codes` documentada nas operações afetadas. |
| `403` de CSRF em mutações `/api/v1` | O middleware global `enforce_cookie_security` pode retornar `CsrfRejected` em qualquer mutação, não só refresh/logout. | Documentado em `CsrfRejected` e no security scheme; comparação por operação fica na #15. |
| `403/404` de runtime ainda ausentes no contrato em alguns recursos (ex.: plans/coupons `403`, assets/notifications `404`, brand settings `403/404`) | A #135 reconciliou o contrato existente; uma auditoria runtime-vs-contrato completa exige varrer guards e `not_found` de todos os serviços. | #20 (autorização por endpoint) e #15 (endurecimento/documentação). |
| `401` de signup documentado | O handler de signup não levanta 401; a resposta permanece como convenção de auth no contrato estático. | Remover ou justificar na #15. |
| `X-Request-ID` e headers de CSRF nos componentes de erro `$ref` | O runtime sempre envia `X-Request-ID`; parte dos componentes compartilhados ainda não o declara. | #15 (headers/observabilidade do contrato). |
| `CsrfTokenResponse.csrf_token` como `writeOnly` | Defeito pré-existente do schema de resposta, fora do diff de operationIds. | #15. |

Login foi alinhado: o runtime retorna `LOGIN_REJECTED`, e YAML, componente e
`app.openapi()` agora publicam `LOGIN_REJECTED`.

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
