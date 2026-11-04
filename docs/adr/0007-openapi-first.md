# ADR-007: OpenAPI first

- Status: accepted (paridade de superfície; operationIds/error responses reconciliados em 2026-11-04, ver emenda abaixo)
- Fonte: `adr_creator_python.pdf`, seção 9
- Tracker: [#40](https://github.com/labLima/creator-backend/issues/40)

## Decisão

O contrato em `docs/openapi.yaml` é revisado antes da implementação. FastAPI deve permanecer compatível com esse contrato e os testes devem cobrir o envelope.

## Emenda 2026-11-03 — o que significa "paritário"

Para o encerramento da Fase 1, **paridade OpenAPI** significa:

- o mesmo conjunto de paths;
- os mesmos métodos por path;
- o mesmo esquema de segurança e os mesmos headers de autenticação.

`operationId` e respostas de erro são parte do contrato, mas os 106
identificadores divergentes e a cobertura de error responses ficam
explicitamente fora do gate da Fase 1 e são tratados na
[0051](../issues/0051-openapi-operation-id-parity.md), com decisão de fonte
autoritativa e plano de breaking change. Nenhuma mudança de `operationId` ou de
respostas de erro deve ser feita silenciosamente.

## Emenda 2026-11-04 — operationIds e error responses

Decisão: `docs/openapi.yaml` é a fonte autoritativa também para `operationId` e
para as respostas de erro documentadas por operação.

- Toda rota FastAPI deve publicar exatamente o `operationId` declarado no YAML.
  Rotas novas exigem a atualização do YAML antes da implementação.
- Os nomes publicados em camelCase (`loginWithPassword`, `listContents`,
  `getBrand`) são contrato imutável. Não derivar `operationId` do nome do
  handler Python.
- `403`, `404` e `409` são comparados por operação entre YAML e
  `app.openapi()`, incluindo `x-error-codes` quando presentes.
- `401`, `422`, `429` e `500` são convenções globais. O app injeta `401`, `429`
  e `500` em todas as operações `/api/v1`; o YAML documenta `401` por operação,
  `429` no bloco global `x-rate-limit` e `500` pelo componente canônico. `422`
  é gerado pelo FastAPI para operações com validação e documentado no YAML
  quando aplicável, sem comparação de presença por operação. O shape canônico
  do erro continua sendo o envelope `ErrorResponse`/`ValidationFailed`, não o
  `HTTPValidationError` padrão do FastAPI.
- Exceções de error response exigem justificativa registrada na
  [0051](../issues/0051-openapi-operation-id-parity.md); não pode haver exceção
  silenciosa.
- A mudança é breaking apenas para consumidores que geram clientes diretamente
  de `app.openapi()`. Consumidores do YAML preservam os nomes. A comunicação
  deve ser registrada no PR da 0051.

## Issues vinculadas

#4, #13, #16, #17, #18, #19, #25, #30, #31, [0051](../issues/0051-openapi-operation-id-parity.md). Consulte o [tracker central](../ADR-ISSUE-TRACKER.md).
