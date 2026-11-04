# ADR-024: Estrutura plana por capacidade

- Status: accepted
- Data: 2026-10-30
- Substitui parcialmente: [ADR-023](0023-estrutura-modular-por-capacidade.md) (níveis `modules/` e `adapters/`)
- Tracker: [docs/issues/0048](../issues/0048-plain-capability-layout.md)
- Consolidação complementar: [docs/issues/0049](../issues/0049-flat-layout-consolidation.md)

## Contexto

A ADR-023 colocou cada capacidade em `src/creator/modules/<entidade>/` com um
subpacote `adapters/` para o ORM. O resultado resolvia o acoplamento, mas
mantinha dois níveis de indireção antes de chegar ao código da entidade, e a
persistência continuava em diretórios compartilhados.

O padrão adotado no projeto de referência NestJS-API é uma pasta por entidade
sob `src/`, contendo controller, service e DTOs. A ideia é que abrir a pasta da
entidade responda a tudo sobre ela.

## Decisão

Cada capacidade é um pacote diretamente sob `src/creator/`, com vocabulário de
arquivos fixo:

```
src/creator/<entidade>/
├── __init__.py
├── router.py       # HTTP
├── service.py      # casos de uso
├── repository.py   # implementação SQLAlchemy
├── models.py       # tabelas SQLAlchemy
├── schemas.py      # DTOs Pydantic
└── ports.py        # Records + Protocolos
```

Sem `modules/`, sem `adapters/`. `creator/repositories/` e
`infrastructure/persistence/repositories/` deixam de existir.

### Fronteiras

- `models.py` e `repository.py` são os únicos arquivos que podem importar
  `sqlalchemy` ou `creator.infrastructure`.
- `router.py`, `service.py`, `schemas.py`, `ports.py` importam apenas
  `core`, `domain`, `uow` e o vocabulário compartilhado de outra capacidade
  (`ports.py`, `schemas.py`, `exceptions.py`, `models.py`).
- Integração entre capacidades acontece por `creator/uow.py`.
- Verificado por `tests/test_module_boundaries.py`.

## Consequências

- 27 pastas de entidade, cada uma com os sete arquivos do vocabulário
  (incluindo `__init__.py`).
- `main.py` continua com 161 linhas e nenhuma rota.
- O contrato HTTP e o schema permanecem congelados: 227 operações, 51 tabelas,
  DDL byte a byte idêntico.
- A separação entre aplicação e transporte, a migração dos quatro routers e a
  consolidação dos repositórios por agregado foram concluídas na
  [issue 0049](../issues/0049-flat-layout-consolidation.md), sem alterar o
  contrato HTTP ou os caminhos persistidos dos workers.

## Critérios de aceite

- [x] `src/creator/modules` não existe
- [x] `src/creator/repositories` e `infrastructure/persistence/repositories` não existem
- [x] 27 `router.py`, `service.py`, `repository.py`, `models.py`, `schemas.py`, `ports.py`
- [x] 27 `__init__.py`; `workflow` tem DTOs e pacote próprios desde a [0049](../issues/0049-flat-layout-consolidation.md)
- [x] 227 operações idênticas e 51 tabelas idênticas
- [x] `make check`, `make e2e`, `make security`, `make migrate-check` verdes
