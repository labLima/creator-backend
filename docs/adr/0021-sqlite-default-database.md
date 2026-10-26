# ADR-021: SQLite como banco padrão e portabilidade

- Status: accepted
- Fonte: decisão da Fase -1, 2026-10-26
- Tracker: [#97](https://github.com/labLima/creator-backend/issues/97)
- Issues: [#98](https://github.com/labLima/creator-backend/issues/98), [#99](https://github.com/labLima/creator-backend/issues/99), [#100](https://github.com/labLima/creator-backend/issues/100), [#101](https://github.com/labLima/creator-backend/issues/101), [#102](https://github.com/labLima/creator-backend/issues/102)

## Contexto

O runtime usava PostgreSQL/Supabase e dependia de tipos e extensões específicas (`JSONB`, `PGUUID`, `gen_random_uuid`, `pg_trgm`, `FOR UPDATE SKIP LOCKED`, `jsonb_typeof`). O produto precisa rodar localmente com SQLite e, depois, apontar para um servidor SQLite-compatível.

## Decisão

SQLite é o banco padrão, em arquivo local:

- `DATABASE_URL` padrão: `sqlite+pysqlite:///./.local/db/creator.db`.
- Em containers, o arquivo fica em `/data/creator.db`, em volume nomeado.
- A conexão ativa `PRAGMA foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000` e `synchronous=NORMAL`.
- Models usam tipos portáveis: `sqlalchemy.Uuid`, `JSON`, `UTCDateTime` e enums não nativos.
- O baseline Alembic é recriado a partir dos models em `0001_sqlite_baseline`; migrations PostgreSQL antigas ficam arquivadas em `migrations/legacy_postgres/`.
- Claims de outbox/jobs usam `UPDATE ... RETURNING`/condicional, não `FOR UPDATE SKIP LOCKED`.
- Busca textual usa FTS5 ou `LIKE`; não há dependência de `pg_trgm`.
- O cutover assume banco novo (decisão C1). Dados PostgreSQL exigem backup e ETL explícito.

O escopo de portabilidade é **SQLite e servidores SQLite-compatíveis** (por exemplo, libSQL). PostgreSQL/MySQL não são bancos de produção suportados nesta decisão.

## Consequências

O ambiente local fica mais simples e não depende de um container de banco. SQLite serializa escritores; API e worker compartilham o mesmo arquivo e precisam de WAL, `busy_timeout` e claims atômicos. O volume precisa ser persistido e incluído na política de backup.

Se o volume de escrita ou a concorrência crescerem além do que o arquivo suporta, a saída é um servidor SQLite-compatível (libSQL `sqld`), decidido no spike #102, sem alterar os casos de uso.

## Fora de escopo

Suporte a PostgreSQL/MySQL como bancos de produção.
