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
