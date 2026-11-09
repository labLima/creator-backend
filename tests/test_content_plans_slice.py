"""Behaviour of the ``content_plans`` expand slice (ADR-028, T9).

The plan is tenant-scoped through composite foreign keys to the campaign and the
persona, and its items/dates follow the plan on delete.
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


def _tenant(connection: sa.Connection, name: str) -> dict[str, str]:
    user, workspace, brand, campaign, persona = (uuid4() for _ in range(5))
    connection.execute(
        sa.text(
            "INSERT INTO users (id, external_id, global_role) VALUES (:id, :external, 'membro')"
        ),
        {"id": user.hex, "external": f"ext-{user}"},
    )
    connection.execute(
        sa.text("INSERT INTO workspaces (id, name) VALUES (:id, :name)"),
        {"id": workspace.hex, "name": f"ws-{name}"},
    )
    connection.execute(
        sa.text(
            "INSERT INTO brands (id, workspace_id, created_by_user_id, name, metadata) "
            "VALUES (:id, :workspace, :user, :name, '{}')"
        ),
        {
            "id": brand.hex,
            "workspace": workspace.hex,
            "user": user.hex,
            "name": f"brand-{name}",
        },
    )
    connection.execute(
        sa.text(
            "INSERT INTO campaigns (id, brand_id, workspace_id, created_by, name) "
            "VALUES (:id, :brand, :workspace, :user, :name)"
        ),
        {
            "id": campaign.hex,
            "brand": brand.hex,
            "workspace": workspace.hex,
            "user": user.hex,
            "name": f"campaign-{name}",
        },
    )
    connection.execute(
        sa.text(
            "INSERT INTO personas (id, brand_id, created_by, name) "
            "VALUES (:id, :brand, :user, :name)"
        ),
        {"id": persona.hex, "brand": brand.hex, "user": user.hex, "name": f"persona-{name}"},
    )
    return {
        "user": user.hex,
        "brand": brand.hex,
        "campaign": campaign.hex,
        "persona": persona.hex,
    }


def _plan(connection: sa.Connection, tenant: dict[str, str], **extra: object) -> str:
    plan = uuid4().hex
    values = {
        "id": plan,
        "brand": tenant["brand"],
        "campaign": tenant["campaign"],
        "persona": tenant["persona"],
        "user": tenant["user"],
        "briefing": "briefing",
        "start_date": None,
        "end_date": None,
    }
    values.update(extra)
    connection.execute(
        sa.text(
            "INSERT INTO content_plans "
            "(id, brand_id, campaign_id, persona_id, created_by, briefing, "
            "start_date, end_date) "
            "VALUES (:id, :brand, :campaign, :persona, :user, :briefing, "
            ":start_date, :end_date)"
        ),
        values,
    )
    return plan


def test_plan_requires_matching_tenant(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        first = _tenant(connection, "a")
        second = _tenant(connection, "b")
        _plan(connection, first)
        with pytest.raises(IntegrityError):
            _plan(
                connection,
                {
                    "brand": first["brand"],
                    "campaign": second["campaign"],
                    "persona": first["persona"],
                    "user": first["user"],
                },
            )
        with pytest.raises(IntegrityError):
            _plan(
                connection,
                {
                    "brand": first["brand"],
                    "campaign": first["campaign"],
                    "persona": second["persona"],
                    "user": first["user"],
                },
            )


def test_plan_period_must_be_ordered(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        tenant = _tenant(connection, "a")
        with pytest.raises(IntegrityError) as error:
            _plan(connection, tenant, start_date="2026-02-01", end_date="2026-01-01")
        assert "chk_content_plans_period_order" in str(error.value)
        _plan(connection, tenant, start_date="2026-01-01", end_date="2026-02-01")


def test_items_and_dates_follow_the_plan(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        tenant = _tenant(connection, "a")
        plan = _plan(connection, tenant)
        connection.execute(
            sa.text(
                "INSERT INTO content_plan_items (id, content_plan_id, format, quantity) "
                "VALUES (:id, :plan, 'IMAGE', 2)"
            ),
            {"id": uuid4().hex, "plan": plan},
        )
        connection.execute(
            sa.text(
                "INSERT INTO content_plan_special_dates "
                "(id, content_plan_id, special_date, label) "
                "VALUES (:id, :plan, '2026-05-10', 'Dia das Mães')"
            ),
            {"id": uuid4().hex, "plan": plan},
        )
        connection.execute(sa.text("DELETE FROM content_plans WHERE id = :id"), {"id": plan})
        items = connection.execute(sa.text("SELECT COUNT(*) FROM content_plan_items")).scalar_one()
        dates = connection.execute(
            sa.text("SELECT COUNT(*) FROM content_plan_special_dates")
        ).scalar_one()
    assert (items, dates) == (0, 0)


def test_item_uniqueness_quantity_and_vocabulary(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        plan = _plan(connection, _tenant(connection, "a"))
        statement = sa.text(
            "INSERT INTO content_plan_items (id, content_plan_id, format, quantity) "
            "VALUES (:id, :plan, :format, :quantity)"
        )
        connection.execute(
            statement, {"id": uuid4().hex, "plan": plan, "format": "IMAGE", "quantity": 1}
        )
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                statement, {"id": uuid4().hex, "plan": plan, "format": "IMAGE", "quantity": 1}
            )
        assert "UNIQUE constraint failed" in str(error.value)
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                statement, {"id": uuid4().hex, "plan": plan, "format": "STORIES", "quantity": -1}
            )
        assert "ck_content_plan_items_quantity" in str(error.value)
        with pytest.raises(IntegrityError):
            connection.execute(
                statement,
                {"id": uuid4().hex, "plan": plan, "format": "NOT_A_FORMAT", "quantity": 1},
            )
        connection.execute(
            statement, {"id": uuid4().hex, "plan": plan, "format": "STORIES", "quantity": 0}
        )


def test_special_dates_are_unique_per_plan(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        plan = _plan(connection, _tenant(connection, "a"))
        statement = sa.text(
            "INSERT INTO content_plan_special_dates "
            "(id, content_plan_id, special_date, label) "
            "VALUES (:id, :plan, '2026-05-10', 'Dia das Mães')"
        )
        connection.execute(statement, {"id": uuid4().hex, "plan": plan})
        with pytest.raises(IntegrityError):
            connection.execute(statement, {"id": uuid4().hex, "plan": plan})
