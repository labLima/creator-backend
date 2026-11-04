# Issue 0027: planning lifecycle and content linkage

- ADR primária: [`0005-postgresql-sqlalchemy-alembic`](../adr/0005-postgresql-sqlalchemy-alembic.md)
- ADR relacionada: [`0011-core-resource-crud`](../adr/0011-core-resource-crud.md)
- ADR tracker: [#38](https://github.com/labLima/creator-backend/issues/38)
- GitHub: [#50](https://github.com/labLima/creator-backend/issues/50)
- Labels: `backend`, `database`, `architecture`, `priority-high`, `adr-005`
- Status: **reescrita em 2026-11-04 para o vocabulário Planning**

## Contexto

O domínio antigo de calendário (`calendars`/`calendar_items`) foi substituído por
Campaign → Persona → Planning → Post Structure. O CRUD de Planning já existe,
mas não há lifecycle explícito de planejamento, aprovação, associação a Content
ou publicação.

## Objetivo

Completar o ciclo de vida do Planning como calendário editorial: estados,
transições, vínculo com Content e prontidão para aprovação/publicação, sem criar
uma entidade Calendar separada.

## Modelo esperado

- Manter `planning` como agregado Brand-scoped, ligado a um Campaign e um Persona.
- Definir estados controlados para o Planning e para Post Structure
  (por exemplo: rascunho, em revisão, aprovado, publicado, cancelado).
- Permitir que um Post Structure origine um Content e preserve o vínculo.
- Definir regras de transição, datas UTC, Soft Delete e metadata.
- Garantir que Planning, Post Structure, Brand, Campaign, Persona e Content
  pertençam ao mesmo Workspace/Brand quando aplicável.

## Critérios de aceite

- [ ] Estados e transições de Planning/Post Structure documentados e testados.
- [ ] Post Structure pode originar e referenciar Content sem perder a especificação.
- [ ] Aprovação humana e publicação são representadas sem antecipar um Provider.
- [ ] Consultas por período, Brand, Campaign, Persona e status têm índices.
- [ ] Isolamento cross-Workspace é coberto por testes.
- [ ] `docs/openapi.yaml` é atualizado antes de mudanças de API.
- [ ] CONTEXT.md permanece a fonte do vocabulário (sem Calendar separado).

## Dependências

- Depends on: `workspaces`, `workspace_memberships`, `brands`, `campaigns`,
  `personas`, `planning`, `post_structure`, `contents`.
- Related: ADR-005, ADR-007, ADR-008, ADR-011; issues #51 e #52.
