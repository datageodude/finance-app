"""v1 core entities: users.is_active, accounts, loan_terms, credit_terms, merchants, categories

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Archive-don't-delete: add is_active to the existing users table
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bank_code", sa.String(), sa.ForeignKey("banks.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("account_code", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), sa.ForeignKey("account_types.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="AUD"),
        sa.Column("bank_account_name", sa.String(), nullable=True),
        sa.Column("opening_balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("current_balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("bank_code", "account_code", name="uq_accounts_bank_account"),
    )

    op.create_table(
        "loan_terms",
        sa.Column("account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("original_principal", sa.Numeric(14, 2), nullable=False),
        sa.Column("interest_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("term_months", sa.Integer(), nullable=False),
    )

    op.create_table(
        "credit_terms",
        sa.Column("account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("credit_limit", sa.Numeric(14, 2), nullable=False),
    )

    op.create_table(
        "merchants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("normalised_name", sa.String(), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), unique=True, nullable=False),
        sa.Column("parent_id", sa.Integer(),
                  sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Indexes
    op.create_index("ix_accounts_bank_code", "accounts", ["bank_code"])
    op.create_index("ix_accounts_is_active", "accounts", ["is_active"])


def downgrade() -> None:
    op.drop_table("categories")
    op.drop_table("merchants")
    op.drop_table("credit_terms")
    op.drop_table("loan_terms")
    op.drop_table("accounts")
    op.drop_column("users", "is_active")
