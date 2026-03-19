#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

COMPANION_LABEL="com.agenticfm.companion-server"
WEBVIEWER_LABEL="com.agenticfm.webviewer-docker"

LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
COMPANION_PLIST="${LAUNCH_AGENTS_DIR}/${COMPANION_LABEL}.plist"
WEBVIEWER_PLIST="${LAUNCH_AGENTS_DIR}/${WEBVIEWER_LABEL}.plist"
COMPOSE_FILE="${ROOT_DIR}/webviewer/docker-compose.stable.yml"

agent_loaded() {
  local label="$1"
  launchctl print "gui/${UID}/${label}" >/dev/null 2>&1
}

ensure_installed() {
  if [[ ! -f "${COMPANION_PLIST}" || ! -f "${WEBVIEWER_PLIST}" ]]; then
    echo "No hay LaunchAgents instalados. Ejecutando instalación..."
    "${SCRIPT_DIR}/install_launchagents.sh"
    exit 0
  fi
}

start_agents() {
  ensure_installed

  launchctl enable "gui/${UID}/${COMPANION_LABEL}" >/dev/null 2>&1 || true
  launchctl enable "gui/${UID}/${WEBVIEWER_LABEL}" >/dev/null 2>&1 || true

  if ! agent_loaded "${COMPANION_LABEL}"; then
    launchctl bootstrap "gui/${UID}" "${COMPANION_PLIST}"
  fi
  if ! agent_loaded "${WEBVIEWER_LABEL}"; then
    launchctl bootstrap "gui/${UID}" "${WEBVIEWER_PLIST}"
  fi

  launchctl kickstart -k "gui/${UID}/${COMPANION_LABEL}" >/dev/null 2>&1 || true
  launchctl kickstart -k "gui/${UID}/${WEBVIEWER_LABEL}" >/dev/null 2>&1 || true
}

stop_agents() {
  launchctl disable "gui/${UID}/${COMPANION_LABEL}" >/dev/null 2>&1 || true
  launchctl disable "gui/${UID}/${WEBVIEWER_LABEL}" >/dev/null 2>&1 || true

  launchctl bootout "gui/${UID}" "${COMPANION_PLIST}" >/dev/null 2>&1 || true
  launchctl bootout "gui/${UID}" "${WEBVIEWER_PLIST}" >/dev/null 2>&1 || true

  if command -v docker >/dev/null 2>&1 && [[ -f "${COMPOSE_FILE}" ]]; then
    docker compose -f "${COMPOSE_FILE}" stop webviewer >/dev/null 2>&1 || true
  fi
}

usage() {
  cat <<'EOF'
Uso:
  ./ops/services/servicesctl.sh install
  ./ops/services/servicesctl.sh start
  ./ops/services/servicesctl.sh stop
  ./ops/services/servicesctl.sh restart
  ./ops/services/servicesctl.sh status
  ./ops/services/servicesctl.sh use-repo /ruta/al/repo/agentic-fm
  ./ops/services/servicesctl.sh uninstall
EOF
}

COMMAND="${1:-status}"

case "${COMMAND}" in
  install)
    "${SCRIPT_DIR}/install_launchagents.sh"
    ;;
  uninstall)
    "${SCRIPT_DIR}/uninstall_launchagents.sh"
    ;;
  start)
    start_agents
    "${SCRIPT_DIR}/status.sh"
    ;;
  stop)
    stop_agents
    "${SCRIPT_DIR}/status.sh"
    ;;
  restart)
    stop_agents
    start_agents
    "${SCRIPT_DIR}/status.sh"
    ;;
  status)
    "${SCRIPT_DIR}/status.sh"
    ;;
  use-repo)
    if [[ "${2:-}" == "" ]]; then
      usage
      exit 1
    fi
    "${SCRIPT_DIR}/use_repo.sh" "${2}"
    ;;
  *)
    usage
    exit 1
    ;;
esac

