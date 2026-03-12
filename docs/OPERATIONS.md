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
- Validate database before/after upgrades:
  - `python scripts/db_validate.py --db-path src/wg.db`
- Rebuild Tailwind CSS after frontend/template updates:
  - `npm run build:css`

## Common Recovery Actions

- Restore DB from backup.
- Re-run `scripts/db_backfill_v0_4.py` after schema/data drift.
- Re-apply dependency installation from `requirements.txt`.
