# WireGuard GUI

WireGuard GUI is a Flask-based management panel for WireGuard networks, focused on self-hosted and small operator deployments.

## Highlights

- Native in-repo WireGuard integration (`src/wireguard_tools`) instead of external dependency coupling.
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
