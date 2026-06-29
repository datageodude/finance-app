# Finance App

A self-hosted, family-shared personal finance app. Weekly manual CSV imports (no
automated bank feeds), privacy-first: financial data never touches the public
internet or any third-party infrastructure. All family members get equal full-read
access, and every action is audited (chain of custody).

> **Status:** pre-Phase 0 — planned, not yet built. The roadmap exists; no application
> code yet. See [planning/PLAN.md](planning/PLAN.md).

## The problem this solves

This project started from a real, specific problem — see the client brief:
[brief.md](brief.md). The proof that the design answers every point of that brief is
mapped in [planning/brief-to-solution.md](planning/brief-to-solution.md).

## What it does (planned)

A phone-friendly PWA with five swipeable pages:

1. **Cash reserves** — total + per bank/account
2. **Spend vs budget** — whole + sub-categories
3. **Flagged transactions** — unusual activity to review and clear
4. **Loans** — balances, rates, repayment progress
5. **Forecast** — 1 / 6 / 12-month savings projection

You drag a CSV from your bank onto the page; the app validates, de-duplicates,
categorises, and flags it — then shows it across those five views.

## Stack

Python · FastAPI (backend, holds all logic) · Svelte (PWA frontend) · PostgreSQL +
Alembic · session auth (Argon2/bcrypt) · Docker Compose, self-hosted behind Tailscale.

## Layout

| Folder | What's in it |
|--------|--------------|
| [brief.md](brief.md) | The original problem brief and measurable success criteria |
| [planning/](planning/) | Build roadmap ([PLAN.md](planning/PLAN.md)) + [brief→solution map](planning/brief-to-solution.md). Specs/architecture/decisions added per phase |
| [src/](src/) | Application code — `backend/` (FastAPI) + `frontend/` (Svelte) *(from Phase 0)* |
| [docs/](docs/) | API docs, family user guides, changelog |
| [ops/](ops/) | Deploy (compose), monitoring, backup/restore runbooks *(from Phase 0)* |
| [TODO.md](TODO.md) | Outstanding tasks, homework, and subfolders to add as the project grows |

> Subfolders are created when their phase begins (not ahead of it), so the tree tracks
> real work. [TODO.md](TODO.md) lists what gets added when.

## Quickstart (picking this up)

Nothing runs yet — the value here is a scoped problem and a buildable system. To start:

1. Read [brief.md](brief.md) — the problem and what "done" means.
2. Skim [planning/brief-to-solution.md](planning/brief-to-solution.md) — how the design
   answers it, then [planning/PLAN.md](planning/PLAN.md) for the phased roadmap.
3. Read [CLAUDE.md](CLAUDE.md) — conventions, routing, and the stage gates.
4. Do the **homework** in [TODO.md](TODO.md) (pull real bank CSVs), then begin **Phase 0**.

> Building with Claude Code? Open the repo and `CLAUDE.md` loads automatically. Start
> Phase 0 and honour each 🛑 checkpoint before moving on.

## How it's built

Phase by phase, each ending in a 🛑 checkpoint — stop, verify with a real test,
re-plan the next phase against what you learned, then proceed. The dangerous logic
(schema, import/dedupe, flagging) fails *silently* on financial data, so it's built
and tested hardest. Full protocol and schema deep-dive in [planning/PLAN.md](planning/PLAN.md).

## Working in this repo with Claude

[CLAUDE.md](CLAUDE.md) is the agent-facing map: tech stack, routing, conventions, and
the per-stage skill gates (run before proceeding). It's also the entry point to the
behavioural layer (identity, rules, examples, glossary) that shapes how Claude builds
here. Project skills live in `.claude/skills/` (`scaffold-endpoint`, `scaffold-page`,
`new-migration`, `check`).

## Privacy

No bank feeds, no cloud, no third parties. Data lives on a home device, reachable only
over Tailscale. Internet exposure is a deliberate later switch-on, never the default.

**This repo never holds real financial data.** Code and *synthetic* sample CSVs only;
real exports, the live database, and backups stay on the offline instance, outside the
tree. The boundary is enforced structurally (`.gitignore` ignores every real CSV/`.env`,
plus a pre-commit scan) — see [docs/data-handling.md](docs/data-handling.md).
