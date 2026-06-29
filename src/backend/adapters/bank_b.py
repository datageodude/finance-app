"""Bank B CSV adapter.

Format (confirmed from reference/bank-csv-notes.md):
  Header on line 1 (clean, no preamble):
    Transaction Date, Details, Account, Category, Subcategory,
    Tags, Notes, Debit, Credit, Balance, Original Description
  Date:        DD Mon YYYY  (e.g. "04 Dec 2023")
  Amount:      split Debit / Credit (both positive); Debit → negative, Credit → positive
  description_raw: Original Description column, stripped (has a leading space in raw CSV)
  normalised_name_hint: Details column (already cleaned by the bank)
  bank_category: Category column or None when blank
  reported_balance: last data row's Balance

Internal transfers are detected from the Original Description using the same
marker patterns as Bank A (TRANSFER, HOME LOAN REPAYMENT, PAYROLL, …).
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


class BankBAdapter:
    def parse(self, content: str, filename: str) -> AdapterResult:
        reader = csv.reader(io.StringIO(content))
        all_rows = list(reader)
        if not all_rows:
            raise ValueError("Bank B CSV: file is empty")

        header = [c.strip() for c in all_rows[0]]
        col = {name: idx for idx, name in enumerate(header)}

        rows: list[ParsedRow] = []
        last_balance = Decimal("0")

        for row in all_rows[1:]:
            stripped = [c.strip() for c in row]
            if not any(stripped):
                continue

            txn_date = datetime.strptime(stripped[col["Transaction Date"]], "%d %b %Y").date()

            debit = stripped[col["Debit"]]
            credit = stripped[col["Credit"]]
            if debit:
                amount = -Decimal(debit)
            elif credit:
                amount = Decimal(credit)
            else:
                raise ValueError(f"Bank B CSV: row has neither Debit nor Credit: {row}")

            balance = Decimal(stripped[col["Balance"]])
            last_balance = balance

            orig_desc = stripped[col["Original Description"]]
            description_raw = orig_desc.strip()

            details = stripped[col["Details"]]
            bank_category = stripped[col["Category"]] or None

            if _INTERNAL_RE.search(description_raw):
                normalised_name_hint = None
            else:
                normalised_name_hint = details.strip() or None

            rows.append(ParsedRow(
                txn_date=txn_date,
                amount=amount,
                description_raw=description_raw,
                balance=balance,
                normalised_name_hint=normalised_name_hint,
                bank_category=bank_category,
            ))

        return AdapterResult(rows=rows, reported_balance=last_balance)
