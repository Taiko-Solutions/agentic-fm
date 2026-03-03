# Clew Pattern — Error Handling System

The Clew pattern is Taiko's standard error handling system for FileMaker. It implements a pseudo try-catch approach using `Loop` / `Exit Loop If` as the try block and an `If [error.WasThrown]` check as the catch block.

**NOTE:** This pattern relies on a suite of `error.*` custom functions that must be present in the FileMaker solution. These functions manage an internal error state (errorTrace) that propagates through the script chain.

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

# --- CATCH BLOCK ---
If [error.WasThrown]
  Exit Script [error.GetTrace]
End If

Exit Script [$Result]
```

The `Loop` always executes exactly once. Each `Exit Loop If` acts as a validation gate — if the condition is true (an error was thrown), execution jumps to the catch block. The final `Exit Loop If [True]` ensures the loop terminates on success.

## Custom Functions

### Parameter Parsing and Validation

- `error.CreateVarsFromKeys(json; namespace)` — parses a JSON object into local `$variables`. Returns True (error) if the JSON is invalid.
- `error.ThrowIfMissingParam(variableList; namespace)` — checks that all variables in the semicolon-delimited list have values. Throws `_error_MISSING_REQUIRED_PARAM` if any are empty.
- `error.ThrowIfMissingVar(variableList; namespace)` — same as above but for variables that may have been set by other means.

### Context Validation

- `error.ThrowIfWrongContext(GetFieldName(Table::Field))` — validates that the current layout's table occurrence matches the expected table. Throws `_error_INVALID_CONTEXT` if not.

### Conditional Throws

- `error.ThrowIf(condition; errorCode; hint)` — throws an error if `condition` is True. The `hint` should be a descriptive Spanish string that helps debugging.
- `error.ThrowIfLast(hint)` — checks `Get(LastError)` and throws if it is not 0. Use immediately after risky FileMaker steps (Perform Find, Commit Records, etc.).
- `error.Throw(errorCode; hint)` — throws an error unconditionally.

### Subscript Error Handling

- `error.InSubscript` — returns True if the last `Perform Script` returned an errorTrace. Does not re-throw.
- `error.InSubscriptThrow` — returns True if the last `Perform Script` returned an errorTrace AND re-throws it into the current error state. Use this in `Exit Loop If` to propagate errors automatically.

### Error State Inspection

- `error.WasThrown` — returns True if an error is active in the current script.
- `error.GetTrace` — returns the full errorTrace JSON object.
- `error.GetCode` — returns the error code from the active error.
- `error.GetHint` — returns the hint string from the active error.
- `error.GetScriptName` — returns the script name where the error originated.
- `error.GetDescription(errorCode)` — returns the standard description for a given error code.
- `error.DeleteTrace` — clears the active error. Use when an error has been handled and should not propagate further.

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

## When to Use Clew vs Transactional

| Scenario | Pattern |
|----------|---------|
| Read-only queries, navigation, UI logic | Clew traditional (Loop/Exit Loop If) |
| Data creation or editing with validation | Utility + Transactional (Open/Revert/Commit Transaction) |
| Subscripts called within a transaction | Transactional (Revert Transaction instead of Exit Loop If) |

See `utility-transactional.md` for the transactional pattern.
