# Propagación de errores entre subscripts Clew — `InSubscript` vs `InSubscriptThrow`

> **¿Cuándo usar este patrón?** Cuando un **Controller de borde** llama a subscripts y quieres que el **Response Envelope** conserve la `category`/`code`/`hint` reales del hijo (en vez de degradarlas a `internal/UNEXPECTED`). Asume que el error del hijo **sí llega** por `Get(ScriptResult)`. Es el problema de *"llega, pero mal resumido"*.
>
> **No es este patrón** si el subscript entra en una **transacción que puede hacer `Revert`** (que mata al hijo y vacía `Get(ScriptResult)`) → ahí necesitas el canal global de **[`clew-transactional-dual.md`](clew-transactional-dual.md)** (problema de *"no llega NADA del hijo"*).
>
> **Los dos a la vez** solo en un Controller de borde que es transaccional **y** devuelve envelope al exterior (caso poco común).

## Regla

Cuando un **Controller de borde** (el que termina con `error.GetResponse` y devuelve el Response Envelope) llama a un **subscript interno** vía `Perform Script` y quiere que el error del subscript se refleje en el envelope **con su categoría/código/hint reales**, debe usar:

```filemaker
Perform Script [ "_subscript" ; Parameter: ... ]
Exit Loop If [ error.InSubscript ]      # ✅ propaga el error ORIGINAL del subscript
```

**NO** uses `error.InSubscriptThrow` para esto:

```filemaker
Exit Loop If [ error.InSubscriptThrow ] # ❌ envuelve TODO como internal/UNEXPECTED
```

## Por qué

`error.InSubscriptThrow` está implementado para **lanzar siempre `_error_UNEXPECTED`** ante cualquier error de subscript (salvo 104 o falta de `script.name`). Su `Case()` final es literalmente:

```filemaker
error.Throw ( _error_UNEXPECTED ; "Unexpected error when calling this subscript: '" & script_name & "'" )
```

Es decir: detecta que el subscript devolvió un `errorTrace`, **antepone** un elemento nuevo `UNEXPECTED` al trace, y como `error.GetCode`/`error.GetCategory` leen el **primer** elemento (config `caller_script_first`), el envelope sale como **`internal/UNEXPECTED`** con un hint genérico. El código original del hijo (p.ej. `NO_RECORDS_FOUND`, `INVALID_PARAM`) queda sepultado en `[1]` del trace.

`error.InSubscript` (sin `Throw`) hace lo correcto para propagación semántica: si el resultado es un `errorTrace` válido (`json.IsErrorTrace`), llama a `error.PrivateSetTrace(result)` —**fija el trace del hijo tal cual como estado de error activo**— y devuelve `True`. No añade wrapper. Al salir del Loop con `error.WasThrown = True`, `error.GetResponse` lee el código/categoría/hint **originales del subscript**.

Efecto en el envelope: el campo `script` apunta al subscript de origen (p.ej. `_resolve.user`), lo cual es informativo (señala dónde nació el error).

## Cuándo usar cada uno (tabla)

| Situación | Función | Resultado en el envelope del Controller |
|---|---|---|
| Propagar el error del subscript con su semántica real (not_found, validation, …) | `Exit Loop If [ error.InSubscript ]` | `category`/`code`/`hint` = los del subscript |
| El fallo del subscript es genuinamente "inesperado" para el caller y quieres marcarlo como tal | `Exit Loop If [ error.InSubscriptThrow ]` | `internal/UNEXPECTED` (hint genérico) |
| Manejar el error localmente (loguear / ruta alternativa) | `If [ error.InSubscript ] … End If` (+ `error.DeleteTrace` si se ignora) | — |

## Precondición: el subscript debe devolver `errorTrace` crudo (patrón clásico), no el envelope

`error.InSubscript` / `InSubscriptThrow` solo reconocen la forma `errorTrace` (`json.IsErrorTrace`). Por eso los **subscripts internos** terminan con el patrón clásico:

```filemaker
If [ error.WasThrown ]
    Exit Script [ error.GetTrace ]   # devuelve el errorTrace crudo
End If
Exit Script [ $Result ]              # éxito: payload crudo
```

Si un subscript terminara con `error.GetResponse` (envelope `{ok,data}`), el caller **no** podría usar `InSubscript`/`InSubscriptThrow` — tendría que parsear el envelope a mano (`GetAsBoolean ( JSONGetElement ( resultado ; "ok" ) )`). Esto es justo lo que hace un agregador que llama a otros **Controllers de borde** (ver `daily.panel`, que llama a `sprint.panel`/`task.list`/etc. y parsea su `ok`/`data` manualmente, degradando a `null`/`[]` si fallan).

## Caso real (974, 2026-06-07)

`task.list` resuelve `usuario`/`proyecto_id` con los subscripts `_resolve.user`/`_resolve.project`. Con `error.InSubscriptThrow`, un usuario ambiguo ("A") o un proyecto inexistente ("99999") devolvían `internal/UNEXPECTED "Unexpected error when calling this subscript"` — perdiendo el `validation/INVALID_PARAM` (con candidatos) y el `not_found` reales. Cambiando a `Exit Loop If [ error.InSubscript ]`, el envelope pasó a reflejar:

- usuario "A" → `validation` + hint con la lista de candidatos.
- proyecto "99999" → `not_found` "Proyecto no encontrado: 99999".

Fue la **primera vez que la capa MCP del 974 usó subscripts**, por eso el matiz no había aparecido (las demás transacciones eran autocontenidas).

## Relacionado

- [[clew-pattern]] — Response Envelope, `error.GetResponse`, `error.GetCategory`, patrón clásico vs envelope.
