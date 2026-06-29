"""Import engine — the heart of the app.

preview_import() is a stateless dry-run: parse + validate + dedupe count, no writes.
run_import() commits the full pipeline. Both share _parse_and_validate() for steps 1–4.

Caller (the API router) is responsible for db.commit(). This keeps the service
layer testable with the rollback-on-teardown test fixture pattern.

Error model: ImportValidationError is raised for any 4xx condition. The router
maps it to HTTP 422 with the error_code as the body "error" field.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session as DBSession

from adapters import AdapterResult, get_adapter
from models.account import Account
from models.import_batch import ImportBatch
from models.rule import Rule
from models.transaction import Transaction
from services import auditing
from services import merchants as merchants_svc
from services.transactions import reconcile

# ---------------------------------------------------------------------------
# Public data shapes
# ---------------------------------------------------------------------------


@dataclass
class PreviewResult:
    account_id: UUID
    account_display_name: str
    bank_code: str
    account_code: str
    txn_date_min: date | None
    txn_date_max: date | None
    rows_found: int
    rows_to_add: int
    rows_duplicate: int
    filename_seen_before: bool
    filename_seen_at: datetime | None


@dataclass
class ImportResult:
    import_id: UUID
    rows_added: int
    rows_skipped: int
    reconciliation_ok: bool
    drift: Decimal


class ImportValidationError(Exception):
    """Any condition that prevents the import from proceeding (maps to HTTP 422)."""

    def __init__(self, error_code: str, detail: str) -> None:
        self.error_code = error_code
        self.detail = detail
        super().__init__(detail)


# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------

_FILENAME_RE = re.compile(r"^\d{8}_([a-z0-9_]+)_([a-z0-9]+)\.csv$", re.IGNORECASE)


def _parse_filename(filename: str) -> tuple[str, str]:
    m = _FILENAME_RE.match(filename)
    if not m:
        raise ImportValidationError(
            "bad_filename",
            f"Filename must be YYYYMMDD_bankcode_accountcode.csv, got: {filename!r}",
        )
    return m.group(1).lower(), m.group(2).lower()


# ---------------------------------------------------------------------------
# Categorisation (private — tested through the integration tests)
# ---------------------------------------------------------------------------


def _categorise(description_raw: str, rules: list[Rule]) -> int | None:
    """First-match-wins substring categorisation. None = Uncategorised."""
    upper = description_raw.upper()
    for rule in rules:
        if rule.match_type == "contains" and rule.match_value.upper() in upper:
            return rule.category_id
    return None


# ---------------------------------------------------------------------------
# Shared private helper — steps 1–4
# ---------------------------------------------------------------------------


def _parse_and_validate(
    db: DBSession,
    *,
    content: str,
    filename: str,
    account_id: UUID | None,
) -> tuple[Account, AdapterResult]:
    """Steps 1–4: account resolution, adapter selection, CSV parse. No DB writes.

    When account_id is provided the filename-parse step is skipped; bank_code is
    read from the account row instead.  Either path produces the same (Account,
    AdapterResult) and raises ImportValidationError on any failure.
    """
    if account_id is not None:
        # Override path: look up account by ID, derive bank_code from the row
        account = db.get(Account, account_id)
        if account is None:
            raise ImportValidationError(
                "unknown_account",
                f"No account found for id={account_id!r}",
            )
        bank_code = account.bank_code
    else:
        # Filename path: parse filename → bank_code + account_code → look up account
        bank_code, account_code = _parse_filename(filename)
        account = (
            db.query(Account)
            .filter_by(bank_code=bank_code, account_code=account_code)
            .first()
        )
        if account is None:
            raise ImportValidationError(
                "unknown_account",
                f"No account found for bank={bank_code!r}, code={account_code!r}",
            )

    try:
        adapter = get_adapter(bank_code)
    except ValueError as exc:
        raise ImportValidationError("unknown_bank", str(exc)) from exc

    try:
        adapter_result = adapter.parse(content, filename)
    except Exception as exc:
        raise ImportValidationError("parse_error", str(exc)) from exc

    return account, adapter_result


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def preview_import(
    db: DBSession,
    *,
    content: str,
    filename: str,
    account_id: UUID | None = None,
) -> PreviewResult:
    """Parse and validate, count duplicates via SELECT, check filename history. No writes."""
    account, adapter_result = _parse_and_validate(
        db, content=content, filename=filename, account_id=account_id
    )

    rows = adapter_result.rows
    rows_found = len(rows)

    if rows_found == 0:
        return PreviewResult(
            account_id=account.id,
            account_display_name=account.display_name,
            bank_code=account.bank_code,
            account_code=account.account_code,
            txn_date_min=None,
            txn_date_max=None,
            rows_found=0,
            rows_to_add=0,
            rows_duplicate=0,
            filename_seen_before=False,
            filename_seen_at=None,
        )

    date_min = min(r.txn_date for r in rows)
    date_max = max(r.txn_date for r in rows)

    existing = {
        (r.txn_date, r.amount, r.description_raw, r.balance)
        for r in db.query(
            Transaction.txn_date,
            Transaction.amount,
            Transaction.description_raw,
            Transaction.balance,
        )
        .filter_by(account_id=account.id)
        .filter(Transaction.txn_date.between(date_min, date_max))
        .all()
    }

    rows_duplicate = sum(
        1
        for row in rows
        if (row.txn_date, row.amount, row.description_raw, row.balance) in existing
    )
    rows_to_add = rows_found - rows_duplicate

    prior = (
        db.query(ImportBatch)
        .filter_by(filename=filename)
        .order_by(ImportBatch.created_at.desc())
        .first()
    )

    return PreviewResult(
        account_id=account.id,
        account_display_name=account.display_name,
        bank_code=account.bank_code,
        account_code=account.account_code,
        txn_date_min=date_min,
        txn_date_max=date_max,
        rows_found=rows_found,
        rows_to_add=rows_to_add,
        rows_duplicate=rows_duplicate,
        filename_seen_before=prior is not None,
        filename_seen_at=prior.created_at if prior is not None else None,
    )


def run_import(
    db: DBSession,
    *,
    content: str,
    filename: str,
    user_id: UUID,
    account_id: UUID | None = None,
) -> ImportResult:
    """Run the full import pipeline in a single DB transaction (no commit here).

    Steps match the spec §Import pipeline exactly. Any failure raises
    ImportValidationError; the caller's exception handler prevents db.commit().
    """
    # 1–4. Parse filename / resolve account / select adapter / parse CSV
    account, adapter_result = _parse_and_validate(
        db, content=content, filename=filename, account_id=account_id
    )

    # 5. Create imports row (counts start at 0; updated in step 8)
    import_batch = ImportBatch(
        user_id=user_id,
        filename=filename,
        bank_code=account.bank_code,
        account_id=account.id,
        rows_added=0,
        rows_skipped=0,
    )
    db.add(import_batch)
    db.flush()

    # 6. Load all rules into memory, sorted by priority ASC, created_at ASC, id ASC
    rules = (
        db.query(Rule)
        .order_by(Rule.priority.asc(), Rule.created_at.asc(), Rule.id.asc())
        .all()
    )

    rows_added = 0
    rows_skipped = 0

    # 7. Process each row
    for row in adapter_result.rows:
        # 7a. Merchant normalisation
        merchant_id = None
        if row.normalised_name_hint is not None:
            normalised_name = row.normalised_name_hint.strip().title()
            merchant = merchants_svc.get_or_create(db, normalised_name)
            merchant_id = merchant.id

        # 7b. First-match categorisation
        category_id = _categorise(row.description_raw, rules)

        # 7c. INSERT ON CONFLICT DO NOTHING — dedupe key enforced by the UNIQUE constraint
        stmt = (
            pg_insert(Transaction)
            .values(
                id=uuid.uuid4(),
                account_id=account.id,
                import_id=import_batch.id,
                txn_date=row.txn_date,
                amount=row.amount,
                description_raw=row.description_raw,
                balance=row.balance,
                merchant_id=merchant_id,
                category_id=category_id,
            )
            .on_conflict_do_nothing(constraint="uq_transactions_dedupe_key")
        )
        result = db.execute(stmt)
        if result.rowcount:
            rows_added += 1
        else:
            rows_skipped += 1

    # 8. Update import batch with final counts
    import_batch.rows_added = rows_added
    import_batch.rows_skipped = rows_skipped
    db.flush()

    # 9. Overwrite current_balance from reported_balance (always — see ADR 3)
    account.current_balance = adapter_result.reported_balance
    if adapter_result.available_balance is not None:
        account.available_balance = adapter_result.available_balance
    db.flush()

    # 10. Reconciliation check
    recon = reconcile(db, account.id)

    # 11. Audit log
    auditing.record(
        db,
        action="import",
        target_type="import",
        target_id=str(import_batch.id),
        user_id=user_id,
        detail={"rows_added": rows_added, "rows_skipped": rows_skipped},
    )

    return ImportResult(
        import_id=import_batch.id,
        rows_added=rows_added,
        rows_skipped=rows_skipped,
        reconciliation_ok=recon.ok,
        drift=recon.drift,
    )
