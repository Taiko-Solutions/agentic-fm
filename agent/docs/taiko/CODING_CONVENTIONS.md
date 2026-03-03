# Taiko Solutions — Coding Conventions

These conventions **override** the base conventions in `agent/docs/CODING_CONVENTIONS.md`. For anything not defined here, the base conventions apply as fallback.

---

## Author metadata

All scripts created for Taiko Solutions use this author in the History section:

```
# Creado: YYYY-MM-DD Marco Antonio Pérez
# Modificado: YYYY-MM-DD Marco Antonio Pérez - Descripción del cambio
```

---

## Language

**Comments and hints: ALWAYS in Spanish.**

- Script header comments in Spanish (Propósito, Contexto, Parámetros, Retorna, Historial)
- Section separators in Spanish
- Inline comments in Spanish
- Error hints in Spanish: `"Cliente con ID " & $ClienteID & " no encontrado"`

**Exceptions — keep in English:**

- Custom function names: `error.Throw`, `json.CreateVars`
- Error constants: `_error_NO_RECORDS_FOUND`
- Internal JSON properties: `success`, `errorTrace`
- Standard technical terms: `success`, `error`, `true`, `false`

---

## Naming Conventions

### Variables

| Scope | Prefix | Convention | Example |
|-------|--------|------------|---------|
| Script-local | `$` | PascalCase | `$ClienteID`, `$FechaInicio`, `$TotalFactura` |
| Global | `$$` | PascalCase | `$$UsuarioActual`, `$$ConfiguracionApp` |
| Private/temporary | `$_` | PascalCase | `$_TempValue`, `$_Counter` |

**NOTE:** The base conventions use camelCase (`$invoiceTotal`). Taiko uses PascalCase (`$TotalFactura`). This override applies to all generated code.

### Fields

| Type | Convention | Example |
|------|-----------|---------|
| Regular | PascalCase | `ClienteID`, `NombreCompleto`, `FechaCreacion` |
| Calculated | PascalCase | Same as regular |
| System/audit | `z_` prefix | `z_CreatedBy`, `z_CreatedTimestamp` |
| Primary key | `Id` | `Id` |
| Foreign key | `Id_Tablename` | `Id_Cliente` |

### Tables and Table Occurrences

| Type | Convention | Example |
|------|-----------|---------|
| Base table | Singular noun | `Cliente`, `Factura`, `Producto` |
| Base TO (anchor) | `PREFIX__Tabla` | `CLI__Cliente`, `FAC__Factura` |
| Related TO | `prefix_PREFIX__Tabla` | `cli_FAC__Facturas`, `fac_PRO__Productos` |

### Scripts

| Layer | Convention | Example |
|-------|-----------|---------|
| Interface | PascalCase + descriptive verb | `BuscarCliente`, `NuevoProducto` |
| Controller | PascalCase + `.Controller` | `CrearCliente.Controller`, `BuscarPedidos.Controller` |
| Private/utility | `_` prefix | `_ValidarEmail`, `_CalcularImpuesto` |
| Utility Manager | `[Entity] Utility \| Alta, Editar` | `Cliente Utility \| Alta, Editar` |
| Initialize Shadow | `[Entity] Utility \| Initialize Shadow` | `Recibidas Utility \| Initialize Shadow` |
| Transactional | `[Entity] \| Alta Modificar [Entity] {json}` | `Empresas \| Alta Modificar Empresa {json}` |

### Custom Functions

| Type | Convention | Example |
|------|-----------|---------|
| Functional | `category.FunctionName` | `error.Throw`, `json.CreateVars`, `date.FormatISO` |
| Constants | `_CATEGORY_CONSTANT` | `_error_NO_RECORDS_FOUND`, `_STATUS_ACTIVE` |

**Parameter naming:** Do NOT use FileMaker reserved words as parameter names (`ScriptResult`, `ScriptName`, `ScriptParameter`, `LayoutName`, `FileName`). They cause silent failures when pasting XML — the function is created but with empty body and parameters. Use Spanish names (`ResultadoScript`) or descriptive prefixes (`theResult`).

### Layouts

- Format: `Tablename: Layout Name (form|list)`
- Same as base conventions — no override needed.

---

## Preferred Script Steps

**Insert Calculated Result** (step id="77") is the PREFERRED step for assigning variables.

Use Insert Calculated Result instead of Set Variable:
- More concise and direct
- Less verbose XML
- Standard across existing Taiko scripts

---

## Script Header Comments

All scripts must include a header block in Spanish:

```
# =====================================================================================
# Propósito: [Descripción del propósito]
# Contexto: [Tabla específica o "insensitive"]
# Capa: [Interfaz | Controlador]
# Parámetros Requeridos:
#   - NombreParam (tipo): descripción
# Parámetros Opcionales:
#   - NombreParam (tipo): descripción
# Retorna:
#   Éxito: {"campo": valor, "success": true}
#   Error: errorTrace JSON
# Historial:
#   Creado: YYYY-MM-DD Marco Antonio Pérez
# =====================================================================================
```

---

## Script Section Separators

Use this format for section comments within scripts:

```
# ──────────────────────────────────────────
# NOMBRE DE LA SECCIÓN
# ──────────────────────────────────────────
```

---

## JSON Conventions

- Property names in `camelCase` (even though variables use PascalCase)
- Group related properties together
- Success result: `{"campo": valor, "success": true}`
- Error result: always the standard Clew errorTrace JSON

---

## Script Length

- Recommended: < 100 steps
- Maximum acceptable: < 200 steps
- If exceeding: split into specialized subscripts

---

## Anti-Patterns

- Do NOT mix camelCase and PascalCase for variables (always PascalCase)
- Do NOT use Set Variable when Insert Calculated Result works
- Do NOT use generic script names (`DoStuff`, `Process`)
- Do NOT write obvious comments ("Seteamos la variable X") — explain _why_, not _what_
- Do NOT use magic numbers — extract to named constants
- Do NOT use reserved FM words as custom function parameter names
