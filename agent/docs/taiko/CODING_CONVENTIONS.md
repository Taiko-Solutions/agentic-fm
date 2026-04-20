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

Use this 3-step format for section comments within scripts:

```
# -------------------------------------------------------------------------------------
# NOMBRE DE LA SECCIÓN
#
```

Each section separator consists of:
1. A comment step with a line of dashes (`-`, NOT box-drawing characters `─`)
2. A comment step with the section title in UPPERCASE
3. An empty comment step for visual spacing

**IMPORTANT:** Use standard ASCII dashes `----...----` for separators and `====...====` for headers. Box-drawing characters (`──────`) look similar but cause rendering issues in some editors and are not the Taiko standard.

---

## XML Comment Formatting

When generating fmxmlsnippet XML, every line of text in comments must be a **separate** `<Step>` element. This is critical for readability in FileMaker's Script Workspace, where multi-line text inside a single comment step collapses into one unreadable line.

### Header comments — each line is a separate step:

```xml
<Step enable="True" id="89" name="# (comment)">
  <Text>=====================================================================================</Text>
</Step>
<Step enable="True" id="89" name="# (comment)">
  <Text>Propósito: Descripción del script</Text>
</Step>
<Step enable="True" id="89" name="# (comment)">
  <Text>Contexto: NombreTabla o insensitive</Text>
</Step>
<!-- ... cada línea es un paso separado ... -->
<Step enable="True" id="89" name="# (comment)">
  <Text>=====================================================================================</Text>
</Step>
```

### Section separators — 3 pasos (separador + título + vacío):

```xml
<Step enable="True" id="89" name="# (comment)">
  <Text>-------------------------------------------------------------------------------------</Text>
</Step>
<Step enable="True" id="89" name="# (comment)">
  <Text>NOMBRE DE LA SECCIÓN</Text>
</Step>
<Step enable="True" id="89" name="# (comment)"/>
```

### Empty comment steps for visual spacing:

Use self-closing tags between sections:

```xml
<Step enable="True" id="89" name="# (comment)"/>
```

---

## FM Script Step ID Reference

When generating fmxmlsnippet XML, use these real step IDs instead of `id="0"`:

| Step Name | ID | Notes |
|-----------|-----|-------|
| `# (comment)` | 89 | Comments, headers, separators |
| `Allow User Abort` | 85 | |
| `Set Error Capture` | 86 | |
| `Loop` | 71 | |
| `End Loop` | 73 | |
| `Exit Loop If` | 72 | Primary Clew control flow |
| `If` | 68 | |
| `Else` | 69 | |
| `Else If` | 125 | |
| `End If` | 70 | |
| `Set Field` | 76 | |
| `Insert Calculated Result` | 77 | Preferred for variables |
| `Set Variable` | 141 | Only for void calls like `error.DeleteTrace` |
| `Perform Script` | 1 | |
| `Exit Script` | 103 | |
| `Go to Layout` | 6 | Use real layout ID, NOT `id="0"` — FM silently fails to bind on some imports |
| `Go to Record/Request/Page` | 16 | Children: `<RowPageLocation value="First\|Next\|…"/>` and `<Exit state="True"/>` — see fmxmlsnippet rules |
| `New Record/Request` | 7 | |
| `Commit Records/Requests` | 75 | |
| `Enter Find Mode` | 22 | |
| `Perform Find` | 28 | |
| `New Window` | 122 | |
| `Close Window` | 118 | |
| `Show Custom Dialog` | 87 | |
| `Open Transaction` | 200 | |
| `Commit Transaction` | 201 | |
| `Revert Transaction` | 202 | |

### Special case: `error.DeleteTrace`

`error.DeleteTrace` clears the error state and returns a void value. It MUST use `Set Variable` (id="141"), NOT `Insert Calculated Result`:

```xml
<Step enable="True" id="141" name="Set Variable">
  <Value>
    <Calculation><![CDATA[error.DeleteTrace]]></Calculation>
  </Value>
  <Repetition>
    <Calculation><![CDATA[1]]></Calculation>
  </Repetition>
  <Name>$_Void</Name>
</Step>
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

## Schema — Text field indexing

**All new Text fields must be configured with `indexLanguage="Spanish"`** (Spanish Modern). This applies regardless of creation channel (OData, manual in Manage Database, or XML paste).

Canonical `<Storage>` block:

```xml
<Storage autoIndex="True" index="Minimal" indexLanguage="Spanish" global="False" maxRepetition="1"/>
```

**Why:** the default indexLanguage in FileMaker installations in English is "English" or "Unicode" — this breaks case-insensitive search and diacritic-agnostic sort for Spanish names (accents, Ñ, ordering). Spanish Modern is the Taiko standard.

**How to apply:**

- **OData field creation**: OData does NOT expose `indexLanguage`. After creating the field via OData, open Manage Database in FM Pro and set Storage → Indexing language → Spanish manually. Treat this as a mandatory step before marking the field creation as done.
- **Manual field creation in Manage Database**: on the Storage tab, set Indexing language = Spanish.
- **fmxmlsnippet paste**: include the `<Storage>` block above. FM will honour it on import.

Applies to: `EmpresaNombre`, `DireccionCiudad`, email fields, any multi-valor checkbox (like `TipoEmpresa`), free-text notes, and any other Text-typed field — **no exceptions**.

---

## Anti-Patterns

- Do NOT mix camelCase and PascalCase for variables (always PascalCase)
- Do NOT use Set Variable when Insert Calculated Result works
- Do NOT use generic script names (`DoStuff`, `Process`)
- Do NOT write obvious comments ("Seteamos la variable X") — explain _why_, not _what_
- Do NOT use magic numbers — extract to named constants
- Do NOT use reserved FM words as custom function parameter names
