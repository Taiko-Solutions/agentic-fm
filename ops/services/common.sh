#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SERVICES_BASE_DIR="${HOME}/Library/Application Support/agentic-fm-services"
ACTIVE_REPO_FILE="${SERVICES_BASE_DIR}/active_repo.path"

LOG_DIR="${HOME}/Library/Logs/agentic-fm"
SERVICES_LOG="${LOG_DIR}/services.log"

COMPANION_PORT="8765"
WEBVIEWER_PORT="8080"
WEBVIEWER_CONTAINER_NAME="agentic-fm-webviewer"

ensure_log_dir() {
  mkdir -p "${LOG_DIR}"
}

ensure_services_base_dir() {
  mkdir -p "${SERVICES_BASE_DIR}"
}

timestamp_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

append_service_log() {
  local level="$1"
  local message="$2"
  ensure_log_dir
  printf '[%s] [%s] %s\n' "$(timestamp_utc)" "${level}" "${message}" >> "${SERVICES_LOG}"
}

log_info() {
  append_service_log "INFO" "$1"
}

log_warn() {
  append_service_log "WARN" "$1"
}

log_error() {
  append_service_log "ERROR" "$1"
}

notify_macos() {
  local title="$1"
  local message="$2"
  /usr/bin/osascript -e "display notification \"${message}\" with title \"${title}\"" >/dev/null 2>&1 || true
}

is_port_in_use() {
  local port="$1"
  /usr/sbin/lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t >/dev/null 2>&1
}

port_owner() {
  local port="$1"
  /usr/sbin/lsof -nP -iTCP:"${port}" -sTCP:LISTEN | /usr/bin/awk 'NR==2 {printf "%s (PID %s)", $1, $2; exit}'
}

get_active_repo() {
  if [[ -f "${ACTIVE_REPO_FILE}" ]]; then
    /bin/cat "${ACTIVE_REPO_FILE}"
  fi
}

set_active_repo() {
  local repo_path="$1"
  ensure_services_base_dir
  printf '%s\n' "${repo_path}" > "${ACTIVE_REPO_FILE}"
}

