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
| Contrato HTTP congelado | ✅ 227 operações |
| Schema congelado | ✅ 51 tabelas, DDL idêntico |

## Evidência

`make check && make e2e && make security && make migrate-check` verdes.
