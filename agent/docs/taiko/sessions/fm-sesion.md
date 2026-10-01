# Sesión de trabajo en un clon agentic-fm (Taiko)

> Para el agente. Si el hook del plugin ya inyectó el resumen de `session_start.py`, no lo repitas: interprétalo.

## 1. Estado del entorno

Si no tienes el resumen en contexto: `python3 agent/scripts/session_start.py`. Línea a línea:

| Línea | Qué hacer |
|---|---|
| `git` WARN "estás en la rama taiko de un clon" | Propón `agentic-fm-sync --migrar` (una vez) y espera el OK; nunca trabajes en `taiko`. |
| `git` WARN "N commit(s) por detrás … novedades: …" | Propón `agentic-fm-sync`; resume las novedades que lista (vienen de `TAIKO-UPDATES.md`). Si alguna dice "Acción requerida", díselo al desarrollador antes de seguir. |
| `env` FAIL (no macOS / sin osascript) | Lee `agent/docs/SANDBOXED_ENVIRONMENT.md`. |
| `embedded` STALE/MISSING | Avisa: el código agentic-fm embebido en la solución está desfasado; re-pegar desde `filemaker/` **[app]**. |
| `companion` sin responder | `agentic-fm-start` **[app]**; si no arranca, sigue en Tier 1 (clipboard) y dilo. |
| `companion` plug-in instalado pero no usable | Ruta OSS; como mucho un aviso en la sesión. |
| `proofkit` SKIP | Flujo estático. Si la tarea necesita estado vivo, pide correr *"Connect To ProofKit MCP"* en FileMaker. |
| `context` ausente/rancio/otro layout | Propón `python3 agent/scripts/refresh_context.py --task "…" [--layout X]` (espera OK → `--yes`) o Push Context manual. |

## 2. Contexto de equipo (Obsidian)

Si el MCP `obsidian-trabajo` responde, lee `Organización/Skills/Claude-Code-FileMaker.md` (equipo, clientes, dónde va el changelog, Dash). Si no responde: **continúa** — las reglas operativas están en este repo — y avisa una vez de que no podrás escribir el changelog en el vault al cerrar.

## 3. Herramientas vivas

- **Estructura** (IDs, quién usa qué, call trees, knowledge): MCP `agentic-fm-app` si está (`fm_find`, `fm_refs`, `kb_search`…); si no, el árbol de búsqueda de `CLAUDE.md` (CONTEXT.json → index → xml_parsed).
- **Estado vivo** (valores, "¿existe aún X?", drift de un layout, ERD): ProofKit MCP, siempre tras `connectedFiles`.
- **Docs FM**: Dash MCP primero; `help.claris.com/llms.txt` como complemento.

## 4. Al recibir la tarea (antes de generar nada)

1. Comprueba que `CONTEXT.json` corresponde al layout y la tarea; si no, refresh (§1).
2. **Clasifica** según `CLAUDE.md` § "Metodología de desarrollo — Superpowers": estructural (≥2 scripts/CFs, esquema, módulo nuevo) → `agent/docs/taiko/knowledge/superpowers-workflow.md`; directa → sin proceso completo.
3. Si encaja una **interfaz web** (listado, dashboard, vista rica), propón ProofKit Web Viewer con sus guardarraíles (`agent/docs/taiko/proofkit/`, plantilla `CLAUDE-webapp.md`).
4. Escribe los **casos de verificación** (entrada → resultado esperado en FileMaker). Sin ellos no se genera.
5. Confirma clasificación y verificación con el desarrollador. Luego, el flujo normal de `CLAUDE.md` (conventions Taiko → knowledge → catálogo → fmlint → deploy).

## 5. Al cerrar

- Changelog del proyecto en el vault (`Proyectos/…/Changelog-Agentic.md`) solo cuando el desarrollador confirme que está hecho.
- Mejoras de la capa herramientas → `agent/UPSTREAM_PROPOSALS.md` (o rama `mejora/<tema>` + PR a `taiko` si es inmediata; nunca datos de cliente).
- Commits del cliente en `trabajo`. Nunca push de `trabajo` ni de `taiko`.
