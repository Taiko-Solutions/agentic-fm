# Novedades de la capa Taiko (rama `taiko`)

Changelog de reglas, scripts, catálogos y fmlint de la rama `taiko`. Lo leen `session_start.py`, `agentic-fm-sync` y Agentic-FM-APP para decir qué llega a un clon. `UPDATES.md` es el changelog de upstream (petrowsky).

**Regla:** toda PR a `taiko` que cambie reglas o herramientas añade una entrada aquí, la más reciente arriba, con `**Acción requerida:**` u `**Acción opcional:**` cuando el desarrollador deba hacer algo.

## 2026-10-02 — Procedimientos de sesión en el repo y plugin taiko-filemaker

**Acción requerida:** instala el plugin `taiko-filemaker` del marketplace `taiko` (README de `claude-plugins`). Los prompts Nueva-Tarea/Puesta-Al-Dia/Nuevo-Proyecto del vault quedan retirados.

- `agent/docs/taiko/sessions/fm-sesion.md` y `fm-nuevo-proyecto.md`: lo que leen las skills `fm-sesion` y `fm-nuevo-proyecto`. El hook `SessionStart` del plugin ejecuta `session_start.py` e inyecta el resumen en cada sesión dentro de un clon.

## 2026-10-01 — Modelo de ramas trabajo/taiko/mejora, hook de cuatro capas y agentic-fm-sync

**Acción requerida:** en cada clon, una vez: `git pull origin taiko && agentic-fm-sync --migrar` (crea `trabajo`, deja `taiko` como espejo, quita `upstream` si lo hubiera, reinstala el hook). Instala el symlink nuevo: `ln -sf "$PWD/agent/scripts/bin/agentic-fm-sync" ~/bin/agentic-fm-sync`.

- Clones: `taiko` = espejo (sin commits propios), `trabajo` = todo lo del cliente (nunca se sube), `mejora/<tema>` = solo capa herramientas, PR a `taiko`.
- Hook pre-push: prohibidos (como antes) + bloqueo de `taiko`/`trabajo` desde clones + allowlist de la capa herramientas en cualquier otra rama del clon (`agent/scripts/hooks/paths.conf`) + aviso si se tocan reglas sin entrada aquí. `agentic-fm-safe-push` y la GitHub Action usan las mismas reglas (`agent/scripts/check_pushed_paths.py`).
- `session_start.py` lista las novedades de este fichero cuando el clon va por detrás y avisa si estás en `taiko` dentro de un clon.
- `agentic-fm-sync --migrar` detecta una reescritura de `origin/taiko` (force-push) con el reflog del remoto: realinea `taiko`/`trabajo` a la historia nueva y reaplica solo los commits propios (sin merges); lo anterior queda en `backup/trabajo-pre-reescritura-<fecha>`.
- Seguridad: `agentic-fm-sync` nunca descarta commits locales de `taiko` (sin `--migrar` se detiene; con `--migrar` los mueve a `trabajo` o los guarda en `backup/taiko-local-<fecha>`). El hook lleva copia de `check_pushed_paths.py` y `paths.conf` en `.git/hooks/` y es **fail-closed**: sin ellas, un clon no puede hacer push. La Action usa las reglas de la rama base y mira commit a commit (merges incluidos).

## 2026-10-01 — ProofKit: gotchas F13–F19, deploy estándar en FileMaker 2026 y plantilla CLAUDE-webapp.md nueva

**Acción requerida:** apps web ProofKit existentes: sustituir su `CLAUDE.md` por `agent/docs/taiko/proofkit/CLAUDE-webapp.md` (ajustando el bloque "Este proyecto"). Verificar que el objeto Web Viewer se llama `web`.
**Acción requerida:** `.mcp.json` pasa a `proofkit mcp` (forma oficial desde ProofKit 3.2.0): `~/.local/bin` debe estar en el PATH de las sesiones de Claude (`echo $PATH` dentro de Claude Code).

- Nombre del Web Viewer `web` (F13); `PK_send_callback` resuelve en la ventana activa (F14); cerrar la pantalla antes de `deploy_html` (F15); `fmBridge` en dev dentro de FM con `?wv=web` (F16); esperar a `window.FileMaker` (F17); claves UUIDDecimal nunca por OData (F19).
- Deploy FM 2026: `deploy_html` guarda en el almacén persistente; el WV lee `"data:text/html," & GetPersistentData ( "proofkit" ; "<app>" )`. Sobrevive migraciones.
- Docs alineados: `proofkit/README.md`, `taiko/README.md`, `troubleshooting.md`, `conventions.md`.
- **Corrección (2026-10-01, tarde):** la PR #11 borró `.cursor/` creyendo que eran copias; en realidad `.claude/skills` es un symlink a `.cursor/skills` (estructura de upstream) y las 25 skills desaparecieron. Restaurado en `taiko`; `agentic-fm-sync` lo trae. Si en un clon `ls .claude/skills/` está vacío o da error, sincroniza.

## 2026-10-01 — Perform Script: orden de los hijos (fmlint X004) y X003 sin falsos positivos

- `<Script>` debe ir el **último** (`FileReference → Calculated → Calculation → Script`); si va primero FileMaker acepta el paste y el paso no llama a nada. Detalle en `agent/docs/taiko/knowledge/silent-discard-params.md`; `fmlint` X004 lo bloquea.
- X003 ya no se dispara en llamadas al mismo archivo con `<FileReference/>` vacío.
- `clipboard.py` pasa el AppleScript por stdin: snippets grandes (una app HTML en `Insert Text`) ya no fallan.
- Catálogo: `Perform Script` documenta `<Calculated>` (by name) y `<FileReference>`.

## 2026-09-19 — Propuestas de clones aplicadas (PRs #7–#10)

- Herramientas de historial del MCP `agentic-fm-app` en el árbol de búsqueda; 17 propuestas de clones registradas en `agent/UPSTREAM_PROPOSALS.md`; `fmparse.sh` borra el `.txt` de CFs sensibles en explode multi-BD; knowledge `SQL.Get*` devuelve `?` con TO no relacionada.
