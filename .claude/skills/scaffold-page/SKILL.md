---
name: scaffold-page
description: Scaffold a new finance-app frontend page — an API client module, a Svelte page/route component, and route wiring. Use when adding a new UI page or view (e.g. "add a cash-reserves page", "new page for X", "scaffold the frontend for Y"). The app is a PWA with swipeable panels plus persistent tab/dot navigation.
---

# Scaffold Page

Adds one frontend page end to end, matching this project's conventions. The frontend
is **Svelte**, delivered as a **PWA** the family opens on a phone: swipeable panels
**with** persistent tab/dot navigation, clean and legible for a non-techy reader.

## Canonical reference
Read the equivalent files for an existing page and copy their shape before writing
anything. Use `src/frontend/src/routes/(app)/cash/+page.svelte` (simple data display)
or `src/frontend/src/lib/api/spend.ts` (API client) as the reference.

The five panels, in order: **Cash reserves → Spend vs budget → Flagged → Loans →
Forecast.**

## Confirm with the user before writing anything
1. **Resource** — which backend endpoint(s) does this page consume?
2. **Page type** — list, list + detail, form (e.g. the import upload), or a swipe panel?
3. **Route path** — e.g. `/cash`, `/spend`, `/flagged`.
4. **Auth** — protected (redirect to login if no session) or public? (App pages are
   protected.)

## Steps

### 1. API client — `src/frontend/src/lib/api/<resource>.ts`
- Mirror the shape of an existing client exactly.
- Export TypeScript interfaces (`X`, `XCreate`, `XUpdate`) and async functions
  (`listX`, `getX`, `createX`, `updateX`, `deleteX`).
- Use raw `fetch` with a relative `/api/...` path — same-origin deployment means the
  browser sends the session cookie automatically. See existing clients for the pattern.
- URL paths must match the FastAPI router exactly.
- **Money is rendered from string/`Decimal` values — never parse into a JS float for
  arithmetic.** Format for display only.

### 2. Page component — `src/frontend/src/routes/<name>/+page.svelte` (or the project's route convention)
- Svelte component; keep data-loading in the page's `load`/store, presentation in the
  component.
- **Loading and error states are required** — never render blank without feedback,
  and never show a raw stack trace; friendly messages for family members.
- Touch-safe: tap targets large enough for a finger; no hover-only interactions.
- If it's one of the five panels, wire it into the swipe flow **and** the persistent
  tab/dot nav (both must work).

### 3. Route wiring & nav
Register the route per the app's routing setup and add it to the tab/dot nav in the
correct panel order if it belongs there.

### 4. PWA & test
- Keep the PWA wrapper intact (home-screen icon, fullscreen, app-like feel).
- Confirm it renders at its route, loads real data, and works on a phone-sized
  viewport (narrow the browser to test).

## Done looks like
`npm run dev` boots with no type errors, the page renders at its route, data loads
from the API, swipe + tab nav both work, and it reads cleanly on a phone.
