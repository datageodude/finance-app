"""v1 flagging: UNIQUE(transaction_id, flag_type) on flags + merchant_threshold_overrides

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_flags_txn_flag_type",
        "flags",
        ["transaction_id", "flag_type"],
    )
    op.create_table(
        "merchant_threshold_overrides",
        sa.Column("merchant_id", sa.Integer(),
                  sa.ForeignKey("merchants.id", ondelete="RESTRICT"),
                  primary_key=True, nullable=False),
        sa.Column("threshold", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("merchant_threshold_overrides")
    op.drop_constraint("uq_flags_txn_flag_type", "flags", type_="unique")
