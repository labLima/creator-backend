"""Behaviour of the campaign/persona parent keys and brand business details (T22).

The composite foreign keys are tenant-scoped: a detail row must reference a
campaign and a persona that belong to the same brand it declares.
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


def _chain(connection: sa.Connection) -> dict[str, str]:
    user, workspace, brand, campaign, persona = (uuid4() for _ in range(5))
    connection.execute(
        sa.text(
            "INSERT INTO users (id, external_id, global_role, created_at, updated_at) "
            "VALUES (:id, :external, 'membro', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": user.hex, "external": f"ext-{user}"},
    )
    connection.execute(
        sa.text(
            "INSERT INTO workspaces (id, name, created_at, updated_at) "
            "VALUES (:id, 'ws', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": workspace.hex},
    )
    connection.execute(
        sa.text(
            "INSERT INTO brands "
            "(id, workspace_id, created_by_user_id, name, metadata, created_at, updated_at) "
            "VALUES (:id, :workspace, :user, 'brand', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": brand.hex, "workspace": workspace.hex, "user": user.hex},
    )
    connection.execute(
        sa.text(
            "INSERT INTO campaigns "
            "(id, brand_id, workspace_id, created_by, name, created_at, updated_at) "
            "VALUES (:id, :brand, :workspace, :user, 'campaign', "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {
            "id": campaign.hex,
            "brand": brand.hex,
            "workspace": workspace.hex,
            "user": user.hex,
        },
    )
    connection.execute(
        sa.text(
            "INSERT INTO personas (id, brand_id, created_by, name, created_at, updated_at) "
            "VALUES (:id, :brand, :user, 'persona', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": persona.hex, "brand": brand.hex, "user": user.hex},
    )
    return {
        "user": user.hex,
        "brand": brand.hex,
        "campaign": campaign.hex,
        "persona": persona.hex,
    }


def test_business_details_requires_matching_tenant(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        chain = _chain(connection)
        connection.execute(
            sa.text(
                "INSERT INTO brand_business_details "
                "(id, brand_id, campaign_id, persona_id, output, created_at, updated_at) "
                "VALUES (:id, :brand, :campaign, :persona, '{}', "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": uuid4().hex,
                "brand": chain["brand"],
                "campaign": chain["campaign"],
                "persona": chain["persona"],
            },
        )
        with pytest.raises(IntegrityError):
            connection.execute(
                sa.text(
                    "INSERT INTO brand_business_details "
                    "(id, brand_id, campaign_id, persona_id, output, created_at, updated_at) "
                    "VALUES (:id, :other_brand, :campaign, :persona, '{}', "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {
                    "id": uuid4().hex,
                    "other_brand": uuid4().hex,
                    "campaign": chain["campaign"],
                    "persona": chain["persona"],
                },
            )


def test_business_details_foreign_keys_are_composite(engine: sa.Engine) -> None:
    inspector = sa.inspect(engine)
    foreign_keys = {
        tuple(item["constrained_columns"]): item
        for item in inspector.get_foreign_keys("brand_business_details")
    }
    assert ("campaign_id", "brand_id") in foreign_keys
    assert ("persona_id", "brand_id") in foreign_keys
    assert foreign_keys[("campaign_id", "brand_id")]["options"]["ondelete"] == "CASCADE"


def test_parent_unique_keys_exist_for_the_composite_foreign_keys(engine: sa.Engine) -> None:
    inspector = sa.inspect(engine)
    campaigns = {index["name"]: index for index in inspector.get_indexes("campaigns")}
    personas = {index["name"]: index for index in inspector.get_indexes("personas")}
    assert campaigns["uq_campaigns_id_brand_id"]["unique"]
    assert personas["uq_personas_id_brand_id"]["unique"]


def test_campaign_brand_id_is_nullable_debt_until_the_backfill(engine: sa.Engine) -> None:
    """Documented gap: the dump requires NOT NULL and there is no backfill yet."""
    campaigns = Base.metadata.tables["campaigns"]
    assert campaigns.c.brand_id.nullable is True
