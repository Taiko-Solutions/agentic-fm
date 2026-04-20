# Trigger Suppression Pattern

## Rule

**MANDATORY**: Every triggered script (OnLayoutEnter, OnModeEnter, OnRecordLoad, etc.) must check `TriggersAreActive` at the top. Every script that navigates layouts or performs actions that fire triggers must wrap those actions with `TriggersDisable` / `TriggersEnable`.

XML source: `agent/docs/taiko/custom_functions/triggers.xml` (module [FileMaker-Techniques](https://github.com/jbante/FileMaker-Techniques) by Jeremy Bante)

## How it works

The system uses a stack-based approach via global variables (`$$~TRIGGERS_DISABLE`, `$$~TRIGGERS_SCRIPTS`). Multiple scripts can disable triggers simultaneously — only when the last one re-enables them do triggers become active again.

## Custom functions

| Function | Purpose |
|----------|---------|
| `TriggersAreActive` | Returns True if triggers should run, False if suppressed |
| `TriggersDisable` | Pushes the current script onto the suppression stack; returns True if successful |
| `TriggersEnable` | Pops the current script off the suppression stack; re-enables triggers if stack is empty |
| `TriggersReset` | Emergency reset — clears all suppression state regardless of stack |

## Pattern 1: Triggered script (guard clause)

Scripts attached to layout triggers (OnLayoutEnter, OnModeEnter, OnRecordLoad, etc.) must start with:

```
If [TriggersAreActive]
  # Script logic here
  ...
End If
```

This ensures the script does nothing when another script is navigating through the layout programmatically.

## Pattern 2: Script that navigates layouts

When a Controller or Data script needs to Go to Layout (which would fire OnLayoutEnter triggers), wrap the navigation:

```
Set Variable [$!; Value: TriggersDisable]
Go to Layout ["Target Layout"]
# ... do work on this layout ...
Go to Layout [original layout]
Set Variable [$!; Value: TriggersEnable]
```

## Pattern 3: Operations that fire triggers

Any operation that fires triggers (Enter Find Mode, switching records, etc.) should be wrapped if the triggered script is not desired:

```
Set Variable [$!; Value: TriggersDisable]
Enter Find Mode []
# ... set find criteria ...
Set Variable [$!; Value: TriggersEnable]
Perform Find []
```

## Pattern 4: Migration / batch scripts

Migration and one-shot batch scripts (e.g., post-deployment scripts that loop over thousands of records across multiple layouts) **must** wrap the entire work body with `TriggersDisable`/`TriggersEnable`. The layout hops that typically happen in these scripts (`Go to Layout`, `Show All Records`, `Go to Record/Request/Page`) fire `OnLayoutEnter` and `OnRecordLoad` triggers at every iteration — without suppression, migration time balloons and side effects (filtering, field updates from triggered scripts) can corrupt the data being migrated.

Canonical structure within a Clew try-block:

```
Loop                                # Clew pseudo try-catch
    Set Variable [ $! ; TriggersDisable ]

    # ... guard global idempotencia ...
    # ... Fase 1: loop sobre tabla A ...
    # ... Fase 2: loop sobre tabla B, con New Record en tabla C ...
    # ... Fase 3: loop sobre tabla D, con idempotencia SQL ...
    # ... Fase 4: marcar DONE ...

    Exit Loop If [ True ]
End Loop

# CATCH — SIEMPRE reactivar triggers, éxito o error
Set Variable [ $! ; TriggersEnable ]

If [ error.WasThrown ]
    Show Custom Dialog [ "Error"; error.GetHint ]
End If

Go to Layout [ OriginalLayout ]
Exit Script [ $Resultado ]
```

Key points:

- **`$!` (bit-bucket Taiko)** — variable nombre intencionalmente fuera de `$camelCase`. fmlint advierte con WARN `N002` pero es falso positivo en este patrón; ignorar.
- **`TriggersEnable` antes del `If [error.WasThrown]`** — va en el bloque catch **antes** de la rama de error, para ejecutarse siempre (éxito o error). Si se pone dentro del If WasThrown, en caso de éxito los triggers quedan desactivados para toda la sesión de FM.
- **Never** use `TriggersReset` in migration scripts — reset es para recovery, no para flujo normal.

Example: a post-deployment migration script that copies records between two tables and populates a bridge table, navigating 4 layouts with thousands of iterations. Without `TriggersDisable`, each iteration fires `OnLayoutEnter` on every layout visited — unacceptable performance penalty + risk of spurious foundset filters from triggered scripts.

## Best practices

- **Always pair**: Every `TriggersDisable` must have a matching `TriggersEnable`. Forgetting to re-enable will leave all triggers suppressed for the session.
- **Use in Clew catch block**: If a script disables triggers in the try block, the catch block must still re-enable them before exiting.
- **TriggersReset is for recovery only**: Use it in startup scripts or debugging, not in normal flow.
- **Do NOT use `$$~TRIGGERS_DISABLE` directly**: Always use the custom functions so the stack mechanism works correctly.

## Anti-patterns

```filemaker
// MAL: comprobar la variable directamente
If [$$~TRIGGERS_DISABLE = ""]
  # ...
End If

// BIEN: usar la función
If [TriggersAreActive]
  # ...
End If

// MAL: olvidar re-habilitar en el catch
Loop
  Exit Loop If [error.ThrowIfLast("...")]
  Set Variable [$!; Value: TriggersDisable]
  Go to Layout [...]
  // Si hay error aquí, triggers quedan deshabilitados
  Exit Loop If [True]
End Loop
If [error.WasThrown]
  // FALTA: Set Variable [$!; Value: TriggersEnable]
End If

// BIEN: re-habilitar siempre
If [error.WasThrown]
  Set Variable [$!; Value: TriggersEnable]
  # ... handle error ...
End If
```
