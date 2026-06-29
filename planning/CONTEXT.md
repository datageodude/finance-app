# Planning

The build roadmap, feature specs, architecture docs, and decision records.

## The master plan

[PLAN.md](PLAN.md) is the living build roadmap — phased, with 🛑 checkpoints. It is
**not a frozen spec**: each phase ends with a checkpoint where you stop, verify the
"done when" bar with a real test (not a plausible-looking output), surface what the
phase taught you, and re-plan the next phase against facts before writing its code.
The dangerous phases (1 schema, 2 import, 5 flagging) fail *silently* on financial
data — pause longest there.

## How specs work here

A spec describes WHAT to build and WHY, not HOW. Claude reads the spec and makes
implementation decisions from the conventions in [../src/CONTEXT.md](../src/CONTEXT.md).

### Spec template

**Problem:** What user problem does this solve?
**Proposal:** What are we building?
**Scope:** What is included? What is explicitly excluded?
**Dependencies:** What does this touch? What must exist first?
**Open questions:** What is not decided yet?

Specs that map to a PLAN phase should cite the phase. Stress-test a spec with the
`grilling` skill before it becomes code.

## Architecture

Key architecture docs live in `architecture/`. The schema is the foundation
(expensive to change later) — the canonical schema model is the Phase 1 deep-dive in
PLAN.md until it graduates into an `architecture/schema.md`.

## Decision records

Record significant technical decisions in `decisions/`, named
`YYYY-MM-DD_decision-title.md`. The `domain-modeling` skill helps capture these well.

### Decision record template

**Decision:** What we decided
**Context:** Why this came up
**Options considered:** What else we looked at
**Rationale:** Why we chose this option
**Consequences:** What this means going forward

Decisions already locked in PLAN.md (stack, generic `accounts` table, stored balance
+ reconciliation, negative = money out) should be promoted into dated decision
records as they are acted on.
