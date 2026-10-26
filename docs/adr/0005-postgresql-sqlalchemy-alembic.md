# ADR-005: PostgreSQL com SQLAlchemy e Alembic

- Status: superseded by [ADR-021](0021-sqlite-default-database.md) for the database engine; SQLAlchemy/Alembic decisions remain
- Fonte: `adr_creator_python.pdf`, seção 7
- Tracker: [#38](https://github.com/labLima/creator-backend/issues/38)

## Decisão

Supabase PostgreSQL é o banco relacional; SQLAlchemy é o boundary ORM e Alembic controla migrations reproduzíveis.

Casos de uso não acessam `Session` SQLAlchemy diretamente. A aplicação depende de repositórios e de uma Unit of Work transacional; SQLAlchemy permanece restrito à infraestrutura, que mapeia falhas de persistência para exceções de domínio.

## Issues vinculadas

#2, #3, #5, #6, #12, #19 e #29. Consulte o [tracker central](../ADR-ISSUE-TRACKER.md).
