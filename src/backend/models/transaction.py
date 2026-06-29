import datetime
import uuid
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from core.types import MoneyAmount


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    import_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("imports.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Dedupe key columns — all NOT NULL (NULL would defeat the UNIQUE constraint)
    txn_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    balance: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    # Interpretation columns — mutable; recategorise/re-merchant writes audit_log
    merchant_id: Mapped[int | None] = mapped_column(
        ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "account_id", "txn_date", "amount", "description_raw", "balance",
            name="uq_transactions_dedupe_key",
        ),
    )
