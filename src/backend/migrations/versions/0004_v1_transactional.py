"""v1 transactional: imports, transactions (dedupe UNIQUE), rules, flags, audit_log

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("bank_code", sa.String(),
                  sa.ForeignKey("banks.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rows_added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("import_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("imports.id", ondelete="RESTRICT"), nullable=False),
        # Dedupe key columns — all NOT NULL
        sa.Column("txn_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("description_raw", sa.Text(), nullable=False),
        sa.Column("balance", sa.Numeric(14, 2), nullable=False),
        # Interpretation columns — mutable
        sa.Column("merchant_id", sa.Integer(),
                  sa.ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_id", sa.Integer(),
                  sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # The keystone — makes re-import idempotent
        sa.UniqueConstraint(
            "account_id", "txn_date", "amount", "description_raw", "balance",
            name="uq_transactions_dedupe_key",
        ),
    )

    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("match_type", sa.String(),
                  sa.ForeignKey("match_types.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("match_value", sa.String(), nullable=False),
        sa.Column("category_id", sa.Integer(),
                  sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "flags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("related_transaction_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("flag_type", sa.String(),
                  sa.ForeignKey("flag_types.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(),
                  sa.ForeignKey("flag_statuses.code", ondelete="RESTRICT"),
                  nullable=False, server_default="open"),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(),
                  sa.ForeignKey("audit_actions.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Indexes
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_txn_date", "transactions", ["txn_date"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_merchant_id", "transactions", ["merchant_id"])
    op.create_index("ix_flags_status", "flags", ["status"])
    op.create_index("ix_audit_log_target", "audit_log", ["target_type", "target_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("flags")
    op.drop_table("rules")
    op.drop_table("transactions")
    op.drop_table("imports")
