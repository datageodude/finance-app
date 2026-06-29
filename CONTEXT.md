# Finance App Domain

A self-hosted, family-shared personal finance app. Transactions are imported weekly
from bank CSVs; the app tracks accounts, categorises spending, and flags unusual activity.

## Language

### Core entities

**Transaction**:
A single line from a bank CSV representing money moving into or out of an account.
Sign convention: negative = money out.
_Avoid_: entry, row, record

**Account**:
A bank account tracked in the app. Generic by design — the same model covers
transaction accounts, savings accounts, loans, and credit cards. Type is a property
of the account, not a separate entity.
_Avoid_: bank account (ambiguous)

**Merchant**:
A normalised payee name derived from a transaction's raw description. Underpins both
categorisation and new-merchant flagging. Internal transfers and loan repayments carry
no merchant (`merchant_id = NULL`).
_Avoid_: payee, vendor, supplier

**Category**:
A user-assigned spending label (e.g. Groceries, Fuel). A transaction with no category
is "Uncategorised" — represented as `NULL category_id`, never a special seeded row.
_Avoid_: tag, label, bucket

**Rule**:
A pattern that auto-assigns a category to any transaction whose `description_raw`
matches. First-match-wins; explicit priority determines evaluation order.
_Avoid_: auto-categorisation rule, matching rule

**Flag**:
A signal that a transaction warrants review, generated automatically by the flagging
engine. Three statuses: open (unreviewed), approved (legitimate), dismissed (noise).
_Avoid_: alert, warning, issue

**Import**:
A committed batch of transactions derived from a single CSV file. Recorded in the
`imports` table after the user confirms a preview. The term refers to the committed
result — not the upload act, the preview state, or the file itself.
_Avoid_: upload, batch, transaction set, CSV import

**Audit log**:
An append-only record of every mutating action in the app, attributing it to the user
who performed it. Provenance, not access control.
_Avoid_: activity log, event log, history

### Balances and cash view

**Available Balance**:
The bank's stated accessible amount for an account, sourced from the bank's CSV export
(Bank A's preamble only; Bank B does not provide it). For loan accounts this is the
redraw — extra repayments that can be withdrawn. For transaction/savings accounts it
represents funds after pending holds. Always stored as a positive number; `NULL` when
the bank does not supply it.
_Avoid_: redraw balance, accessible balance, offset (an offset is a separate
transaction/savings account, not a loan redraw)

**Cash Position**:
The headline total shown on the Cash Reserves page. Toggled by the user between two
modes: *cash-only* (sum of transaction and savings `current_balance`) and
*redraw-inclusive* (adds loan `available_balance` to the cash-only total). Defaults to
cash-only. Persisted as a display preference in the browser; not stored server-side.
_Avoid_: balance total, net worth, total balance

**Repayment Progress**:
The proportion of a loan's original principal that has been paid down. Measures
principal reduction only — not time elapsed in the loan term or number of payments
made. Displayed as a progress bar on the Loans page.
_Avoid_: loan progress, payment progress, repayment percentage

**Total Owing**:
The headline figure on the Loans page — the sum of all active loan balances, displayed
as a positive number. The internal `current_balance` for loans is negative (money out);
Total Owing is its absolute value summed across all active loans.
_Avoid_: total debt, total liability, total loan balance

### Import flow

**Preview**:
The intermediate state between uploading a CSV and committing it as an Import. The
backend parses the file and checks for duplicates without writing anything, then
returns: the resolved account, the transaction date range covered, and the counts
(rows found, duplicates skipped, rows to be added). The user reviews a preview before
confirming. A preview showing zero rows to add is not an error — it means the file is
already fully imported.
_Avoid_: dry-run, pre-import, staging, scan

**Filename resolution**:
The process of identifying the bank and account from an uploaded CSV's filename.
Succeeds when the filename matches `YYYYMMDD_bankcode_accountcode.csv` with recognised
codes. When resolution fails (unrecognised code or malformed filename), the user
manually selects the account; the correct filename is then shown as a training hint.
_Avoid_: filename parsing, filename matching

### Flagging engine

**Flagging engine**:
The service (`services/flagging.py`) that evaluates imported transactions against flag
rules and inserts `Flag` rows. Runs as a separate DB transaction after the import
commits — a bug in flagging cannot roll back a successful import. Triggered
automatically after every confirmed import and also callable on demand for backfill.
_Avoid_: flag generator, flag service, alert engine

**Threshold**:
The global minimum debit amount that triggers an `over_threshold` flag. Configured via
the `FLAG_THRESHOLD` environment variable (default: `100.00`). Applies to `transaction`
and `credit` account types only — loan and savings accounts are excluded. A per-merchant
override (see Merchant Threshold Override) takes precedence when set.
_Avoid_: limit, cap, alert threshold

**Merchant Threshold Override**:
A per-merchant custom threshold stored in `merchant_threshold_overrides
(merchant_id, threshold, created_by, created_at)`. When a merchant has an override, the
flagging engine uses it instead of the global threshold for `over_threshold` evaluation.
Set optionally when approving an `over_threshold` flag. Suppresses repeated flags for
large-but-expected recurring charges (e.g. mortgage repayments on a credit account).
_Avoid_: merchant limit, merchant exception, suppression rule

**Double-charge window**:
The maximum number of days between two transactions that may be considered a double
charge. Configured via `DOUBLE_CHARGE_DAYS` (default: `7`). Two transactions must share
the same `merchant_id` (non-NULL) and exact `amount` and fall within this window to
trigger a `double_charge` flag.
_Avoid_: duplicate window, lookback period

**Backfill**:
Running the flagging engine against transactions that were imported before the flagging
engine existed or before a rule was tuned. Triggered via `POST /flags/generate` scoped
to an account. Idempotent: the `UNIQUE (transaction_id, flag_type)` constraint with
`ON CONFLICT DO NOTHING` ensures re-running never creates duplicate flags.
_Avoid_: re-flag, retro-flag, batch flag

### Spend vs Budget

**Budget**:
A monthly spending target for a category. Stored in the `budgets` table as a
`(category_id, valid_from, amount)` row, where `valid_from` is the first day of the
month the budget takes effect. A category may have zero or many budget rows; a category
with no rows has no budget.
_Avoid_: spending limit, target, allowance

**Effective Budget**:
The budget amount that applies to a given month for a given category. Determined by
rollforward: the most recent `budgets` row where `valid_from ≤ first day of that month`.
A category with no prior rows has no effective budget for any month.
_Avoid_: current budget, active budget

**Rollforward**:
The carry-forward rule for budgets: once a budget is set for a category, it remains
the effective budget for every subsequent month until a new budget row supersedes it.
Setting a new budget for July does not affect June. A category with no rows at all has
no effective budget for any month.
_Avoid_: carry-forward, inherit, default

**Monthly Spend**:
The total spending for a category in a given calendar month — the absolute value of the
sum of all negative-amount transactions assigned to that category (and its sub-categories)
in that month. Always a positive number.
_Avoid_: total spend, category spend, spending total

**Expense Category**:
A category that has net-negative transactions in the current month — i.e. a category
that represents money going out. The Spend page shows only expense categories (and
Uncategorised). Categories with net ≥ 0 for the month (Income, Transfers) are excluded
by the net-positive heuristic and do not appear.
_Avoid_: spending category, cost category

### Forecast

**Funds**:
The signed sum of all active account `current_balance` values — transaction and savings
accounts contribute positively; loan and credit accounts contribute negatively (their
balances are stored as negative per the sign convention). The Forecast panel's headline
metric. Shown in the "today" header as a Cash / Loans breakdown with a net total.
_Avoid_: net worth (implies property and investment assets the app doesn't know about),
equity (too formal), cash position (cash-only view on the Cash Reserves page), financial
position (vague)

**Monthly Funds Change**:
The net change in Funds over a single complete calendar month — the signed sum of all
transactions across all active accounts for that month. Principal repayments are naturally
equity-neutral: the cash debit and the matching loan credit cancel to zero. Averaged over
the Forecast Lookback to produce the projection rate.
_Avoid_: savings rate, monthly savings, cash flow (implies cash accounts only)

**Forecast Lookback**:
The 3 most recent complete calendar months used to compute the average Monthly Funds
Change that drives the Forecast. The current (partial) calendar month is always excluded.
When fewer than 3 complete months of transaction data exist, a warning banner is shown
alongside the projection.
_Avoid_: lookback period, historical window, rolling average window

**Forecast Horizon**:
One of three fixed projection windows: 1 month, 6 months, 12 months. Each horizon
card shows: projected Funds at that date, and the delta from today's Funds with a
colour-coded arrow (green ↑ = improving, red ↓ = declining).
_Avoid_: time horizon, projection window, forecast period
