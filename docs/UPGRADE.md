# Upgrade Guide

This guide is for production-safe upgrades, including database continuity checks.

## Pre-Upgrade Checklist

1. Stop application traffic.
2. Backup database file.
3. Record current app version and commit.
4. Verify free disk space.

## Database Backup (SQLite)

```bash
cp src/wg.db "src/wg.db.backup.$(date +%Y%m%d%H%M%S)"
```

## Validate Existing Database Before Upgrade

```bash
python scripts/db_validate.py --db-path src/wg.db
```

## Apply Upgrade

```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt
npm install
npm run build:css
```

## Run Additive Data Backfill

```bash
python scripts/db_backfill_v0_4.py --db-path src/wg.db
```

## Post-Upgrade Validation

```bash
python scripts/db_validate.py --db-path src/wg.db
```

Then run smoke checks:

- Login
- Dashboard loads
- Networks list/add/edit/delete
- Peers list/add/edit/delete
- Wizard basic setup

## Rollback

1. Stop application.
2. Restore backed up DB.
3. Checkout previous known-good commit.
4. Restart service.
