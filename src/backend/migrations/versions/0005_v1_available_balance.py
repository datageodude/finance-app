"""v1 available_balance: add available_balance to accounts

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("available_balance", sa.Numeric(14, 2), nullable=True),
    )
    op.create_check_constraint(
        "ck_accounts_available_balance_non_negative",
        "accounts",
        "available_balance >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_accounts_available_balance_non_negative",
        "accounts",
        type_="check",
    )
    op.drop_column("accounts", "available_balance")
