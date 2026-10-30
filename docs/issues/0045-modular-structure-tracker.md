# 0045 — Estrutura modular por capacidade (tracker)

- ADR: [ADR-023](../adr/0023-estrutura-modular-por-capacidade.md)
- Status: em andamento
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
| 5 | Consolidar 47 repositórios em ~30 por agregado | pendente |
| 6 | Mover `database/models` e `schema_models` para `modules/*/adapters/tables.py` | pendente |
| 7 | Atualizar cobertura, README e `AGENTS.md` | concluída |

## Critérios de aceite

- [x] `main.py` sem decorators de rota
- [x] 227 operações idênticas (path, método, `operationId`, tags)
- [x] 51 tabelas com DDL byte a byte idêntico
- [x] Regra de import verificada por teste
- [x] `make check`, `make e2e`, `make migrate-check` verdes
- [ ] Repositórios consolidados por agregado
- [ ] ORM sob `modules/*/adapters/tables.py`

## Evidência

- `src/creator/main.py`: 5.722 → 174 linhas
- `src/creator/modules/`: 27 capacidades
- `tests/contracts/route_table.json`: 227 operações
- `tests/contracts/schema_tables.json`: 51 tabelas
- Backlog de segurança pré-existente exposto pela movimentação: [0046](0046-security-backlog-after-modularization.md)
