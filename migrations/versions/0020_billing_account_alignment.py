"""Align billing accounts, addresses and payment methods (T15, B1).

The final modeling stores the document as bytes plus a SHA-256 hash, uses
``line_1``/``line_2``/``district`` for addresses and card enums plus external
ids for payment methods. The repositories keep the previous API vocabulary by
translating at the boundary; this revision rebuilds the three tables and maps
the existing rows.
"""

import hashlib
import re

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import uf_check, zip_code_check
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0020_billing_account_alignment"
down_revision = "0019_legacy_contract"
branch_labels = None
depends_on = None

_CARD_BRANDS = {
    "VISA",
    "MASTERCARD",
    "AMEX",
    "ELO",
    "HIPERCARD",
    "DINERS",
    "DISCOVER",
    "JCB",
    "AURA",
    "CABAL",
    "OTHER",
}
_FUNDING = {"CREDIT", "DEBIT"}
_ZIP = re.compile(r"^[0-9]{8}$")
_UF = re.compile(r"^[A-Z]{2}$")


def _columns(table: str) -> dict[str, dict[str, object]]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return {}
    return {column["name"]: column for column in inspector.get_columns(table)}


def _rows(statement: str) -> list[dict[str, object]]:
    return [dict(row._mapping) for row in op.get_bind().execute(sa.text(statement))]


def _rebuild_accounts() -> None:
    columns = _columns("billing_accounts")
    if not columns or "document_hash" in columns:
        return
    rows = _rows(
        "SELECT id, user_id, payer_type, name, email, phone, document, company_name, "
        "provider, provider_customer_id, provider_customer_code, delinquent, metadata, "
        "created_at, updated_at FROM billing_accounts WHERE deleted_at IS NULL"
    )
    normalized = []
    for row in rows:
        document = row["document"]
        encoded = str(document).encode("utf-8") if document else None
        payer_type = str(row["payer_type"] or "INDIVIDUAL").upper()
        if payer_type not in {"INDIVIDUAL", "COMPANY"}:
            payer_type = "INDIVIDUAL"
        company_name = row["company_name"]
        if company_name is not None:
            payer_type = "COMPANY"
        elif payer_type == "COMPANY":
            company_name = str(row["name"])[:64]
        normalized.append(
            {
                **row,
                "payer_type": payer_type,
                "email": str(row["email"])[:254],
                "company_name": company_name,
                "provider": str(row["provider"] or "PAGARME").upper(),
                "document": encoded,
                "document_hash": hashlib.sha256(encoded).hexdigest() if encoded else None,
                "metadata": row["metadata"],
            }
        )
    op.create_table(
        "billing_accounts_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "user_id",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "payer_type",
            enum_column("billing_account_type", create_constraint=False),
            nullable=False,
        ),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("document", sa.LargeBinary()),
        sa.Column("document_hash", sa.String(64)),
        sa.Column("company_name", sa.String(64)),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("external_id", sa.String(64)),
        sa.Column("external_code", sa.String(52)),
        sa.Column("delinquent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", json_type),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(payer_type = 'COMPANY') = (company_name IS NOT NULL)",
            name="chk_billing_accounts_company_name",
        ),
        sa.CheckConstraint(
            "(document IS NULL) = (document_hash IS NULL)",
            name="chk_billing_accounts_document_pair",
        ),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO billing_accounts_old "
                "(id, user_id, payer_type, name, email, phone, document, document_hash, "
                "company_name, provider, external_id, external_code, delinquent, metadata, "
                "created_at, updated_at) "
                "VALUES (:id, :user_id, :payer_type, :name, :email, :phone, :document, "
                ":document_hash, :company_name, :provider, :provider_customer_id, "
                ":provider_customer_code, :delinquent, :metadata, :created_at, :updated_at)"
            ),
            normalized,
        )
    op.drop_table("billing_accounts")
    op.rename_table("billing_accounts_old", "billing_accounts")
    op.create_index("ix_billing_accounts_document_hash", "billing_accounts", ["document_hash"])
    op.create_index("ix_billing_accounts_user_id", "billing_accounts", ["user_id"])
    op.create_index(
        "uq_billing_accounts_provider_external_id",
        "billing_accounts",
        ["provider", "external_id"],
        unique=True,
    )


def _rebuild_addresses() -> None:
    columns = _columns("billing_addresses")
    if not columns or "line_1" in columns:
        return
    rows = _rows(
        "SELECT id, billing_account_id, street, number, complement, neighborhood, "
        "zip_code, city, state, created_at, updated_at FROM billing_addresses "
        "WHERE deleted_at IS NULL"
    )
    normalized = []
    for row in rows:
        zip_code = str(row["zip_code"] or "")
        state = str(row["state"] or "").upper()[:2]
        country = "BR" if _ZIP.match(zip_code) and _UF.match(state) else "US"
        normalized.append(
            {
                "id": row["id"],
                "billing_account_id": row["billing_account_id"],
                "line_1": str(row["street"] or ""),
                "number": str(row["number"] or ""),
                "line_2": row["complement"],
                "district": row["neighborhood"],
                "zip_code": zip_code[:8],
                "city": str(row["city"] or ""),
                "state": state,
                "country": country,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    op.create_table(
        "billing_addresses_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "billing_account_id",
            uuid_pk,
            sa.ForeignKey("billing_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(64)),
        sa.Column("line_1", sa.String(256), nullable=False),
        sa.Column("number", sa.String(20), nullable=False),
        sa.Column("line_2", sa.String(128)),
        sa.Column("district", sa.String(64)),
        sa.Column("zip_code", sa.String(8), nullable=False),
        sa.Column("city", sa.String(64), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column(
            "status",
            enum_column("address_status", create_constraint=False),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", json_type),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("external_id", name="uq_billing_addresses_external_id"),
        sa.CheckConstraint(
            f"country <> 'BR' OR {zip_code_check('zip_code')}",
            name="chk_billing_addresses_zip_code",
        ),
        sa.CheckConstraint(
            f"country <> 'BR' OR {uf_check('state')}",
            name="chk_billing_addresses_state_uf",
        ),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO billing_addresses_old "
                "(id, billing_account_id, line_1, number, line_2, district, zip_code, "
                "city, state, country, created_at, updated_at) "
                "VALUES (:id, :billing_account_id, :line_1, :number, :line_2, :district, "
                ":zip_code, :city, :state, :country, :created_at, :updated_at)"
            ),
            normalized,
        )
    op.drop_table("billing_addresses")
    op.rename_table("billing_addresses_old", "billing_addresses")
    op.create_index(
        "ix_billing_addresses_billing_account_id", "billing_addresses", ["billing_account_id"]
    )
    op.create_index(
        "uq_billing_addresses_default",
        "billing_addresses",
        ["billing_account_id"],
        unique=True,
        sqlite_where=sa.text("is_default AND status = 'ACTIVE'"),
    )


def _rebuild_payment_methods() -> None:
    columns = _columns("billing_payment_methods")
    if not columns or "external_id" in columns:
        return
    rows = _rows(
        "SELECT id, billing_account_id, provider_card_id, holder_name, holder_document, "
        "card_brand, card_last_four, exp_month, exp_year, card_type, card_status, "
        "is_default, created_at, updated_at FROM billing_payment_methods "
        "WHERE deleted_at IS NULL"
    )
    seen_default: set[object] = set()
    normalized = []
    for row in rows:
        brand = str(row["card_brand"] or "").upper()
        funding = str(row["card_type"] or "").upper()
        status = str(row["card_status"] or "ACTIVE").upper()
        if status not in {"ACTIVE", "DELETED", "EXPIRED"}:
            status = "ACTIVE"
        is_default = bool(row["is_default"])
        if is_default and row["billing_account_id"] in seen_default:
            is_default = False
        if is_default:
            seen_default.add(row["billing_account_id"])
        normalized.append(
            {
                "id": row["id"],
                "billing_account_id": row["billing_account_id"],
                "external_id": row["provider_card_id"],
                "brand": brand if brand in _CARD_BRANDS else None,
                "card_last_four": row["card_last_four"],
                "holder_name": row["holder_name"],
                "holder_document": row["holder_document"],
                "exp_month": row["exp_month"],
                "exp_year": row["exp_year"],
                "type": funding if funding in _FUNDING else None,
                "status": status,
                "is_default": is_default,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    op.create_table(
        "billing_payment_methods_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "billing_account_id",
            uuid_pk,
            sa.ForeignKey("billing_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "billing_address_id",
            uuid_pk,
            sa.ForeignKey("billing_addresses.id", ondelete="SET NULL"),
        ),
        sa.Column("external_id", sa.String(64)),
        sa.Column("external_network_token_id", sa.String(64)),
        sa.Column("first_six_digits", sa.String(6)),
        sa.Column("brand", enum_column("card_brand", create_constraint=False)),
        sa.Column("card_last_four", sa.String(4)),
        sa.Column("holder_name", sa.String(64)),
        sa.Column("holder_document", sa.String(16)),
        sa.Column("exp_month", sa.Integer()),
        sa.Column("exp_year", sa.Integer()),
        sa.Column("type", enum_column("funding_source", create_constraint=False)),
        sa.Column(
            "status",
            enum_column("card_status", create_constraint=False),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", json_type),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "exp_month IS NULL OR exp_month BETWEEN 1 AND 12",
            name="chk_billing_payment_methods_exp_month",
        ),
        sa.CheckConstraint(
            "exp_year IS NULL OR exp_year BETWEEN 2000 AND 2100",
            name="chk_billing_payment_methods_exp_year",
        ),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO billing_payment_methods_old "
                "(id, billing_account_id, external_id, brand, card_last_four, holder_name, "
                "holder_document, exp_month, exp_year, type, status, is_default, "
                "created_at, updated_at) "
                "VALUES (:id, :billing_account_id, :external_id, :brand, :card_last_four, "
                ":holder_name, :holder_document, :exp_month, :exp_year, :type, :status, "
                ":is_default, :created_at, :updated_at)"
            ),
            normalized,
        )
    op.drop_table("billing_payment_methods")
    op.rename_table("billing_payment_methods_old", "billing_payment_methods")
    op.create_index(
        "ix_billing_payment_methods_account_default",
        "billing_payment_methods",
        ["billing_account_id", "is_default"],
    )
    op.create_index(
        "idx_m8_billing_payment_methods_billing_address_id",
        "billing_payment_methods",
        ["billing_address_id"],
        sqlite_where=sa.text("billing_address_id IS NOT NULL"),
    )
    op.create_index(
        "uq_billing_payment_methods_default",
        "billing_payment_methods",
        ["billing_account_id"],
        unique=True,
        sqlite_where=sa.text("is_default AND status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_billing_payment_methods_account_external_id",
        "billing_payment_methods",
        ["billing_account_id", "external_id"],
        unique=True,
    )


def upgrade() -> None:
    _rebuild_accounts()
    _rebuild_addresses()
    _rebuild_payment_methods()


def downgrade() -> None:
    """Recreate the legacy shape; the document hash and card externals are lossy."""

    _downgrade_payment_methods()
    _downgrade_addresses()
    _downgrade_accounts()


def _downgrade_payment_methods() -> None:
    if "provider_card_id" in _columns("billing_payment_methods"):
        return
    op.create_table(
        "billing_payment_methods_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("billing_account_id", uuid_pk, nullable=False),
        sa.Column("provider_card_id", sa.String(64)),
        sa.Column("holder_name", sa.String(64)),
        sa.Column("holder_document", sa.String(16)),
        sa.Column("card_brand", sa.String(20)),
        sa.Column("card_last_four", sa.String(4)),
        sa.Column("exp_month", sa.Integer()),
        sa.Column("exp_year", sa.Integer()),
        sa.Column("card_type", sa.String(20)),
        sa.Column("card_status", sa.String(20)),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO billing_payment_methods_legacy "
        "(id, billing_account_id, provider_card_id, holder_name, holder_document, "
        "card_brand, card_last_four, exp_month, exp_year, card_type, card_status, "
        "is_default, created_at, updated_at) "
        "SELECT id, billing_account_id, external_id, holder_name, holder_document, "
        "lower(brand), card_last_four, exp_month, exp_year, lower(type), lower(status), "
        "is_default, created_at, updated_at FROM billing_payment_methods"
    )
    op.drop_table("billing_payment_methods")
    op.rename_table("billing_payment_methods_legacy", "billing_payment_methods")


def _downgrade_addresses() -> None:
    if "street" in _columns("billing_addresses"):
        return
    op.create_table(
        "billing_addresses_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("billing_account_id", uuid_pk, nullable=False),
        sa.Column("street", sa.String(128)),
        sa.Column("number", sa.String(16)),
        sa.Column("complement", sa.String(64)),
        sa.Column("neighborhood", sa.String(64)),
        sa.Column("zip_code", sa.String(16)),
        sa.Column("city", sa.String(64)),
        sa.Column("state", sa.String(16)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO billing_addresses_legacy "
        "(id, billing_account_id, street, number, complement, neighborhood, zip_code, "
        "city, state, created_at, updated_at) "
        "SELECT id, billing_account_id, line_1, number, line_2, district, zip_code, "
        "city, state, created_at, updated_at FROM billing_addresses"
    )
    op.drop_table("billing_addresses")
    op.rename_table("billing_addresses_legacy", "billing_addresses")


def _downgrade_accounts() -> None:
    if "provider_customer_id" in _columns("billing_accounts"):
        return
    op.create_table(
        "billing_accounts_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("user_id", uuid_pk, nullable=False),
        sa.Column("payer_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("email", sa.String(64), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("document", sa.String(50)),
        sa.Column("document_type", sa.String(10)),
        sa.Column("company_name", sa.String(64)),
        sa.Column("provider", sa.String(20)),
        sa.Column("provider_customer_id", sa.String(64)),
        sa.Column("provider_customer_code", sa.String(52)),
        sa.Column("delinquent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", json_type),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO billing_accounts_legacy "
        "(id, user_id, payer_type, name, email, phone, document, document_type, "
        "company_name, provider, provider_customer_id, provider_customer_code, "
        "delinquent, metadata, created_at, updated_at) "
        "SELECT id, user_id, payer_type, substr(name, 1, 64), substr(email, 1, 64), "
        "phone, CASE WHEN document IS NULL THEN NULL ELSE CAST(document AS TEXT) END, "
        "CASE length(document) WHEN 11 THEN 'cpf' WHEN 14 THEN 'cnpj' ELSE NULL END, "
        "company_name, provider, external_id, external_code, delinquent, metadata, "
        "created_at, updated_at FROM billing_accounts"
    )
    op.drop_table("billing_accounts")
    op.rename_table("billing_accounts_legacy", "billing_accounts")
