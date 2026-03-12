# Operations

## Service Lifecycle

- Start app with `python src/run.py` for local/dev.
- For production, run WSGI behind reverse proxy and systemd.

## Backups

- Database: backup `src/wg.db` regularly.
- Config: backup `src/config.yaml`.
- Generated output: backup `src/output/` if needed.

## Health and Troubleshooting

- Check app logs and reverse proxy logs first.
- In `server` mode, startup performs a best-effort runtime sync from `wg` into the DB.
- If runtime state drifts from DB, use **Admin -> Resync from WireGuard** to import adapters/peers.
- Validate database before/after upgrades:
  - `python scripts/db_validate.py --db-path src/wg.db`
- Rebuild Tailwind CSS after frontend/template updates:
  - `npm run build:css`

## Common Recovery Actions

- Restore DB from backup.
- Re-run `scripts/db_backfill_v0_4.py` after schema/data drift.
- Re-apply dependency installation from `requirements.txt`.
- If adapter operations fail because an adapter is already running, run runtime resync and retry.

## Adapter Safety Rules (Server Mode)

- Network create/update is blocked when a target adapter already exists live and is not owned by the same DB network.
- Wizard basic setup refuses to overwrite a running adapter (for example, existing `wg0`).
- Activation checks adapter state before `wg-quick up`; if adapter is already up for that same network, it returns a safe no-op.
- Runtime sync errors are non-fatal for app startup but logged for operator visibility.
