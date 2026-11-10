"""SQLAlchemy implementation of the billing_account persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
from creator.billing_account.ports import (
    BillingAccountRecord,
    BillingAddressRecord,
    BillingAddressRepository,
)


def _document_text(value: bytes | None) -> str | None:
    return value.decode("utf-8") if value is not None else None


def _document_type(value: bytes | None) -> str | None:
    if value is None:
        return None
    return {11: "cpf", 14: "cnpj"}.get(len(value))


def _document_fields(value: object) -> dict[str, object]:
    if value is None:
        return {"document": None, "document_hash": None}
    encoded = str(value).encode("utf-8")
    return {"document": encoded, "document_hash": hashlib.sha256(encoded).hexdigest()}


def _billing_account(row: billing_account_models.BillingAccount) -> BillingAccountRecord:
    return BillingAccountRecord(
        id=row.id,
        user_id=row.user_id,
        payer_type=row.payer_type,
        name=row.name,
        email=row.email,
        phone=row.phone,
        document=_document_text(row.document),
        document_type=_document_type(row.document),
        company_name=row.company_name,
        provider=row.provider,
        provider_customer_id=row.external_id,
        provider_customer_code=row.external_code,
        delinquent=row.delinquent,
        metadata=dict(row.metadata_json or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=None,
    )


class SqlAlchemyBillingAccountRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_user(self, *, user_id: UUID) -> list[BillingAccountRecord]:
        rows = self._session.scalars(
            select(billing_account_models.BillingAccount)
            .where(billing_account_models.BillingAccount.user_id == user_id)
            .order_by(billing_account_models.BillingAccount.created_at.desc())
        ).all()
        return [_billing_account(row) for row in rows]

    def get_for_user(self, *, user_id: UUID, account_id: UUID) -> BillingAccountRecord | None:
        row = self._session.scalars(
            select(billing_account_models.BillingAccount).where(
                billing_account_models.BillingAccount.id == account_id,
                billing_account_models.BillingAccount.user_id == user_id,
            )
        ).one_or_none()
        return _billing_account(row) if row else None

    def add(
        self,
        *,
        user_id: UUID,
        payer_type: str,
        name: str,
        email: str,
        phone: str | None,
        document: str | None,
        document_type: str | None,
    ) -> BillingAccountRecord:
        row = billing_account_models.BillingAccount(
            user_id=user_id,
            payer_type=payer_type,
            name=name,
            email=email,
            phone=phone,
            provider="PAGARME",
            **_document_fields(document),
        )
        self._session.add(row)
        self._session.flush()
        return _billing_account(row)

    def update(
        self, *, user_id: UUID, account_id: UUID, fields: dict[str, object]
    ) -> BillingAccountRecord:
        row = self._session.scalars(
            select(billing_account_models.BillingAccount).where(
                billing_account_models.BillingAccount.id == account_id,
                billing_account_models.BillingAccount.user_id == user_id,
            )
        ).one_or_none()
        if row is None:
            raise ValueError("Billing account not found")
        mapping = {
            "provider_customer_id": "external_id",
            "provider_customer_code": "external_code",
            "document_type": None,
            "document": "document",
        }
        for name, value in fields.items():
            if name == "document_type":
                continue
            if name == "document":
                for column, column_value in _document_fields(value).items():
                    setattr(row, column, column_value)
                continue
            target = mapping.get(name, name)
            if target is not None:
                setattr(row, target, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _billing_account(row)

    def soft_delete(self, *, user_id: UUID, account_id: UUID) -> None:
        row = self._session.scalars(
            select(billing_account_models.BillingAccount).where(
                billing_account_models.BillingAccount.id == account_id,
                billing_account_models.BillingAccount.user_id == user_id,
            )
        ).one_or_none()
        if row is None:
            raise ValueError("Billing account not found")
        self._session.delete(row)
        self._session.flush()


class SqlAlchemyBillingAddressRepository(BillingAddressRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _record(self, x: billing_account_models.BillingAddress) -> BillingAddressRecord:
        return BillingAddressRecord(
            id=x.id,
            billing_account_id=x.billing_account_id,
            street=x.line_1,
            number=x.number,
            complement=x.line_2,
            neighborhood=x.district,
            zip_code=x.zip_code,
            city=x.city,
            state=x.state,
            created_at=x.created_at,
            updated_at=x.updated_at,
            deleted_at=None,
        )

    def _owned(self, uid: UUID, aid: UUID):
        return self.s.scalar(
            select(billing_account_models.BillingAddress)
            .join(billing_account_models.BillingAccount)
            .where(
                billing_account_models.BillingAddress.id == aid,
                billing_account_models.BillingAccount.user_id == uid,
                billing_account_models.BillingAddress.status != "DELETED",
            )
        )

    def list_for_user(self, *, user_id: UUID, account_id: UUID | None = None):
        q = (
            select(billing_account_models.BillingAddress)
            .join(billing_account_models.BillingAccount)
            .where(
                billing_account_models.BillingAccount.user_id == user_id,
                billing_account_models.BillingAddress.status != "DELETED",
            )
        )
        if account_id is not None:
            q = q.where(billing_account_models.BillingAddress.billing_account_id == account_id)
        return [self._record(x) for x in self.s.scalars(q).all()]

    def get_for_user(self, *, user_id: UUID, address_id: UUID):
        x = self._owned(user_id, address_id)
        return self._record(x) if x else None

    def add(self, *, billing_account_id: UUID, fields: dict[str, object]):
        mapping = {
            "street": "line_1",
            "complement": "line_2",
            "neighborhood": "district",
        }
        values = {mapping.get(key, key): value for key, value in fields.items()}
        values["line_1"] = values.get("line_1") or ""
        values["number"] = values.get("number") or ""
        values["zip_code"] = values.get("zip_code") or ""
        values["city"] = values.get("city") or ""
        values["state"] = values.get("state") or ""
        values.setdefault("country", "BR")
        values.setdefault("status", "ACTIVE")
        x = billing_account_models.BillingAddress(billing_account_id=billing_account_id, **values)
        self.s.add(x)
        self.s.flush()
        return self._record(x)

    def update(self, *, address_id: UUID, fields: dict[str, object]):
        x = self.s.get(billing_account_models.BillingAddress, address_id)
        if x is None or x.status == "DELETED":
            raise ValueError("Billing address not found")
        mapping = {"street": "line_1", "complement": "line_2", "neighborhood": "district"}
        for key, value in fields.items():
            if key in {"status", "is_default", "country", "external_id", "metadata"}:
                setattr(x, key, value)
            else:
                setattr(x, mapping.get(key, key), value)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._record(x)

    def soft_delete(self, *, address_id: UUID):
        x = self.s.get(billing_account_models.BillingAddress, address_id)
        if x is None or x.status == "DELETED":
            raise ValueError("Billing address not found")
        x.status = "DELETED"
        x.updated_at = datetime.now(UTC)
        self.s.flush()
