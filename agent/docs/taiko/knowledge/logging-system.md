# Logging System

Taiko's logging system records errors and optionally full transaction results for debugging and retry. It operates independently of the main transaction — log scripts open their own windows so they are never affected by a `Revert Transaction` in the parent script.

## Two-Level Logging

### Level 1: Error Log (always active)

**Table:** `Log`
**Script:** `Create Log Clew`

Every error that reaches a catch block is recorded. This is mandatory and cannot be disabled.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `Id` | Text | UUID (auto-enter) |
| `CreationTimestamp` | Timestamp | Auto-enter |
| `CreationAccountName` | Text | Auto-enter |
| `Response` | Text | Full errorTrace JSON |
| `errorCode` | Number | Extracted from Response (calculated) |
| `ScriptName` | Text | Script that failed (extracted from Response) |
| `ScriptParameter` | Text | Original parameters (extracted from Response) |
| `ONE` | Number | Constant 1 (auto-enter, used for relationships) |

### Level 2: Transaction Log (activated per script)

**Table:** `Registro`
**Script:** `Crear Registro Clew`

Records both successes and errors with full context. Activated by setting `$RegistroActivo = True` at the beginning of the parent script.

Same fields as Log plus:
- `TransactionLog` — complete transaction log
- Repetition fields for multiple subscript results
- `$$TransactionCounter` for repetition control

## Create Log Clew Script

```
# Opens its own window (independent of parent transaction)
# Goes to Log layout
# Creates new record
# Saves errorTrace in Response
# Extracts errorCode, ScriptName, ScriptParameter
# Closes window
```

**Key rule:** This script opens a new window and creates a record independently. It NEVER participates in the parent script's transaction. If the parent reverts, the log entry persists.

## Usage in a Script

### In the catch block (always)

```
If [error.WasThrown]
  # ALWAYS log the error
  Perform Script [Create Log Clew]

  # If transaction logging is active, also save to Registro
  If [$RegistroActivo]
    Perform Script [Crear Registro Clew]
  End If

  Exit Script [error.GetTrace]
End If
```

### On success (only if logging active)

```
If [$RegistroActivo]
  Perform Script [Crear Registro Clew; Parameter: $Result]
End If

Exit Script [$Result]
```

## Activation Control

Logging is controlled per-script with a local variable:

```
# Activate full transaction logging for this script
Insert Calculated Result [$RegistroActivo; True]
```

To disable: remove or comment the line. Error logging (Level 1) always works regardless.

## Geist-to-Clew Normalization

Some Taiko solutions use the Geist/TaikoController framework alongside Clew. When a Clew script calls a Geist subscript, the error format differs. The custom function `error.NormalizeFromGeist(scriptResult)` handles this:

1. If the result is already a Clew errorTrace → returns False (already handled by `error.InSubscript`)
2. If the result is a Geist error (`Error.IsError` returns True) → converts to Clew errorTrace format and throws → returns True
3. If neither → returns False (no error)

**Usage in try block, after calling a Geist subscript:**

```
Perform Script [GeistController; Parameter: $Params]
Exit Loop If [error.InSubscriptThrow]
# If no Clew error detected, check for Geist error format
Exit Loop If [error.NormalizeFromGeist(Get(ScriptResult))]
```

This dual check is temporary during migration from Geist to Clew. Once all scripts use Clew, only `error.InSubscriptThrow` is needed.

## Nota sobre el Hint en Log

`Create Log Clew` extrae `errorCode`, `ScriptName` y `ScriptParameter` del errorTrace y los almacena en campos separados del registro de Log. Sin embargo, el `hint` (texto descriptivo del error) **no se almacena en un campo independiente** — solo está disponible dentro del JSON completo del campo `Response`. Para consultar hints de errores pasados, hay que parsear el JSON de `Response`.

## Retry from Log

Scripts `Reintentar Log Clew` and `Reintentar Registro Clew` re-execute failed operations:

1. Read `ScriptName` and `ScriptParameter` from the log record
2. Execute `Perform Script [Calculated]` with the stored values
3. Follow standard Clew pattern for the retry attempt

## Important Rules

1. **Log scripts open their own windows** — never participate in parent transactions
2. **Log AFTER the transaction ends** — in the catch block, outside any Loop or Transaction
3. **Never log inside a transaction** — if Revert Transaction fires, the log record would be lost
4. **error.NormalizeFromGeist goes in Exit Loop If** — inside the try block, after each Perform Script to a Geist controller
