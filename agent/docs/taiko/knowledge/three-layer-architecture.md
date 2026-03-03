# Three-Layer Architecture

Taiko Solutions organizes FileMaker development into three distinct layers with strict separation of responsibilities. This architecture ensures maintainability, testability, and clear data flow.

## Layer Overview

```
Interface  ──>  Controller  ──>  Data
           <──  (result)   <──
```

### Interface Layer (Presentation)

**Purpose:** User interaction — what the user sees and does.

**Responsibilities:**
- Display layouts and views
- Capture user input
- Basic UI validation (empty fields, format checks)
- Call Controller scripts
- Present results (success messages, error dialogs)
- Navigation between layouts

**Must NOT:**
- Modify data directly (no `Set Field` on data tables)
- Contain business logic
- Execute transactions
- Perform commits/reverts on data records
- Access the Data layer directly (always go through Controller)

**Script naming:** PascalCase with a descriptive verb — `BuscarCliente`, `NuevoProducto`, `MostrarFactura`

### Controller Layer (Business Logic)

**Purpose:** Execute business rules and manage data operations.

**Responsibilities:**
- Navigate to data layouts (`Go to Layout`)
- Find records (`Enter Find Mode`, `Perform Find`)
- Create records (`New Record/Request`)
- Modify records (`Set Field`)
- Validate business rules
- Execute complete transactions
- Commit/Revert changes
- Return structured results as JSON
- Handle errors with the Clew pattern

**Must NOT:**
- Have UI dependencies (no `Show Custom Dialog`)
- Know about presentation layouts
- Show dialogs to the user directly

**Script naming:** PascalCase + `.Controller` suffix — `CrearCliente.Controller`, `ActualizarFactura.Controller`, `BuscarPedidos.Controller`

### Data Layer (Storage)

**Purpose:** Define data structure and storage.

**Elements:**
- Table definitions
- Stored and calculated fields
- Auto-enter calculations
- Field validations
- Relationships (TOG — Table Occurrence Groups)
- Indexes

**Must NOT:**
- Contain scripts (with rare, justified exceptions)
- Have presentation logic
- Execute complex transactions

## Typical Execution Flow

```
1. USER clicks "Nueva Factura" button
   |
2. INTERFACE: Script "NuevaFactura"
   - Validates that the user selected a client
   - Prepares JSON parameters
   - Calls CrearFactura.Controller
   |
3. CONTROLLER: Script "CrearFactura.Controller"
   - Parses parameters
   - Goes to Facturas layout
   - Validates client exists
   - Creates new record
   - Sets fields (ClienteID, Fecha, etc.)
   - Validates business rules
   - Commits record
   - Returns {"FacturaID": 123, "success": true}
   |
4. INTERFACE: Receives result
   - If success: shows success message
   - If error: shows error.GetHint
   - Updates UI
```

## Communication Between Layers

### Parameters (Interface -> Controller)

```json
{
  "ClienteID": 123,
  "Fecha": "2025-01-01",
  "Productos": [
    {"ProductoID": 1, "Cantidad": 5},
    {"ProductoID": 2, "Cantidad": 3}
  ]
}
```

### Results (Controller -> Interface)

**Success:**
```json
{
  "FacturaID": 456,
  "Total": 1250.50,
  "success": true
}
```

**Error:**
```json
{
  "errorTrace": [
    {
      "code": "NO_RECORDS_FOUND",
      "hint": "Cliente ID 123 no existe",
      "script": {"name": "CrearFactura.Controller"}
    }
  ]
}
```

## Design Principles

- **Single responsibility:** one script, one purpose. Do not mix create + update in one script.
- **Unidirectional flow:** Interface -> Controller -> Data -> (result) -> Interface.
- **Minimal coupling:** Interface scripts do not know about data structure. Controller scripts do not know about presentation layouts.
- **Maximum cohesion:** each script has a clear, focused responsibility.
- **JSON communication:** structured parameters and results, always.
- **Explicit transactions:** conscious Commit/Revert, never implicit.

## Anti-Patterns to Avoid

### Interface with Business Logic

```
# BAD — business logic in Interface script
New Record
Set Field [Cliente::Nombre; $Nombre]
Set Field [Cliente::Credito; $CreditoInicial * 1.1]  # business rule!
Commit Record
```

### Controller with UI Dependencies

```
# BAD — Controller showing dialogs
Show Custom Dialog ["Cliente creado"]
Go to Layout ["Vista Cliente"]  # presentation layout!
```

### Direct Data Access from Interface

```
# BAD — Interface bypassing Controller
Go to Layout ["Clientes_Datos"]
Perform Find [...]
```

## Relationship Management

In Controller scripts, prefer explicit navigation over complex relationships:

```
# PREFER: explicit script navigation
Go to Layout [Facturas]
Perform Find [Cliente::Id = $ClienteID]
Set Field [Facturas::Total; ...]

# AVOID: accessing data through relationships
Set Field [CLI_FAC__Facturas::Total; ...]  # relationship dependency
```
