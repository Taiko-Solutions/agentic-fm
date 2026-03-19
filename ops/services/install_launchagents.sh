#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
RUNTIME_BASE="${HOME}/Library/Application Support/agentic-fm-services"
RUNTIME_ROOT="${RUNTIME_BASE}/runtime"
RUNTIME_SERVICES_DIR="${RUNTIME_ROOT}/ops/services"
RUNTIME_AGENT_SCRIPTS_DIR="${RUNTIME_ROOT}/agent/scripts"
RUNTIME_WEBVIEWER_DIR="${RUNTIME_ROOT}/webviewer"

COMPANION_LABEL="com.agenticfm.companion-server"
WEBVIEWER_LABEL="com.agenticfm.webviewer-docker"
COMPANION_TEMPLATE="${RUNTIME_SERVICES_DIR}/launchd/${COMPANION_LABEL}.plist.template"
WEBVIEWER_TEMPLATE="${RUNTIME_SERVICES_DIR}/launchd/${WEBVIEWER_LABEL}.plist.template"

COMPANION_PLIST="${LAUNCH_AGENTS_DIR}/${COMPANION_LABEL}.plist"
WEBVIEWER_PLIST="${LAUNCH_AGENTS_DIR}/${WEBVIEWER_LABEL}.plist"

render_template() {
  local template_file="$1"
  local output_file="$2"
  /usr/bin/sed \
    -e "s#__HOME__#${HOME}#g" \
    -e "s#__ROOT__#${RUNTIME_ROOT}#g" \
    "${template_file}" > "${output_file}"
}

prepare_runtime_files() {
  mkdir -p "${RUNTIME_SERVICES_DIR}" "${RUNTIME_AGENT_SCRIPTS_DIR}" "${RUNTIME_WEBVIEWER_DIR}"
  /usr/bin/rsync -a --delete "${SCRIPT_DIR}/" "${RUNTIME_SERVICES_DIR}/"
  /bin/cp "${ROOT_DIR}/agent/scripts/companion_server.py" "${RUNTIME_AGENT_SCRIPTS_DIR}/companion_server.py"
  /bin/cp "${ROOT_DIR}/version.txt" "${RUNTIME_ROOT}/version.txt"
  /bin/cp "${ROOT_DIR}/webviewer/docker-compose.stable.yml" "${RUNTIME_WEBVIEWER_DIR}/docker-compose.stable.yml"
  /bin/chmod +x "${RUNTIME_SERVICES_DIR}"/*.sh
}

safe_bootout() {
  local plist_path="$1"
  launchctl bootout "gui/${UID}" "${plist_path}" >/dev/null 2>&1 || true
}

bootstrap_agent() {
  local plist_path="$1"
  launchctl bootstrap "gui/${UID}" "${plist_path}"
}

kickstart_agent() {
  local label="$1"
  launchctl kickstart -k "gui/${UID}/${label}" >/dev/null 2>&1 || true
}


mkdir -p "${LAUNCH_AGENTS_DIR}"
ensure_log_dir
prepare_runtime_files
CURRENT_ACTIVE_REPO="$(get_active_repo || true)"
if [[ -z "${CURRENT_ACTIVE_REPO}" || ! -d "${CURRENT_ACTIVE_REPO}" ]]; then
  set_active_repo "${ROOT_DIR}"
fi

if [[ ! -f "${COMPANION_TEMPLATE}" || ! -f "${WEBVIEWER_TEMPLATE}" ]]; then
  echo "Faltan plantillas de launchd en ${RUNTIME_SERVICES_DIR}/launchd."
  exit 1
fi

render_template "${COMPANION_TEMPLATE}" "${COMPANION_PLIST}"
render_template "${WEBVIEWER_TEMPLATE}" "${WEBVIEWER_PLIST}"

safe_bootout "${COMPANION_PLIST}"
safe_bootout "${WEBVIEWER_PLIST}"
launchctl enable "gui/${UID}/${COMPANION_LABEL}" >/dev/null 2>&1 || true
launchctl enable "gui/${UID}/${WEBVIEWER_LABEL}" >/dev/null 2>&1 || true

bootstrap_agent "${COMPANION_PLIST}"
bootstrap_agent "${WEBVIEWER_PLIST}"

kickstart_agent "${COMPANION_LABEL}"
kickstart_agent "${WEBVIEWER_LABEL}"

echo "LaunchAgents instalados:"
echo "- ${COMPANION_PLIST}"
echo "- ${WEBVIEWER_PLIST}"
echo "- Runtime: ${RUNTIME_ROOT}"
echo
echo "Estado actual:"
"${RUNTIME_SERVICES_DIR}/status.sh"

