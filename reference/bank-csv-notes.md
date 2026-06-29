# Bank CSV notes

The real export shapes, confirmed from template files (`bank_a.csv`, `bank_b.csv` in
this folder). This is the CSV homework that gated Phases 1–2. The per-bank **adapters**
([../src/CONTEXT.md](../src/CONTEXT.md)) are built against these shapes — one per bank,
because the two are very different.

> **Synthetic samples.** The values in `bank_a.csv` / `bank_b.csv` (and quoted below)
> are fabricated — fake merchants, round balances, no real account numbers or locations —
> so this folder is safe in a public repo. Only the *format* is real. They don't follow
> the `YYYYMMDD_bankcode_accountcode.csv` filename convention (that's for actual
> imports). Re-confirm against a real export privately before trusting edge cases.

## Side by side

| | **Bank A** (`bank_a`) | **Bank B** (`bank_b`) |
|---|---|---|
| **Header location** | Line **3** — two balance *preamble* rows sit above it | Line 1 (clean) |
| **Columns** | `Transaction Date, Amount, Reference, Balance` (leading spaces in names) | `Transaction Date, Details, Account, Category, Subcategory, Tags, Notes, Debit, Credit, Balance, Original Description` |
| **Date format** | `DD/MM/YYYY` (`01/02/2024`) | `DD Mon YYYY` (`01 Feb 2024`) |
| **Time field** | **None** — date only | **None** — date only |
| **Amount** | Single **signed** column (`-9.99` = money out) | **Split** `Debit` / `Credit`, both positive |
| **Description** | One messy field (`POS (Cr) purchase000000_EXAMPLE *SAMPLE SUBSCR`) | Clean `Details` **+** raw `Original Description` (leading space) |
| **Account id** | Only in preamble text ("for account A1") | Full name string per row (e.g. "Everyday Transaction Account") |
| **Extra data** | Preamble carries Current + Available balance | Bank-supplied `Category` / `Subcategory` |

## Bank A adapter rules

- **Skip the preamble.** Lines above the real header are balance rows
  (`…,Balance,1000.00,Current Balance for account A1` /
  `…,Available Balance…`). Find the header row (`Transaction Date, Amount, …`),
  parse from there. Don't assume it's line 3 — match on the header, not a line number.
- **Capture the preamble balance.** Current + Available balance are the input the
  stored-vs-derived balance reconciliation wants (see TODO open item).
- **Strip whitespace** from column names (` Amount`, ` Reference`, ` Balance`).
- **Amount is already signed**, negative = money out → maps straight to the internal
  convention. No conversion.
- **Date** `DD/MM/YYYY` → `date`.
- **Account** isn't reliably in the rows ("A1" only in preamble) → take it from the
  filename convention; dropdown fallback if unclear.

## Bank B adapter rules

- **Header on line 1**, no preamble.
- **Convert Debit/Credit → signed amount.** A value in `Debit` is money out → negative;
  a value in `Credit` is money in → positive. Exactly one is populated per row.
- **Date** `DD Mon YYYY` → `date`.
- **Description**: prefer `Original Description` as `description_raw` (the bank's own
  truth); `Details` is already cleaned and can seed merchant normalisation.
- **Bank category**: `Category`/`Subcategory` are provided. Treat as a *suggestion* to
  seed the categoriser, **not** as truth — keep our own categorisation authoritative so
  it's consistent across both banks. (Decision to confirm.)
- **Account** is a full name string per row → still prefer the filename for the clean
  `accountcode`; the name is a cross-check.

## Cross-cutting findings

- **No time data anywhere.** Both banks are date-only. The Phase 5 "unusual timing"
  flag has no data to run on → **dropped from v1** (formally removed from PLAN.md, not
  left half-promised). "Unusual location" was already infeasible. Flagging is therefore
  amount-threshold + dedupe + new-merchant based.
- **No unique bank txn id** in either export → the dedupe key is a composite `UNIQUE`
  constraint on `(account_id, txn_date, amount, description_raw, balance)` — no hash.
  The running `Balance` column is a full member of the key, making legitimate same-day
  same-amount repeats (e.g. two identical coffees) distinguishable.
- **The two shapes justify the per-bank adapter design** — different header position,
  different date format, signed vs split amounts, different description quality.
