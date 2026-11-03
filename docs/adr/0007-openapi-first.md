# ADR-007: OpenAPI first

- Status: accepted (paridade de superfície; operationIds em [0051](../issues/0051-openapi-operation-id-parity.md))
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

## Issues vinculadas

#4, #13, #16, #17, #18, #19, #25, #30, #31, [0051](../issues/0051-openapi-operation-id-parity.md). Consulte o [tracker central](../ADR-ISSUE-TRACKER.md).
