# 📐 Rules

Operating rules for the Finance App. [CLAUDE.md](CLAUDE.md) is the source of truth for
conventions and the stage gates; this restates the non-negotiables as crisp do/don'ts.
When a rule here and CLAUDE.md ever disagree, CLAUDE.md wins — fix this file.

## Data integrity (these fail silently — treat as sacred)

- **DO** store money as `Decimal`/`numeric`, end to end. **DON'T** ever use float for a
  monetary value.
- **DO** use `timestamptz` (UTC) for timestamps.
- **DO** keep the sign convention **negative = money out**, everywhere, no exceptions.
- **DO** make import idempotent via the `transactions` dedupe key (composite `UNIQUE` on
  `account_id, txn_date, amount, description_raw, balance`); re-importing the same file
  must add **zero** rows.
- **DO** prove dangerous behaviour with a real assertion (a duplicate insert is
  *actually rejected*). **DON'T** accept a plausible-looking output as proof.
- **DON'T** silently drop, merge, or "fix" a transaction. Prefer a loud, audited reject
  over a quiet wrong insert.

## Architecture

- **DO** put business logic in `src/backend/services/`. **DON'T** put `db.query` /
  `db.commit` logic in a route handler — routers stay thin.
- **DO** write every import and every flag-approval to `audit_log` (chain of custody),
  in the same transaction as the change.
- **DO** keep bank-specific parsing in `src/backend/adapters/` (one adapter per bank).

## Security & privacy

- **DON'T** put secrets in git. `.env` only; `.gitignore` from commit one.
- **DON'T** ever let real financial data enter the repo. The repo holds **synthetic**
  fixtures only (`reference/bank_a.csv`, `bank_b.csv`); real CSVs, the live DB, and
  backups live outside the tree on the offline instance. Full boundary +
  pre-commit scan: [docs/data-handling.md](docs/data-handling.md).
- **DON'T** stage a `*.csv` (other than the two fixtures), a `.env`, or anything with a
  real merchant/balance/account/location in it. When in doubt, don't commit — ask.
- **DO** keep auth at B-grade from day one (Argon2/bcrypt, sessions, rate-limit, MFA
  hooks present even while off).
- **DO** keep the app private — home device + Tailscale, nothing on the public
  internet. Internet exposure is a deliberate later switch-on, never the default.
- **DON'T** trust an untested backup — a restore isn't real until you've restored it
  into a clean DB and confirmed it works.

## Family-facing surface

- **DO** show friendly errors and clear previews ("47 found, 3 duplicates, 44 will be
  added"). **DON'T** ever surface a raw stack trace to a family member.
- **DO** make every flag explainable ("flagged because: first time at this merchant").
- **DO** keep pages touch-safe and legible for a non-techy reader.

## Process (how we work, not just what we build)

- **DON'T** build ahead of the current phase. Honour the 🛑 checkpoints in
  [planning/PLAN.md](planning/PLAN.md).
- **DO** run the stage skill-gates before proceeding (CLAUDE.md → Skills → Stage
  gates): `grilling` before re-planning a phase, `domain-modeling` + `codebase-design`
  before designing schema/resources, `tdd` while building (mandatory on Phases 1/2/5),
  `diagnosing-bugs` when stuck, `check` before closing a phase or committing.
- **DO** slow Geodude down during brainstorm/planning — he's asked for that. Talk the
  design through before writing code.
- **DON'T** start work on an unnamed project or folder — confirm the name first.
- **DO** record significant decisions in `planning/decisions/YYYY-MM-DD_title.md`, and
  keep `TODO.md` current.
- **DO** be honest about state: failed tests reported with output, skipped steps named,
  done-and-verified stated plainly without hedging.

See also: [identity.md](identity.md) · [examples.md](examples.md) · [reference/](reference/)
