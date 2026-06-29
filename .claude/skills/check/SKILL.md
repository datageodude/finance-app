---
name: check
description: Run the finance app's full quality gate — backend lint (ruff) and tests (pytest), frontend lint + type-check (svelte-check) and build. Use before committing, after scaffolding, or when asked to "check everything", "run checks", "verify the build", or "does this pass CI".
---

# Check

Runs the full quality gate in the order CI would. **Stop at the first failure and fix
it before continuing** — a green gate means nothing if you skipped a red step.

## Adjust to what exists
This project is built phase by phase. If a step's tooling isn't installed yet, note
"not set up yet" and continue — don't fabricate a pass. Update this file as the gate
grows (Phase 0 wires in lint; tests arrive with the dangerous logic in Phases 1/2/5).

## Commands

Run from the project root.

### Backend lint
```bash
cd src/backend && ./.venv/bin/ruff check .
```
Fix all errors. Auto-fix the mechanical ones: `ruff check --fix .`

### Backend tests
```bash
cd src/backend && ./.venv/bin/pytest
```
All must pass. Pay special attention to the **dangerous-logic** tests — schema
constraints (dedupe-key uniqueness), import idempotency/dedupe, merchant
normalisation, and flagging. These fail silently in production if untested, so a real
assertion is required, not a plausible-looking output.

### Frontend lint + type-check
```bash
cd src/frontend && npm run lint
cd src/frontend && npm run check     # svelte-check — zero type errors required
```

### Frontend tests
```bash
cd src/frontend && npm run test      # Vitest (unit) — and Playwright e2e once set up
```

### Frontend build (smoke check)
```bash
cd src/frontend && npm run build
```
A clean build means no type errors or missing imports slipped through lint.

## Done looks like
Every applicable step completes with zero errors. Record any new failure you can't
fix immediately in [TODO.md](../../TODO.md) rather than leaving it silent.
