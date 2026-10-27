# Issue 0044: decisão do provider de autenticação em cookies

- ADR primária: [ADR-022](../adr/0022-cookie-auth-provider.md)
- GitHub: [#116](https://github.com/labLima/creator-backend/issues/116)
- Status: aceita; implementação em andamento
- Epic relacionado: [#117](https://github.com/labLima/creator-backend/issues/117)

## Objetivo

Decidir uma estratégia sustentável para o transporte de autenticação em cookies
sem adotar literalmente uma release incompatível de `fastapi-jwt-auth` e sem
alterar o modelo de `Auth Session` da ADR-020.

## Decisão

Usar um fork/vendor Creator-owned baseado em `fastapi-jwt-auth` 0.5.0, corrigido
para Pydantic 2 e PyJWT 2, confinado atrás de uma interface interna de
infraestrutura. O fork será pinado por commit/release, manterá MIT, terá CI
Python 3.12/3.13 e passará por `pip-audit`.

## Critérios de aceite

- [x] Reprodução Python 3.12 + Pydantic 2 documentada na ADR.
- [x] Matriz de compatibilidade documentada.
- [x] Fork/vendor versus adapter interno decidido.
- [x] Contrato de cookies, CSRF, rotação, revogação, claims, topologias, flags,
      rollback e manutenção documentado.
- [x] Nenhuma alteração de produção nesta issue.
- [x] Owner de arquitetura + segurança atribuído.
- [x] ADR-022 aprovada e marcada como `accepted`.

## Dependências e bloqueio

As issues #118–#128 foram liberadas pelo aceite formal da ADR-022. Elas são o
plano de implementação e devem manter esta ADR como decisão primária e o
tracker versionado como índice.

## Fora de escopo

Rotas, cookies, CSRF, CORS, OpenAPI, migrations, alteração de dependências e
qualquer código em `src/`.
