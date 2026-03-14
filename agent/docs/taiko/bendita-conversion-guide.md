# Guía de Conversión: Geist → Clew Transaccional (Bendita)

> **Alcance**: Scripts transaccionales de BPController que migran a BPController2025.
> **Local a este repo** — no se comparte vía taiko-conventions.

---

## 1. Por qué se migra

| Aspecto | Geist (BPController) | Clew (BPController2025) |
|---------|---------------------|------------------------|
| Transacciones | Helper scripts (`Start Transaction` / `End Transaction`) que crean registro en `DBTransactions` y navegan por relaciones | `Open Transaction` / `Commit Transaction` / `Revert Transaction` nativos FM 2024 |
| Rollback | Manual (borrar registro `DBTransactions`, revertir campos) | Automático (`Revert Transaction` deshace todos los cambios) |
| Acceso a datos | Relación vía `DBTransactions::IdXxx` | `Go to Layout` + `Perform Find` directo |
| Error handling | `Error.IsError()` + `Custom.Error()` | `error.ThrowIf()` + `error.GetTrace` (traza acumulativa) |
| Rendimiento | Lento (crea registros auxiliares, navega relaciones) | Rápido (operación nativa, sin registros temporales) |

---

## 2. Inventario de cambios por sección

### 2.1 Estructura transaccional

| Geist | Clew |
|-------|------|
| `Freeze Window` | No necesario (ventana temporal) |
| `Perform Script ["Start Transaction"]` | `Open Transaction` |
| Acceso vía `DBTransactions::Campo` | `Go to Layout ["Proc_*"]` + `Perform Find` |
| `Perform Script ["Save Transaction Result"]` | *(no existe — el resultado se construye en variables)* |
| `Perform Script ["End Transaction"]` | `Commit Transaction` |
| Error → `End Transaction` con flag | `Revert Transaction` (automático, salta a `Commit Transaction`) |

### 2.2 Validación de parámetros

| Geist | Clew |
|-------|------|
| `JSON.Format( Get(ScriptParameter) ; "" )` | `error.CreateVarsFromKeys( Get(ScriptParameter) ; "" )` |
| `JSON.Validate.This($Data)` | *(incluido en CreateVarsFromKeys)* |
| `JSON.Validate.Rule.IsRequired("campo")` | `error.ThrowIfMissingParam( $REQUIRED ; "" )` |
| `JSON.Validate.ApplyRules( List(...) )` | *(un solo paso con ThrowIfMissingParam)* |
| `JSONGetElement($Data; "campo")` → `$campo` | Automático: `CreateVarsFromKeys` crea `$campo` directamente |

### 2.3 Error handling

| Geist | Clew |
|-------|------|
| `Error.IsError( $error )` | `error.WasThrown` (booleano, consulta tras Exit Loop o tras Revert) |
| `Custom.Error( "mensaje" ; -2 )` | `error.ThrowIf( True ; _error_FAILED_CONDITION ; "mensaje" )` |
| `Exit Loop If [ Error.IsError($error) ]` | `Revert Transaction [ Condition: error.ThrowIf(...) ]` |
| `Exit Loop If [ Error.IsError($error) ]` (tras Find) | `Revert Transaction [ Condition: error.ThrowIfLast("contexto") ]` |
| `Get(LastError) = 401` check manual | `error.ThrowIfLast("contexto")` (incluye 401 automáticamente) |
| `Exit Script [ Custom.Error(...) ]` | `Exit Script [ error.GetTrace ]` |

### 2.4 Acceso a datos (sin DBTransactions)

| Geist (vía DBTransactions) | Clew (directo) |
|---------------------------|----------------|
| `Set Field [ DBTransactions::IdProyecto ; $Id ]` + relación | `Go to Layout ["Proc_Proyecto"]` + `Enter Find Mode` + `Set Field [__kpln__Proyecto; $Id]` + `Perform Find` |
| `DBTransactions::CampoRelacionado` | Campo directo en el layout encontrado |
| `Usuarios::AccountPrivilegesSetName` (vía relación) | `Get( AccountPrivilegeSetName )` (función nativa) |
| `ExecuteSQL( "SELECT..." )` | `Perform Find` con criterios en campos (más eficiente dentro de transacción) |

### 2.5 Logging

| Geist | Clew |
|-------|------|
| `Log.Entry( nivel ; mensaje )` inline | `Log.Entry( nivel ; mensaje )` inline (igual) |
| `Log.Reset` al inicio | `Log.Reset` al inicio (igual) |
| Error log: incluido en End Transaction | `Perform Script ["Create Log Clew" ; Parameter: $ErrorData]` en catch block |
| N/A | `error.NormalizeFromGeist( $geistError )` para errores cross-framework |

### 2.6 Resultado del script

| Geist | Clew |
|-------|------|
| Éxito: `Exit Script [ JSONSetElement("{}" ; [...]) ]` | Éxito: `Exit Script [ JSONSetElement( error.GetTrace ; ["result"; $Resp; JSONRaw] ; ["environment"; getScriptEnvironment.old; JSONRaw] ) ]` |
| Error: `Exit Script [ Custom.Error("msg"; -2) ]` | Error: `Exit Script [ error.GetTrace ]` |
| Detección en caller: `Error.IsError( $result )` | Detección en caller: `not IsEmpty( JSONGetElement( $result ; "errorTrace" ) )` |
| Parseo: `JSONGetElement( $result ; "campo" )` | Parseo: `JSONGetElement( $result ; "result.campo" )` |

---

## 3. Patrón transaccional Clew (estructura completa)

```
Allow User Abort [ Off ]
Set Error Capture [ On ]

# ── CHECK TRANSACTION STATE ──
Insert Calculated Result [ $TransactionOpenState ; Get(TransactionOpenState) ]
If [ not $TransactionOpenState ]
    Log.Reset
    Insert Calculated Result [ $WindowName ; "tmp_" & Get(UUID) ]
    New Window [ Document ; $WindowName ; Layout: "Proc_*" ]
End If

# ── OPEN TRANSACTION ──
Open Transaction

    # ── PARSE & VALIDATE ──
    Revert Transaction [ Condition: error.CreateVarsFromKeys( Get(ScriptParameter) ; "" ) ]
    Insert Calculated Result [ $REQUIRED ; List( "Param1" ; "Param2" ) ]
    Revert Transaction [ Condition: error.ThrowIfMissingParam( $REQUIRED ; "" ) ]

    # ── ACCEDER A DATOS ──
    Go to Layout [ "Proc_*" ]
    Enter Find Mode []
    Set Field [ Table::__kpln__Id ; $IdParametro ]
    Perform Find []
    Revert Transaction [ Condition: error.ThrowIfLast( "Registro no encontrado: " & $IdParametro ) ]

    # ── LÓGICA DE NEGOCIO ──
    # ... validaciones con Revert Transaction [ Condition: error.ThrowIf(...) ]
    # ... Set Field para modificar datos

    # ── CONSTRUIR RESULTADO ──
    Insert Calculated Result [ $Respuesta ; JSONSetElement( "{}" ; [...] ) ]

# ── COMMIT TRANSACTION ──
Commit Transaction

# ── POST-TRANSACTION ──
If [ error.WasThrown ]
    # Error: la transacción ya fue revertida
    Insert Calculated Result [ $ErrorData ; JSONSetElement( error.GetTrace ;
        [ "environment" ; getScriptEnvironment.old ; JSONRaw ] ) ]
    Perform Script [ "Create Log Clew" ; Parameter: $ErrorData ]
    Close Window [ $WindowName ]
    Go to Layout [ original layout ]
    Exit Script [ error.GetTrace ]
End If

# Verificar que Commit fue exitoso
Insert Calculated Result [ $CommitError ; error.ThrowIfLast( "Error al confirmar transacción" ) ]
If [ $CommitError ]
    Perform Script [ "Create Log Clew" ; Parameter: error.GetTrace ]
    Close Window [ $WindowName ]
    Go to Layout [ original layout ]
    Exit Script [ error.GetTrace ]
End If

# ── SUCCESS ──
Close Window [ $WindowName ]
Go to Layout [ original layout ]
Exit Script [ JSONSetElement( error.GetTrace ;
    [ "result" ; $Respuesta ; JSONRaw ] ;
    [ "environment" ; getScriptEnvironment.old ; JSONRaw ]
) ]
```

### Notas sobre el patrón

- **`Revert Transaction [Condition:]`** funciona como compuerta: si la condición es `True` (error), revierte la transacción y **salta automáticamente al `Commit Transaction` correspondiente**. Desde ahí, la ejecución continúa normalmente.
- **`error.WasThrown`** después de `Commit Transaction` detecta si hubo un Revert previo.
- **No se usa Loop/Exit Loop If**: El `Revert Transaction [Condition:]` reemplaza esa estructura.
- **Ventana temporal**: Se crea solo si no estamos dentro de una transacción existente (`Get(TransactionOpenState) = 0`).

---

## 4. Adaptación del caller (BP 2016)

Cuando un script en BP 2016 llama a un controlador que migró a Clew:

### 4.1 Cambiar referencia de archivo

```
# ANTES:
Perform Script [ "NombreScript" ; File: "Controlador" ; Parameter: ... ]

# DESPUÉS:
Perform Script [ "NombreScript" ; File: "BPController2025" ; Parameter: ... ]
```

> **Requisito**: Crear/verificar External Data Source en BP 2016 que apunte a BPController2025.

### 4.2 Cambiar detección de errores

```
# ANTES (Geist):
If [ Error.IsError( $Result ) ]

# DESPUÉS (Clew, sin CFs Clew en BP 2016):
If [ not IsEmpty( JSONGetElement( $Result ; "errorTrace" ) ) ]
```

> Si BP 2016 tiene instalada `json.IsErrorTrace`, usar: `If [ json.IsErrorTrace( $Result ) ]`

### 4.3 Cambiar mensaje de error

```
# ANTES:
Show Custom Dialog [ "Error" ; JSONFormatElements( $Result ) ]

# DESPUÉS:
Show Custom Dialog [ "Error" ; JSONGetElement( $Result ; "errorTrace[0].hint" ) ]
```

### 4.4 Cambiar parseo del resultado exitoso

```
# ANTES:
JSONGetElement( $Result ; "Campo" )

# DESPUÉS:
JSONGetElement( $Result ; "result.Campo" )
```

El resultado exitoso Clew envuelve los datos:
```json
{
  "result": { "Campo": "valor", ... },
  "environment": { ... }
}
```

---

## 5. Checklist por script

Usar esta lista para cada script transaccional que se migre:

### Preparación
- [ ] Verificar que las Custom Functions Clew están instaladas en BPController2025
- [ ] Verificar que existe la referencia de archivo BP 2016 → BPController2025
- [ ] Identificar el layout `Proc_*` correspondiente a cada tabla accedida

### Análisis del script original
- [ ] Leer el script original completo en `scripts_sanitized/BPController/`
- [ ] Identificar parámetros de entrada (JSON keys)
- [ ] Mapear relaciones via `DBTransactions` → layouts + campos directos
- [ ] Identificar accesos a tabla `Usuarios` → sustituir por `Get()` o `Perform Find`
- [ ] Identificar validaciones y su lógica de negocio
- [ ] Identificar qué datos se devuelven en el resultado

### Generación del script Clew
- [ ] Crear estructura transaccional (Open/Revert/Commit)
- [ ] Convertir validaciones de params a `error.CreateVarsFromKeys` + `error.ThrowIfMissingParam`
- [ ] Reemplazar acceso por relaciones → `Go to Layout` + `Perform Find`
- [ ] Convertir `Error.IsError` / `Custom.Error` → `error.ThrowIf` / `error.ThrowIfLast`
- [ ] Incluir logging con `Log.Entry` y `Create Log Clew` en catch
- [ ] Construir resultado con `JSONSetElement` incluyendo `result` y `environment`
- [ ] Generar fmxmlsnippet XML con agentic-fm
- [ ] Validar XML con `validate_snippet.py`

### Adaptación del caller (BP 2016)
- [ ] Cambiar referencia de archivo en `Perform Script`
- [ ] Cambiar detección de errores (`Error.IsError` → `errorTrace`)
- [ ] Cambiar parseo de resultado (`"Campo"` → `"result.Campo"`)
- [ ] Generar snippet de adaptación si aplica

### Verificación
- [ ] Probar flujo exitoso completo
- [ ] Probar flujo con error de validación (params faltantes)
- [ ] Probar flujo con error de negocio (sin autorización, registro no encontrado)
- [ ] Verificar rollback: cambiar datos → provocar error → confirmar que se revirtió
- [ ] Verificar que `Create Log Clew` registra errores correctamente
- [ ] Verificar que el caller recibe y muestra errores correctamente
- [ ] Verificar que el resultado exitoso se parsea correctamente en el caller

---

## 6. Ejemplo completo: `Roles | Control Bloqueo`

### Antes (BPController, Geist — ID 632)

```
Freeze Window
Perform Script [ "Start Transaction" ; Parameter: JSON con IdRol, IdProyecto... ]
    ↓
DBTransactions::IdProyecto → relación a Proyectos
Usuarios::AccountPrivilegesSetName → relación a Usuarios
    ↓
Validación autorización con Case()
    ↓
Set Field [ DBTransactions::PermisoBloqueo ; $Permiso ]
    ↓
ExecuteSQL para FechaTodosRoles3
    ↓
Exit Loop If [ Error.IsError($error) ] en cada compuerta
    ↓
Perform Script [ "End Transaction" ]
Exit Script [ resultado JSON plano ]
```

### Después (BPController2025, Clew)

```
Open Transaction
    ↓
error.CreateVarsFromKeys → parsea $IdRol, $IdProyecto, etc.
error.ThrowIfMissingParam → valida requeridos
    ↓
Go to Layout ["Proc_Proyecto"] → Perform Find → lee campos directos
Get(AccountPrivilegeSetName) → sin relación a Usuarios
    ↓
Validación autorización con Case() (misma lógica)
    ↓
Go to Layout ["Proc_Rol"] → Perform Find → Set Field directamente
    ↓
Perform Find con "<2" para FechaTodosRoles3 (en vez de ExecuteSQL)
    ↓
Revert Transaction [Condition: error.ThrowIf/ThrowIfLast] en cada compuerta
    ↓
Commit Transaction
Exit Script [ JSON con result + environment ]
```

### Archivos generados

| Archivo | Descripción |
|---------|-------------|
| `agent/sandbox/roles-control-bloqueo-clew.xml` | Script XML completo para BPController2025 |
| `agent/sandbox/bp2016-bloqueo-roles-error-clew.xml` | Snippet de adaptación para BP 2016 |

---

## 7. Notas específicas Bendita

### Recursos en BPController2025

| Recurso | Detalle |
|---------|---------|
| Layout `Proc_Rol` | Basado en tabla `Roles` — buscar/editar roles |
| Layout `Proc_Proyecto` | Basado en tabla `Proyectos` — buscar/editar proyectos |
| Script `Create Log Clew` (ID 1291) | Logging independiente de transacción |
| Script `Create Log` | Logging legacy (para scripts que aún no migraron) |

### Convenciones de variables

- **PascalCase** para variables: `$IdProyecto`, `$PermisoBloqueo`, `$NombreProyecto`
- **Comentarios en español** con separadores `── SECCIÓN ──`
- **`Insert Calculated Result`** preferido sobre `Set Variable`
- **`$REQUIRED`** en mayúsculas para la lista de parámetros requeridos (constante)

### Referencia de archivos

BP 2016 actualmente llama a `File: "Controlador"` (BPController). Para scripts migrados a BPController2025, se necesita:
1. External Data Source en BP 2016 apuntando a BPController2025
2. Cambiar el `File:` en cada `Perform Script` que llame al script migrado

### Perform Find dentro de transacción

Dentro de una transacción abierta con `Open Transaction`, un `Perform Find` ejecutado en la **misma sesión** ve los cambios no confirmados. Esto permite:
- Modificar un campo → buscar registros basándose en el valor modificado
- Si en pruebas esto no se cumple, fallback: usar ExecuteSQL con el patrón resiliente documentado en `agent/docs/taiko/knowledge/executesql-pattern.md`

---

## Historial

| Fecha | Script | Estado |
|-------|--------|--------|
| 2026-03-04 | `Roles \| Control Bloqueo` | Migrado (XML generado + snippet BP 2016) |
