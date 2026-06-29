# Finance App

A self-hosted, family-shared personal finance app. Weekly manual CSV imports — no
bank feeds, no cloud, no third parties. Financial data never leaves the home device.

**Why it exists:** [brief.md](brief.md) — the problem and what "done" means.

---

## Status

V1 complete (Phases 0–5, June 2026). All five dashboard panels live and tested.

| Phase | What | State |
|-------|------|-------|
| 0 | Auth, project scaffold | ✅ |
| 1 | Schema (accounts, transactions, categories, rules) | ✅ |
| 2 | Import engine — CSV adapters, dedupe, auto-categorisation | ✅ |
| 3 | Import UX — drag-drop, per-file preview, bulk confirm | ✅ |
| 4 | Dashboard panels — Cash, Spend vs Budget, Loans, Forecast | ✅ |
| 5 | Flagging engine — over-threshold, double charge, new merchant | ✅ |
| 6 | Categorisation refinement | 🔜 |

## What it does

A phone-friendly PWA with five swipeable panels:

1. **Cash reserves** — total + per account
2. **Spend vs budget** — categories vs monthly budget caps
3. **Flagged transactions** — unusual activity to review and clear
4. **Loans** — balances, rates, repayment progress
5. **Forecast** — 1 / 6 / 12-month funds projection

Drag a CSV from your bank onto the Import page; the app validates, de-duplicates,
categorises, and flags it — then shows it across all five views.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python · FastAPI · SQLAlchemy · Alembic |
| Frontend | Svelte · SvelteKit · PWA |
| Database | PostgreSQL (money as `numeric`, never float) |
| Auth | Session-based · Argon2 hashing · login rate-limit |
| Deploy | Docker Compose · self-hosted behind Tailscale |

## Quickstart

```bash
# 1. Copy and edit env
cp .env.example .env          # set a real DB password

# 2. Start the dev stack (Postgres + backend + frontend)
./ops/scripts/dev.sh

# 3. Create a user
cd src/backend && uv run python cli.py create-user \
  --email you@example.com --name "Your Name" --password yourpassword

# 4. Seed accounts, categories, and rules via the app
# Import tab → drag in fixtures/imports/20240229_*.csv (synthetic data)
# Then fixtures/imports/20260531_*.csv to populate the Forecast tab
```

> See [docs/data-handling.md](docs/data-handling.md) for the privacy boundary —
> real bank CSVs live outside the repo, never in it.

## Layout

| Path | What |
|------|------|
| [brief.md](brief.md) | The original problem brief and success criteria |
| [planning/PLAN.md](planning/PLAN.md) | Phased roadmap and schema deep-dive |
| [src/backend/](src/backend/) | FastAPI app — models, services, API, migrations |
| [src/frontend/](src/frontend/) | Svelte PWA |
| [fixtures/](fixtures/) | Synthetic test corpus (generate.py + CSVs) |
| [ops/](ops/) | Docker Compose, dev script |
| [docs/](docs/) | Data-handling policy, changelog |

## Privacy

No bank feeds, no aggregators, no cloud sync. Data lives on a home device, reachable
only over Tailscale. Real exports, the live database, and backups stay on the offline
instance — outside this repo entirely. The boundary is structural: `.gitignore` blocks
every real CSV and `.env`, and a pre-commit hook scans staged content before it
leaves the machine.

## Building with Claude Code

[CLAUDE.md](CLAUDE.md) is the agent-facing map: stack, routing, conventions, and the
per-phase stage gates. Project skills in `.claude/skills/` cover the four common
operations: `check`, `new-migration`, `scaffold-endpoint`, `scaffold-page`.

## License

MIT — see [LICENSE](LICENSE).
