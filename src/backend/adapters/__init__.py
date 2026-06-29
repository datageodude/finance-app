"""Adapter layer — bank-specific CSV parsers and their shared contract.

Every adapter implements BankAdapter and returns an AdapterResult whose rows
all conform to ParsedRow. Adding a new bank = one adapter file + one line in
get_adapter().
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass
class ParsedRow:
    txn_date: date
    amount: Decimal          # signed; negative = money out
    description_raw: str     # bank's raw text, whitespace-stripped; feeds dedupe key
    balance: Decimal
    normalised_name_hint: str | None  # adapter's best merchant-name guess; None = internal
    bank_category: str | None         # bank-supplied category (Bank B only); engine ignores in v1


@dataclass
class AdapterResult:
    rows: list[ParsedRow]
    reported_balance: Decimal  # bank's stated balance after the last transaction row
    available_balance: Decimal | None = None  # bank's stated available balance (e.g. loan redraw); always positive


class BankAdapter(Protocol):
    def parse(self, content: str, filename: str) -> AdapterResult: ...


def get_adapter(bank_code: str) -> BankAdapter:
    """Return an instantiated adapter for bank_code; raise ValueError on unknown bank."""
    from adapters.bank_a import BankAAdapter
    from adapters.bank_b import BankBAdapter

    registry: dict[str, type] = {
        "bank_a": BankAAdapter,
        "bank_b": BankBAdapter,
    }
    cls = registry.get(bank_code)
    if cls is None:
        raise ValueError(f"No adapter registered for bank: {bank_code!r}")
    return cls()
