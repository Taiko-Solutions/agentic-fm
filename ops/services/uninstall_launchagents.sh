#!/usr/bin/env bash

set -euo pipefail

COMPANION_LABEL="com.agenticfm.companion-server"
WEBVIEWER_LABEL="com.agenticfm.webviewer-docker"

LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
COMPANION_PLIST="${LAUNCH_AGENTS_DIR}/${COMPANION_LABEL}.plist"
WEBVIEWER_PLIST="${LAUNCH_AGENTS_DIR}/${WEBVIEWER_LABEL}.plist"
RUNTIME_BASE="${HOME}/Library/Application Support/agentic-fm-services"

launchctl bootout "gui/${UID}" "${COMPANION_PLIST}" >/dev/null 2>&1 || true
launchctl bootout "gui/${UID}" "${WEBVIEWER_PLIST}" >/dev/null 2>&1 || true

rm -f "${COMPANION_PLIST}" "${WEBVIEWER_PLIST}"
rm -rf "${RUNTIME_BASE}"

echo "LaunchAgents eliminados y descargados:"
echo "- ${COMPANION_PLIST}"
echo "- ${WEBVIEWER_PLIST}"
echo "- Runtime eliminado: ${RUNTIME_BASE}"

