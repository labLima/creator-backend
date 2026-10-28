"""Concrete adapters for external systems and persistence.

Subpackages are intentionally split by responsibility:

* ``auth``: authentication provider adapters;
* ``database``: SQLAlchemy engine, schema, and ORM models;
* ``persistence``: repository implementations and Unit of Work;
* ``runtime``: queue, storage, rate limiting, and observability adapters.
"""
