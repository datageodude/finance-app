# 💬 Examples

Worked examples of what good looks like on this project. Each is a scenario with the
right move (✅) and the tempting-but-wrong one (❌). These make [identity.md](identity.md)
and [rules.md](rules.md) concrete.

---

## 1. Hitting a 🛑 checkpoint

**Scenario:** Phase 1 schema migrations apply cleanly. Geodude says "great, keep going."

✅ "Migrations apply, but the checkpoint bar isn't met yet — I haven't proven the
dedupe-key constraint *rejects* a duplicate insert. Let me write that test first." Then
run it, show the result, and re-plan Phase 2 against the real CSVs before any adapter code.

❌ Take "keep going" as licence to start Phase 2 immediately, assuming the constraint
works because the migration didn't error.

> Rule: don't build ahead; verify done-when with a real assertion.

---

## 2. Adding a backend resource

**Scenario:** "Add an accounts endpoint."

✅ Route to the `scaffold-endpoint` skill. Model + schema + **service (logic here)** +
thin router, register the model, generate a migration via `new-migration`, add a test.
Confirm fields: money columns as `Numeric`, not float.

❌ Write a fat router with `db.query`/`db.commit` inline and skip the service layer
"to save time."

> Rule: logic in `services/`, routers stay thin.

---

## 3. Handling a money value

**Scenario:** Summing transactions for the Cash Reserves page.

✅ Keep values as `Decimal` (Python) / `numeric` (DB) the whole way; format to a string
only for display.

❌ `float(amount)` to make the arithmetic "easier," then round at the end.

> Rule: never float for money — rounding errors in financial data are unacceptable.

---

## 4. A re-import

**Scenario:** Geodude drops the same Bank A CSV he imported last week.

✅ Preview reports "47 found, 47 duplicates, 0 will be added." Zero rows inserted, an
audit entry records the no-op. You confirm idempotency held on *real* data.

❌ Insert 47 new rows because the dedupe logic was only tested on synthetic input.

> Rule: import is idempotent; prove it on real data.

---

## 5. Talking to a family member (errors)

**Scenario:** An upload fails because the filename doesn't match a known bank.

✅ "I couldn't tell which account this file is from. Which account is it?" — with a
dropdown, and an offer to rename the file correctly next time.

❌ Render `ValueError: could not parse bank_code from filename` to the screen.

> Rule: friendly errors, never a raw stack trace.

---

## 6. Brainstorming / planning a phase

**Scenario:** Geodude is excited and wants to start coding Phase 5 flagging now.

✅ "Before code — let's slow down and grill this. The $100 threshold is a guess until
we see the real spread of amounts; and the timing flag depends on whether the CSVs
even carry a time field. Let me run `grilling` on the plan first." Then capture the
agreed scope with `to-prd`/`to-issues`.

❌ Start writing flag rules from the plan's summary without checking the data first.

> Rule: slow down in planning (Geodude asked for this); run the stage gate before
> proceeding.

---

## 7. Reporting status

**Scenario:** Tests pass except one flaky merchant-normalisation case.

✅ "12 of 13 pass. One fails: 'WOOLWORTHS 1234' and 'WOOLWORTHS METRO' collapse to the
same merchant when they shouldn't. Here's the output — want me to fix the normaliser
or adjust the test?"

❌ "All good, tests pass ✅" and move on.

> Rule: honesty — failures reported with output, nothing hidden.

See also: [identity.md](identity.md) · [rules.md](rules.md) · [reference/](reference/)
