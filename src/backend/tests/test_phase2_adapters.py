"""Phase 2 — adapter unit tests. No DB. Pure CSV parsing.

Tests drive the BankAdapter Protocol and the two concrete adapters into
existence, verifying shape, sign convention, date format, and merchant hint
extraction for each bank format.
"""
import datetime
from decimal import Decimal
from pathlib import Path

from adapters.bank_a import BankAAdapter
from adapters.bank_b import BankBAdapter

_IMPORTS_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "imports"


def _read(filename: str) -> str:
    return (_IMPORTS_DIR / filename).read_text()


# ---------------------------------------------------------------------------
# Bank A — tracer bullet
# ---------------------------------------------------------------------------


class TestBankAAdapter:
    def test_row_count(self):
        result = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv")
        assert len(result.rows) == 43

    def test_reported_balance(self):
        result = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv")
        assert result.reported_balance == Decimal("3988.76")

    def test_first_row_date(self):
        rows = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv").rows
        assert rows[0].txn_date == datetime.date(2023, 12, 3)

    def test_debit_is_negative(self):
        rows = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv").rows
        # First row: -85.40 (POS purchase, money out)
        assert rows[0].amount == Decimal("-85.40")

    def test_credit_is_positive(self):
        rows = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv").rows
        # Second row: +2000.00 (payroll)
        assert rows[1].amount == Decimal("2000.00")

    def test_description_raw_is_reference_stripped(self):
        rows = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv").rows
        assert rows[0].description_raw == "POS (Cr) purchase100021_SAMPLE GROCER *METRO"

    def test_pos_merchant_hint_strips_prefix_and_id(self):
        rows = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv").rows
        # POS (Cr) purchase100021_SAMPLE GROCER *METRO → SAMPLE GROCER *METRO
        assert rows[0].normalised_name_hint == "SAMPLE GROCER *METRO"

    def test_payroll_has_no_merchant_hint(self):
        rows = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv").rows
        # DIRECT CREDIT PAYROLL ACME PTY LTD → internal
        assert rows[1].normalised_name_hint is None

    def test_transfer_has_no_merchant_hint(self):
        rows = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv").rows
        # TRANSFER TO SAVER a2 → internal
        assert rows[2].normalised_name_hint is None

    def test_bpay_merchant_hint_strips_prefix(self):
        rows = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv").rows
        # BPAY SAMPLE POWER UTILITIES → SAMPLE POWER UTILITIES
        assert rows[3].normalised_name_hint == "SAMPLE POWER UTILITIES"

    def test_direct_debit_merchant_hint_strips_prefix(self):
        rows = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv").rows
        # DIRECT DEBIT SAMPLE INSURE → SAMPLE INSURE
        assert rows[4].normalised_name_hint == "SAMPLE INSURE"

    def test_home_loan_has_no_merchant_hint(self):
        rows = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv").rows
        # HOME LOAN REPAYMENT b2 → internal
        assert rows[7].normalised_name_hint is None

    def test_bank_category_is_none(self):
        rows = BankAAdapter().parse(_read("20240229_bank_a_a1.csv"), "20240229_bank_a_a1.csv").rows
        assert rows[0].bank_category is None


# ---------------------------------------------------------------------------
# Bank B
# ---------------------------------------------------------------------------


class TestBankBAdapter:
    def test_row_count(self):
        result = BankBAdapter().parse(_read("20240229_bank_b_b1.csv"), "20240229_bank_b_b1.csv")
        assert len(result.rows) == 15

    def test_reported_balance(self):
        result = BankBAdapter().parse(_read("20240229_bank_b_b1.csv"), "20240229_bank_b_b1.csv")
        assert result.reported_balance == Decimal("565.87")

    def test_first_row_date(self):
        rows = BankBAdapter().parse(_read("20240229_bank_b_b1.csv"), "20240229_bank_b_b1.csv").rows
        assert rows[0].txn_date == datetime.date(2023, 12, 4)

    def test_debit_is_negative(self):
        rows = BankBAdapter().parse(_read("20240229_bank_b_b1.csv"), "20240229_bank_b_b1.csv").rows
        # First row: Debit=72.10 → -72.10
        assert rows[0].amount == Decimal("-72.10")

    def test_description_raw_is_original_description_stripped(self):
        rows = BankBAdapter().parse(_read("20240229_bank_b_b1.csv"), "20240229_bank_b_b1.csv").rows
        # " FRESH MART 0291 SUBURB 02" (leading space) → stripped
        assert rows[0].description_raw == "FRESH MART 0291 SUBURB 02"

    def test_normalised_name_hint_from_details(self):
        rows = BankBAdapter().parse(_read("20240229_bank_b_b1.csv"), "20240229_bank_b_b1.csv").rows
        assert rows[0].normalised_name_hint == "Fresh Mart"

    def test_bank_category_populated_when_present(self):
        rows = BankBAdapter().parse(_read("20240229_bank_b_b1.csv"), "20240229_bank_b_b1.csv").rows
        assert rows[0].bank_category == "Groceries"

    def test_bank_category_none_when_blank(self):
        rows = BankBAdapter().parse(_read("20240229_bank_b_b1.csv"), "20240229_bank_b_b1.csv").rows
        # Row 13 (index): Sample Cafe 21 Feb — Category column is blank
        assert rows[13].bank_category is None
