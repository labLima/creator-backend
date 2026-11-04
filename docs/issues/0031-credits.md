# Issue 0031: credits wallet and transactions

- ADR primária: [`0005-postgresql-sqlalchemy-alembic`](../adr/0005-postgresql-sqlalchemy-alembic.md)
- ADR relacionada: [`0019-credit-ledger`](../adr/0019-credit-ledger.md)
- ADR tracker: [#38](https://github.com/labLima/creator-backend/issues/38)
- GitHub: [#54](https://github.com/labLima/creator-backend/issues/54)
- Labels: `backend`, `database`, `architecture`, `priority-high`, `adr-005`
- Status: **aberta em 2026-11-04; schema antigo removido, ledger real pendente**

## Contexto

Creator precisa controlar saldo e consumo por Workspace para gerações de imagem,
texto, melhorias e agentes. A issue #23 cobre tokens/custo estimado de Provider;
esta issue define o ledger de créditos do produto sem duplicar telemetria.

## Estado atual do código

- A migration `0004_drop_dead_tables` removeu `credit_wallets`,
  `credit_transactions` e `credit_prices` porque não tinham repositório ou caso
  de uso alcançável.
- Existe apenas `workspace_credit_transactions`, uma tabela genérica exposta por
  CRUD (`/api/v1/workspace-credit-transactions`), sem wallet, saldo, débito
  atômico, preço por ação ou idempotência de consumo.
- A ADR-019 descreve o alvo (wallet, ledger append-only, preços e débito
  transacional), mas esse alvo não está implementado.

## Objetivo

Criar carteira, transações append-only e preços configuráveis, com débito atômico
e saldo auditável por Workspace, conforme ADR-019.

## Modelo esperado

- `credit_wallets`: `workspace_id` único, `balance`, `monthly_allowance`,
  `purchased_credits`, `total_spent`, `cycle_started_at`, `created_at`,
  `updated_at`.
- `credit_transactions`: `id`, `workspace_id`, `user_id` nullable, `action_key`,
  `credits`, `quantity`, `balance_after`, `metadata`, `created_at`.
- `credit_prices`: `action_key` único, `category`, `credits`, `description`,
  `active`, `metadata`.
- Definir unidade/tipo, sinal de `credits`, ciclo mensal, allowance/purchased/spent,
  reembolso, idempotência e política de saldo negativo.
- Indexar wallet por Workspace, transactions por Workspace/data/action/user e
  prices por action/active.

## Critérios de aceite

- [ ] Migration Alembic reversível e modelos SQLAlchemy implementados.
- [ ] Há no máximo uma wallet ativa por Workspace e o saldo é atualizado
      transacionalmente.
- [ ] Débito, crédito, estorno e idempotência têm regras documentadas e testadas.
- [ ] Transactions são auditáveis e não podem ser alteradas silenciosamente.
- [ ] Prices suportam texto, imagem, melhorias e agentes sem hardcode disperso.
- [ ] A integração com #23 correlaciona consumo técnico e débito de produto sem
      duplicar eventos.
- [ ] Testes cobrem concorrência, saldo insuficiente, ciclo, estorno, ownership e
      isolamento.
- [ ] Qualquer endpoint atualiza `docs/openapi.yaml` antes da implementação.

## Dependências

- Depends on: `workspaces`, `workspace_memberships`, `users`, consumo de
  Provider/Geração da #23.
- Related: ADR-001, ADR-005, ADR-007, ADR-008, ADR-019; issue #23.
