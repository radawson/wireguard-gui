# Changelog

All notable changes to this project are documented in this file.

## 0.4.0 - 2026-03-12

### Added

- Added backend architecture layers:
  - `src/gui/services/`
  - `src/gui/repositories/`
  - `src/gui/integrations/wireguard/`
  - `src/gui/utils/command_runner.py`
  - `src/gui/errors.py`
- Added database safety tooling:
  - `scripts/db_validate.py`
  - `scripts/db_backfill_v0_4.py`
  - `migrations/README.md`
- Added operator/developer documentation set:
  - `docs/INSTALLATION.md`
  - `docs/UPGRADE.md`
  - `docs/CONFIGURATION.md`
  - `docs/OPERATIONS.md`
  - `docs/DEVELOPER_GUIDE.md`
  - `docs/RELEASE_CHECKLIST.md`
- Added smoke/regression tests in `tests/test_app_smoke.py`.
- Added WireGuard runtime sync and adapter safety controls:
  - new runtime sync service in `src/gui/services/runtime_sync_service.py`
  - startup server-mode auto sync plus manual admin resync action
  - adapter conflict checks for wizard/network create-update and activation preflight
- Added Tailwind build pipeline:
  - `package.json`
  - `tailwind.config.js`
  - `src/gui/static/src/tailwind.input.css`
  - compiled output at `src/gui/static/dist/css/output.css`

### Changed

- Replaced MDB-based templates with Tailwind-based templates across core pages:
  - `base`, `dashboard`, `networks`, `peers`, `settings`, `wizard_setup`,
    `network_detail`, `peer_detail`, `login`, `register`, `index`, `about`, `profile`, `test`.
- Reworked network/peer route flows to use service-layer orchestration and consistent JSON error handling.
- Improved command execution reliability by adding non-zero exit handling and typed command failures.
- Improved server-mode safety by preventing adapter overwrite when live WireGuard interfaces already exist.
- Updated IPv4 forwarding persistence to use `/etc/sysctl.d/99-wireguard-gui.conf` with `sysctl --system`.
- Updated app factory to support explicit config path and optional startup side effects.
- Updated docs index in `README.md` to point to dedicated docs pages.

### Removed

- Removed MDB runtime dependencies from templates and client interactions.
- Removed external `wireguard-tools` dependency from:
  - `requirements.in`
  - `requirements.txt`
  - `requirements-dev.txt`
  - `pyproject.toml`

### Notes for Production Upgrades

- UI backward compatibility is intentionally not preserved in this release.
- Database continuity is preserved through additive migration/backfill workflow.
- Run:
  - `python scripts/db_validate.py --db-path src/wg.db`
  - `python scripts/db_backfill_v0_4.py --db-path src/wg.db`
  - `python scripts/db_validate.py --db-path src/wg.db`
  before and after production rollout.
