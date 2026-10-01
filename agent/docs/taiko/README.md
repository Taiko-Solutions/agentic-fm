# Capa Taiko de agentic-fm — índice

Esta carpeta y unos pocos ficheros fuera de ella son **todo lo que Taiko añade** sobre el agentic-fm de upstream. Viven solo en la rama `taiko` y nunca se proponen a petrowsky tal cual (las piezas genéricas se sanitizan y van como PR desde el repo base).

## Orden de lectura para el agente

1. `CODING_CONVENTIONS.md` — convenciones Taiko (PascalCase, español, Insert Calculated Result, `.Controller`). **Mandan** sobre `agent/docs/CODING_CONVENTIONS.md`.
2. `knowledge/MANIFEST.md` — patrones Taiko (Clew, tres capas, transaccional, logging, silent-discard…). Se escanea por keywords antes de escribir; con el MCP `agentic-fm-app`, `kb_search` lo sustituye.
3. `agent/docs/knowledge/MANIFEST.md` — knowledge general de upstream (fallback).
4. `fm-access.md` — las tres vías de acceso a FileMaker (ProofKit MCP · OData · ProofKit Web Viewer) y el gating `connectedFiles`.

## Qué hay en cada sitio

| Carpeta / fichero | Contenido | Cuándo se usa |
|---|---|---|
| `CODING_CONVENTIONS.md` | Convenciones de código Taiko | Siempre que se genera código |
| `knowledge/` | Patrones y gotchas Taiko (uno por fichero + `MANIFEST.md`) | Antes de escribir un script; `kb_search` |
| `templates/` | Esqueletos de scripts Clew en formato HR (`clew-simple`, `clew-transactional`, dual, orchestrator, completo) | Al componer un script nuevo |
| `custom_functions/` | fmxmlsnippet de los módulos obligatorios: Clew (`clew.xml`), fm-sql-cfs (`sql-cfs.xml`), triggers (`triggers.xml`) | Al preparar una solución nueva |
| `proofkit/` | Base de conocimiento ProofKit: `mcp-connector.md` (Vía 1), `webviewer-build.md`, `architecture.md`, `gotchas.md` (F1–F19), `troubleshooting.md`, `conventions.md`, `CLAUDE-webapp.md` (plantilla para apps web) | Consulta en vivo o interfaz web |
| `fm-access.md` | Mapa de las tres vías y reparto explode vs. en vivo | Antes de tocar FileMaker |
| `sessions/` | Procedimientos de sesión que leen las skills del plugin `taiko-filemaker` (`fm-sesion.md`, `fm-nuevo-proyecto.md`) | Al arrancar una sesión o un proyecto |
| `UPSTREAM_IMPROVEMENTS.md` | Cómo registrar mejoras desde un clon (`agent/UPSTREAM_PROPOSALS.md`) | Al cerrar una tarea |
| `bendita-conversion-guide.md` | Guía de conversión de una solución concreta | Solo en ese proyecto |
| `../../scripts/bin/` | `agentic-fm-start`, `-update`, `-sync`, `-safe-push` (symlinks a `~/bin`) | Terminal |
| `../../scripts/hooks/` | Hook pre-push + `paths.conf` (reglas de rutas) | Instalado por `install-hooks.sh` |
| `/TAIKO-UPDATES.md` | Changelog de esta capa; lo leen `session_start.py` y `agentic-fm-sync` | Al actualizar un clon |
| `/.claude/CLAUDE.md` | Las secciones marcadas "(Taiko)" y "override" | Siempre |
| `/.cursor/skills/` | Las 25 skills (upstream las mantiene aquí; `/.claude/skills` es un **symlink** a esta carpeta: no borrar `.cursor/`) | Skills del agente |

## Cómo se propaga

```
petrowsky/agentic-fm ──(repo base: pull main → merge; PRs sanitizadas)── Taiko-Solutions/agentic-fm · taiko
                                                                                    │
                     clon de cliente: taiko (espejo) ─► trabajo (cliente, local) ─► mejora/<tema> ─PR─► taiko
```

- Actualizar un clon: `agentic-fm-sync` (primera vez `--migrar`).
- Subir una mejora: rama `mejora/<tema>` con solo la capa herramientas + entrada en `TAIKO-UPDATES.md` + PR a `taiko`. El hook y la GitHub Action rechazan lo demás.
- Detalle: `.claude/CLAUDE.md` § "Propagación de reglas y actualizaciones (Taiko)".

## Mantenimiento

Lo mantiene el equipo Taiko. Los nombres de cliente no aparecen como procedencia en estos ficheros ("proyecto cliente (AAAA-MM)"); los specs y decisiones de cada solución viven en el vault de Obsidian, nunca aquí.
