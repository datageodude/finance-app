# Documentation

API docs, user guides, and the changelog.

## Audiences

- `api/` — For anyone (incl. future you) integrating with or maintaining the API.
- `guides/` — For the **non-techy family members** who use the app. Plain language,
  step-by-step, no jargon. The import guide is the important one: "download your CSV
  and drag it here."
- `changelog.md` — Running log of what changed and when.

## Standards

- API docs: FastAPI auto-generates OpenAPI at `/docs`; capture anything non-obvious
  (auth flow, import contract, dedupe-key behaviour) here in markdown.
- User guides: step-by-step, written for someone who has never seen a terminal.
- Changelog: `YYYY-MM-DD — what changed — why`.

## Rules

- Every new API endpoint gets documented before it is considered done.
- User guides update when user-facing behaviour changes.
- Changelog updates with every release or significant change.
