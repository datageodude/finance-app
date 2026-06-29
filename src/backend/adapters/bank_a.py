"""Bank A CSV adapter.

Format (confirmed from reference/bank-csv-notes.md):
  Lines 1-N:  preamble balance rows (date, "Balance", amount, label)
  Line N+1:   header — "Transaction Date, Amount, Reference, Balance"
               (leading spaces on non-first column names; stripped by adapter)
  Data rows:  DD/MM/YYYY, signed amount, description, running balance

The Current Balance is in the first preamble row where the label contains
"Current". Amount is already signed (negative = money out).

Merchant hint strategy:
  - Internal transfers (TRANSFER, HOME LOAN REPAYMENT, PAYROLL,
    PAYMENT TO CREDIT CARD) → None
  - POS: strip "POS (Cr) purchase{digits}_" prefix
  - Other known prefixes (BPAY, DIRECT DEBIT, EFTPOS, REFUND): strip prefix
  - Anything else: use the full description as the hint
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from decimal import Decimal

from adapters import AdapterResult, ParsedRow

_INTERNAL_RE = re.compile(
    r"TRANSFER|HOME\s+LOAN\s+REPAYMENT|PAYROLL|PAYMENT\s+TO\s+CREDIT\s+CARD",
    re.IGNORECASE,
)
_POS_RE = re.compile(r"^POS\s+\(Cr\)\s+purchase\d+_(.+)$", re.IGNORECASE)
_PREFIX_RE = re.compile(
    r"^(?:BPAY\s+|DIRECT\s+DEBIT\s+|EFTPOS\s+|REFUND\s+)(.+)$",
    re.IGNORECASE,
)


def _merchant_hint(reference: str) -> str | None:
    if _INTERNAL_RE.search(reference):
        return None
    m = _POS_RE.match(reference)
    if m:
        return m.group(1).strip() or None
    m = _PREFIX_RE.match(reference)
    if m:
        return m.group(1).strip() or None
    return reference.strip() or None


class BankAAdapter:
    def parse(self, content: str, filename: str) -> AdapterResult:
        reader = csv.reader(io.StringIO(content))
        all_rows = list(reader)

        reported_balance = Decimal("0")
        available_balance: Decimal | None = None
        header_idx = -1

        for i, row in enumerate(all_rows):
            stripped = [c.strip() for c in row]
            if not any(stripped):
                continue
            # Preamble row: [date, "Balance", amount, label]
            if len(stripped) >= 4 and stripped[1] == "Balance":
                if reported_balance == Decimal("0") and "Current" in stripped[3]:
                    reported_balance = Decimal(stripped[2])
                if available_balance is None and "Available" in stripped[3]:
                    available_balance = Decimal(stripped[2])
            # Header row: first cell is "Transaction Date"
            if stripped[0] == "Transaction Date":
                header_idx = i
                break

        if header_idx == -1:
            raise ValueError("Bank A CSV: could not find 'Transaction Date' header row")

        header = [c.strip() for c in all_rows[header_idx]]
        col = {name: idx for idx, name in enumerate(header)}

        rows: list[ParsedRow] = []
        for row in all_rows[header_idx + 1:]:
            stripped_row = [c.strip() for c in row]
            if not any(stripped_row):
                continue
            if len(stripped_row) <= max(col.values()):
                continue
            txn_date = datetime.strptime(stripped_row[col["Transaction Date"]], "%d/%m/%Y").date()
            amount = Decimal(stripped_row[col["Amount"]])
            description_raw = stripped_row[col["Reference"]]
            balance = Decimal(stripped_row[col["Balance"]])
            rows.append(ParsedRow(
                txn_date=txn_date,
                amount=amount,
                description_raw=description_raw,
                balance=balance,
                normalised_name_hint=_merchant_hint(description_raw),
                bank_category=None,
            ))

        return AdapterResult(rows=rows, reported_balance=reported_balance, available_balance=available_balance)
