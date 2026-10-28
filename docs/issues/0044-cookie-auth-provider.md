# Issue 0044: decisão do provider de autenticação em cookies

- ADR primária: [ADR-022](../adr/0022-cookie-auth-provider.md)
- GitHub: [#116](https://github.com/labLima/creator-backend/issues/116)
- Status: aceita; encerrada como não necessária
- Epic relacionado: [#117](https://github.com/labLima/creator-backend/issues/117)

## Objetivo

Decidir uma estratégia sustentável para o transporte de autenticação em cookies
sem adotar literalmente uma release incompatível de `fastapi-jwt-auth` e sem
alterar o modelo de `Auth Session` da ADR-020.

## Decisão

Usar um adapter interno Creator-owned, confinado atrás de uma interface de
infraestrutura, sobre a dependência PyJWT 2.x já adotada pelo projeto. Não será
mantido fork/vendor de `fastapi-jwt-auth` 0.5.0, pois a lib é incompatível com
Pydantic 2 e fixa PyJWT 1.x.

## Critérios de aceite

- [x] Reprodução Python 3.12 + Pydantic 2 documentada na ADR.
- [x] Matriz de compatibilidade documentada.
- [x] Adapter interno escolhido; fork/vendor rejeitado.
- [x] `fastapi-jwt-auth` não é dependência do projeto.
- [x] Adapter confinado a `src/creator/infrastructure/auth/`.
- [x] `PyJWT[crypto]>=2.15,<3` preservado.
- [x] Contrato de cookies, CSRF, rotação, revogação, claims, topologias, flags,
      rollback e manutenção documentado.
- [x] Nenhum fork/vendor de produção é necessário nesta issue.
- [x] Owner de arquitetura + segurança atribuído.
- [x] ADR-022 aprovada e marcada como `accepted`.

## Dependências e bloqueio

As issues #118–#128 foram liberadas pelo aceite formal da ADR-022. Elas são o
plano de implementação e devem manter esta ADR como decisão primária e o
tracker versionado como índice.

## Fora de escopo

Rotas, cookies, CSRF, CORS, OpenAPI, migrations, alteração de dependências e
qualquer código em `src/`.
