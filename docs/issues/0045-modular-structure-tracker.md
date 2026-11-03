# 0045 — Estrutura modular por capacidade (tracker histórico)

> **Documento histórico.** A estrutura `modules/` e os `adapters/` foram
> substituídos pela [ADR-024](../adr/0024-estrutura-plana-por-capacidade.md).
> Os caminhos `modules/*` abaixo descrevem o estado anterior. A fase 5
> (consolidação de repositórios) foi transferida para a
> [0049](0049-flat-layout-consolidation.md).

- ADR: [ADR-023](../adr/0023-estrutura-modular-por-capacidade.md)
- Status: histórica — substituída pela ADR-024
- Owner: backend/platform

## Objetivo

Mover o backend de organização por camada técnica para módulos por capacidade,
mantendo o contrato HTTP congelado.

## Fases

| Fase | Escopo | Estado |
|---|---|---|
| 0 | Congelar contrato: tabela de rotas, inventário de schema, serializers, `make migrate-check` | concluída |
| 1 | Remover código morto inalcançável + migration `0004` | concluída |
| 2 | Extrair 222 rotas de `main.py` para `modules/*/router.py` | concluída |
| 3 | Mover 76 DTOs para `modules/*/schemas.py` | concluída |
| 4 | Dissolver `application/` em `modules/*/{service,ports}.py` | concluída |
| 5 | Consolidar 47 repositórios em ~30 por agregado | transferida para [0049](0049-flat-layout-consolidation.md) |
| 6 | Mover `database/models` e `schema_models` para `modules/*/adapters/tables.py` | concluída |
| 7 | Atualizar cobertura, README e `AGENTS.md` | concluída |

## Critérios de aceite

- [x] `main.py` sem decorators de rota
- [x] 227 operações idênticas (path, método, `operationId`, tags)
- [x] 51 tabelas com DDL byte a byte idêntico
- [x] Regra de import verificada por teste
- [x] `make check`, `make e2e`, `make migrate-check` verdes
- [ ] Repositórios consolidados por agregado — transferido para [0049](0049-flat-layout-consolidation.md)
- [x] ORM sob `modules/*/adapters/tables.py` (histórico; hoje `<entidade>/models.py`)
- [x] `SqlAlchemyUnitOfWork` herda `UnitOfWork`

## Evidência

- `src/creator/main.py`: 5.722 → 161 linhas
- `src/creator/modules/`: 27 capacidades (histórico; hoje `src/creator/<entidade>/`)
- `tests/contracts/route_table.json`: 227 operações
- `tests/contracts/schema_tables.json`: 51 tabelas em 27 capacidades
- Backlog de segurança pré-existente exposto pela movimentação: [0046](0046-security-backlog-after-modularization.md)
