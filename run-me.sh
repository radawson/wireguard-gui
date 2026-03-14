#!/usr/bin/env bash
# Idempotent installer mirroring docs/INSTALLATION.md
VERSION=0.2.0

set -euo pipefail

REPO_ROOT=""
TOOLS_REPO_ROOT=""

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

set_tools_repo_root() {
  # Prefer sibling repo in split-project layout.
  local sibling
  sibling="$(cd "${REPO_ROOT}/.." && pwd)/wireguard-tools"
  if [[ -d "${sibling}/.git" ]]; then
    TOOLS_REPO_ROOT="${sibling}"
    log "Using wireguard-tools repository at ${TOOLS_REPO_ROOT}"
    return
  fi

  # Otherwise mirror quick-start: clone into ~/wireguard-tools if missing.
  TOOLS_REPO_ROOT="${HOME}/wireguard-tools"
  if [[ ! -d "${TOOLS_REPO_ROOT}/.git" ]]; then
    log "Cloning wireguard-tools to ${TOOLS_REPO_ROOT}"
    git clone https://github.com/radawson/wireguard-tools "${TOOLS_REPO_ROOT}"
  else
    log "Using existing wireguard-tools repository at ${TOOLS_REPO_ROOT}"
  fi
}

install_node_deps() {
  log "Installing Node dependencies"
  # Check if node is installed
  if ! command -v node >/dev/null 2>&1; then
    log "Node is not installed"
    require_command curl
    log "Installing Node.js"
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt-get install -y nodejs
  fi
  cd "${REPO_ROOT}"
  log "Installing Node dependencies"
  npm install
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
  if [[ -f "${TOOLS_REPO_ROOT}/pyproject.toml" ]]; then
    log "Installing local wireguard-tools package from ${TOOLS_REPO_ROOT}"
    .venv/bin/pip install -e "${TOOLS_REPO_ROOT}"
  else
    log "wireguard-tools repository not found; installing from PyPI"
    .venv/bin/pip install "wireguard-tools>=0.7.0"
  fi
  .venv/bin/pip install -r requirements.txt
}

build_frontend_css() {
  cd "${REPO_ROOT}"
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

If you run in server mode with the daemon:
  1) Install wg-daemon systemd unit from wireguard-tools:
     sudo cp "${TOOLS_REPO_ROOT}/contrib/wg-daemon.service" /etc/systemd/system/
  2) Install GUI service unit:
     sudo cp "${REPO_ROOT}/contrib/wg_db.service" /etc/systemd/system/
  3) Update ExecStart/User paths in both unit files for your environment.
  4) Enable services:
     sudo systemctl daemon-reload
     sudo systemctl enable --now wg-daemon.service wg_db.service
EOF
}

main() {
  require_non_root
  require_command git
  require_command python3
  set_repo_root
  set_tools_repo_root
  install_node_deps
  install_python_deps
  build_frontend_css
  print_config_reminder
}

main "$@"
