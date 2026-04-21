#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Uso:
  ./ops/services/use_repo.sh /ruta/al/repo/agentic-fm

Reglas:
  - La ruta debe contener webviewer/package.json
  - La ruta debe contener agent/scripts/companion_server.py
EOF
}

if [[ "${1:-}" == "" ]]; then
  usage
  exit 1
fi

RAW_INPUT="${1}"
if [[ "${RAW_INPUT}" == "~"* ]]; then
  RAW_INPUT="${HOME}${RAW_INPUT:1}"
fi

if [[ ! -d "${RAW_INPUT}" ]]; then
  echo "La ruta no existe: ${RAW_INPUT}"
  exit 1
fi

TARGET_REPO="$(cd "${RAW_INPUT}" && pwd -P)"

if [[ ! -f "${TARGET_REPO}/webviewer/package.json" ]]; then
  echo "Ruta inválida: falta ${TARGET_REPO}/webviewer/package.json"
  exit 1
fi

if [[ ! -f "${TARGET_REPO}/agent/scripts/companion_server.py" ]]; then
  echo "Ruta inválida: falta ${TARGET_REPO}/agent/scripts/companion_server.py"
  exit 1
fi

set_active_repo "${TARGET_REPO}"

MESSAGE="Repo activo de Webviewer cambiado a ${TARGET_REPO}"
log_info "${MESSAGE}"
notify_macos "agentic-fm Webviewer" "${MESSAGE}"

"${SCRIPT_DIR}/start_webviewer_docker.sh"

echo "${MESSAGE}"
"${SCRIPT_DIR}/status.sh"

