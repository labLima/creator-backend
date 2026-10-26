# Legacy PostgreSQL migrations

These migrations were the original PostgreSQL/Supabase schema history. They are
kept for reference only and are no longer executed by Alembic.

The SQLite baseline lives in `migrations/versions/0001_sqlite_baseline.py`.
There is no data migration from PostgreSQL in this cutover (decision C1): the
SQLite database starts empty. If production data needs to be preserved, add an
explicit ETL step and backup before running the baseline.
