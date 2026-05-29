# Clew Pattern — Error Handling System

The Clew pattern is Taiko's standard error handling system for FileMaker. It implements a pseudo try-catch approach using `Loop` / `Exit Loop If` as the try block and an `If [error.WasThrown]` check as the catch block.

**NOTE:** This pattern relies on a suite of `error.*` custom functions that must be present in the FileMaker solution. These functions manage an internal error state (errorTrace) that propagates through the script chain.

XML source: `agent/docs/taiko/custom_functions/clew.xml` (43 functions — Clew framework by Marcelo Piñeyro / Soliant Consulting, with Taiko adaptations including the Response Envelope layer)

## Pseudo Try-Catch Structure

Every Clew script follows this skeleton:

```
Allow User Abort [Off]
Set Error Capture [On]

Loop
  # --- TRY BLOCK ---
  # Parse parameters
  Exit Loop If [error.CreateVarsFromKeys(Get(ScriptParameter); "")]

  # Validate required parameters
  Exit Loop If [error.ThrowIfMissingParam($REQUIRED; "")]

  # Validate context (if context-sensitive)
  Exit Loop If [error.ThrowIfWrongContext(GetFieldName(Table::Field))]

  # Business logic
  ...
  Exit Loop If [error.ThrowIf(condition; _error_CODE; "hint en español")]

  # Call subscripts
  Perform Script [Subscript.Controller]
  Exit Loop If [error.InSubscriptThrow]

  # Build result
  ...
  Exit Loop If [True]
End Loop

# --- EXIT (con Response Envelope, para Controllers de borde) ---
Exit Script [error.GetResponse ( $Result )]
```

The `Loop` always executes exactly once. Each `Exit Loop If` acts as a validation gate — if the condition is true (an error was thrown), execution jumps out of the loop. The final `Exit Loop If [True]` ensures the loop terminates on success.

`error.GetResponse ( $Result )` produce un **Response Envelope** uniforme (ver sección abajo): si hubo error, devuelve `{"ok": false, ...}`; si no, devuelve `{"ok": true, "data": $Result}`. Esto sustituye al patrón clásico de doble `Exit Script` (uno para `$Result`, otro para `error.GetTrace`) — un único punto de salida, un único formato para los consumidores.

> **Sólo para Controllers de borde.** Usa `error.GetResponse` en scripts consumidos directamente por sistemas externos (Data API, OData, MCP del agente IA, wrapper Node.js). Los **subscripts internos** llamados con `Perform Script` deben mantener el patrón clásico (devolver `errorTrace`/`$Result` raw), porque `error.InSubscript` / `error.InSubscriptThrow` esperan la forma `errorTrace` y no reconocen el envelope.

> **Patrón clásico (subscripts internos / legado):**
> ```
> If [error.WasThrown]
>   Exit Script [error.GetTrace]
> End If
> Exit Script [$Result]
> ```
> Es funcionalmente equivalente al envelope cuando el consumidor conoce el formato `errorTrace`. Mantén este patrón en subscripts internos y en scripts existentes que aún no se hayan migrado.

## Custom Functions

### ⚠️ Namespace vs Hint — Distinción Crítica

Las funciones Clew tienen dos tipos de segundo parámetro que **NO deben confundirse**:

| Segundo parámetro | Tipo | Valor habitual | Funciones |
|-------------------|------|----------------|-----------|
| `namespace` | Prefijo para nombres de variable | `""` (vacío) | `error.CreateVarsFromKeys`, `error.ThrowIfMissingParam`, `error.ThrowIfMissingVar` |
| `hint` | Texto descriptivo para debugging | Frase en español | `error.ThrowIf`, `error.ThrowIfLast`, `error.Throw` |

**¿Qué hace `namespace`?** Se antepone al nombre de cada variable creada o verificada. Si pasas `""`, se crean `$NumeroFactura`, `$Proveedor`, etc. Si pasas `"Fac"`, se crean `$FacNumeroFactura`, `$FacProveedor`.

**Error común:** Pasar un texto descriptivo como namespace (p.ej. `error.CreateVarsFromKeys($Param; "Error al procesar parámetros")`) crea variables con nombres rotos como `$Error al procesar parámetrosNumeroFactura` — que luego no se encuentran en `error.ThrowIfMissingParam`.

**Regla:** Si no necesitas un prefijo específico, usa siempre `""` como namespace.

### Parameter Parsing and Validation

- `error.CreateVarsFromKeys(json; namespace)` — parses a JSON object into local `$variables`. The `namespace` is prepended to each variable name (use `""` unless you need a prefix). Returns True (error) if the JSON is invalid.
- `error.ThrowIfMissingParam(variableList; namespace)` — checks that all variables in the semicolon-delimited list have values. The `namespace` must match what was used in `CreateVarsFromKeys`. Throws `_error_MISSING_REQUIRED_PARAM` if any are empty.
- `error.ThrowIfMissingVar(variableList; namespace)` — same as above but for variables that may have been set by other means. Same `namespace` rule applies.

### Context Validation

- `error.ThrowIfWrongContext(GetFieldName(Table::Field))` — validates that the current layout's table occurrence matches the expected table. Throws `_error_INVALID_CONTEXT` if not.

### Conditional Throws

- `error.ThrowIf(condition; errorCode; hint)` — throws an error if `condition` is True. The `hint` should be a descriptive Spanish string that helps debugging.
- `error.ThrowIfLast(hint)` — checks `Get(LastError)` and throws if it is not 0. Use immediately after risky FileMaker steps (Perform Find, Commit Records, etc.).
- `error.Throw(errorCode; hint)` — throws an error unconditionally.

### Subscript Error Handling

- `error.InSubscript` — returns True if the last `Perform Script` returned an errorTrace. Does NOT re-throw. Use this when you want to **check** the error and **decide locally** how to handle it (log it, take alternative action, or ignore it).
- `error.InSubscriptThrow` — returns True if the last `Perform Script` returned an errorTrace AND re-throws it into the current error state. Use this in `Exit Loop If` to **propagate errors automatically** to the caller. This is the **default/most common** pattern.

**Choosing between them:**

| Scenario | Function | Pattern |
|----------|----------|---------|
| Subscript error should abort the caller | `error.InSubscriptThrow` | `Exit Loop If [ error.InSubscriptThrow ]` |
| Subscript error should be handled locally | `error.InSubscript` | `If [ error.InSubscript ] ... End If` |
| Subscript error should be logged but ignored | `error.InSubscript` + `error.DeleteTrace` | Check → log → clean |

### Error State Inspection

- `error.WasThrown` — returns True if an error is active in the current script.
- `error.GetTrace` — returns the full errorTrace JSON object.
- `error.GetCode` — returns the error code from the active error.
- `error.GetHint` — returns the hint string from the active error.
- `error.GetScriptName` — returns the script name where the error originated.
- `error.GetDescription(errorCode)` — returns the standard description for a given error code.
- `error.DeleteTrace` — clears the active error. Use when an error has been handled and should not propagate further. **IMPORTANT:** Must be called via `Set Variable` (step id="141"), not `Insert Calculated Result`, because it modifies internal state and returns a void value. Pattern: `Set Variable [$_Void; Value: error.DeleteTrace]`

### Response Envelope (Output)

Las funciones siguientes son una capa Taiko sobre el framework Clew original. Producen una envoltura JSON uniforme para que cualquier consumidor (wrapper Node.js, MCP del agente IA, dialog FM, otra solución FM) discrimine éxito de error sin parsear el contenido.

- `error.GetCategory` — clasifica el error activo en una categoría de alto nivel (`validation`, `not_found`, `conflict`, `business_rule`, `internal`). Pensada para ser invocada desde `error.GetResponse`, no directamente. Si no hay error activo o el código no se reconoce, devuelve `internal` como fallback seguro.
- `error.GetResponse ( payload )` — construye el Response Envelope completo. Si `error.WasThrown = True`, devuelve el envelope de error; si no, el de éxito con `payload` como `data`. **Es la pieza de salida del framework**: reemplaza al patrón clásico de doble `Exit Script` por un único `Exit Script [error.GetResponse ( $Result )]`. Úsala sólo en Controllers de borde (ver sección Response Envelope).
- `_clew_VERSION` — constante que devuelve la versión semver del framework Clew instalado (p.ej. `"1.1.0"`). Útil para que consumidores y scripts de mantenimiento comprueben qué versión está presente.

## Error Constants

These custom functions return fixed string codes:

| Constant | Meaning |
|----------|---------|
| `_error_FAILED_CONDITION` | A business rule condition was not met |
| `_error_INVALID_CONTEXT` | Script is running on the wrong table/layout |
| `_error_INVALID_JSON` | JSON parameter could not be parsed |
| `_error_INVALID_PARAM` | A parameter value is invalid (wrong type, out of range) |
| `_error_MISSING_REQUIRED_PARAM` | A required parameter is empty or missing |
| `_error_MISSING_REQUIRED_VAR` | A required variable is empty or missing |
| `_error_NO_RECORDS_FOUND` | A Perform Find returned zero records |
| `_error_MULTIPLE_RECORDS_FOUND` | A Perform Find returned more records than expected |
| `_error_UNEXPECTED` | An unexpected error occurred |
| `_error_MALFORMED_ERROR_OBJECT` | The errorTrace JSON is malformed |

## Response Envelope

El Response Envelope es la envoltura de salida estándar para cualquier transacción Clew **de borde** — es decir, consumida por un sistema externo (wrapper HTTP, MCP del agente IA, llamada Data API/OData, dialog FM, otra solución FM por subscript). Su objetivo es eliminar el parseo ad-hoc que cada consumidor implementaba para distinguir éxito de error.

### Esquema

**Éxito** ( `error.WasThrown = False` ):

```json
{
  "ok": true,
  "data": <payload>
}
```

`<payload>` es lo que la transacción acumula en `$Result`. Puede ser cadena, número, objeto JSON, array JSON o vacío. Se serializa con el flag JSON apropiado (JSONRaw si es JSON válido, JSONString si es texto plano, JSONNull si está vacío).

**Error** ( `error.WasThrown = True` ):

```json
{
  "ok": false,
  "category": "<categoría>",
  "code": "<código>",
  "hint": "<frase en español>",
  "script": "<nombre del script>",
  "trace": { ... }
}
```

`trace` se incluye **sólo si `$$DEBUG_MODE = "true"`** (insensible a mayúsculas). Contiene el `errorTrace` completo que produce `error.GetTrace`. Para no filtrar parámetros, state ni la cadena de subscripts a consumidores externos en producción, en modo no-debug `trace` se omite.

`category`, `code`, `hint` y `script` se serializan siempre como string para garantizar consistencia de tipo a consumidores externos. Los códigos FM nativos numéricos (p.ej. 401) se convierten a string ("401") en el envelope.

### Mapeo de categorías

| Categoría | Códigos `_error_*` que la activan | Significado para el consumidor |
|-----------|----------------------------------|-------------------------------|
| `validation` | `MISSING_REQUIRED_PARAM`, `MISSING_REQUIRED_VAR`, `INVALID_PARAM`, `INVALID_JSON` | El input del cliente está mal formado. Mapea a HTTP 400 / 422. |
| `not_found` | `NO_RECORDS_FOUND` | El recurso solicitado no existe. Mapea a HTTP 404. |
| `conflict` | `MULTIPLE_RECORDS_FOUND` | Estado inconsistente en los datos (más registros de los esperados). Mapea a HTTP 409. |
| `business_rule` | `FAILED_CONDITION` | Una regla de negocio rechazó la operación. Mapea a HTTP 422 con mensaje al usuario. |
| `internal` | `INVALID_CONTEXT`, `UNEXPECTED`, `MALFORMED_ERROR_OBJECT`, códigos FM nativos, códigos no reconocidos, sin error activo | Error interno o inesperado. Mapea a HTTP 500. **No mostrar `hint` al usuario final** salvo en debug. |

> **Por qué `internal` para códigos FM nativos**: en este repo template no asumimos un mapeo fijo para errores FM nativos (104, 401, 301, 306…) porque su semántica depende del contexto de cada solución. Cada solución puede extender `error.GetCategory` localmente añadiendo ramas al `Case()` con los códigos FM que quiera categorizar.

### Convención `$$DEBUG_MODE`

`error.GetResponse` lee la variable global `$$DEBUG_MODE` para decidir si incluye el `trace` en el envelope de error.

| Valor de `$$DEBUG_MODE` | Comportamiento |
|------------------------|----------------|
| `"true"` (insensible a mayúsculas: `True`, `TRUE`, `true`) | Incluye `trace` con el errorTrace completo |
| Vacío | Omite `trace` |
| Cualquier otro valor | Omite `trace` |

La variable se establece en una capa de bootstrap del cliente (script de inicialización del fichero, endpoint que la fija al recibir un header `X-Debug: true`, o toggle de desarrollador). El framework Clew no la fija ni la limpia automáticamente.

> **Seguridad**: Nunca dejes `$$DEBUG_MODE = "true"` en producción para clientes externos. El errorTrace contiene parámetros de entrada, state del cliente (account name, layout name) y la cadena completa de subscripts — información que no debe filtrarse fuera del entorno de desarrollo.

### Ejemplos

**Éxito con payload simple** (transacción que crea un registro y devuelve el ID):

```
$Result = "FAC-2026-00042"
Exit Script [ error.GetResponse ( $Result ) ]
```

Envelope producido:

```json
{ "ok": true, "data": "FAC-2026-00042" }
```

**Éxito con payload JSON** (transacción que devuelve un objeto):

```
$Result = JSONSetElement ( "{}"
    ; [ "FacturaID" ; "FAC-2026-00042" ; JSONString ]
    ; [ "Total" ; 1250 ; JSONNumber ]
)
Exit Script [ error.GetResponse ( $Result ) ]
```

Envelope producido (nota: `data` se embebe como objeto, no como string):

```json
{
  "ok": true,
  "data": { "FacturaID": "FAC-2026-00042", "Total": 1250 }
}
```

**Error de validación** (`$ClienteID` no recibido):

```json
{
  "ok": false,
  "category": "validation",
  "code": "MISSING_REQUIRED_PARAM",
  "hint": "Missing ClienteID required parameter(s)",
  "script": "Cliente.Read.Controller"
}
```

**Error de validación en modo debug** (`$$DEBUG_MODE = "true"`):

```json
{
  "ok": false,
  "category": "validation",
  "code": "MISSING_REQUIRED_PARAM",
  "hint": "Missing ClienteID required parameter(s)",
  "script": "Cliente.Read.Controller",
  "trace": {
    "directionOfTrace": "caller_script_first",
    "errorTrace": [
      {
        "code": "MISSING_REQUIRED_PARAM",
        "description": "Missing a required parameter",
        "hint": "Missing ClienteID required parameter(s)",
        "script": { "name": "Cliente.Read.Controller", "parameter": {} },
        "state": { "accountName": "Admin", "layoutName": "Clientes" }
      }
    ]
  }
}
```

### Cuándo NO usar el envelope

- **Subscripts internos** llamados con `Perform Script`: deben seguir devolviendo `errorTrace` o `$Result` raw. El envelope sólo es la salida hacia consumidores externos. Si un subscript devolviera el envelope, el caller no podría usar `error.InSubscriptThrow` / `error.InSubscript` (que esperan la forma `errorTrace`).
- **Controllers transaccionales llamados por un Utility Manager** (ver `utility-transactional.md`): el Manager los invoca con `error.InSubscript`, así que el Controller transaccional NO lleva envelope. Si necesitas exponer una escritura transaccional a un consumidor externo, envuelve la llamada en un Controller de borde separado que termine con `error.GetResponse`.
- **Scripts que no se consumen externamente**: triggers, scripts UI puros, navegación. Mantén el patrón tradicional.

La regla práctica: **sólo los Controllers de borde (llamados por Data API, OData, MCP, o un wrapper Node.js) usan el envelope**. Los Interface scripts y los subscripts internos siguen el patrón clásico.

## ErrorTrace JSON Format

When an error is thrown, the errorTrace has this structure:

```json
{
  "directionOfTrace": "caller_script_first",
  "errorTrace": [
    {
      "code": "NO_RECORDS_FOUND",
      "description": "No records were found",
      "hint": "No se encontró cliente con ID: 123",
      "script": {
        "name": "BuscarCliente.Controller",
        "parameter": {"ClienteID": 123}
      },
      "state": {
        "accountName": "Admin",
        "layoutName": "Clientes"
      }
    }
  ]
}
```

As errors propagate through the script chain, each script adds its own entry to the `errorTrace` array. This provides a complete trace from the point of failure to the top-level caller.

## Relationship to Single-Pass Loop

Clew is Taiko's implementation of the single-pass loop pattern described in `agent/docs/knowledge/single-pass-loop.md`. When the Clew custom functions are available in the solution, **always** use Clew instead of the generic pattern. The generic single-pass loop applies only as a conceptual reference or as a fallback in solutions where Clew is not installed.

**Decision hierarchy:**

1. Clew CFs exist in the solution → use Clew (this document)
2. Clew CFs do NOT exist → use generic single-pass loop (`agent/docs/knowledge/single-pass-loop.md`)

## Best Practices

### DO

- Use descriptive Spanish hints that help debugging: `"Factura con ID " & $FacturaID & " no encontrada"`
- Validate ALL required parameters with `error.ThrowIfMissingParam`
- Use the most specific error code available
- Document what the script returns on success and error (in the header)
- Clean handled errors with `error.DeleteTrace` when appropriate

### DO NOT

- Do not call `error.Throw` without a descriptive hint
- Do not skip context validation in context-sensitive scripts
- Do not use `error.InSubscript` without handling the error
- Do not mix Clew error handling with traditional `Get(LastError)` checks
- Do not return data and errors simultaneously — a script returns either a result or an errorTrace

## Cross-Script Hint Propagation

When an Interface script calls a Controller subscript and needs to show the error hint to the user, the hint context can get lost between `error.InSubscript` and the CATCH dialog. This happens because `Exit Loop If [True]` changes the execution context.

**Patrón correcto:** Capturar `$ErrorHint` inmediatamente después de `error.InSubscript`, antes de `Exit Loop If`:

```
Perform Script [Controller.Script]
If [error.InSubscript]
  Insert Calculated Result [$ErrorHint; error.GetHint]
  Exit Loop If [True]
End If
```

En el CATCH dialog, usar la variable capturada con fallback:

```
Show Custom Dialog ["Error"; If ( not IsEmpty ( $ErrorHint ) ; $ErrorHint ; error.GetHint )]
```

**¿Por qué?** `error.GetHint` lee del errorTrace activo. Si entre `error.InSubscript` y el `Show Custom Dialog` se ejecutan otros pasos que cambian el contexto (como `Exit Loop If`), el hint puede estar vacío. Capturarlo en una variable local garantiza que se preserva.

## When to Use Clew vs Transactional

| Scenario | Pattern |
|----------|---------|
| Read-only queries, navigation, UI logic | Clew traditional (Loop/Exit Loop If) |
| Data creation or editing with validation | Utility + Transactional (Open/Revert/Commit Transaction) |
| Subscripts called within a transaction | Transactional (Revert Transaction instead of Exit Loop If) |

See `utility-transactional.md` for the transactional pattern.
