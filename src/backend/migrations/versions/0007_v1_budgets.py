"""v1 budgets: add budgets table for per-month category spending targets

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "category_id",
            sa.Integer,
            sa.ForeignKey("categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("valid_from", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_budgets_category_month", "budgets", ["category_id", "valid_from"]
    )
    op.create_check_constraint(
        "ck_budgets_valid_from_first_of_month",
        "budgets",
        "EXTRACT(day FROM valid_from) = 1",
    )
    op.create_index(
        "ix_budgets_category_valid_from", "budgets", ["category_id", "valid_from"]
    )


def downgrade() -> None:
    op.drop_index("ix_budgets_category_valid_from", table_name="budgets")
    op.drop_table("budgets")
