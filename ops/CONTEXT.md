# Operations

Deploy config, monitoring, and operational runbooks.

## Infrastructure

- Hosting: home device (Pi / NAS / spare machine), always-on. Phase 7.
- Database: self-hosted PostgreSQL in a container. **Encrypted nightly `pg_dump`** to
  an off-device location — and a *tested* restore (restore into a clean DB and
  confirm it works; an untested backup is not a backup).
- Network: **Tailscale** on the device + each family member's phone/laptop. Private
  access only — nothing on the public internet in v1. Internet exposure (Cloudflare
  Tunnel) is a Phase 8 switch-on, not a rebuild.
- Domain: none in v1 (Tailscale handles addressing).

## Compose layout

`docker-compose` lives here in `ops/deploy/` (the house standard). Dev runs the DB in
Docker with local servers; a dev boot script belongs in `ops/scripts/` (see how the
zircon project does `ops/scripts/dev.sh`).

## Deploy process

Phase 7. In short: build images → bring up Postgres + app via compose on the home
device → connect family devices over Tailscale → switch on MFA (the Phase-0 hook) →
security pass (deps current, no secrets in git, HTTPS end-to-end).

## Monitoring

- At minimum: app up/down, import errors, and backup success/failure.
- Alerts go to Geodude (channel TBD at Phase 7).

## Runbooks

Store runbooks in `scripts/` for common tasks:
- How to roll back a deploy
- How to restore from backup (and the routine that *tests* it)
- How to take and verify an encrypted `pg_dump`

## Rules

- All deploy/ops scripts must be idempotent (safe to run twice).
- Never trust an untested backup with the family's only copy of their financial data.
- No secrets in git; `.env` only.
