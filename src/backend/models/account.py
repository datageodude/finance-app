import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from core.types import MoneyAmount, PercentageRate


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bank_code: Mapped[str] = mapped_column(
        String, ForeignKey("banks.code", ondelete="RESTRICT"), nullable=False
    )
    account_code: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(
        String, ForeignKey("account_types.code", ondelete="RESTRICT"), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String, nullable=False, server_default="AUD"
    )
    bank_account_name: Mapped[str | None] = mapped_column(String, nullable=True)
    opening_balance: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    available_balance: Mapped[Decimal | None] = mapped_column(MoneyAmount, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("bank_code", "account_code", name="uq_accounts_bank_account"),
    )


class LoanTerms(Base):
    __tablename__ = "loan_terms"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    original_principal: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    interest_rate: Mapped[Decimal] = mapped_column(PercentageRate, nullable=False)
    term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class CreditTerms(Base):
    __tablename__ = "credit_terms"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    credit_limit: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
