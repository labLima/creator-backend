# ADR-005: PostgreSQL com SQLAlchemy e Alembic

- Status: accepted
- Fonte: `adr_creator_python.pdf`, seção 7
- Tracker: [#38](https://github.com/lefilcompany/creator-backend-python/issues/38)

## Decisão

Supabase PostgreSQL é o banco relacional; SQLAlchemy é o boundary ORM e Alembic controla migrations reproduzíveis.

Casos de uso não acessam `Session` SQLAlchemy diretamente. A aplicação depende de repositórios e de uma Unit of Work transacional; SQLAlchemy permanece restrito à infraestrutura, que mapeia falhas de persistência para exceções de domínio.

Os modelos usam os tipos genéricos do SQLAlchemy (`Uuid`, `JSON` e um
`UTCDateTime` com timezone) e defaults Python para UUIDs. Enums são strings
com `CHECK`; índices parciais declaram predicados para SQLite e PostgreSQL.
PostgreSQL continua sendo o banco principal, enquanto SQLite é usado para
testes de schema e desenvolvimento local sem depender de tipos, funções ou
defaults PostgreSQL no runtime da aplicação.

## Issues vinculadas

#2, #3, #5, #6, #12, #19 e #29. Consulte o [tracker central](../ADR-ISSUE-TRACKER.md).
