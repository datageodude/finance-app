# Changelog

Format: `YYYY-MM-DD — what changed — why`.

## 2026-06-27
- CSV homework done: analysed Bank A + Bank B template exports, wrote
  reference/bank-csv-notes.md (per-bank adapter rules), confirmed both are date-only →
  formally dropped the Phase 5 "unusual timing" flag in PLAN.md (table, checkpoint,
  schema note + removed `txn_time`). Updated TODO open items (sign, balance, category).
- Privacy pass for the public repo: replaced sample CSVs with synthetic data (fake
  merchants, round balances, no locations/account numbers) and anonymised bank identity
  throughout — real bank names → Bank A (`bank_a`) and Bank B (`bank_b`); renamed the
  sample files. Done before any git history exists. Verified clean by sweep.
- Synthetic test corpus (`fixtures/`): deterministic `generate.py` emits 6 bank-format
  CSVs (5 accounts spanning both banks + all four account types, 3 months of history)
  plus `seed/` accounts/categories/rules. Deliberately seeds every feature and flag
  rule (dedupe overlap, over-$100, double-charge ×2, new merchant, price-jump,
  Uncategorised, over-budget Dining, loan repayment progress, forecast slope); catalogue
  of expected outcomes in fixtures/README.md. Allow-listed in `.gitignore`.
- Data-handling boundary: real data and the public repo never meet. Added `.gitignore`
  (ignores every real CSV/`.env`/`data/`, allow-lists the two synthetic fixtures),
  docs/data-handling.md (two-zone policy, offline-before-real-data rule, pre-push
  checklist + pre-commit scan hook), and a rules.md non-negotiable. Real exports live
  outside the tree; hook install + `.env.example` queued for Phase 0.

## 2026-06-25
- Workspace scaffolded from the code-project blueprint (CLAUDE.md, per-workspace
  CONTEXT.md, planning/PLAN.md, project skills) — kick off structured build of the
  family finance app.
- Added behavioural layer (identity.md, rules.md, examples.md, reference/).
- Portfolio review pass: added measurable success criteria to brief.md, a
  planning/brief-to-solution.md traceability map, a README Quickstart, and a TBA
  LICENSE; linked the brief from README + CLAUDE.md; removed premature empty
  subfolders to honour the don't-build-ahead rule.
