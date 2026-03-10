# Detección de mejoras upstream

Esta sección debe incluirse en el CLAUDE.md de cada repo de solución para habilitar un flujo donde las mejoras de herramientas vuelvan al repo template.

Copiar la sección de abajo en el `.cursor/AGENTS.md` (o `.claude/CLAUDE.md`) de la solución.

---

## Contenido para copiar

```markdown
# Detección de mejoras upstream

Esta solución está basada en el repo template agentic-fm (rama `taiko`). Cuando identifiques mejoras en la **capa de herramientas** durante el trabajo de desarrollo habitual, márcalas para que puedan contribuirse de vuelta al template.

## Qué es una mejora upstream

- **snippet_examples** nuevos o mejorados (plantillas XML para pasos de script)
- **Documentos de knowledge** nuevos o mejorados (`agent/docs/knowledge/` o `agent/docs/taiko/knowledge/`)
- **Custom functions** nuevas o mejoradas (`agent/docs/taiko/custom_functions/`)
- Correcciones o mejoras en las utilidades de **agent/scripts/** (validate_snippet.py, clipboard.py, fm_xml_to_snippet.py, etc.)
- Mejoras en **CODING_CONVENTIONS.md** o las **convenciones Taiko**
- **Items de library** nuevos o mejorados (`agent/library/`)
- **Templates de scripts** nuevos o mejorados (`agent/docs/taiko/templates/`)

## Qué NUNCA va upstream

- Nada de `xml_parsed/` — esquema y scripts específicos de la solución
- Nada de `context/` — archivos index específicos de la solución
- `CONTEXT.json` — contexto de tarea específico
- Nada de `sandbox/` — scripts generados para esta solución
- Nombres de campos, tablas, layouts, scripts u otros identificadores específicos de la solución
- Credenciales, tokens o configuración de entorno

## Cómo registrar una mejora

Cuando detectes una posible mejora upstream durante una tarea, NO actúes sobre ella inmediatamente. En su lugar, añade una entrada al archivo `agent/UPSTREAM_PROPOSALS.md` de este repo con:

    ## YYYY-MM-DD — Título breve

    - **Categoría**: snippet_example | knowledge | custom_function | script_utility | convention | library | template
    - **Descripción**: 1-2 frases explicando la mejora
    - **Archivos afectados**: qué archivos del template cambiarían
    - **Origen**: qué tarea o problema reveló la necesidad

Si el archivo no existe, créalo con un encabezado `# Propuestas Upstream`.

## Cuándo comprobar

Al finalizar cada tarea significativa (después de que el usuario confirme que está completa), evalúa brevemente:

1. ¿Escribí un patrón que debería ser un snippet_example o documento de knowledge?
2. ¿Descubrí un gotcha de FileMaker que la base de conocimiento debería documentar?
3. ¿Creé o mejoré una custom function que beneficiaría a otras soluciones?
4. ¿Encontré un bug o limitación en alguna utilidad de agent/scripts/?
5. ¿Usé una convención o enfoque que debería estandarizarse?

Si la respuesta a cualquiera de estas es sí, añade una propuesta. NO crees ramas, commits ni PRs en este repo — solo registra la propuesta. El desarrollador revisará las propuestas periódicamente y las aplicará al repo template.
```
