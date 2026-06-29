# Phase 3 Import UX — Decisions

**Date:** 2026-06-29
**Status:** Accepted
**Gate:** Output of the `grilling` + `domain-modeling` skills on the Phase-3 Import UX
plan. Next gates before code: `codebase-design` → build (no `tdd` mandate here — Phase 3
is a UX phase, not a dangerous-logic phase).

Two decisions from Phase 3 planning that are hard to reverse, surprising without
context, and the result of a real trade-off. Recorded so future contributors don't
re-litigate them or add "protective" logic thinking these were oversights.

---

## 1. Two-step import API: preview then confirm

**Decision:** The import flow is split into two separate API calls:
`POST /imports/preview` (dry-run — parses the file, checks for duplicates, returns
counts; **no DB write**) followed by `POST /imports/confirm` (commits the import).
The user sees and approves a preview before anything is written to the database.

**Why:** Family members who import CSVs are non-technical. Committing on upload with
no preview gives them no opportunity to catch a wrong file (e.g. re-downloading last
week's export by mistake) or a mismatch ("this says Bank B but I thought I picked
Bank A"). The preview is the last human checkpoint before financial data enters the
system. A single-step "upload and commit" would be simpler to build but removes that
checkpoint entirely.

**Alternatives considered:**
- Single-step import (upload → commit, no preview) — rejected. Simpler, but a
  non-techy user has no visibility into what's about to happen, and no graceful
  recovery if the wrong file is dropped.
- Client-side preview (parse the CSV in the browser and show counts without a server
  call) — rejected. Would require reimplementing the adapter logic in TypeScript,
  creating a divergence risk between what the browser says and what the backend
  actually does. The backend is the single source of truth for all import logic.

**Consequences:**
- The backend must support a stateless dry-run mode in the import engine: run all
  parsing and dedupe checks, return counts, commit nothing.
- The frontend holds the file between preview and confirm and re-submits it on
  confirm (no server-side session state required).
- Preview counts are authoritative — they reflect the actual dedupe result, not an
  estimate.

---

## 2. Multi-file parallel preview, not sequential

**Decision:** When multiple CSV files are dropped at once, all files are previewed
simultaneously — one card per file, all loading in parallel, with a single "Import N
files" button that commits the valid cards together. Files with errors or unresolved
accounts are excluded from the bulk confirm and handled inline.

**Why:** The user deliberately dropped multiple files at once. A sequential
wizard (preview file 1 → confirm → preview file 2 → confirm → …) treats that as a
series of independent acts and forces the user through N confirmation steps. Parallel
preview shows the full picture before any commit, matching the user's intent. Import
day (weekly CSV downloads from two banks, possibly multiple accounts) is the primary
use case — parallel saves meaningful time and cognitive load.

**Alternatives considered:**
- Sequential preview (one file at a time, auto-advancing after each confirm) —
  rejected. Feels like unnecessary hand-holding when the user has already chosen
  to drop multiple files together. N confirmation steps is friction, not safety.
- Combined summary (all files in one preview card, one count total) — rejected.
  Loses per-file visibility; if one file has an error the whole summary is ambiguous.

**Consequences:**
- The frontend fires parallel `POST /imports/preview` requests (one per file) and
  renders each card independently as its response arrives.
- Partial error handling is required: an error card is clearly marked and excluded
  from "Import N files"; the button label updates dynamically to reflect the count
  of committable cards.
- The "Import N files" button is disabled until all cards are in a resolved state
  (preview shown, error shown, or account manually selected).
