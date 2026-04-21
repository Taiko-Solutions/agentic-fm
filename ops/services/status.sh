#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

COMPANION_LABEL="com.agenticfm.companion-server"
WEBVIEWER_LABEL="com.agenticfm.webviewer-docker"
COMPOSE_FILE="${ROOT_DIR}/webviewer/docker-compose.stable.yml"

agent_loaded() {
  local label="$1"
  launchctl print "gui/${UID}/${label}" >/dev/null 2>&1
}

companion_health() {
  curl -s --max-time 2 "http://127.0.0.1:${COMPANION_PORT}/health" || true
}

webviewer_http_code() {
  curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://127.0.0.1:${WEBVIEWER_PORT}" || true
}

current_container_repo() {
  docker inspect -f '{{range .Mounts}}{{if eq .Destination "/workspace"}}{{.Source}}{{end}}{{end}}' "${WEBVIEWER_CONTAINER_NAME}" 2>/dev/null || true
}

echo "== agentic-fm servicios locales =="
echo

if agent_loaded "${COMPANION_LABEL}"; then
  echo "LaunchAgent Companion: cargado (${COMPANION_LABEL})"
else
  echo "LaunchAgent Companion: no cargado (${COMPANION_LABEL})"
fi

HEALTH_JSON="$(companion_health)"
if [[ -n "${HEALTH_JSON}" ]]; then
  echo "Companion health: ${HEALTH_JSON}"
else
  echo "Companion health: sin respuesta en 127.0.0.1:${COMPANION_PORT}"
fi

echo

if agent_loaded "${WEBVIEWER_LABEL}"; then
  echo "LaunchAgent Webviewer: cargado (${WEBVIEWER_LABEL})"
else
  echo "LaunchAgent Webviewer: no cargado (${WEBVIEWER_LABEL})"
fi

if command -v docker >/dev/null 2>&1; then
  CONTAINER_STATUS="$(docker ps -a --filter "name=^${WEBVIEWER_CONTAINER_NAME}$" --format '{{.Status}}' | head -n 1)"
  if [[ -n "${CONTAINER_STATUS}" ]]; then
    echo "Docker container (${WEBVIEWER_CONTAINER_NAME}): ${CONTAINER_STATUS}"
    CONTAINER_REPO="$(current_container_repo)"
    if [[ -n "${CONTAINER_REPO}" ]]; then
      echo "Webviewer repo montado en contenedor: ${CONTAINER_REPO}"
    fi
  else
    echo "Docker container (${WEBVIEWER_CONTAINER_NAME}): no creado"
  fi
else
  echo "Docker: no disponible"
fi

ACTIVE_REPO="$(get_active_repo || true)"
if [[ -n "${ACTIVE_REPO}" ]]; then
  echo "Repo activo configurado para Webviewer: ${ACTIVE_REPO}"
else
  echo "Repo activo configurado para Webviewer: no definido"
fi

HTTP_CODE="$(webviewer_http_code)"
if [[ "${HTTP_CODE}" == "200" ]]; then
  echo "Webviewer HTTP: OK (200) en http://127.0.0.1:${WEBVIEWER_PORT}"
else
  echo "Webviewer HTTP: ${HTTP_CODE:-sin respuesta} en http://127.0.0.1:${WEBVIEWER_PORT}"
fi

echo
echo "Rutas útiles:"
echo "- Compose: ${COMPOSE_FILE}"
echo "- Logs launchd: ${HOME}/Library/Logs/agentic-fm/"
echo "- Log de eventos: ${HOME}/Library/Logs/agentic-fm/services.log"

