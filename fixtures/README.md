# Test fixtures — synthetic corpus

A deliberately-designed dataset for building and testing the app. **Everything here is
fabricated** (fake merchants, round-ish balances, no real accounts or locations), so it
lives safely in the public repo — see [../docs/data-handling.md](../docs/data-handling.md).
It's the allow-listed exception to the "ignore every CSV" rule in [`.gitignore`](../.gitignore).

Regenerate anytime (deterministic, stdlib-only, no deps):

```bash
python3 fixtures/generate.py
```

## Layout

| Path | What |
|------|------|
| `generate.py` | The generator — single source of truth for the corpus. |
| `imports/*.csv` | Bank-format CSVs the import adapters parse (the data you "drag in"). |
| `seed/accounts.json` | Accounts and their metadata (type, loan rate/term) — *not* carried in any CSV; set up in-app. |
| `seed/categories.json` | Category starter list + monthly budgets. |
| `seed/rules.json` | Auto-categorisation rules (description substring → category). |

## Accounts (covers all four `type`s, both banks, both formats)

| Code | Bank / format | Type | Role |
|------|---------------|------|------|
| `a1` | Bank A (signed, preamble, `DD/MM/YYYY`) | transaction | Main everyday — salary in, bills out, most edge cases |
| `a2` | Bank A | savings | Transfers in + interest — drives the forecast slope |
| `b1` | Bank B (debit/credit split, `DD Mon YYYY`) | transaction | Partner's everyday — exercises the Bank B adapter |
| `b2` | Bank B | loan | Home loan — repayment + interest, repayment-progress maths |
| `b3` | Bank B | credit | Credit card — purchases + payment, balance owing |

3 months of history (Dec 2023 – Feb 2024) so the forecast and recurring-payment logic
have a trend to work with.

## Import files

| File | Use |
|------|-----|
| `20240229_bank_a_a1.csv` … `_b3.csv` | The five accounts, full 3-month history. |
| `20240307_bank_a_a1.csv` | **Partial-overlap** re-export: last 3 Feb rows of `a1` + 2 new March rows. |

## Edge cases → what each one tests → expected outcome

### Import & adapters (Phase 2)
- **Two formats.** Bank A: balance preamble rows above a header on line 3, leading
  spaces in column names, single signed `Amount`, `DD/MM/YYYY`. Bank B: header on line 1,
  split `Debit`/`Credit`, clean `Details` + raw `Original Description` (leading space),
  `DD Mon YYYY`. → *Each adapter maps its format to the same internal shape.*
- **Sign convention.** Bank A is natively signed (negative = out); Bank B's adapter must
  convert debit→negative, credit→positive. → *All amounts land as negative = money out.*
- **Filename parsing.** `YYYYMMDD_bankcode_accountcode.csv`. → *bank + account inferred
  from the name.*
- **Running balances reconcile.** Every file's `Balance` column is internally consistent
  with `opening_balance` (in `seed/accounts.json`) + the transactions. → *stored-vs-derived
  balance check passes; Bank A preamble Current/Available match the final row.*

### Dedupe / idempotency (Phase 2)
- **Re-import the same file** → **0 new rows** (dedupe key = `account_id + txn_date + amount + description_raw + balance` composite UNIQUE constraint).
- **`20240307_bank_a_a1.csv`** after the Feb file → **adds exactly 2 rows** (the 3
  overlapping Feb rows are recognised as duplicates, the 2 March rows are new).

### Categorisation (Phase 2 / 6)
- Rules in `seed/rules.json` auto-categorise most rows (Groceries, Fuel, Utilities,
  Insurance, Mortgage, Dining, Subscriptions, Medical, Income, Transfers).
- **Uncategorised:** `ABC123 UNKNOWN PAYEE` (a1, 13 Feb) matches no rule → **stays
  Uncategorised** → exercises the manual-clear → offer-to-create-rule loop.
- **Bank-supplied category:** Bank B rows carry `Category`/`Subcategory`. One b1 row
  (`Sample Cafe`, 21 Feb) has them **blank** → tests our own categoriser when the bank
  gives nothing, and the "use bank category as a *suggestion* only" decision.

### Flagging engine (Phase 5)
| Rule | Seeded by | Expect to flag |
|------|-----------|----------------|
| Over $100 (configurable) | Mortgage 1800, Utilities 220.50, Insurance 130, Medical 189, one Groceries 101.20, Fresh Mart 110.45, the two Electronics 129 | each debit > $100 (not income credits) |
| Double charge (same amount + merchant within N days) | `Sample Streaming` 15.99 ×2 (b1, 14 & 16 Jan); `Sample Electronics` 129.00 ×2 (b3, 9 & 10 Feb) | both pairs |
| New merchant | `Sample Vetcare` (a1, 26 Feb) — first ever appearance | the Vetcare row |
| Change in regular payment *(v1.5)* | `Sample Stream Plus` 9.99 (Dec, Jan) → 14.99 (Feb) | the Feb amount shift, once recurring is detected |

> The dropped flags have **no data on purpose**: there is no time column anywhere
> (timing flag) and no location field (location flag). See
> [../reference/bank-csv-notes.md](../reference/bank-csv-notes.md).

### Viewing pages (Phase 4)
- **Cash reserves:** positive balances on `a1`/`a2`/`b1`; total + per-account.
- **Spend vs budget:** spend spread across categories vs `seed/categories.json` budgets;
  **Dining is deliberately over budget** ($200 budget, ~$255 spent over 3 months).
- **Loans:** `b2` shows principal moving from −350,000 toward 0 (repayment 1,800 −
  interest 1,718 = 82/mo); `original_amount`, `interest_rate`, `term_months` in the seed
  drive repayment-progress.
- **Forecast:** `a2` rises a steady ~815/mo (transfer + interest) and `a1` runs a monthly
  surplus → a non-trivial upward slope for the 1/6/12-month projection.

### Income & refunds
- **Income:** fortnightly `PAYROLL` credits on `a1` → income-vs-outflows is visible.
- **Refund:** a positive `REFUND SAMPLE RETAILER` (+45, a1, 23 Jan) → a credit on a
  spending account (not all positives are income).

## Changing the corpus

Edit `generate.py` and re-run. Keep it **synthetic** — no real values, ever. If you add a
new edge case, note it here with its expected outcome so the tests stay meaningful.
