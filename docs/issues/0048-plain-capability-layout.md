# 0048 — Estrutura plana por capacidade

- ADR: [ADR-024](../adr/0024-estrutura-plana-por-capacidade.md)
- Status: concluída

## Resultado

| Item | Estado |
|---|---|
| `modules/` removido | ✅ |
| `adapters/` removido | ✅ |
| ORM em `<entidade>/models.py` | ✅ 51 tabelas |
| Repositórios em `<entidade>/repository.py` | ✅ 27 |
| Protocolos em `<entidade>/ports.py` | ✅ 27 |
| Serviços em `<entidade>/service.py` | ✅ 27 |
| DTOs em `<entidade>/schemas.py` | ✅ 27 |
| Pacotes com `__init__.py` | ✅ 27 |
| Contrato HTTP congelado | ✅ 227 operações |
| Schema congelado | ✅ 51 tabelas, DDL idêntico |
| Consolidação complementar | [0049](0049-flat-layout-consolidation.md) |

## Evidência

`make check && make e2e && make security && make migrate-check` verdes. A
verificação de vocabulário completo das 27 capacidades foi incorporada em
`tests/test_module_boundaries.py` e consolidada na [0049](0049-flat-layout-consolidation.md).

Evidência local de 2026-11-03: `make check` com **391 passed** e cobertura
**73,75%**; `make e2e` com **16 passed**; `make security` sem vulnerabilidades
ou vazamentos; `docs/openapi.yaml` e `CONTEXT.md` sem diff.
