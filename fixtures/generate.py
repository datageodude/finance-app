#!/usr/bin/env python3
"""Generate the synthetic test corpus for the Finance App.

Deterministic — no randomness, no external dependencies (stdlib only). Re-running
produces byte-identical output. Emits:

  fixtures/imports/*.csv   — bank-format CSVs the import adapters parse
  fixtures/seed/*.json     — account / category / rule metadata not carried in CSVs

Everything here is FABRICATED. No real merchants, balances, accounts, or locations.
See fixtures/README.md for the catalogue of edge cases and expected outcomes.

Run:  python3 fixtures/generate.py
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

TWOPLACES = Decimal("0.01")
HERE = Path(__file__).parent
IMPORTS = HERE / "imports"
SEED = HERE / "seed"

# Statement / export date stamped into the 3-month consolidated filenames.
EXPORT = date(2024, 2, 29)
MONTHS = [date(2023, 12, 1), date(2024, 1, 1), date(2024, 2, 1)]


# ── Accounts ────────────────────────────────────────────────────────────────
@dataclass
class Account:
    code: str
    bank: str                # bank_a | bank_b
    type: str                # transaction | savings | loan | credit
    display_name: str        # internal label
    bank_account_name: str   # string Bank B writes in its "Account" column
    opening_balance: Decimal
    # loan-only metadata (set up in-app, never in a CSV):
    original_amount: Decimal | None = None
    interest_rate: Decimal | None = None  # annual %, for repayment-progress maths
    term_months: int | None = None

ACCOUNTS = [
    Account("a1", "bank_a", "transaction", "Bank A Everyday",
            "Everyday Transaction Account", Decimal("3000.00")),
    Account("a2", "bank_a", "savings", "Bank A Saver",
            "Online Saver Account", Decimal("12000.00")),
    Account("b1", "bank_b", "transaction", "Bank B Everyday",
            "Everyday Transaction Account", Decimal("1500.00")),
    Account("b2", "bank_b", "loan", "Bank B Home Loan",
            "Home Loan Account", Decimal("-350000.00"),
            original_amount=Decimal("360000.00"), interest_rate=Decimal("5.89"),
            term_months=360),
    Account("b3", "bank_b", "credit", "Bank B Credit Card",
            "Platinum Credit Card", Decimal("-800.00")),
]
ACC = {a.code: a for a in ACCOUNTS}


# ── Categories & rules (the app's seed config) ──────────────────────────────
# Monthly budgets let the Spend-vs-budget page show under/over states.
CATEGORIES = [
    {"name": "Income",        "budget": None},
    {"name": "Transfers",     "budget": None},
    {"name": "Groceries",     "budget": "900.00"},
    {"name": "Fuel",          "budget": "260.00"},
    {"name": "Utilities",     "budget": "240.00"},
    {"name": "Insurance",     "budget": "150.00"},
    {"name": "Mortgage",      "budget": "1800.00"},
    {"name": "Dining",        "budget": "200.00"},   # deliberately overspent
    {"name": "Subscriptions", "budget": "40.00"},
    {"name": "Medical",       "budget": "120.00"},
    {"name": "Uncategorised", "budget": None},
]

# Substring (case-insensitive) → category. First match wins.
RULES = [
    ("PAYROLL",        "Income"),
    ("INTEREST PAID",  "Income"),
    ("TRANSFER",       "Transfers"),
    ("SAMPLE GROCER",  "Groceries"),
    ("FRESH MART",     "Groceries"),
    ("SAMPLE FUEL",    "Fuel"),
    ("PETRO",          "Fuel"),
    ("SAMPLE POWER",   "Utilities"),
    ("SAMPLE WATER",   "Utilities"),
    ("SAMPLE INSURE",  "Insurance"),
    ("HOME LOAN",      "Mortgage"),
    ("SAMPLE CAFE",    "Dining"),
    ("SAMPLE DINER",   "Dining"),
    ("SAMPLE STREAM",  "Subscriptions"),
    ("SAMPLE MUSIC",   "Subscriptions"),
    ("SAMPLE PHARMACY", "Medical"),
    ("SAMPLE MEDICAL", "Medical"),
    ("SAMPLE VETCARE", "Medical"),
]

def categorise(text: str) -> str:
    up = text.upper()
    for needle, cat in RULES:
        if needle in up:
            return cat
    return "Uncategorised"


# ── Transactions ────────────────────────────────────────────────────────────
@dataclass
class Txn:
    account: str
    day: date
    amount: Decimal          # signed; negative = money out
    raw: str                 # Bank A "Reference" / Bank B "Original Description"
    details: str             # Bank B clean "Details"
    edge: str = ""           # tag for the README catalogue / expected outcomes

EVENTS: list[Txn] = []

def add(account, day, amount, raw, details, edge=""):
    EVENTS.append(Txn(account, day, Decimal(amount), raw, details, edge))

def d(m: date, day: int) -> date:
    return m.replace(day=day)

# Recurring monthly pattern across all three months.
for i, m in enumerate(MONTHS):
    # a1 — main everyday account ------------------------------------------------
    add("a1", d(m, 5),  "2000.00", "DIRECT CREDIT PAYROLL ACME PTY LTD", "Payroll Acme")
    add("a1", d(m, 19), "2000.00", "DIRECT CREDIT PAYROLL ACME PTY LTD", "Payroll Acme")
    add("a1", d(m, 6),  "-800.00", "TRANSFER TO SAVER a2", "Transfer to Saver")
    add("a1", d(m, 15), "-1800.00", "HOME LOAN REPAYMENT b2", "Home Loan Repayment",
        edge="over-100")
    add("a1", d(m, 8),  "-220.50", "BPAY SAMPLE POWER UTILITIES", "Sample Power",
        edge="over-100")
    add("a1", d(m, 10), "-130.00", "DIRECT DEBIT SAMPLE INSURE", "Sample Insure",
        edge="over-100")
    add("a1", d(m, 3),  "-85.40", "POS (Cr) purchase100021_SAMPLE GROCER *METRO", "Sample Grocer")
    add("a1", d(m, 17), "-101.20", "POS (Cr) purchase100022_SAMPLE GROCER *METRO", "Sample Grocer",
        edge="over-100")
    add("a1", d(m, 12), "-65.00", "POS (Cr) purchase100031_SAMPLE FUEL *PAY AT PUMP", "Sample Fuel")
    add("a1", d(m, 24), "-45.00", "POS (Cr) purchase100041_SAMPLE CAFE *CBD", "Sample Cafe")
    add("a1", d(m, 14), "-11.99", "DIRECT DEBIT SAMPLE MUSIC", "Sample Music")
    add("a1", d(m, 28), "-300.00", "PAYMENT TO CREDIT CARD b3", "Payment to Credit Card")
    # subscription price jump (recurring-change / v1.5): 9.99 → 9.99 → 14.99
    sub = "9.99" if i < 2 else "14.99"
    add("a1", d(m, 21), f"-{sub}", "DIRECT DEBIT SAMPLE STREAM PLUS", "Sample Stream Plus",
        edge="price-jump" if i == 2 else "")

    # a2 — savings (transfers in + interest) — feeds the forecast slope ----------
    add("a2", d(m, 6),  "800.00", "TRANSFER FROM EVERYDAY a1", "Transfer from Everyday")
    add("a2", d(m, 28), "15.30", "INTEREST PAID", "Interest Paid")

    # b1 — partner everyday (Bank B format) -------------------------------------
    add("b1", d(m, 4),  "-72.10", "FRESH MART 0291 SUBURB 02", "Fresh Mart")
    add("b1", d(m, 18), "-110.45", "FRESH MART 0291 SUBURB 02", "Fresh Mart", edge="over-100")
    add("b1", d(m, 9),  "-52.00", "SAMPLE DINER 7781 SUBURB 11", "Sample Diner")
    add("b1", d(m, 22), "-60.00", "PETRO 5540 SUBURB 04", "Petro")

    # b2 — home loan: interest charged, repayment received ----------------------
    add("b2", d(m, 15), "-1718.00", "INTEREST CHARGE HOME LOAN", "Interest Charge")
    add("b2", d(m, 15), "1800.00", "HOME LOAN REPAYMENT RECEIVED", "Home Loan Repayment")

    # b3 — credit card: purchases + the monthly payment from a1 ------------------
    add("b3", d(m, 7),  "-75.00", "SAMPLE CLOTHING 3320 SUBURB 09", "Sample Clothing")
    add("b3", d(m, 20), "-32.00", "SAMPLE BOOKS 1190 SUBURB 06", "Sample Books")
    add("b3", d(m, 28), "300.00", "PAYMENT RECEIVED THANK YOU", "Payment Received")

# One-off edge cases (placed on specific dates) -------------------------------
# Refund (positive amount on a spending account)
add("a1", date(2024, 1, 23), "45.00", "REFUND SAMPLE RETAILER", "Sample Retailer Refund",
    edge="refund")
# Big medical (over-100) in January
add("a1", date(2024, 1, 11), "-189.00", "EFTPOS SAMPLE MEDICAL CLINIC", "Sample Medical Clinic",
    edge="over-100")
# Uncategorised — no rule matches
add("a1", date(2024, 2, 13), "-60.00", "DIRECT DEBIT ABC123 UNKNOWN PAYEE", "Abc123 Unknown Payee",
    edge="uncategorised")
# New merchant — first ever appearance, in February
add("a1", date(2024, 2, 26), "-95.00", "EFTPOS SAMPLE VETCARE", "Sample Vetcare",
    edge="new-merchant")
# Double charge on b1 (under $100): two identical streaming debits 2 days apart
add("b1", date(2024, 1, 14), "-15.99", "SAMPLE STREAMING 0001 SUBURB 00", "Sample Streaming",
    edge="double-charge")
add("b1", date(2024, 1, 16), "-15.99", "SAMPLE STREAMING 0001 SUBURB 00", "Sample Streaming",
    edge="double-charge")
# Double charge on b3 (over $100): two identical electronics purchases 1 day apart
add("b3", date(2024, 2, 9),  "-129.00", "SAMPLE ELECTRONICS 8800 SUBURB 03", "Sample Electronics",
    edge="double-charge,over-100")
add("b3", date(2024, 2, 10), "-129.00", "SAMPLE ELECTRONICS 8800 SUBURB 03", "Sample Electronics",
    edge="double-charge,over-100")
# Blank bank-category on b1 (tests our own categoriser when Bank B leaves it empty)
add("b1", date(2024, 2, 21), "-18.50", "SAMPLE CAFE 7781 SUBURB 11", "Sample Cafe",
    edge="blank-bank-category")


# ── Writers ─────────────────────────────────────────────────────────────────
def money(x: Decimal) -> str:
    return str(x.quantize(TWOPLACES))

def fmt_a(day: date) -> str:    # Bank A: DD/MM/YYYY
    return day.strftime("%d/%m/%Y")

def fmt_b(day: date) -> str:    # Bank B: DD Mon YYYY
    return day.strftime("%d %b %Y")

def running(txns: list[Txn], opening: Decimal) -> list[tuple[Txn, Decimal]]:
    bal = opening
    out = []
    for t in sorted(txns, key=lambda x: (x.day, x.raw)):
        bal = (bal + t.amount).quantize(TWOPLACES)
        out.append((t, bal))
    return out

def write_bank_a(acc: Account, rows: list[tuple[Txn, Decimal]], path: Path):
    # Two preamble balance lines, header on line 3 (leading spaces), then rows.
    final = rows[-1][1]
    stamp = fmt_a(rows[-1][0].day)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([stamp, "Balance", money(final), f"Current Balance for account {acc.code.upper()}"])
        w.writerow([stamp, "Balance", money(final), f"Available Balance for account {acc.code.upper()}"])
        w.writerow(["Transaction Date", " Amount", " Reference", " Balance"])
        for t, bal in rows:
            w.writerow([fmt_a(t.day), money(t.amount), t.raw, money(bal)])

def write_bank_b(acc: Account, rows: list[tuple[Txn, Decimal]], path: Path):
    header = ["Transaction Date", "Details", "Account", "Category", "Subcategory",
              "Tags", "Notes", "Debit", "Credit", "Balance", "Original Description"]
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for t, bal in rows:
            debit = money(-t.amount) if t.amount < 0 else ""
            credit = money(t.amount) if t.amount > 0 else ""
            # Bank B supplies a category, except where we deliberately blank it.
            if "blank-bank-category" in t.edge:
                cat = sub = ""
            else:
                cat = categorise(t.raw)
                sub = cat
            w.writerow([fmt_b(t.day), t.details, acc.bank_account_name, cat, sub,
                        "", "", debit, credit, money(bal), " " + t.raw])


# ── Recent fixtures (March–May 2026) ────────────────────────────────────────
# Used to populate the Forecast tab with 3 complete months of history.
# Import these via the Import tab after seeding accounts/categories/rules.
RECENT_EXPORT = date(2026, 5, 31)
RECENT_MONTHS = [date(2026, 3, 1), date(2026, 4, 1), date(2026, 5, 1)]

# Approximate account balances at the start of March 2026 (~26 months on from
# the 2024 corpus at the same recurring rates).
RECENT_OPENING: dict[str, Decimal] = {
    "a1": Decimal("7200.00"),
    "a2": Decimal("32000.00"),
    "b1": Decimal("1500.00"),
    "b2": Decimal("-347000.00"),
    "b3": Decimal("-600.00"),
}

RECENT_EVENTS: list[Txn] = []


def add_r(account: str, day: date, amount: str, raw: str, details: str, edge: str = "") -> None:
    RECENT_EVENTS.append(Txn(account, day, Decimal(amount), raw, details, edge))


for m in RECENT_MONTHS:
    # a1 — main everyday account
    add_r("a1", d(m, 5),  "2000.00", "DIRECT CREDIT PAYROLL ACME PTY LTD", "Payroll Acme")
    add_r("a1", d(m, 19), "2000.00", "DIRECT CREDIT PAYROLL ACME PTY LTD", "Payroll Acme")
    add_r("a1", d(m, 6),  "-800.00", "TRANSFER TO SAVER a2", "Transfer to Saver")
    add_r("a1", d(m, 15), "-1800.00", "HOME LOAN REPAYMENT b2", "Home Loan Repayment")
    add_r("a1", d(m, 8),  "-220.50", "BPAY SAMPLE POWER UTILITIES", "Sample Power")
    add_r("a1", d(m, 10), "-130.00", "DIRECT DEBIT SAMPLE INSURE", "Sample Insure")
    add_r("a1", d(m, 3),  "-85.40", "POS (Cr) purchase100021_SAMPLE GROCER *METRO", "Sample Grocer")
    add_r("a1", d(m, 17), "-101.20", "POS (Cr) purchase100022_SAMPLE GROCER *METRO", "Sample Grocer")
    add_r("a1", d(m, 12), "-65.00", "POS (Cr) purchase100031_SAMPLE FUEL *PAY AT PUMP", "Sample Fuel")
    add_r("a1", d(m, 24), "-45.00", "POS (Cr) purchase100041_SAMPLE CAFE *CBD", "Sample Cafe")
    add_r("a1", d(m, 14), "-14.99", "DIRECT DEBIT SAMPLE MUSIC", "Sample Music")
    add_r("a1", d(m, 21), "-14.99", "DIRECT DEBIT SAMPLE STREAM PLUS", "Sample Stream Plus")
    add_r("a1", d(m, 28), "-300.00", "PAYMENT TO CREDIT CARD b3", "Payment to Credit Card")

    # a2 — savings
    add_r("a2", d(m, 6),  "800.00", "TRANSFER FROM EVERYDAY a1", "Transfer from Everyday")
    add_r("a2", d(m, 28), "18.50", "INTEREST PAID", "Interest Paid")

    # b1 — partner everyday (Bank B format)
    add_r("b1", d(m, 4),  "-72.10", "FRESH MART 0291 SUBURB 02", "Fresh Mart")
    add_r("b1", d(m, 18), "-110.45", "FRESH MART 0291 SUBURB 02", "Fresh Mart")
    add_r("b1", d(m, 9),  "-52.00", "SAMPLE DINER 7781 SUBURB 11", "Sample Diner")
    add_r("b1", d(m, 22), "-60.00", "PETRO 5540 SUBURB 04", "Petro")

    # b2 — home loan
    add_r("b2", d(m, 15), "-1718.00", "INTEREST CHARGE HOME LOAN", "Interest Charge")
    add_r("b2", d(m, 15), "1800.00", "HOME LOAN REPAYMENT RECEIVED", "Home Loan Repayment")

    # b3 — credit card
    add_r("b3", d(m, 7),  "-75.00", "SAMPLE CLOTHING 3320 SUBURB 09", "Sample Clothing")
    add_r("b3", d(m, 20), "-32.00", "SAMPLE BOOKS 1190 SUBURB 06", "Sample Books")
    add_r("b3", d(m, 28), "300.00", "PAYMENT RECEIVED THANK YOU", "Payment Received")


def _generate_recent_fixtures(imports_dir: Path) -> list[str]:
    summary: list[str] = []
    for acc in ACCOUNTS:
        txns = [t for t in RECENT_EVENTS if t.account == acc.code]
        rows = running(txns, RECENT_OPENING[acc.code])
        fname = f"{RECENT_EXPORT.strftime('%Y%m%d')}_{acc.bank}_{acc.code}.csv"
        path = imports_dir / fname
        (write_bank_a if acc.bank == "bank_a" else write_bank_b)(acc, rows, path)
        summary.append(f"{fname}: {len(rows)} rows, closing balance {money(rows[-1][1])}")
    return summary


# ── Build ───────────────────────────────────────────────────────────────────
def main() -> None:
    IMPORTS.mkdir(parents=True, exist_ok=True)
    SEED.mkdir(parents=True, exist_ok=True)

    summary: list[str] = []
    for acc in ACCOUNTS:
        txns = [t for t in EVENTS if t.account == acc.code]
        rows = running(txns, acc.opening_balance)
        fname = f"{EXPORT.strftime('%Y%m%d')}_{acc.bank}_{acc.code}.csv"
        path = IMPORTS / fname
        (write_bank_a if acc.bank == "bank_a" else write_bank_b)(acc, rows, path)
        summary.append(f"{fname}: {len(rows)} rows, closing balance {money(rows[-1][1])}")

    # Overlap file for partial-dedupe testing: last 3 Feb a1 rows + 2 new March rows.
    a1 = [t for t in EVENTS if t.account == "a1"]
    a1_rows = running(a1, ACC["a1"].opening_balance)
    tail = a1_rows[-3:]
    march = [
        (Txn("a1", date(2024, 3, 5), Decimal("2000.00"),
             "DIRECT CREDIT PAYROLL ACME PTY LTD", "Payroll Acme"), None),
        (Txn("a1", date(2024, 3, 6), Decimal("-800.00"),
             "TRANSFER TO SAVER a2", "Transfer to Saver"), None),
    ]
    bal = tail[-1][1]
    overlap_rows = list(tail)
    for t, _ in march:
        bal = (bal + t.amount).quantize(TWOPLACES)
        overlap_rows.append((t, bal))
    opath = IMPORTS / "20240307_bank_a_a1.csv"
    write_bank_a(ACC["a1"], overlap_rows, opath)
    summary.append(f"{opath.name}: {len(overlap_rows)} rows "
                   f"(3 overlap + 2 new → re-import adds only 2)")

    # Seed metadata (not carried in any CSV).
    accounts_json = [{
        "code": a.code, "bank": a.bank, "type": a.type,
        "display_name": a.display_name, "bank_account_name": a.bank_account_name,
        "opening_balance": money(a.opening_balance),
        **({"original_amount": money(a.original_amount),
            "interest_rate": str(a.interest_rate), "term_months": a.term_months}
           if a.type == "loan" else {}),
    } for a in ACCOUNTS]
    (SEED / "accounts.json").write_text(json.dumps(accounts_json, indent=2) + "\n")
    (SEED / "categories.json").write_text(json.dumps(CATEGORIES, indent=2) + "\n")
    (SEED / "rules.json").write_text(json.dumps(
        [{"match": n, "category": c} for n, c in RULES], indent=2) + "\n")

    recent_summary = _generate_recent_fixtures(IMPORTS)

    print("Generated:")
    for line in summary:
        print("  " + line)
    print(f"  seed/accounts.json, seed/categories.json ({len(CATEGORIES)}), "
          f"seed/rules.json ({len(RULES)})")
    print("Recent fixtures (import these to populate the Forecast tab):")
    for line in recent_summary:
        print("  " + line)


if __name__ == "__main__":
    main()
