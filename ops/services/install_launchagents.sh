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

# Configuración overridable desde environment:
#   COMPANION_BIND_HOST   IP/hostname donde el companion escucha (default: 127.0.0.1)
COMPANION_BIND_HOST_VALUE="${COMPANION_BIND_HOST:-127.0.0.1}"

render_template() {
  local template_file="$1"
  local output_file="$2"
  /usr/bin/sed \
    -e "s#__HOME__#${HOME}#g" \
    -e "s#__ROOT__#${RUNTIME_ROOT}#g" \
    -e "s#__COMPANION_BIND_HOST__#${COMPANION_BIND_HOST_VALUE}#g" \
    "${template_file}" > "${output_file}"
}

prepare_runtime_files() {
  mkdir -p "${RUNTIME_SERVICES_DIR}" "${RUNTIME_AGENT_SCRIPTS_DIR}" "${RUNTIME_WEBVIEWER_DIR}"
  /usr/bin/rsync -a --delete "${SCRIPT_DIR}/" "${RUNTIME_SERVICES_DIR}/"
  /bin/cp "${ROOT_DIR}/agent/scripts/companion_server.py" "${RUNTIME_AGENT_SCRIPTS_DIR}/companion_server.py"
  /bin/cp "${ROOT_DIR}/version.txt" "${RUNTIME_ROOT}/version.txt"
  if [[ -f "${ROOT_DIR}/webviewer/docker-compose.stable.yml" ]]; then
    /bin/cp "${ROOT_DIR}/webviewer/docker-compose.stable.yml" "${RUNTIME_WEBVIEWER_DIR}/docker-compose.stable.yml"
  fi
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

if [[ ! -f "${COMPANION_TEMPLATE}" ]]; then
  echo "Falta plantilla de companion en ${RUNTIME_SERVICES_DIR}/launchd."
  exit 1
fi

render_template "${COMPANION_TEMPLATE}" "${COMPANION_PLIST}"

# Webviewer es opcional — requiere docker-compose.stable.yml en el repo fuente.
INSTALL_WEBVIEWER=0
if [[ -f "${WEBVIEWER_TEMPLATE}" && -f "${ROOT_DIR}/webviewer/docker-compose.stable.yml" ]]; then
  render_template "${WEBVIEWER_TEMPLATE}" "${WEBVIEWER_PLIST}"
  INSTALL_WEBVIEWER=1
else
  echo "Webviewer LaunchAgent omitido (falta webviewer/docker-compose.stable.yml)."
fi

safe_bootout "${COMPANION_PLIST}"
launchctl enable "gui/${UID}/${COMPANION_LABEL}" >/dev/null 2>&1 || true
bootstrap_agent "${COMPANION_PLIST}"
kickstart_agent "${COMPANION_LABEL}"

if [[ "${INSTALL_WEBVIEWER}" -eq 1 ]]; then
  safe_bootout "${WEBVIEWER_PLIST}"
  launchctl enable "gui/${UID}/${WEBVIEWER_LABEL}" >/dev/null 2>&1 || true
  bootstrap_agent "${WEBVIEWER_PLIST}"
  kickstart_agent "${WEBVIEWER_LABEL}"
fi

echo "LaunchAgents instalados:"
echo "- ${COMPANION_PLIST}  (COMPANION_BIND_HOST=${COMPANION_BIND_HOST_VALUE})"
if [[ "${INSTALL_WEBVIEWER}" -eq 1 ]]; then
  echo "- ${WEBVIEWER_PLIST}"
fi
echo "- Runtime: ${RUNTIME_ROOT}"
echo
echo "Estado actual:"
"${RUNTIME_SERVICES_DIR}/status.sh"
