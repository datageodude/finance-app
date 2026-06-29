# Phase 4 Spend vs Budget — Decisions

**Date:** 2026-06-29
**Status:** Accepted
**Gate:** Output of the `grilling` + `domain-modeling` skills on the Phase-4 Spend vs
Budget panel. Next gate before code: `codebase-design`.

Two decisions that are hard to reverse, surprising without context, and the result of
a real trade-off.

---

## 1. Budgets are stored in a separate `budgets` table, not as a column on `categories`

**Decision:** Budget amounts live in a new `budgets` table:
`(id, category_id, valid_from date, amount money_amount, created_by, created_at)`.
`valid_from` is always the first day of the month (`CHECK (EXTRACT(day FROM valid_from) = 1)`).
`UNIQUE (category_id, valid_from)` — one budget per category per month.
The `categories` table gains no new column.

**Why:** A `budget` column on `categories` would mean one budget amount per category,
ever. The household explicitly wants per-month budget history — the ability to look back
and see what was budgeted in a given month, and to change budgets over time without
losing the past. A column cannot represent this; a table can.

**Alternatives considered:**
- `budget nullable money_amount` column on `categories` — rejected. Only one value per
  category; no history, no month-to-month change tracking. Would need a migration to a
  table the moment the first month-to-month change is needed.
- `budget jsonb` column on `categories` storing a month→amount map — rejected. Opaque
  to SQL queries; can't index or join; pushes logic into application code that SQL
  handles cleanly.

**Consequences:**
- A new Alembic migration adds the `budgets` table.
- The seed loader (`services/seed.py`) is updated to read the `budget` field from
  `categories.json` and insert rows into `budgets` (currently silently ignored).
- The Spend page query joins `budgets` on `category_id` with a `MAX(valid_from)` filter
  per category (the rollforward query) rather than reading a column.
- Adding or editing a budget requires an insert/upsert into `budgets`, not an update to
  `categories`. A future budget-editing UI surfaces this naturally.

---

## 2. Budgets roll forward — the last-set amount applies until explicitly changed

**Decision:** The effective budget for month M is the most recent `budgets` row where
`valid_from ≤ first day of M`. A category with at least one budget row carries that
amount forward to all subsequent months until a new row supersedes it. A category with
no rows has no effective budget for any month.

**Why:** Households set budgets once and adjust them occasionally — they do not
re-enter $900 for Groceries every month. Requiring explicit entry every month would
mean the Spend page shows "no budget" for every category after the first month unless
the user manually copies it forward. Rollforward makes the common case (stable budget)
require zero ongoing maintenance, while still allowing month-specific overrides when
needed.

**Alternatives considered:**
- Explicit-per-month (no row = no budget): rejected. Every month with no row shows
  "no budget" even when the household has a clear target. Converts a stable preference
  into ongoing maintenance work.
- Pre-populate future rows on save (e.g. insert the same amount for the next 12 months):
  rejected. Creates write amplification and stale rows when the user later changes the
  budget. The rollforward query is simpler and correct under any insert/update pattern.

**Consequences:**
- The Spend page backend query uses a lateral join or window function to find
  `MAX(valid_from) WHERE valid_from <= date_trunc('month', CURRENT_DATE)` per category.
- Changing a budget creates a new row; it does not update the old one. Old months'
  effective budgets remain correct (their `valid_from ≤ their month` still resolves to
  the older row).
- The seed loader inserts one row per budgeted category with `valid_from` set to the
  first day of the month when the seed is run. Future months inherit via rollforward.
