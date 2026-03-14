# Operations

## Two-Service Architecture

The system uses **privilege separation** via two systemd services:

| Service | User | Purpose |
| --- | --- | --- |
| `wg-daemon.service` | root | Privileged helper that manages WireGuard interfaces, peers, and routes via a Unix socket |
| `wg_db.service` | unprivileged | Flask web GUI that connects to `wg-daemon` over `/var/run/wg-daemon.sock` |

The GUI never runs as root and never needs `sudo`. All privileged
WireGuard operations are dispatched to `wg-daemon` over a JSON-over-Unix-socket protocol.

### Setup

1. Create the `wireguard` group (used for socket permissions):

```bash
sudo groupadd wireguard
sudo usermod -aG wireguard <gui-user>
```

1. Install both services:

```bash
# Privileged daemon (from wireguard-tools repo)
sudo cp /path/to/wireguard-tools/contrib/wg-daemon.service /etc/systemd/system/
# Edit ExecStart to point at the venv where wireguard-tools is installed

# Web GUI
sudo cp contrib/wg_db.service /etc/systemd/system/
# Edit User, WorkingDirectory, ExecStart to match your install

sudo systemctl daemon-reload
sudo systemctl enable --now wg-daemon.service wg_db.service
```

**Important:** `ExecStart` must point to the **venv** Python
(e.g. `/home/<user>/wireguard-gui/.venv/bin/python`), not `/usr/bin/python3`.
System Python will not have the project's dependencies installed.

### Socket Configuration

The daemon listens on `/var/run/wg-daemon.sock` by default. Override
with the `WG_DAEMON_SOCKET` environment variable (set in both service
files if changed).

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
