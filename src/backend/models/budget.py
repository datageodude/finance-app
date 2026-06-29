import datetime
import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from core.types import MoneyAmount


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    valid_from: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("category_id", "valid_from", name="uq_budgets_category_month"),
        CheckConstraint(
            "EXTRACT(day FROM valid_from) = 1",
            name="ck_budgets_valid_from_first_of_month",
        ),
    )
