# 📚 Reference

Agent-facing reference material for the Finance App — the facts and shorthand that
inform *how* the work is done. Distinct from [../docs/](../docs/), which holds project
*output* (API docs, family user guides, changelog) for human readers.

## What's here

| File | Contents |
|------|----------|
| [glossary.md](glossary.md) | The project's domain language (ubiquitous terms) — accounts, transactions, dedupe key, merchant normalisation, flags, audit log, etc. |
| [bank-csv-notes.md](bank-csv-notes.md) | The real column shapes, date formats, sign conventions, and time-field findings per bank — the per-bank adapter rules. |
| `bank_a.csv`, `bank_b.csv` | Format **sample** exports (not real imports) the adapter rules are derived from. |

## Pointers (don't duplicate — link)

- **Schema** — the canonical model is the Phase 1 deep-dive in
  [../planning/PLAN.md](../planning/PLAN.md) until it graduates into
  `../planning/architecture/schema.md`.
- **Decisions** — `../planning/decisions/` (sign convention, stored balance, dedupe
  window, …).
- **Conventions & stage gates** — [../CLAUDE.md](../CLAUDE.md).

Keep this folder lean: link to the source of truth rather than copying it, so nothing
drifts out of sync.
