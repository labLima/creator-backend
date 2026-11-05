# 0050 — Paridade de comportamento com o Create Bloom legado e ETL

- ADR primária: [ADR-010](../adr/0010-architecture-governance.md)
- Issue remota: [#134](https://github.com/labLima/creator-backend/issues/134)
- Substitui o escopo de migração de comportamento da #44
- Status: **encerrada como não planejada em 2026-11-04**
- Owner: backend/platform + produto

## Decisão

O Creator está sendo construído com arquitetura nova. A paridade de comportamento
com o Create Bloom legado deixou de ser um objetivo de produto e não haverá ETL
de dados nem reimplementação de fluxos legados.

Consequências:

- A matriz de compatibilidade e o inventário em `docs/migration/` permanecem
  como registro histórico, não como backlog.
- Tabelas legadas que ainda existem no schema não são migradas por causa desta
  decisão. Qualquer remoção exige uma issue própria, com consumidores migrados e
  evidência de ausência de uso.
- `docs/SCHEMA-MIGRATION-MATRIX.md` não deve mais tratar a #134 como dependência.
- A #44 permanece fechada como inventário; a parte de migração foi abandonada
  junto com esta issue.

## Escopo histórico (não executado)

- Autenticação: recuperação de senha, OTP/magic link, confirmação de e-mail,
  OAuth e importação de usuários.
- Workspace/equipe: feature flags, limites, aceite de convite, troca de role,
  remoção/leave.
- Marca/persona/planejamento/post: JSON `extra`/`creator_state`, campos e limites.
- Créditos: wallet, lotes, expiração, consumo, free allowance e custos de IA.
- Billing/Pagar.me: checkout, webhook, reconciliação e schema.
- Pipeline calendário → copy → design, composição de imagem, carrossel, resize
  e QA.
- Vídeo, feed/comunidade, admin, histórico, uploads, e-mail e rotas públicas.
- ETL de dados/storage, incluindo mapeamento de IDs, PII e SQLite.

## Evidência

- Inventário de código completo (104 server functions, 4 handlers HTTP, 107 RPCs,
  32 views, ~70 tabelas ativas, 5 buckets).
- Nenhum comportamento classificado como plenamente equivalente: 0 equivalentes,
  20 parciais, 9 ausentes, 3 novos/fora de escopo.
- Sem dump de dados/storage; ETL não executável.
- Decisão de produto registrada em 2026-11-04: arquitetura nova, sem legado.
