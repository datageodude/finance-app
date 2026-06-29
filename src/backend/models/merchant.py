import uuid
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from core.types import MoneyAmount


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    normalised_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MerchantThresholdOverride(Base):
    """Per-merchant over_threshold override. One row per merchant; merchant_id is PK."""

    __tablename__ = "merchant_threshold_overrides"

    merchant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("merchants.id", ondelete="RESTRICT"), primary_key=True
    )
    threshold: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
