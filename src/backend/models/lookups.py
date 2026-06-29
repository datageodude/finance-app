from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Bank(Base):
    __tablename__ = "banks"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)


class AccountType(Base):
    __tablename__ = "account_types"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)


class MatchType(Base):
    __tablename__ = "match_types"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)


class FlagStatus(Base):
    __tablename__ = "flag_statuses"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)


class FlagType(Base):
    __tablename__ = "flag_types"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)


class AuditAction(Base):
    __tablename__ = "audit_actions"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
