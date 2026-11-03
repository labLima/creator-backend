# 0049 — Consolidação da estrutura plana por capacidade

- ADR primária: [ADR-024](../adr/0024-estrutura-plana-por-capacidade.md)
- ADRs relacionadas: [ADR-023](../adr/0023-estrutura-modular-por-capacidade.md)
- Issues relacionadas: [0045](0045-modular-structure-tracker.md),
  [0046](0046-security-backlog-after-modularization.md),
  [0048](0048-plain-capability-layout.md)
- Status: em andamento
- Owner: backend/platform

## Objetivo

Fechar as lacunas deixadas pelo PR #129 na estrutura plana por capacidade,
preservando o contrato HTTP e o schema, e registrar explicitamente o que ainda
é dívida estrutural.

## Escopo deste incremento

- Corrigir a regressão de `GET /api/v1/assets/{id}` que retornava 500 quando o
  identificador pertencia a um Brand Asset.
- Uniformizar o pacote `workflow` ao vocabulário da ADR-024, com `schemas.py` e
  `__init__.py` próprios.
- Adicionar guardas estruturais que impeçam a reintrodução de pacotes legados,
  de capacidades incompletas e de respostas HTTP dentro de `service.py`.
- Alinhar README, AGENTS, status, ADRs e issues ao layout plano.
- Registrar as dívidas que permanecem fora deste incremento.

## Fora de escopo / dívidas deferidas

Estas dívidas não impedem o funcionamento atual e permanecem rastreadas aqui:

- **23 de 27 `service.py` importam `creator.api`** (erros HTTP, respostas e
  serializers). A separação completa entre aplicação e transporte exige um
  incremento próprio.
- **4 routers ainda acessam o UoW diretamente**: `auth`, `content`, `generation`
  e `workflow`. Em `content` e `generation`, parte do CRUD e da autorização
  ainda vive no router.
- **47 repositórios por agregado**: a fase 5 da ADR-023 (consolidar 47 em ~30)
  continua pendente e foi transferida para esta issue.
- **Backlog de segurança S1–S13** da [0046](0046-security-backlog-after-modularization.md):
  itens pré-existentes, incluindo o S1 (cross-tenant Brand Settings), fora do
  escopo da consolidação estrutural.

## Critérios de aceite

- [x] `GET /api/v1/assets/{id}` com Brand Asset retorna 200, envelope único e
      `data.id` correto; Asset comum continua funcionando.
- [x] As 27 capacidades expõem `__init__.py`, `router.py`, `schemas.py`,
      `service.py`, `ports.py`, `repository.py` e `models.py`.
- [x] `src/creator/modules`, `src/creator/repositories` e
      `src/creator/infrastructure/persistence/repositories` não existem.
- [x] Nenhum `service.py` chama `success_response()` ou `error_response()`.
- [x] `docs/openapi.yaml` e `CONTEXT.md` sem diff.
- [x] `make check`, `make security` e `make e2e` verdes.
- [x] README, AGENTS, status, 0045, 0046, 0048 e tracker consistentes com a
      estrutura plana.
- [x] Dívidas deferidas acima registradas com caminhos e contagens verificáveis.

## Evidência

Execução local em 2026-11-03, branch `dev` (`cdb3696` + este incremento):

- `make check`: **391 passed**, 16 e2e deselected, cobertura **73,75%**;
  Ruff check/format e mypy strict limpos; Alembic `upgrade head` + `check` sem
  operações pendentes.
- `make security`: pip-audit sem vulnerabilidades; Gitleaks sem vazamentos.
- `make e2e`: **16 passed** (inclui o teste de cookies em Chromium).
- `git diff --exit-code docs/openapi.yaml`: sem diff.
- `git diff --exit-code CONTEXT.md`: sem diff.
- Teste de regressão do asset: falha antes da correção com
  `TypeError: Object of type JSONResponse is not JSON serializable` e passa
  depois.
- CI remoto: ainda não executado para este incremento local; a `dev` de origem
  já tinha o CI verde do PR #129.

## Rastreabilidade

Tracker local aceito pela regra D1 do `docs/ADR-ISSUE-TRACKER.md` enquanto a
issue remota não for criada. O `gh` não está autenticado neste ambiente; a
criação da issue no GitHub é um bloqueio externo a resolver antes de fechar a
fase.
