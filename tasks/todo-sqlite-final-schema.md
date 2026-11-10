# TODO — Alinhamento do schema SQLite ao Creator_DB_final.sql

> Checklist de execução de [`plan-sqlite-final-schema.md`](plan-sqlite-final-schema.md).
> Issues filhas no board `SHC` (Shared Context): `SHC-2` em diante, filhas de `SHC-1`.
> Issue global: [#159](https://github.com/labLima/creator-backend/issues/159).
> Rastreabilidade local: [docs/issues/0058](../docs/issues/0058-sqlite-final-schema-alignment.md).
>
> Gates por tarefa: `XDG_DATA_HOME=$PWD/.local/xdg make check PYTHON=.venv/bin/python`,
> `... make security ...`, `... make e2e ...`. PRs contra `dev`.

## Fase 0 — Contrato, paridade e portabilidade

- [x] **T1** (SHC-2, S) ADR-028, épico e tracker — depende de —
- [x] **T2** (SHC-3, L) Comparador único e teste de paridade com orçamento — depende de T1
- [x] **T3** (SHC-4, S) Helpers portáveis de enum e nome de índice — depende de T1
- [x] **T4** (SHC-5, M) Portabilidade das CHECK constraints e defaults — depende de T3
- [x] **T19** (SHC-20, M) Snapshot como gate, índices no fixture e teste de upgrade anterior — depende de T2

### Checkpoint — Fase 0 — Contrato, paridade e portabilidade

- [ ] Tarefas da fase concluídas e issues filhas em `review`.
- [ ] `make check`, `make security` e `make e2e` verdes.
- [ ] `python scripts/schema_parity_report.py` sem divergência não justificada.

## Fase 1 — Criar tabelas

- [x] **T5** (SHC-6, S) Conformidade, consentimento e interesses — depende de T4
- [x] **T6** (SHC-7, M) Satélites de Brand e Campanha — depende de T4
- [x] **T7** (SHC-8, M) Satélites de Billing e Créditos — depende de T4

### Checkpoint — Fase 1 — Criar tabelas

- [ ] Tarefas da fase concluídas e issues filhas em `review`.
- [ ] `make check`, `make security` e `make e2e` verdes.
- [ ] `python scripts/schema_parity_report.py` sem divergência não justificada.

## Fase 2 — Renomear e redesenhar (expand)

- [x] **T8** (SHC-9, M) workspace_members: rename, status, invited_by e exclusão física — depende de T4
- [x] **T9** (SHC-10, M) planning para content_plans e satélites — depende de T4
- [x] **T10** (SHC-11, M) post_structure e design_structure para posts, captions, post_designs e design_slides — depende de T4
- [x] **T11** (SHC-12, M) generated_image para generated_images e image_resizes — depende de T4
- [x] **T21** (SHC-22, M) Vocabulário de workspace_role e autorização — depende de T8

### Checkpoint — Fase 2 — Renomear e redesenhar (expand)

- [ ] Tarefas da fase concluídas e issues filhas em `review`.
- [ ] `make check`, `make security` e `make e2e` verdes.
- [ ] `python scripts/schema_parity_report.py` sem divergência não justificada.

## Fase 3 — Backfill e contract

- [x] **T12** (SHC-13, M) Backfill dos 4 redesenhos — depende de T8, T9, T10, T11
- [x] **T13** (SHC-14, S) Contract: remover as tabelas antigas — depende de T12

### Checkpoint — Fase 3 — Backfill e contract

- [ ] Tarefas da fase concluídas e issues filhas em `review`.
- [ ] `make check`, `make security` e `make e2e` verdes.
- [ ] `python scripts/schema_parity_report.py` sem divergência não justificada.

## Fase 4 — Alinhar tabelas comuns

- [ ] **T14** (SHC-15, M) Lote A: identidade, notificações, brand, campanha e persona — depende de T13
- [ ] **T15** (SHC-16, M) Lote B: billing, créditos e cupons — depende de T14

### Checkpoint — Fase 4 — Alinhar tabelas comuns

- [ ] Tarefas da fase concluídas e issues filhas em `review`.
- [ ] `make check`, `make security` e `make e2e` verdes.
- [ ] `python scripts/schema_parity_report.py` sem divergência não justificada.

## Fase 5 — Aposentadoria do legado

- [ ] **T16** (SHC-17, M) ADR-029, 11 legadas e 2 tabelas sem alvo — depende de T15
- [ ] **T20** (SHC-21, M) Triggers, funções e view do dump — depende de T15

### Checkpoint — Fase 5 — Aposentadoria do legado

- [ ] Tarefas da fase concluídas e issues filhas em `review`.
- [ ] `make check`, `make security` e `make e2e` verdes.
- [ ] `python scripts/schema_parity_report.py` sem divergência não justificada.

## Fase 6 — Consolidação e fechamento

- [ ] **T17** (SHC-18, M) Consolidar a baseline — depende de T13, T15, T16
- [ ] **T18** (SHC-19, S) Fechamento do épico — depende de T17

### Checkpoint — Fase 6 — Consolidação e fechamento

- [ ] Tarefas da fase concluídas e issues filhas em `review`.
- [ ] `make check`, `make security` e `make e2e` verdes.
- [ ] `python scripts/schema_parity_report.py` sem divergência não justificada.

