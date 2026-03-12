#!/usr/bin/env bash
# Idempotent installer mirroring docs/INSTALLATION.md

set -euo pipefail

log() {
  printf "\n[run-me] %s\n" "$1"
}

require_non_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    echo "Please run as a normal user (not root)."
    exit 1
  fi
}

require_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}"
    echo "Install it first, then rerun this script."
    exit 1
  fi
}

set_repo_root() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  # If script is run inside an existing clone, use it.
  if [[ -f "${script_dir}/pyproject.toml" ]]; then
    REPO_ROOT="${script_dir}"
    return
  fi

  # Otherwise mirror docs: clone into ~/wireguard-gui if missing.
  REPO_ROOT="${HOME}/wireguard-gui"
  if [[ ! -d "${REPO_ROOT}/.git" ]]; then
    log "Cloning repository to ${REPO_ROOT}"
    git clone https://github.com/radawson/wireguard-gui "${REPO_ROOT}"
  else
    log "Using existing repository at ${REPO_ROOT}"
  fi
}

install_python_deps() {
  cd "${REPO_ROOT}"
  if [[ ! -d ".venv" ]]; then
    log "Creating virtual environment"
    python3 -m venv .venv
  else
    log "Virtual environment already exists"
  fi

  log "Installing Python dependencies"
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
}

build_frontend_css() {
  cd "${REPO_ROOT}"
  log "Installing frontend dependencies"
  npm install
  log "Building Tailwind CSS"
  npm run build:css
}

print_config_reminder() {
  cat <<EOF

[run-me] Installation steps complete.

Before running, edit:
  ${REPO_ROOT}/src/config.yaml

Set at least:
  - SECRET_KEY
  - SUDO_PASSWORD (if MODE=server)
  - MODE (database/server)
  - HOST_IP / HOST_PORT and TLS paths as needed

Run app:
  cd "${REPO_ROOT}/src"
  ../.venv/bin/python run.py

Optional (production WSGI):
  cd "${REPO_ROOT}/src"
  ../.venv/bin/python wsgi.py
EOF
}

main() {
  require_non_root
  require_command git
  require_command python3
  require_command npm
  set_repo_root
  install_python_deps
  build_frontend_css
  print_config_reminder
}

main "$@"
