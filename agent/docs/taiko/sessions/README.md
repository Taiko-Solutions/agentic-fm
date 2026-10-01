# Procedimientos de sesión (Taiko)

Lo que antes eran prompts en Obsidian. Los invoca el plugin `taiko-filemaker` del marketplace `taiko`
(skills `fm-sesion` y `fm-nuevo-proyecto`, hook `SessionStart`) y los puede ejecutar cualquier agente
que lea este repo. Los pasos marcados **[app]** los asumirá Agentic-FM-APP (fases F6/F7).

| Fichero | Lo lee | Cuándo |
|---|---|---|
| `fm-sesion.md` | skill `fm-sesion` (tras el hook `SessionStart`) | Cada sesión de trabajo en un clon |
| `fm-nuevo-proyecto.md` | skill `fm-nuevo-proyecto` | Al configurar agentic-fm para un cliente nuevo |

Reglas de fondo: `.claude/CLAUDE.md` (manda), `agent/docs/taiko/README.md` (índice de la capa Taiko),
`TAIKO-UPDATES.md` (qué ha cambiado).
