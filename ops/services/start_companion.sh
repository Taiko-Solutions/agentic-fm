#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

ensure_log_dir

export PATH="${HOME}/bin:${PATH}"
if [[ -x "${HOME}/bin/fm-xml-export-exploder" ]]; then
  export FM_XML_EXPLODER_BIN="${HOME}/bin/fm-xml-export-exploder"
fi

BIND_HOST="${COMPANION_BIND_HOST:-127.0.0.1}"

if is_port_in_use "${COMPANION_PORT}"; then
  OWNER="$(port_owner "${COMPANION_PORT}")"
  MESSAGE="No se arranca Companion: puerto ${COMPANION_PORT} ocupado por ${OWNER}."
  log_warn "${MESSAGE}"
  notify_macos "agentic-fm Companion" "${MESSAGE}"
  exit 0
fi

PYTHON_BIN="${ROOT_DIR}/.venv/bin/python3"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="/usr/bin/python3"
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  MESSAGE="No se encontró python3 ejecutable para Companion Server."
  log_error "${MESSAGE}"
  notify_macos "agentic-fm Companion" "${MESSAGE}"
  exit 1
fi

COMPANION_SCRIPT="${ROOT_DIR}/agent/scripts/companion_server.py"
if [[ ! -f "${COMPANION_SCRIPT}" ]]; then
  MESSAGE="No existe ${COMPANION_SCRIPT}."
  log_error "${MESSAGE}"
  notify_macos "agentic-fm Companion" "${MESSAGE}"
  exit 1
fi

log_info "Arrancando Companion Server en ${BIND_HOST}:${COMPANION_PORT} con ${PYTHON_BIN}."
exec env COMPANION_BIND_HOST="${BIND_HOST}" "${PYTHON_BIN}" "${COMPANION_SCRIPT}" --port "${COMPANION_PORT}"
