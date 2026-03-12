# Utility + Transactional Pattern

The Utility + Transactional pattern extends the Clew pattern for data editing scenarios. It provides non-destructive editing through global fields, complete validation before commit, and automatic rollback on error.

**NOTE:** This pattern is used for data creation and editing. For read-only operations (queries, navigation, UI logic), use the traditional Clew pattern described in `clew-pattern.md`.

## When to Use

- Form-based creation or editing of important records
- Operations involving multiple tables
- Complex business validations before committing
- Any operation that requires complete rollback on error

## Architecture

```
INTERFACE
  Layout (main table) --> Utility Manager script
    |
    |--> Initialize Shadow script (fills global fields from AsJSON)
    |
    |--> Modal Card Window (Utility table with global fields)
    |      User edits global fields
    |      Clicks "Guardar" or "Cancelar"
    |
    |--> Utility Manager: "Guardar" action
           |
           v
CONTROLLER
  Transactional script
    - Open Transaction (with temporary window)
    - Parse and validate parameters
    - Find or create record
    - Set fields from parameters
    - Commit Transaction (or Revert on error)
    |
    |--> On error: Create Log Clew --> Log table
    |
    v
DATA
  Main table (with AsJSON calculated field)
  Utility table (all global fields)
  Log table
```

## Components

### 1. Utility Table

- **Location:** Interface file
- **All fields are global** (storage: global)
- **Naming:** `Utility__TableName` (e.g., `Utility__Recibidas`)
- Includes an `AsJSON` calculated field that serializes all editable fields
- Control fields: `zz__Response`, `zz__Prompt`, etc.

### 2. Utility Manager Script (Interface)

**Name:** `[Entity] Utility | Alta, Editar`

Orchestrates all card window actions: Nuevo, Editar, Guardar, Cancelar.

**Parameter:** `{"Accion": "Editar", "Id": "ABC-123"}`

**Key behaviors:**
- **Editar/Nuevo:** calls Initialize Shadow, opens card window
- **Guardar:** commits global fields, calls Transactional script. If error: logs it, shows dialog, card stays open for correction. If success: closes card.
- **Cancelar:** closes card window, calls Initialize Shadow (empty) to clear globals

### 3. Initialize Shadow Script (Interface)

**Name:** `[Entity] Utility | Initialize Shadow`

Fills Utility global fields from the main table's AsJSON. When called without parameters, clears all globals.

### 4. Transactional Script (Controller)

**Name:** `[Entity] | Alta Modificar [Entity] {json}`

Applies changes with full transactional control.

**Key structure:**

```
1. Check transaction state
   - If no transaction open: open a temporary window
2. Open Transaction
3. Parse and validate parameters
   - Use Revert Transaction [Condition: ...] (NOT Exit Loop If)
4. Business logic
   - Find or create record
   - Set fields
   - Call transactional subscripts
5. Package result
6. Commit Transaction
7. Close temporary window
8. Return result
```

## Critical Differences: Clew vs Transactional

| Aspect | Clew Traditional | Utility + Transactional |
|--------|-----------------|------------------------|
| Flow control | `Loop` / `Exit Loop If` | `Open Transaction` / `Revert Transaction` |
| Validation | `Exit Loop If [error.ThrowIf(...)]` | `Revert Transaction [Condition: error.ThrowIf(...)]` |
| Rollback | Manual (if needed) | Automatic via `Revert Transaction` |
| Temporary window | Not used | Opens automatically if no transaction active |
| Data editing | Direct on records | Through global fields (non-destructive) |
| Cancel UX | Depends on logic | Automatic: close window, clear globals |
| Logging | Optional | Automatic with Create Log Clew |

**CRITICAL:** In transactional scripts, ALWAYS use `Revert Transaction [Condition: ...]` instead of `Exit Loop If`. The `Exit Loop If` step does NOT revert the transaction — it leaves it open, causing data corruption.

## Temporary Window

Transactional scripts open a temporary window to isolate the transaction context:

```
Set Variable [$transactionOpenState; Get(TransactionOpenState)]

If [not $transactionOpenState]
  Set Variable [$windowName; Random]
  If [Get(WindowStyle) = 3]  # Currently in card
    New Window [Style: Document; Name: $windowName]
  Else
    New Window [Style: Card; Name: $windowName]
  End If
End If

Open Transaction
# ... business logic ...
Commit Transaction
Close Window [Name: $windowName]
```

Always check `Get(TransactionOpenState)` first — if a parent script already opened a transaction, do not create another window.

## Error Handling in Transactional Scripts

### Validation pattern

```
# CORRECT: validate BEFORE modifying data
Revert Transaction [Condition: error.ThrowIfMissingParam($REQUIRED; "")]
Revert Transaction [Condition: error.ThrowIf($Total < 0; _error_INVALID_PARAM; "Total debe ser positivo")]
Set Field [Cliente::Total; $Total]

# WRONG: validate AFTER modifying data
Set Field [Cliente::Total; $Total]
Revert Transaction [Condition: error.ThrowIf($Total < 0; ...)]
```

### Subscript error propagation

When a transactional script calls another transactional subscript:

```
# In the subscript:
Revert Transaction [Condition: error.ThrowIfMissingParam($REQUIRED; "")]
Exit Script [error.GetTrace]

# In the parent:
Perform Script [Subscript Transaccional]
Revert Transaction [Condition: error.InSubscript]
```

### Error 3 en transacciones padre/hijo

Cuando un script hijo se ejecuta dentro de la transacción del padre, `Open Transaction` y `Commit Transaction` devuelven error 3 (comando no disponible) porque la transacción ya está controlada por el padre. Esto es **comportamiento esperado** y no debe tratarse como error.

**Patrón de Commit con manejo de error 3:**

```
Commit Transaction
Insert Calculated Result [$ErrorCommit; Get(LastError)]

# Check: error real solo si no es error 3 dentro de transacción del padre
# Y solo si no hay ya un error Clew activo (evita sobreescribir el hint original)
If [$ErrorCommit ≠ 0 and not ( $ErrorCommit = 3 and $TransactionOpenState ) and not error.WasThrown]
  error.Throw ( $ErrorCommit ; "Error al confirmar transacción" )
End If
```

**Tres condiciones del check de Commit:**

1. `$ErrorCommit ≠ 0` — hay un error real
2. `not ( $ErrorCommit = 3 and $TransactionOpenState )` — no es el error 3 esperado en un hijo
3. `not error.WasThrown` — no hay ya un error Clew activo (p.ej. después de Revert por error en paso anterior, `Get(LastError)` devuelve 5499, que dispararía un throw que sobreescribiría el hint original)

### Revert Transaction: NUNCA condicionado en scripts hijo

Los pasos `Revert Transaction` que responden a errores **nunca** deben estar condicionados a `$TransactionOpenState`. El hijo DEBE revertir la transacción del padre en caso de error:

```
# CORRECTO: Revert incondicional
Revert Transaction [Condition: error.ThrowIf(...)]

# INCORRECTO: Revert condicionado — dejaría la transacción del padre abierta
If [not $TransactionOpenState]
  Revert Transaction [Condition: error.ThrowIf(...)]
End If
```

`$TransactionOpenState` solo se usa para decidir si abrir ventana temporal y para el check de error 3 en Commit. Los Revert de validación siempre se ejecutan incondicionalmente.

### Logging solo en script padre

Los pasos de logging (`Create Log Clew`, `Crear Registro Clew`) solo deben ejecutarse en el script que originó la transacción. Si un hijo registra un log y luego el padre hace Revert, el flujo se complica innecesariamente.

```
# Solo el script que abrió la transacción registra
If [not $TransactionOpenState]
  Perform Script [Create Log Clew]
End If
```

### Error flow through layers

```
Transactional Script (child)
  --> Revert Transaction (error detected)
  --> Exit Script [error.GetTrace]

Transactional Script (parent)
  --> error.InSubscript = True
  --> Revert Transaction
  --> Commit check: $ErrorCommit ≠ 0 and not (3 + state) and not error.WasThrown
  --> If [not $TransactionOpenState]: Perform Script [Create Log Clew]
  --> Exit Script [error.GetTrace]

Utility Manager (Interface)
  --> error.InSubscript = True
  --> $ErrorHint = error.GetHint  (capturar inmediatamente)
  --> Perform Script [Create Log Clew]
  --> Show Custom Dialog ["Error"; $ErrorHint]
  --> Card window stays open for correction
```

## Card Window Behavior

**On error:** the card window stays open so the user can correct and retry.

```
If [error.InSubscript]
  Perform Script [Create Log Clew; Parameter: Get(ScriptResult)]
  Show Custom Dialog ["Error"; error.GetHint]
  # Card stays open — user can fix and retry
Else
  Perform Script [Accion: "Cancelar"]  # closes card
End If
```

**On cancel:** close the card and clear globals.

```
Close Window [Name: "EditorCliente"]
Perform Script [Initialize Shadow]  # clear all global fields
```
