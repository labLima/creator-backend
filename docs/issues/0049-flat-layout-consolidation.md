# 0049 — Consolidação da estrutura plana por capacidade

- ADR primária: [ADR-024](../adr/0024-estrutura-plana-por-capacidade.md)
- ADRs relacionadas: [ADR-023](../adr/0023-estrutura-modular-por-capacidade.md)
- Issues relacionadas: [0045](0045-modular-structure-tracker.md),
  [0046](0046-security-backlog-after-modularization.md),
  [0048](0048-plain-capability-layout.md)
- Issue remota: [#133](https://github.com/labLima/creator-backend/issues/133)
- Status: concluída e mergeada no PR
  [#137](https://github.com/labLima/creator-backend/pull/137)
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

## Resultado da consolidação

As dívidas estruturais deste incremento foram resolvidas:

- Nenhum `service.py` importa `creator.api`; erros, paginação e serializers de
  aplicação agora vivem em `creator.application`, e o transporte mantém a
  tradução para respostas HTTP.
- Os routers `auth`, `content`, `generation` e `workflow` recebem casos de uso
  pela composição e não acessam UoW nem repositórios.
- Os 47 contratos de repositório antes expostos como atributos planos foram
  agrupados em 28 interfaces de agregado no UoW. Auth Sessions e Outbox
  continuam independentes por seus ciclos de vida próprios; os grupos mantêm a
  mesma sessão e fronteira transacional.
- O backlog de segurança S1–S13 da
  [0046](0046-security-backlog-after-modularization.md) continua fora de escopo.

## Critérios de aceite

- [x] `GET /api/v1/assets/{id}` com Brand Asset retorna 200, envelope único e
      `data.id` correto; Asset comum continua funcionando.
- [x] As 27 capacidades expõem `__init__.py`, `router.py`, `schemas.py`,
      `service.py`, `ports.py`, `repository.py` e `models.py`.
- [x] `src/creator/modules`, `src/creator/repositories` e
      `src/creator/infrastructure/persistence/repositories` não existem.
- [x] Nenhum `service.py` chama `success_response()` ou `error_response()`.
- [x] `docs/openapi.yaml` e `CONTEXT.md` sem diff.
- [x] Nenhum `service.py` importa `creator.api`.
- [x] Nenhum router de `auth`, `content`, `generation` e `workflow` acessa UoW
      ou repositórios.
- [x] Interfaces de repositório agrupadas por agregado; regressões de
      persistência, isolamento e transação cobertas.
- [x] `make check` e `make e2e` verdes.
- [x] `make security` verde no ambiente isolado do projeto; o pip-audit ignorou
      apenas as quatro vulnerabilidades já configuradas e Gitleaks não encontrou
      vazamentos.
- [x] README, AGENTS, status, 0045, 0046, 0048 e tracker consistentes com a
      estrutura plana.
- [x] Dívidas deferidas acima registradas com caminhos e contagens verificáveis.

## Evidência

Execução local em 2026-11-04, branch `codex/0049-application-boundaries`:

- `make check PYTHON=.venv/Scripts/python.exe`: Ruff check/format e mypy limpos;
  **451 passed**, cobertura **74,17%**; Alembic `upgrade head` + `check` sem
  operações pendentes.
- `make e2e PYTHON=.venv/Scripts/python.exe`: **15 passed, 1 skipped**.
- `make security PYTHON=.venv/Scripts/python.exe`: pip-audit sem vulnerabilidades
  não ignoradas; Gitleaks em container examinou 136 commits e não encontrou
  vazamentos. O ambiente isolado foi resolvido a partir de `pyproject.toml`;
  nenhuma dependência ou item do backlog 0046 foi alterado.
- `docker build -t creator-backend-python:0049 .`: concluído.
- `git diff --exit-code docs/openapi.yaml`: sem diff.
- `git diff --exit-code CONTEXT.md`: sem diff.
- `tests/test_module_boundaries.py`: guardas verificam imports de transporte
  nos services e acessos de persistência nos quatro routers.
- Os caminhos de módulos dos workers persistidos em Redis não foram renomeados.

## Rastreabilidade

Tracker local aceito pela regra D1 do `docs/ADR-ISSUE-TRACKER.md`. A issue
remota é [#133](https://github.com/labLima/creator-backend/issues/133).
