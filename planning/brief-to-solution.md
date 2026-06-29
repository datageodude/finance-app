# Brief → Solution

How each need in [../brief.md](../brief.md) is met by the design in
[PLAN.md](PLAN.md). This is the at-a-glance proof that the system answers the brief —
read it before doubting scope, and update it if the brief or plan changes.

## Requirements → where they're solved

| Brief need | How it's solved | Where |
|------------|-----------------|-------|
| Self-hosted, fully controlled | Home device, app + DB in containers | Phase 7 · [../ops/CONTEXT.md](../ops/CONTEXT.md) |
| No aggregator, no data leaving home | Manual CSV import only; private network (Tailscale), no public internet | Phases 2 & 7 |
| Weekly manual CSV import | Drag-drop import with per-bank adapters, validation, dedupe | Phases 2–3 |
| PostgreSQL | Postgres + Alembic; money `numeric`, never float | Phase 1 |
| Open-source | License TBA (see [../LICENSE](../LICENSE)); self-hosted stack | Phase 0 |
| Security-first | B-grade auth from day one (Argon2/bcrypt, sessions, rate-limit, MFA hooks); secrets in `.env` | Phase 0 |
| Phone-friendly & visual | Svelte PWA, swipeable pages + tab/dot nav | Phase 4 |
| Effortless for a non-techy family member | Friendly errors, preview-before-commit, dropdown fallback; touch-safe pages | Phases 3–4 |
| Everyone stays involved | Equal full-read access for all family members; audit log for chain of custody | Phases 0–1 |
| Multi-bank | One CSV adapter per bank (Bank A + Bank B in v1) | Phase 2 |
| Future loan tracker | Generic `accounts` table — loans are a *view* over `type=loan` | Phases 1 & 4 |
| Catch dodgy transactions | Flagging engine: over-threshold, double charge, new merchant | Phase 5 |
| Single view of what we have | Cash Reserves page (total + per account) | Phase 4 |
| Savings forecast | Forecast page (1 / 6 / 12-month projection) | Phase 4 |
| See outflows vs income clearly | Spend vs budget page (whole + sub-categories) | Phase 4 |

## Success criteria → how the build meets them

The six measurable bars in the brief, mapped to the phase that delivers each:

| Success criterion | Delivered by |
|-------------------|--------------|
| Weekly check < 5 min (from ~30) | The dashboard pages — Phase 4 |
| Income vs outflows visible, no manual entry | Import + categorisation → Spend page — Phases 2, 4, 6 |
| Family imports & reads unaided | Import UX — Phase 3 (validated by watching a real family member) |
| Dodgy transactions surface themselves | Flagging engine — Phase 5 |
| Nothing leaves home + tested backup | Tailscale + encrypted `pg_dump` with tested restore — Phase 7 |
| Sustainable (self-improving categorisation) | The mix-pattern loop — Phase 6 |

> **Status honesty:** this maps the *plan* to the brief. The app is pre-Phase 0 — these
> are designed-and-traced, not yet built-and-verified. Each is confirmed only when its
> phase clears its 🛑 checkpoint with a real test.
