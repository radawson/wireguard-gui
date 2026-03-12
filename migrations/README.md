# Migration Notes

This project currently uses additive-first migration strategy for production safety.

Until full Alembic revision history is formalized, use:

- `scripts/db_validate.py` for pre/post checks
- `scripts/db_backfill_v0_4.py` for v0.4 compatibility normalization

Future schema updates should follow:

1. Add new columns/tables first.
2. Backfill data.
3. Switch application logic.
4. Remove deprecated columns in a later release.
