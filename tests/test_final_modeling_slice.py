"""Behaviour of the first final-modeling slice: audit, consent, persona interests.

These tables were added before any route consumes them, so the tests protect the
contract they will rely on: append-only audit with ``SET NULL`` actor, one
consent per user/type/version with a closed vocabulary, and unique interest per
persona (``CASCADE`` with the persona).
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from creator.infrastructure.database import metadata as _models  # noqa: F401
from creator.infrastructure.database.db import Base


@pytest.fixture()
def engine() -> Iterator[sa.Engine]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @sa.event.listens_for(engine, "connect")
    def _foreign_keys(connection: object, _record: object) -> None:
        cursor = connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def _insert_user(connection: sa.Connection) -> object:
    user_id = uuid4()
    connection.execute(
        sa.text(
            "INSERT INTO users (id, external_id, global_role, created_at, updated_at) "
            "VALUES (:id, :external_id, 'membro', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": user_id.hex, "external_id": f"ext-{user_id}"},
    )
    return user_id


def _insert_brand(connection: sa.Connection) -> tuple[object, object]:
    workspace_id, user_id, brand_id = uuid4(), uuid4(), uuid4()
    connection.execute(
        sa.text(
            "INSERT INTO workspaces (id, name, created_at, updated_at) "
            "VALUES (:id, 'ws', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": workspace_id.hex},
    )
    connection.execute(
        sa.text(
            "INSERT INTO users (id, external_id, global_role, created_at, updated_at) "
            "VALUES (:id, :external_id, 'membro', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": user_id.hex, "external_id": f"ext-{user_id}"},
    )
    connection.execute(
        sa.text(
            "INSERT INTO brands "
            "(id, workspace_id, created_by_user_id, name, metadata, created_at, updated_at) "
            "VALUES (:id, :workspace, :user, 'brand', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": brand_id.hex, "workspace": workspace_id.hex, "user": user_id.hex},
    )
    return brand_id, user_id


def _insert_persona(connection: sa.Connection) -> object:
    brand_id, user_id = _insert_brand(connection)
    persona_id = uuid4()
    connection.execute(
        sa.text(
            "INSERT INTO personas (id, brand_id, created_by, name, created_at, updated_at) "
            "VALUES (:id, :brand, :user, 'persona', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": persona_id.hex, "brand": brand_id.hex, "user": user_id.hex},
    )
    return persona_id


def _insert_campaign(connection: sa.Connection) -> object:
    workspace_id, user_id = uuid4(), uuid4()
    connection.execute(
        sa.text(
            "INSERT INTO workspaces (id, name, created_at, updated_at) "
            "VALUES (:id, 'ws', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": workspace_id.hex},
    )
    connection.execute(
        sa.text(
            "INSERT INTO users (id, external_id, global_role, created_at, updated_at) "
            "VALUES (:id, :external_id, 'membro', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": user_id.hex, "external_id": f"ext-{user_id}"},
    )
    campaign_id = uuid4()
    connection.execute(
        sa.text(
            "INSERT INTO campaigns (id, workspace_id, created_by, name, created_at, updated_at) "
            "VALUES (:id, :workspace, :user, 'campaign', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": campaign_id.hex, "workspace": workspace_id.hex, "user": user_id.hex},
    )
    return campaign_id


def test_audit_log_actor_becomes_null_when_user_is_deleted(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        user_id = _insert_user(connection)
        log_id = uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO audit_logs (id, actor_id, action, entity_type, entity_id, created_at) "
                "VALUES (:id, :actor, 'brand.updated', 'brand', :entity, CURRENT_TIMESTAMP)"
            ),
            {"id": log_id, "actor": user_id.hex, "entity": uuid4().hex},
        )
        connection.execute(sa.text("DELETE FROM users WHERE id = :id"), {"id": user_id.hex})
        actor = connection.execute(
            sa.text("SELECT actor_id FROM audit_logs WHERE id = :id"), {"id": log_id}
        ).scalar_one()
    assert actor is None


@pytest.mark.parametrize(
    ("columns", "values"),
    [
        ("id, entity_type, entity_id, created_at", ":id, 'brand', :entity, CURRENT_TIMESTAMP"),
        ("id, action, entity_id, created_at", ":id, 'brand.updated', :entity, CURRENT_TIMESTAMP"),
        ("id, action, entity_type, created_at", ":id, 'brand.updated', 'brand', CURRENT_TIMESTAMP"),
    ],
)
def test_audit_log_requires_action_entity_type_and_entity_id(
    engine: sa.Engine, columns: str, values: str
) -> None:
    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            sa.text(f"INSERT INTO audit_logs ({columns}) VALUES ({values})"),
            {"id": uuid4().hex, "entity": uuid4().hex},
        )


def test_consent_is_unique_per_user_type_and_version(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        user_id = _insert_user(connection)
        row = {
            "id": uuid4().hex,
            "user": user_id.hex,
            "type": "TERMS_OF_USE",
            "version": "2026-01",
        }
        connection.execute(
            sa.text(
                "INSERT INTO user_consents (id, user_id, type, document_version, created_at) "
                "VALUES (:id, :user, :type, :version, CURRENT_TIMESTAMP)"
            ),
            row,
        )
        with pytest.raises(IntegrityError):
            connection.execute(
                sa.text(
                    "INSERT INTO user_consents (id, user_id, type, document_version, created_at) "
                    "VALUES (:id, :user, :type, :version, CURRENT_TIMESTAMP)"
                ),
                {**row, "id": uuid4().hex},
            )
        connection.execute(
            sa.text(
                "INSERT INTO user_consents (id, user_id, type, document_version, created_at) "
                "VALUES (:id, :user, :type, '2027-01', CURRENT_TIMESTAMP)"
            ),
            {**row, "id": uuid4().hex},
        )


def test_consent_rejects_value_outside_the_vocabulary(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        user_id = _insert_user(connection)
        with pytest.raises(IntegrityError):
            connection.execute(
                sa.text(
                    "INSERT INTO user_consents "
                    "(id, user_id, type, document_version, created_at) "
                    "VALUES (:id, :user, 'NOT_A_CONSENT', '2026-01', CURRENT_TIMESTAMP)"
                ),
                {"id": uuid4().hex, "user": user_id.hex},
            )


def test_persona_interest_is_unique_per_persona(engine: sa.Engine) -> None:
    statement = sa.text(
        "INSERT INTO persona_interests (id, persona_id, interest, created_at, updated_at) "
        "VALUES (:id, :persona, 'fitness', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )
    with engine.begin() as connection:
        persona_id = _insert_persona(connection)
        connection.execute(statement, {"id": uuid4().hex, "persona": persona_id.hex})
        with pytest.raises(IntegrityError):
            connection.execute(statement, {"id": uuid4().hex, "persona": persona_id.hex})
        count = connection.execute(sa.text("SELECT COUNT(*) FROM persona_interests")).scalar_one()
    assert count == 1, "the second insert must fail on the unique index, not silently persist"


def test_persona_interest_requires_an_existing_persona(engine: sa.Engine) -> None:
    """FK RESTRICT/CASCADE must be enforced, so the unique test cannot be an FK error."""
    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            sa.text(
                "INSERT INTO persona_interests "
                "(id, persona_id, interest, created_at, updated_at) "
                "VALUES (:id, :persona, 'fitness', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": uuid4().hex, "persona": uuid4().hex},
        )


@pytest.mark.parametrize(
    ("table", "expected"),
    [
        ("audit_logs", {"actor_id": "SET NULL", "workspace_id": "SET NULL"}),
        ("user_consents", {"user_id": "RESTRICT"}),
        ("persona_interests", {"persona_id": "CASCADE"}),
    ],
)
def test_foreign_key_delete_actions_match_the_final_modeling(
    engine: sa.Engine, table: str, expected: dict[str, str]
) -> None:
    inspector = sa.inspect(engine)
    actual = {
        fk["constrained_columns"][0]: (fk.get("options", {}).get("ondelete") or "").upper()
        for fk in inspector.get_foreign_keys(table)
    }
    for column, action in expected.items():
        assert actual.get(column) == action, (table, column, actual)


def test_brand_hashtags_and_values_are_unique_per_brand(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        brand_id, _user_id = _insert_brand(connection)
        for table, column, value in (
            ("brand_hashtags", "hashtag", "verao"),
            ("brand_values", "value", "qualidade"),
        ):
            statement = sa.text(
                f"INSERT INTO {table} (id, brand_id, {column}, created_at, updated_at) "
                f"VALUES (:id, :brand, :value, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
            connection.execute(
                statement, {"id": uuid4().hex, "brand": brand_id.hex, "value": value}
            )
            with pytest.raises(IntegrityError):
                connection.execute(
                    statement, {"id": uuid4().hex, "brand": brand_id.hex, "value": value}
                )


def test_campaign_hashtags_are_unique_per_campaign(engine: sa.Engine) -> None:
    statement = sa.text(
        "INSERT INTO campaign_hashtags (id, campaign_id, hashtag, created_at, updated_at) "
        "VALUES (:id, :campaign, 'lancamento', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )
    with engine.begin() as connection:
        campaign_id = _insert_campaign(connection)
        connection.execute(statement, {"id": uuid4().hex, "campaign": campaign_id.hex})
        with pytest.raises(IntegrityError):
            connection.execute(statement, {"id": uuid4().hex, "campaign": campaign_id.hex})


def test_campaign_voice_vocabulary_is_closed(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        campaign_id = _insert_campaign(connection)
        connection.execute(
            sa.text(
                "INSERT INTO campaign_voices (id, campaign_id, voice, created_at, updated_at) "
                "VALUES (:id, :campaign, 'INSPIRATIONAL', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": uuid4().hex, "campaign": campaign_id.hex},
        )
        with pytest.raises(IntegrityError):
            connection.execute(
                sa.text(
                    "INSERT INTO campaign_voices (id, campaign_id, voice, created_at, updated_at) "
                    "VALUES (:id, :campaign, 'NOT_A_VOICE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"id": uuid4().hex, "campaign": campaign_id.hex},
            )
