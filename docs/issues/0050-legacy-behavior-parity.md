# 0050 — Paridade de comportamento com o Create Bloom legado e ETL

- ADR primária: [ADR-010](../adr/0010-architecture-governance.md)
- Issue remota: [#134](https://github.com/labLima/creator-backend/issues/134)
- Substitui o escopo de migração de comportamento da #44
- Status: aberta (Fase 2)
- Owner: backend/platform + produto

## Contexto

A #44 está fechada como `completed`, mas os critérios de migração de
comportamento e ETL não foram atendidos. O inventário de código está em
[`docs/migration/legacy-inventory.md`](../migration/legacy-inventory.md) e a
matriz de compatibilidade em
[`docs/migration/legacy-compatibility-matrix.md`](../migration/legacy-compatibility-matrix.md).
O escopo remanescente está nesta issue.

## Escopo

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

## Fora de escopo

- Migrar dados de produção sem dump/backup validado.
- Copiar hashes do Supabase Auth; contas migradas devem definir nova senha.

## Critérios de aceite

- [ ] Cada comportamento da matriz tem status, issue e teste de contrato.
- [ ] Dados legados têm plano de ETL, validação, rollback e dono.
- [ ] Nenhuma tabela legada é removida antes de seus leitores/escritores serem migrados.
- [ ] `docs/SCHEMA-MIGRATION-MATRIX.md` e o inventário são atualizados a cada migração.
- [ ] Evidência de execução em banco novo e dados de teste.

## Evidência atual

- Inventário de código completo (104 server functions, 4 handlers HTTP, 107 RPCs,
  32 views, ~70 tabelas ativas, 5 buckets).
- Nenhum comportamento classificado como plenamente equivalente: 0 equivalentes,
  20 parciais, 9 ausentes, 3 novos/fora de escopo.
- Sem dump de dados/storage; ETL não executável.
