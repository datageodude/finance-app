# Data handling & privacy boundary

This is a privacy-first finance app. The guiding rule: **real financial data and the
public repo never meet.** The repo holds code, synthetic fixtures, and docs — nothing
real. Real data lives only on a private, offline instance. Because the boundary is
structural (not just discipline), pushing the repo is always safe.

## Two zones

| | **Public repo** (this folder, git-tracked, pushable) | **Private instance** (offline, never git-tracked) |
|---|---|---|
| Contents | Source code, synthetic CSV fixtures, docs, plan | Real bank CSVs, live PostgreSQL data, real `.env`, DB backups |
| Lives | In this working tree, on GitHub | On the home device only, reachable via Tailscale |
| Network | Can be public | Offline / private network only — taken offline before real data is loaded |
| Example data | `reference/bank_a.csv`, `reference/bank_b.csv` (fabricated) | `~/finance-data/imports/20240201_bank_a_a1.csv` (real, outside the repo) |

## Where real things live (all outside the repo)

- **Real CSV exports** → a directory *outside* the working tree, e.g.
  `~/finance-data/imports/`. Keeping them out of the tree entirely makes an accidental
  commit structurally impossible. (If one ever sits inside the tree, `.gitignore`
  catches it — see below — but outside is the stronger guarantee.)
- **The live database** → a Docker named volume or a path under a gitignored `./data/`.
  Never committed; backed up separately.
- **Backups / dumps** → outside the repo (home device, ideally a second location).
  A backup is only real once you've restored it into a clean DB and confirmed it works.
- **Secrets** → `.env` (gitignored). The repo ships `.env.example` with placeholder
  values only.

## The `.gitignore` safety net

[`.gitignore`](../.gitignore) enforces the boundary even if a file lands in the tree by
mistake:

- **Every `*.csv` is ignored**, with only the synthetic zones allow-listed: the two
  format samples (`reference/bank_*.csv`) and the generated test corpus
  (`fixtures/**/*.csv`, see [fixtures/README.md](../fixtures/README.md)). Drop a real
  export anywhere else and git won't see it — you'd have to `git add -f` on purpose.
- `./data/`, `./imports/`, `./backups/`, DB dumps, and `*.sqlite*` are ignored.
- `.env` and `.env.*` are ignored; `.env.example` is the only tracked env file.

> If you add a *new* synthetic fixture later, git will ignore it too (safe default) —
> allow it explicitly with a `!path/to/fixture.csv` line.

## Operating rule: offline before real data

1. **Develop and demo against the synthetic fixtures** with the app in normal dev mode.
2. **Before loading any real data**, take the instance offline / private — real data
   only ever exists on the home device, never on an internet-exposed surface. Internet
   exposure stays a deliberate later switch-on, never the default.
3. **Real imports go through the running app** (drag-drop upload → DB), reading from the
   external `~/finance-data/` location — not by copying CSVs into the repo.

## Before every push — checklist

Belt-and-suspenders on top of `.gitignore`:

- [ ] `git status` shows no `.csv` other than the two fixtures, no `.env`, no `data/`.
- [ ] `git diff --cached` contains no real merchant names, balances, account numbers, or
      locations.
- [ ] The pre-commit scan hook (below) is installed and passing.

### Pre-commit scan hook (install at Phase 0, once git exists)

Save as `.git/hooks/pre-commit`, `chmod +x` it. It blocks a commit that stages a real
CSV, a `.env`, or content matching a real-data signature:

```bash
#!/usr/bin/env bash
set -euo pipefail
staged=$(git diff --cached --name-only --diff-filter=ACM)
fail=0

# 1. No real CSVs — only the two synthetic fixtures are allowed.
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in
    reference/bank_a.csv|reference/bank_b.csv) ;;
    *.csv) echo "BLOCKED: $f looks like a real CSV import"; fail=1 ;;
  esac
done <<< "$staged"

# 2. No .env (only .env.example).
if echo "$staged" | grep -E '(^|/)\.env($|\.)' | grep -qv '\.env\.example'; then
  echo "BLOCKED: a .env file is staged"; fail=1
fi

# 3. Content scan — anonymised names must not reappear; tune this list to your data.
if git diff --cached -U0 | grep -nEi 'YOUR_BANK_A_NAME|YOUR_BANK_B_NAME|YOUR_SUBURB'; then
  echo "BLOCKED: staged content matches a real-data signature"; fail=1
fi

[ "$fail" -eq 0 ] || { echo "Pre-commit blocked — see docs/data-handling.md"; exit 1; }
```

## If real data ever lands in git

Deleting the file in a later commit is **not** enough — git keeps history. If real data
is committed:

1. **Before pushing:** if it's the last commit and unpushed, `git reset` it out and
   recommit clean.
2. **After it exists in history:** rewrite history to purge it (`git filter-repo`, or the
   BFG Repo-Cleaner), force-push, and rotate any exposed secret. Assume anything that was
   pushed is compromised.

The whole point of the structure above is to never need this.
