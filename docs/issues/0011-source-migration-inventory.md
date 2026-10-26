# Inventory and migrate the legacy Create Bloom behavior

- ADR: [`0010-architecture-governance`](../adr/0010-architecture-governance.md)
- Labels: `migration`, `blocked`
- GitHub: [#44](https://github.com/labLima/creator-backend/issues/44) (reaberta em 2026-10-26)

## Goal

Compare the legacy repository `lefilcompany/create-bloom-73` with this foundation and produce a compatibility matrix before porting behavior.

## Acceptance criteria

- Legacy repository snapshot or authenticated access is available.
- Existing routes, data shapes, and user-visible behaviors are inventoried.
- Each migrated behavior has a contract test and links back to this issue.
