# Clew Transactional Dual Pattern — Padre/Hijo con `$$ClewError`

> **¿Cuándo usar este patrón?** Cuando el subscript entra en una **transacción que puede hacer `Revert`**: el Revert mata al hijo antes de su `Exit Script`, `Get(ScriptResult)` llega **vacío**, y la variable global `$$ClewError` es el único canal que sobrevive. Es el problema de *"no llega NADA del hijo"*.
>
> **No es este patrón** si un Controller de borde llama a subscripts **no transaccionales** (resolvers/reads) y solo quieres que el **Response Envelope** conserve la `category`/`code`/`hint` reales del error → ese es **[`clew-subscript-propagation.md`](clew-subscript-propagation.md)** (problema de *"llega, pero mal resumido"*).
>
> **Los dos a la vez** solo en un Controller de borde que es transaccional **y** devuelve envelope al exterior (caso poco común).

Patrón canónico de script transaccional Clew que se comporta idénticamente sea invocado como **root** (crea su propia transacción) o como **hijo** (hereda la del padre). Escala a **N niveles** de anidamiento. Validado empíricamente con 6 casos de test — ver `Clew | Runner Pruebas` en BPController2025.

**Relación con otros patrones:**
- Extiende `clew-pattern.md` (error handling base) añadiendo el eje transaccional y la propagación cross-script vía variable global.
- Complementa `utility-transactional.md` (Utility Manager + Shadow + Controller para edición UI); ese patrón usa un mecanismo equivalente (`$$TRANSACTION_ERROR` + `transaction.*`). Este documento describe el flujo transaccional **puro** (sin UI) y lo estandariza.

XML fuente de templates: `agent/sandbox/Clew_Template_Dual.xml` y `agent/sandbox/Clew_Template_Orchestrator.xml`.

## El problema que resuelve

Cuando un script hijo anidado hace `Revert Transaction`, FileMaker:

1. **Revierte la transacción externa completa** (no solo su nivel anidado).
2. **Mata el hijo antes de ejecutar su `Exit Script`** — cualquier código post-Revert no corre.
3. **Limpia el estado Clew local** tras el `Commit Transaction` emparejado.

Resultado: el padre recibe `Get(ScriptResult)` vacío y nunca detecta que el hijo falló. El rollback ocurre pero el error no se propaga. `error.InSubscriptThrow` no sirve aquí.

## La solución: variable global `$$ClewError` + 4 CFs

Una variable global sobrevive al `Revert Transaction` que mata al hijo. El hijo persiste el error en la global antes del Revert. El padre lee la global tras el Perform Script.

### Custom Functions requeridas

| Nombre | Parámetros | Calculation |
|---|---|---|
| `Clew.SetError` | `trace` | `Let ( $$ClewError = If ( IsEmpty ( $$ClewError ) ; trace ; $$ClewError ) ; "" )` |
| `Clew.ClearError` | (ninguno) | `Let ( $$ClewError = "" ; "" )` |
| `Clew.HasError` | (ninguno) | `not IsEmpty ( $$ClewError )` |
| `Clew.GetError` | (ninguno) | `$$ClewError` |

Semánticas:
- `Clew.SetError` **preserva el primer error**: aguas arriba no sobreescriben.
- `Clew.ClearError` **solo lo llama el root** al terminar (éxito o error).
- `Clew.HasError` / `Clew.GetError` son lectores idempotentes.

## Dualidad padre/hijo: una sola variable lo decide todo

```
$TransactionOpenState = Get ( TransactionOpenState )
$IsRoot               = not $TransactionOpenState
```

| Comportamiento | Si es root (IsRoot=1) | Si es hijo (IsRoot=0) |
|---|---|---|
| `Log.Reset` | ✅ | ❌ |
| `Clew.ClearError` inicial | ✅ | ❌ |
| `Commit Records/Requests` | ✅ (limpia edits del caller) | ❌ |
| Ventana temporal (`New Window`) | ✅ | ❌ |
| `Open Transaction` | ✅ (abre) | ✅ (FM anida) |
| `Commit Transaction` | ✅ (cierra real) | ✅ (cierra anidado, padre sigue) |
| `Create Log Clew` | ✅ (persiste log) | ❌ (padre logeará) |
| `Close Window` final | ✅ | ❌ |
| `Clew.ClearError` final | ✅ | ❌ |

## Template canónico (Worker)

```
# ========== SETUP ==========
Allow User Abort [OFF]
Set Error Capture [ON]

# ========== DETECTAR ESTADO ==========
Insert Calculated Result [Select:ON; Target: $TransactionOpenState; Get(TransactionOpenState)]
Insert Calculated Result [Select:ON; Target: $IsRoot; not $TransactionOpenState]

# ========== PREPARAR ENTORNO SI SOY ROOT ==========
If [$IsRoot]
    Insert Calculated Result [Select:ON; Target: $null; Log.Reset]
    Insert Calculated Result [Select:ON; Target: $null; Clew.ClearError]
    Commit Records/Requests [With dialog: Off]
    Insert Calculated Result [Select:ON; Target: $WindowName; "tmp_" & Get(UUID)]
    New Window [Style: Document; Name: $WindowName; Layout: "Proc_Globales"]
End If

# ========== OPEN TRANSACTION ==========
Open Transaction

# ========== TRY — pseudo try-catch con Loop ==========
Loop [Flush: Always]
    # Parsear y validar
    Exit Loop If [error.CreateVarsFromKeys(Get(ScriptParameter); "")]
    Insert Calculated Result [Select:ON; Target: $REQUIRED; List("param1"; "param2")]
    Exit Loop If [error.ThrowIfMissingParam($REQUIRED; "")]

    # Defaults para opcionales
    Insert Calculated Result [Select:ON; Target: $opcional; If(IsEmpty($opcional); "default"; $opcional)]

    # Lógica de negocio
    ...
    Exit Loop If [error.ThrowIf(condition; _error_UNEXPECTED; "hint en español")]

    # Llamadas a subscripts (si procede — ver sección Orchestrator)
    Perform Script [SubScript]
    ...

    # Armar respuesta
    Insert Calculated Result [Select:ON; Target: $Respuesta; JSONSetElement("{}"; ...)]
    Insert Calculated Result [Select:ON; Target: $null; Log.Entry(1; "Fin: " & $Marca; $Respuesta)]

    Exit Loop If [True]
End Loop

# ========== PERSISTIR ERROR LOCAL EN GLOBAL ==========
If [error.WasThrown]
    Insert Calculated Result [Select:ON; Target: $null; Clew.SetError(error.GetTrace)]
End If

# ========== REVERT CONDICIONAL + COMMIT LINEAL ==========
Revert Transaction [Condition: Clew.HasError]
Commit Transaction

Insert Calculated Result [Select:ON; Target: $ErrorCommit; Get(LastError)]

# Ignorar error 3 si soy hijo (commit anidado sin cambios propios) y si no hay error previo
If [$ErrorCommit ≠ 0 and not ($ErrorCommit = 3 and not $IsRoot) and not Clew.HasError]
    Insert Calculated Result [Select:ON; Target: $null; error.Throw($ErrorCommit; "Error al confirmar transacción")]
    Insert Calculated Result [Select:ON; Target: $null; Clew.SetError(error.GetTrace)]
End If

# ========== SALIDA ==========
If [Clew.HasError]
    # Capturar el trace ANTES de limpiar (Exit Script evalúa después)
    Insert Calculated Result [Select:ON; Target: $ErrorTrace; Clew.GetError]
    If [$IsRoot]
        Perform Script [Create Log Clew; Parameter: $ErrorTrace]
        Close Window [Name: $WindowName; Current file]
        Insert Calculated Result [Select:ON; Target: $null; Clew.ClearError]
    End If
    Exit Script [$ErrorTrace]
End If

# Salida éxito
If [$IsRoot]
    Close Window [Name: $WindowName; Current file]
End If

Exit Script [JSONSetElement(error.GetTrace;
    ["result"; $Respuesta; JSONRaw];
    ["environment"; getScriptEnvironment; JSONRaw]
)]
```

## Orchestrator: la única diferencia

Un Orchestrator es igual al Worker pero con un **loop interno** que llama a otros scripts (workers o sub-orchestrators). Tras cada `Perform Script`, se comprueba `Clew.HasError` y se propaga al estado local:

```
Loop [Flush: Always]
    # iteración
    Exit Loop If [$i > $NumWorkers]
    Exit Loop If [Clew.HasError]       # fail-fast: no llamar más subs si ya hay error

    # Construir JSON y llamar al sub
    Perform Script [Subscript]

    # Si el sub dejó error en global, propagar al estado local
    If [Clew.HasError and not error.WasThrown]
        Insert Calculated Result [Select:ON; Target: $null;
            error.Throw(_error_UNEXPECTED;
                "Error en subscript: " & JSONGetElement(Clew.GetError; "errorTrace[0].hint")
            )
        ]
    End If
End Loop
```

El resto (Revert/Commit lineal, salida) es idéntico al Worker.

## Reglas de oro

1. **`Revert Transaction` siempre condicional con `Clew.HasError`**, seguido de `Commit Transaction` incondicional. El linter rechaza `Commit` dentro de `If` — la estructura lineal es obligatoria.
2. **`Clew.SetError` antes del Revert**: el Revert puede matar el script en contexto anidado. Si el Set va después, se pierde.
3. **`Clew.ClearError` solo en el root** al salir. Los intermedios nunca limpian — el trace del error original viaja intacto hasta arriba.
4. **Capturar `Clew.GetError` en `$ErrorTrace` antes de limpiar**: `Exit Script [Clew.GetError]` evalúa **después** del `Clew.ClearError` precedente y devolvería vacío.
5. **Ignorar `$ErrorCommit = 3` cuando soy hijo**: es el error legítimo del `Commit Transaction` anidado que no tiene cambios propios.
6. **Layout para `New Window`**: usar un layout neutral (`Proc_Globales` o similar) que apunte a una tabla global del archivo local. No dependas del layout del caller.

## Error 301 y `Commit Records/Requests` defensivo

El caller puede tener records en edit mode pendientes. Cuando el Worker abre su ventana temporal y empieza a escribir en los mismos records, FM genera **error 301** ("Record is in use by another user" entre ventanas del mismo archivo).

**Fix**: `Commit Records/Requests [With dialog: Off]` **antes** de `New Window` en el bloque `If [$IsRoot]`. Limpia el edit pendiente del caller. Sin este step, cualquier Worker que sea llamado desde un caller "sucio" fallará con 301 al commitear.

## Validación empírica

Los 6 casos ejecutados por `Clew | Runner Pruebas` confirman:

| Caso | Estructura | Esperado | Resultado |
|---|---|---|---|
| 1 | Worker solo, sin error | commit, valor final = marca | ✅ |
| 2 | Worker solo, error DESPUÉS del Set Field | rollback revierte al commit previo | ✅ |
| 3 | Orch → 3 workers OK | commit agregado, valor = último worker | ✅ |
| 4 | Orch → 3 workers, falla el 2º | rollback total, error propagado con hint específico | ✅ |
| 5 | 3 niveles (Orch→Orch→Orch→Worker) OK | commit recursivo completo | ✅ |
| 6 | 3 niveles, error en la hoja | rollback global, error propagado hasta la raíz | ✅ |

## Migración de scripts legacy

Para adaptar un script Clew transaccional existente (ej. `#1372 Asignaciones | Calculo Financiero {json}`) al patrón canónico:

1. **Reemplazar** cada `Revert Transaction [Condition: error.Xxx(...)]` por `Exit Loop If [error.Xxx(...)]` dentro de un Loop try-catch.
2. **Añadir** al inicio (si IsRoot): `Clew.ClearError` + `Commit Records/Requests`.
3. **Mover** toda la lógica de negocio dentro del Loop.
4. **Después del Loop**: `If [error.WasThrown] Clew.SetError(error.GetTrace)`.
5. **Reemplazar** la salida: `Revert Transaction [Condition: Clew.HasError]` + `Commit Transaction` + gestión `$ErrorCommit`.
6. **Salida final** con captura de `$ErrorTrace` antes de `Clew.ClearError` en el root.

## Pendiente de validar — caso combinado (Controller de borde transaccional)

> **Estado: experimento sin validar.** Anotado 2026-06-14.

Cuando un Orchestrator de este patrón es **a la vez** un Controller de borde (devuelve Response Envelope al exterior), la propagación actual **degrada la semántica**: el `error.Throw(_error_UNEXPECTED; …)` de la sección *Orchestrator* envuelve el error del hijo como `internal/UNEXPECTED`, perdiendo su `category`/`code`/`hint` reales — el mismo problema que evita [`clew-subscript-propagation.md`](clew-subscript-propagation.md), pero aquí el error viaja por la global `$$ClewError`, no por `Get(ScriptResult)`.

**Experimento propuesto:** en el loop del Orchestrator, sustituir el `error.Throw(_error_UNEXPECTED; …)` por la fijación directa del trace real del hijo desde la global:

```
# en vez de error.Throw(_error_UNEXPECTED; "Error en subscript: " & …):
Insert Calculated Result [Select:ON; Target: $null; error.PrivateSetTrace(Clew.GetError)]
```

Combinaría el canal que sobrevive al `Revert` (la global) con la fidelidad de `error.InSubscript` (que internamente usa esa misma `error.PrivateSetTrace`).

**A confirmar con `Clew | Runner Pruebas` antes de adoptar:**
- `error.PrivateSetTrace` acepta el `errorTrace` crudo guardado en `$$ClewError`.
- Tras fijarlo, `error.GetResponse` del Controller devuelve la categoría/código del hijo, no `UNEXPECTED`.
- El Revert condicional (`Clew.HasError`) y el rollback a N niveles siguen intactos.
