"""v1 loan_dates: add start_date and end_date to loan_terms

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("loan_terms", sa.Column("start_date", sa.Date, nullable=True))
    op.add_column("loan_terms", sa.Column("end_date", sa.Date, nullable=True))


def downgrade() -> None:
    op.drop_column("loan_terms", "end_date")
    op.drop_column("loan_terms", "start_date")
