# ADR-010: Governança de decisões e issues

- Status: accepted
- Fonte: decisão de bootstrap do repositório
- Tracker: [#43](https://github.com/labLima/creator-backend/issues/43)

## Contexto

O projeto será desenvolvido com engenharia agêntica e precisa manter decisões explicáveis e trabalho rastreável.

## Decisão

Toda decisão arquitetural material deve ter ADR, issue versionada e, quando possível, issue remota no GitHub. O `AGENTS.md` define o fluxo e o script de sincronização é idempotente.

O fluxo de qualidade é centralizado nos alvos versionados do `Makefile`. `make check`
executa Ruff lint, Ruff format check, mypy e pytest; CI e desenvolvimento local usam
esse mesmo alvo. `make security` executa `pip-audit` e Gitleaks. Qualquer vulnerabilidade
reportada pelo `pip-audit` ou secret detectado bloqueia o merge. O Gitleaks usa somente
allowlist de valores determinísticos já presentes em fixtures e configuração local,
sem exclusão ampla de diretórios.

O pre-commit é opcional e chama os mesmos comandos de Ruff e mypy antes do commit.

## Consequências

Há uma fonte auditável no repositório mesmo quando GitHub estiver indisponível. A publicação remota exige credencial válida e não bloqueia o desenvolvimento local.

## Emenda 2026-11-03 — dispensa e reatribuição de tracker

Uma issue de implementação aberta pode ser **explicitamente dispensada** de um
tracker quando:

1. for reatribuída a outra ADR, fase ou issue substituta;
2. a justificativa, a milestone de destino e a evidência estiverem registradas no
   tracker central e no corpo da issue;
3. o dono da fase aprovar a dispensa.

Dispensa não significa declarar a issue concluída. Significa que ela deixa de
bloquear aquele tracker. A regra 3 do tracker central é atualizada para refletir
esse mecanismo.

## Issues vinculadas

#1, #21, #26, #30, #31, #44, [#133](https://github.com/labLima/creator-backend/issues/133), [#134](https://github.com/labLima/creator-backend/issues/134), [#135](https://github.com/labLima/creator-backend/issues/135) e [controles de qualidade](../issues/0025-quality-controls.md).
Consulte o [tracker central](../ADR-ISSUE-TRACKER.md).
