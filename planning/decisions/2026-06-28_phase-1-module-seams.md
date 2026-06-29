# Phase 1 Module Seams

**Date:** 2026-06-28
**Status:** Accepted
**Gate:** Output of the `codebase-design` skill on Phase 1. Feeds directly into `tdd`.
**Depends on:** [2026-06-28_phase-1-schema.md](2026-06-28_phase-1-schema.md)

Six seam decisions taken while designing the Phase-1 module structure. Each notes the
decision, rationale, and what the alternative was.

---

## Decision 1 — Shared types in `core/types.py`

`MoneyAmount` (SQLAlchemy wrapper for `numeric(14,2)`) and `PercentageRate`
(`numeric(6,4)`) live in `core/types.py`, alongside `core/database.py` and
`core/config.py`. All model files that carry money or rate columns import from there.

**Why:** one import path, no cross-model dependencies, consistent with `core/database.py`
already being the shared foundation for `Base`. Alternative (define in `models/account.py`,
import from there) would create a spurious coupling from `transaction.py` → `account.py`
just for a type.

The Alembic migration creates the Postgres `DOMAIN` declarations once, in
`v1_domains_and_lookups`.

---

## Decision 2 — 9 model files, grouped by cohesion

| File | Contents |
|------|----------|
| `models/account.py` | `Account`, `LoanTerms`, `CreditTerms` |
| `models/lookups.py` | `Bank`, `AccountType`, `MatchType`, `FlagStatus`, `FlagType`, `AuditAction` |
| `models/transaction.py` | `Transaction` |
| `models/merchant.py` | `Merchant` |
| `models/category.py` | `Category` |
| `models/rule.py` | `Rule` |
| `models/flag.py` | `Flag` |
| `models/import_batch.py` | `ImportBatch` (`import.py` shadows Python's keyword) |
| `models/audit_log.py` | `AuditLog` |

**Why:** `LoanTerms`/`CreditTerms` have no independent identity — they only describe an
account. A reader of `account.py` sees the full picture. All six lookup models are the
same shape and lifecycle; one file is less noise than six. Every other table is
complex enough to stand alone. Alternative (one file per table, 13 files) would give
`loan_terms.py` a 3-column file with no independent meaning.

---

## Decision 3 — Three service modules; `auditing` is a deep module

| Module | Interface |
|--------|-----------|
| `services/auditing.py` | `record(db, *, action, target_type, target_id, user_id, detail=None) -> None` |
| `services/accounts.py` | `create_account`, `get_account`, `list_accounts`, `archive_account`, `update_balance` |
| `services/transactions.py` | `insert_batch`, `recategorise`, `reconcile` |

**`auditing.py` is the keystone.** Every service that writes calls `record()` in the
same `db` session. Callers never construct `AuditLog(...)` directly. One function,
five params — the entire audit interface. Implementation hides ORM interaction and
`detail` serialisation.

**Why:** audit correctness is chain-of-custody — it must never be wrong, and "never be
wrong" is easiest when all the logic is in one place. Deletion test: delete
`auditing.py` and the question "what goes in detail?" reappears in every service.
Alternative (inline `AuditLog(...)` in each service) scatters the construction logic and
means a future format change touches every service.

**`insert_batch` is the dangerous deep function.** Single call hides: dedupe enforcement
(the UNIQUE constraint fires here), merchant lookup, rule matching, audit writing. Callers
pass `rows: list[TransactionRow]` in, get `BatchResult` back. The import router never
touches deduplication logic directly.

---

## Decision 4 — Three ordered migrations matching the FK dependency layers

| Migration | Contents |
|-----------|----------|
| `v1_domains_and_lookups` | Postgres `DOMAIN` declarations + all six lookup tables + seed data |
| `v1_core_entities` | `users.is_active`; `accounts`, `loan_terms`, `credit_terms`, `merchants`, `categories` |
| `v1_transactional` | `transactions` (dedupe UNIQUE), `rules`, `flags`, `imports`, `audit_log` |

Each layer FKs only to earlier layers — independently reversible without touching later
ones. Lookup seed data (`INSERT` rows) lives in `v1_domains_and_lookups`'s `upgrade()`
and is reversed in `downgrade()`, keeping lookup values version-controlled.

**Why:** the keystone test (duplicate insert rejected) runs against migration 3 alone —
verifiable before any service code. Review burden is split into three focused files.
Alternative (one combined migration) produces a long file where reviewer attention drifts
and partial failure rolls back everything.

---

## Decision 5 — `users.is_active` folds into `v1_core_entities`

`op.add_column('users', Column('is_active', Boolean, ...))` opens `v1_core_entities`'s
`upgrade()`. Not a separate migration.

**Why:** the column exists because of the archive-don't-delete policy decided in Phase 1;
it belongs with that decision's migration layer. A one-column file is ceremony without
benefit.

---

## Decision 6 — Eight mandatory tests in `tests/test_phase1_schema.py`

All tests cross the **database seam** — SQLAlchemy into a real Postgres test DB, no
mocks. They prove the schema has teeth, not that the services use it correctly (that's
Phase 2).

| Test | Behaviour proved |
|------|-----------------|
| Duplicate insert rejected | UNIQUE constraint fires |
| Near-duplicate accepted | `balance` is a true key member |
| `NULL` key column rejected | `NOT NULL` on all five dedupe columns |
| `category_id = NULL` accepted | `NULL` = Uncategorised is valid |
| Loan account without `loan_terms` | Service-layer invariant catches missing sidecar |
| `opening_balance + Σtxns == current_balance` | Reconciliation formula closes |
| Reconciliation detects drift | Dropped transaction makes reconciliation fail |
| Audit record on recategorise | `recategorise()` writes `audit_log` row |

**Why real DB:** the dangerous logic (UNIQUE constraint, NOT NULL, reconciliation math)
lives in Postgres, not in Python. Mocking the DB would test the ORM, not the constraint.
Consistent with Phase-0 auth tests (`conftest.py` already wires a test DB session).

---

## File tree after Phase 1

```
src/backend/
├── core/
│   ├── database.py        (existing)
│   ├── config.py          (existing)
│   ├── security.py        (existing)
│   ├── deps.py            (existing)
│   ├── limiter.py         (existing)
│   └── types.py           ← NEW: MoneyAmount, PercentageRate
├── models/
│   ├── __init__.py        (updated: all new models registered)
│   ├── user.py            (existing)
│   ├── session.py         (existing)
│   ├── lookups.py         ← NEW
│   ├── account.py         ← NEW (+ LoanTerms, CreditTerms)
│   ├── transaction.py     ← NEW
│   ├── merchant.py        ← NEW
│   ├── category.py        ← NEW
│   ├── rule.py            ← NEW
│   ├── flag.py            ← NEW
│   ├── import_batch.py    ← NEW
│   └── audit_log.py       ← NEW
├── services/
│   ├── auth.py            (existing)
│   ├── auditing.py        ← NEW
│   ├── accounts.py        ← NEW
│   └── transactions.py    ← NEW (insert_batch, recategorise, reconcile)
├── migrations/versions/
│   ├── <existing Phase-0 migration>
│   ├── v1_domains_and_lookups.py   ← NEW
│   ├── v1_core_entities.py         ← NEW
│   └── v1_transactional.py         ← NEW
└── tests/
    ├── conftest.py        (existing)
    ├── test_auth.py       (existing)
    └── test_phase1_schema.py  ← NEW (8 mandatory tests)
```
