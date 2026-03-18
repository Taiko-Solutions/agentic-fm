# Navigation Within Open Transactions

FileMaker transactions hold record changes in a local temporary file until `Commit Transaction`. This has critical implications for how scripts locate and navigate records created during a transaction.

## The Core Problem

`Perform Find` and `ExecuteSQL` both operate against the main file's indexes, which are only updated after `Commit Transaction`. Records created with `New Record/Request` inside an open transaction **cannot be found** by either method. `Perform Find` returns error 401; `ExecuteSQL` simply does not include them in its result set. Pre-existing records (created before the transaction opened) **are** findable by both methods — only newly created records within the transaction are invisible.

This also applies to related records accessed through relationships — new records created within a transaction may not appear in portals or through relationship-based navigation until committed.

## Strategies

### Strategy 1: Preserve Position (preferred for single records)

After creating a record, save its ID to a variable before leaving the layout. When returning to the layout, the active record is preserved — verify with a simple check instead of performing a find.

```
# BEFORE leaving the layout after creating a record:
Insert Calculated Result [$IdFactura; Facturas::__kpln__Factura]

# ... (other work on other layouts) ...

# AFTER returning to the layout:
Go to Layout ["Proc_Facturas"]
Revert Transaction [Condition: error.ThrowIf (
    Facturas::__kpln__Factura ≠ $IdFactura ;
    _error_FAILED_CONDITION ; "Registro activo no coincide"
)]
```

**When to use:** You created one record on a layout, went to other layouts (or called subscripts), and need to come back to update it.

### Strategy 2: Navigate Found Set (multiple records)

When multiple records are created on the same layout within a transaction, the found set contains all of them. Navigate with `Go to Record/Request/Page` to find a specific one.

```
# Created 5 invoices on Proc_Facturas within transaction
# Currently positioned on the last one created
Go to Record/Request/Page [First]
Loop
    Exit Loop If [Facturas::__kpln__Factura = $IdFacturaBuscada]
    Go to Record/Request/Page [Next; Exit after last]
End Loop
Revert Transaction [Condition: error.ThrowIf (
    Facturas::__kpln__Factura ≠ $IdFacturaBuscada ;
    _error_FAILED_CONDITION ; "Factura no encontrada en found set"
)]
```

**When to use:** You created N records and need to return to a specific one that isn't the last.

### Strategy 3: Collect Before Leaving

Capture everything you need from a newly created record into variables before navigating away. This eliminates the need to return to the record at all.

```
New Record/Request
Set Field [Facturas::_kfln__Cliente; $IdCliente]
# ... set all fields ...

# Capture everything needed BEFORE leaving
Insert Calculated Result [$IdFactura; Facturas::__kpln__Factura]
Insert Calculated Result [$NumeroFactura; Facturas::NumeroFactura]

Go to Layout ["Proc_FacturasLineas"]  # safe to leave now
```

**When to use:** You know in advance what data you'll need from the record later.

### Strategy 4: Communicate Via ScriptResult

Subscripts return data via `Get(ScriptResult)` in JSON. The parent script never needs to relocate the child's records — the child reports everything the parent needs.

```
# Child script creates a record and returns its data:
Exit Script [JSONSetElement(error.GetTrace;
    "result"; JSONSetElement("{}";
        ["IdFactura"; Facturas::__kpln__Factura; JSONString];
        ["DineroNeto"; Facturas::DineroNeto; JSONNumber]
    ); JSONRaw
)]

# Parent reads the result without finding the record:
Insert Calculated Result [$IdFactura;
    JSONGetElement(Get(ScriptResult); "result.IdFactura")]
```

**When to use:** Parent-child script communication. This is the **recommended pattern** for transactional subscripts in the Clew architecture.

### Strategy 5: Don't Read Auto-Enter Values Inside Transactions

Auto-enter calculations are deferred until `Commit Transaction` (unless "Skip auto-enter options" is enabled). A field with an auto-enter formula will show an empty or stale value within the transaction.

```
# WRONG: reading auto-enter value before commit
Set Field [Facturas::SuplidosTotalSupplies; $BaseFactura * $NumAsignaciones]
# SuplidosWithholding has auto-enter: SuplidosTotalSupplies * SuplidosWithholdingPercentage / 100
Insert Calculated Result [$Withholding; Facturas::SuplidosWithholding]
# $Withholding will be EMPTY — auto-enter hasn't fired yet

# CORRECT: calculate manually if you need the value before commit
Insert Calculated Result [$Withholding;
    ($BaseFactura * $NumAsignaciones) * $IRPFtipo / 100]
```

**When to use:** Whenever you need a computed value that depends on an auto-enter formula before the transaction commits.

### Strategy 6: Set Revert Transaction on Error [Off] for Controlled Errors

By default (`On`), validation errors and privilege errors auto-revert the entire transaction. When a `Perform Find` returning error 401 is expected behavior (not a data error), this can accidentally revert your work.

```
# Temporarily disable auto-revert for a find that might return 401
Set Revert Transaction on Error [Off]
Enter Find Mode []
Set Field [Roles::__kpln__Rol; $IdRol]
Perform Find []
Insert Calculated Result [$FindError; Get(LastError)]
Set Revert Transaction on Error [On]  # restore default

If [$FindError = 401]
    # Handle "not found" gracefully without reverting the whole transaction
End If
```

**When to use:** When an operation inside a transaction might produce an error that is expected/handled, not a sign of data corruption. Note: `Perform Find` returning 401 does NOT auto-revert by itself (it's not a validation/privilege error), but other operations might.

## Quick Reference: What Works Inside Transactions

| Operation | Works? | Notes |
|-----------|--------|-------|
| `New Record/Request` | Yes | Record is held in temp space |
| `Set Field` on new record | Yes | Changes held until Commit |
| `Perform Find` for new records | **No** | New records not indexed yet |
| `ExecuteSQL` for new records | **No** | Same limitation — operates on indexes |
| `Perform Find` for existing records | Yes | Existing records are in the index |
| `ExecuteSQL` for existing records | Yes | Existing records are in the index |
| `Go to Record [Next/Previous]` | Yes | Navigates within current found set |
| Read field values from new record | Yes | Values are in temp space |
| Read auto-enter calculated values | **Deferred** | Calculated at Commit time |
| Relationship-based access to new records | **Unreliable** | Depends on indexing |
| `Revert Transaction` in subscript | Yes | Reverts parent's transaction |
| `Open Transaction` in subscript | Skipped | Returns error 3 (expected) |

## Anti-Patterns

```
# ANTI-PATTERN 1: Find after create within transaction
Open Transaction
    New Record/Request
    Set Field [Table::PK; $newId]
    Go to Layout ["Other Layout"]
    # ... do other work ...
    Go to Layout ["Original Layout"]
    Enter Find Mode []
    Set Field [Table::PK; $newId]
    Perform Find []  # ERROR 401 — record not indexed
Commit Transaction

# ANTI-PATTERN 2: Reading auto-enter before commit
Open Transaction
    Set Field [Table::Input; 100]
    Insert Calculated Result [$computed; Table::AutoCalcField]
    # $computed is EMPTY — auto-enter hasn't fired
Commit Transaction

# ANTI-PATTERN 3: Assuming relationship access to new records
Open Transaction
    Go to Layout ["Parent"]
    New Record/Request
    Set Field [Parent::PK; $parentId]
    Go to Layout ["Child"]
    New Record/Request
    Set Field [Child::FK; $parentId]
    Go to Layout ["Parent"]
    # Portal showing children may be EMPTY — relationship not resolved
Commit Transaction
```
