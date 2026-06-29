# Client Brief — Household Finance App

**Client:** Me (and my family).

## What's broken

Each week I spend ~30 minutes clicking through several bank apps, checking each
transaction makes sense. Others spend on these accounts too, so without easy family
involvement I can't fully see the picture.

I used to budget in Excel — 1–2 hours of manual data entry each month, into
expenditure buckets that were never well-defined. It worked, but the manual load was
heavy and it lapsed years ago as life got busier. The result: **no good
understanding of income vs outflows** — which, with recent changes to home life,
matters more than ever.

There's no single view of what we have now, no loan tracking, no savings forecast,
and no reliable way to catch dodgy transactions (double charges, silent premium
hikes).

## What I've tried

- **Excel** — effective but too manual to sustain; lapsed.
- **Off-the-shelf apps** (e.g. Gather, ~$15/mo) — paid, and all hand our finances to
  a third-party aggregator via Open Banking/CDR.
- **Open-source self-hosted** — none have native local bank linking; they lean on the
  same aggregators. Automatic feeds can't avoid the middleman.

## What I need

A **self-built, self-hosted app** I fully control. Weekly manual CSV imports — no
aggregator, no data leaving home. PostgreSQL, open-source, security-first.
Phone-friendly and visual, effortless for a non-techy family member so everyone
stays involved. Multi-bank, future loan tracker. Goal: turn the weekly manual
checking into a quick glance at a pre-processed dashboard — and finally see outflows
vs income clearly.

## Success criteria (done = )

Measurable bar this app must clear to count as solved:

1. **Faster weekly check** — the ~30-min/week click-through across bank apps becomes a
   **< 5-min glance** at one dashboard.
2. **Income vs outflows is visible** — at any time I can see the month's spend by
   category against income, without manual data entry.
3. **Family can use it unaided** — a non-techy family member imports a CSV and reads
   the dashboard with no help beyond "download your CSV and drag it here."
4. **Dodgy transactions surface themselves** — double charges, new merchants, and
   silent premium hikes appear on a Flagged list I review, rather than me hunting for
   them.
5. **Nothing leaves home** — no third-party aggregator; data lives on a home device,
   reachable only over the private network. A *tested* backup exists.
6. **Sustainable** — the ongoing manual load is the weekly CSV drop, not hours of data
   entry. Categorisation gets less manual over time, not more.
