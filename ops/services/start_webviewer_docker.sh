#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

ensure_log_dir

COMPOSE_FILE="${ROOT_DIR}/webviewer/docker-compose.stable.yml"

resolve_host_root() {
  local from_file
  from_file="$(get_active_repo || true)"
  if [[ -n "${from_file}" ]]; then
    printf '%s\n' "${from_file}"
    return
  fi
  if [[ -n "${AGENTIC_FM_HOST_ROOT:-}" ]]; then
    printf '%s\n' "${AGENTIC_FM_HOST_ROOT}"
    return
  fi
  printf '%s\n' "${ROOT_DIR}"
}

current_container_repo() {
  docker inspect -f '{{range .Mounts}}{{if eq .Destination "/workspace"}}{{.Source}}{{end}}{{end}}' "${WEBVIEWER_CONTAINER_NAME}" 2>/dev/null || true
}

validate_host_root() {
  local repo_root="$1"
  [[ -d "${repo_root}" ]] || return 1
  [[ -f "${repo_root}/webviewer/package.json" ]] || return 1
  [[ -f "${repo_root}/agent/scripts/companion_server.py" ]] || return 1
}

HOST_ROOT="$(resolve_host_root)"
if [[ -d "${HOST_ROOT}" ]]; then
  HOST_ROOT="$(cd "${HOST_ROOT}" && pwd -P)"
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  MESSAGE="No existe ${COMPOSE_FILE}."
  log_error "${MESSAGE}"
  notify_macos "agentic-fm Webviewer" "${MESSAGE}"
  exit 1
fi

if ! validate_host_root "${HOST_ROOT}"; then
  MESSAGE="Repo activo inválido para Webviewer: ${HOST_ROOT}. Debe contener webviewer/package.json y agent/scripts/companion_server.py."
  log_error "${MESSAGE}"
  notify_macos "agentic-fm Webviewer" "${MESSAGE}"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  MESSAGE="No se encontró Docker CLI; no se puede arrancar Webviewer."
  log_error "${MESSAGE}"
  notify_macos "agentic-fm Webviewer" "${MESSAGE}"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  MESSAGE="Docker/OrbStack no está disponible todavía; se reintentará en el próximo ciclo."
  log_warn "${MESSAGE}"
  notify_macos "agentic-fm Webviewer" "${MESSAGE}"
  exit 0
fi

CONTAINER_RUNNING=0
if docker ps --format '{{.Names}}' | grep -qx "${WEBVIEWER_CONTAINER_NAME}"; then
  CONTAINER_RUNNING=1
  CURRENT_REPO="$(current_container_repo)"
  if [[ "${CURRENT_REPO}" == "${HOST_ROOT}" ]]; then
    log_info "Webviewer ya está en ejecución con repo activo ${HOST_ROOT}."
    exit 0
  fi
  log_info "Webviewer en ejecución con repo ${CURRENT_REPO}; se recreará para usar ${HOST_ROOT}."
fi

if [[ "${CONTAINER_RUNNING}" -eq 0 ]] && is_port_in_use "${WEBVIEWER_PORT}"; then
  OWNER="$(port_owner "${WEBVIEWER_PORT}")"
  MESSAGE="No se arranca Webviewer Docker: puerto ${WEBVIEWER_PORT} ocupado por ${OWNER}."
  log_warn "${MESSAGE}"
  notify_macos "agentic-fm Webviewer" "${MESSAGE}"
  exit 0
fi

log_info "Arrancando Webviewer en Docker con ${COMPOSE_FILE} (host root: ${HOST_ROOT})."
if ! AGENTIC_FM_HOST_ROOT="${HOST_ROOT}" docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans; then
  MESSAGE="Error al arrancar el contenedor de Webviewer."
  log_error "${MESSAGE}"
  notify_macos "agentic-fm Webviewer" "${MESSAGE}"
  exit 1
fi

HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${WEBVIEWER_PORT}" || true)"
if [[ "${HTTP_CODE}" != "200" ]]; then
  log_warn "Webviewer Docker arrancado; comprobación inicial HTTP=${HTTP_CODE} (puede tardar unos segundos)."
else
  log_info "Webviewer operativo en http://127.0.0.1:${WEBVIEWER_PORT}."
fi

