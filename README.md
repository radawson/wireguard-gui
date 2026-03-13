# WireGuard GUI

WireGuard GUI is a Flask-based management panel for WireGuard networks, focused on self-hosted and small operator deployments.

## Highlights

- Uses the [`wireguard-tools`](https://github.com/radawson/wireguard-tools) Python library (forked from [cmusatyalab/wireguard-tools](https://github.com/cmusatyalab/wireguard-tools)) for pure-Python WireGuard UAPI, netlink, and wg-quick operations.
- Tailwind frontend stack with material-inspired UI patterns.
- Modular backend boundaries:
  - routes/controllers
  - services
  - repositories
  - integration adapters
- Production-safe DB continuity workflow with validation + backfill scripts.

## Quick Start

```bash
git clone https://github.com/radawson/wireguard-gui
cd wireguard-gui
python3 -m venv .venv
source .venv/bin/activate
pip install -e ../wireguard-tools  # or: pip install wireguard-tools>=0.7.0
pip install -r requirements.txt
npm install
npm run build:css
cd src
python run.py
```

## Documentation

- [Installation](docs/INSTALLATION.md)
- [Upgrade](docs/UPGRADE.md)
- [Configuration](docs/CONFIGURATION.md)
- [Operations](docs/OPERATIONS.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)
- [Release Checklist](docs/RELEASE_CHECKLIST.md)

## Development Roadmap

Current roadmap is tracked in [ROADMAP.md](ROADMAP.md).
