# Installation

## Supported Platform

- Debian-based Linux distributions (primary support target)
- Python 3.10+
- WireGuard kernel module + `wg`/`wg-quick`

## 1) Clone Repository

```bash
git clone https://github.com/radawson/wireguard-gui
cd wireguard-gui
```

## 2) Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Frontend CSS Build (Tailwind)

```bash
npm install
npm run build:css
```

Use `npm run watch:css` during development.

## 4) Configure Runtime

Edit `src/config.yaml` and set at least:

- `SECRET_KEY`
- `SUDO_PASSWORD` (if server mode)
- `MODE` (`database` or `server`)
- host/port and TLS paths as needed

## 5) Initialize and Run

```bash
cd src
python run.py
```

## 6) Optional: Production WSGI

```bash
cd src
python wsgi.py
```

Use systemd + reverse proxy for production deployments.
