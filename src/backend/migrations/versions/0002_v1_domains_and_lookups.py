"""v1 domains and lookup tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres DOMAIN declarations — used by money/rate columns in later migrations
    op.execute("CREATE DOMAIN money_amount AS numeric(14,2)")
    op.execute("CREATE DOMAIN percentage_rate AS numeric(6,4)")

    # --- Lookup tables (natural text PK, seeded below) ---

    op.create_table(
        "banks",
        sa.Column("code", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
    )

    op.create_table(
        "account_types",
        sa.Column("code", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
    )

    op.create_table(
        "match_types",
        sa.Column("code", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
    )

    op.create_table(
        "flag_statuses",
        sa.Column("code", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
    )

    op.create_table(
        "flag_types",
        sa.Column("code", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
    )

    op.create_table(
        "audit_actions",
        sa.Column("code", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
    )

    # --- Seed data ---

    op.bulk_insert(
        sa.table("banks",
            sa.column("code", sa.String),
            sa.column("label", sa.String),
        ),
        [
            {"code": "bank_a", "label": "Bank A"},
            {"code": "bank_b", "label": "Bank B"},
        ],
    )

    op.bulk_insert(
        sa.table("account_types",
            sa.column("code", sa.String),
            sa.column("label", sa.String),
        ),
        [
            {"code": "transaction", "label": "Transaction"},
            {"code": "savings",     "label": "Savings"},
            {"code": "loan",        "label": "Loan"},
            {"code": "credit",      "label": "Credit"},
        ],
    )

    op.bulk_insert(
        sa.table("match_types",
            sa.column("code", sa.String),
            sa.column("label", sa.String),
        ),
        [
            {"code": "contains", "label": "Contains"},
            {"code": "equals",   "label": "Equals"},
            {"code": "regex",    "label": "Regex"},
        ],
    )

    op.bulk_insert(
        sa.table("flag_statuses",
            sa.column("code", sa.String),
            sa.column("label", sa.String),
        ),
        [
            {"code": "open",      "label": "Open"},
            {"code": "approved",  "label": "Approved"},
            {"code": "dismissed", "label": "Dismissed"},
        ],
    )

    op.bulk_insert(
        sa.table("flag_types",
            sa.column("code", sa.String),
            sa.column("label", sa.String),
            sa.column("description", sa.String),
        ),
        [
            {
                "code": "over_threshold",
                "label": "Over threshold",
                "description": "Transaction amount exceeds the configured threshold",
            },
            {
                "code": "double_charge",
                "label": "Possible double charge",
                "description": "Same amount and similar merchant within N days",
            },
            {
                "code": "new_merchant",
                "label": "New merchant",
                "description": "First time this merchant has appeared",
            },
            {
                "code": "recurring_change",
                "label": "Change in regular payment",
                "description": "Amount shift on a previously regular payment (v1.5)",
            },
        ],
    )

    op.bulk_insert(
        sa.table("audit_actions",
            sa.column("code", sa.String),
            sa.column("label", sa.String),
        ),
        [
            {"code": "import",          "label": "Import batch"},
            {"code": "reverse_import",  "label": "Reverse import"},
            {"code": "recategorise",    "label": "Recategorise transaction"},
            {"code": "approve_flag",    "label": "Approve flag"},
            {"code": "dismiss_flag",    "label": "Dismiss flag"},
            {"code": "create_rule",     "label": "Create rule"},
        ],
    )


def downgrade() -> None:
    op.drop_table("audit_actions")
    op.drop_table("flag_types")
    op.drop_table("flag_statuses")
    op.drop_table("match_types")
    op.drop_table("account_types")
    op.drop_table("banks")
    op.execute("DROP DOMAIN percentage_rate")
    op.execute("DROP DOMAIN money_amount")
