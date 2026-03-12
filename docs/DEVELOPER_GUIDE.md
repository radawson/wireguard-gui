# Developer Guide

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
npm install
npm run build:css
```

## Architecture Overview

- `src/gui/routes/`: HTTP controllers
- `src/gui/services/`: workflow orchestration
- `src/gui/repositories/`: data access helpers
- `src/gui/integrations/wireguard/`: WireGuard integration boundary
- `src/gui/utils/`: shared utility primitives

## Testing

```bash
pytest
```

## Style and Safety

- Keep DB migrations additive-first for production compatibility.
- Avoid direct shelling in routes; use integration/service layers.
- Prefer typed/structured errors over broad exceptions.

## Frontend

- Tailwind source: `src/gui/static/src/tailwind.input.css`
- Tailwind output: `src/gui/static/dist/css/output.css`
- Build command: `npm run build:css`
