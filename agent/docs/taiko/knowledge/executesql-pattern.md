# ExecuteSQL — Patrón resiliente con SQL.Get*

## Regla

**OBLIGATORIO**: Toda consulta ExecuteSQL en soluciones Taiko debe usar `SQL.GetFieldName()` y `SQL.GetTableName()` para resolver nombres de campos y tablas dinámicamente. **NUNCA** hardcodear nombres de tabla o campo como strings literales en la query SQL.

## Motivación

- Si un campo o tabla se renombra en FileMaker, la query no se rompe — las funciones resuelven el nombre actual.
- Evita problemas con caracteres especiales o nombres reservados en SQL.
- Es autodocumentado: la referencia al campo FileMaker es explícita.

## Custom functions disponibles

XML source: `agent/docs/taiko/custom_functions/sql-cfs.xml` (module [fm-sql-cfs](https://github.com/karbonfm/fm-sql-cfs) by Geist Interactive)

| Función | Propósito |
|---------|-----------|
| `SQL.GetTableName ( campo )` | Devuelve el nombre SQL (quoted) de la tabla base del campo |
| `SQL.GetFieldName ( campo )` | Devuelve el nombre SQL (quoted) del campo como `"TO"."Field"` |
| `SQL.GetColumnStatement ( theField ; whereField ; whereValue )` | Construye un SELECT/FROM/WHERE como texto — usado internamente por las demás |
| `SQL.GetColumn ( columnField ; whereField ; whereValue )` | Ejecuta SELECT de un campo con un WHERE |
| `SQL.GetColumn2Fields ( columnField ; whereField ; whereValue ; whereField2 ; whereValue2 )` | SELECT con dos condiciones WHERE (AND) |
| `SQL.GetRecordsAsJSON ( whereField ; whereValue )` | Busca registros y devuelve un JSON array usando el campo `AsJSON` de la tabla |
| `SQL.RecordExists ( whereField ; whereValue )` | **⚠ BUG upstream — NO USAR**. Ver aviso más abajo. Siempre devuelve `True`. Reemplazar por `not IsEmpty ( SQL.GetColumn ( <col> ; <whereField> ; <whereValue> ) )`. |

## Patrón estándar

```filemaker
Let (
    [
    ~sql = "
        SELECT COUNT(*)
        FROM ~table
        WHERE
            ~campo1 = ?
            AND ~campo2 = 1
    " ;
    ~sqlQuery = Substitute ( ~sql ;
        [ "~table" ; SQL.GetTableName ( MiTO::CampoCualquiera ) ] ;
        [ "~campo1" ; SQL.GetFieldName ( MiTO::CampoFiltro ) ] ;
        [ "~campo2" ; SQL.GetFieldName ( MiTO::OtroCampo ) ]
        )
    ] ;
    ExecuteSQL ( ~sqlQuery ; "" ; "" ; $VariableParametro )
)
```

### Estructura del patrón

1. **Definir `~sql`** con placeholders descriptivos (`~table`, `~campo1`, etc.)
2. **Sustituir** cada placeholder con `SQL.GetTableName()` o `SQL.GetFieldName()` usando una referencia de campo válida
3. **Ejecutar** `ExecuteSQL()` con la query resuelta
4. Los parámetros `?` se pasan como argumentos posicionales al final

### Convenciones de placeholders

- `~table`, `~table1`, `~table2` para tablas
- `~nombreDescriptivo` para campos (ej: `~fkProyecto`, `~rolNuevo`, `~estado`)
- Los placeholders deben ser únicos y no ser substring de otros (ej: no usar `~id` si también existe `~idProyecto`)

## Anti-patrones

```filemaker
// MAL: nombres hardcodeados
ExecuteSQL ( "SELECT COUNT(*) FROM Roles WHERE \"_kfln__Proyecto\" = ?" ; "" ; "" ; $Id )

// MAL: solo tabla dinámica pero campos hardcodeados
ExecuteSQL ( "SELECT COUNT(*) FROM " & SQL.GetTableName ( Roles::Id ) & " WHERE PermisoBloqueo = 2" ; "" ; "" )

// BIEN: todo dinámico
Let (
    [
    ~sql = "SELECT COUNT(*) FROM ~table WHERE ~permiso = 2" ;
    ~sqlQuery = Substitute ( ~sql ;
        [ "~table" ; SQL.GetTableName ( Roles::PermisoBloqueo ) ] ;
        [ "~permiso" ; SQL.GetFieldName ( Roles::PermisoBloqueo ) ]
        )
    ] ;
    ExecuteSQL ( ~sqlQuery ; "" ; "" )
)
```

## Referencia de campo

La referencia de campo pasada a `SQL.GetTableName()` y `SQL.GetFieldName()` puede ser de cualquier TO que apunte a la tabla base deseada. Las funciones resuelven al nombre de la tabla/campo base, independientemente del TO usado.

---

## ⚠ Bug upstream: `SQL.RecordExists` siempre devuelve `True`

La función `SQL.RecordExists` del pack [fm-sql-cfs](https://github.com/karbonfm/fm-sql-cfs) está mal implementada en el upstream. Su cuerpo es:

```filemaker
SQL.GetColumnStatement ( WhereField ; WhereField ; WhereValue ) <> ""
```

Es decir, devuelve `True` si el **string SQL construido** es no vacío — cosa que siempre ocurre, independientemente de si la query devuelve filas. **No ejecuta la query**.

### Patrón correcto

Para comprobar existencia de un registro por un único campo, usar `SQL.GetColumn` y chequear `IsEmpty`:

```filemaker
// BIEN — ejecuta la query real
Insert Calculated Result [ $ExisteEnClientes ;
    not IsEmpty ( SQL.GetColumn (
        CLI__Clientes::__kpln__Cliente ;  // columna a seleccionar
        CLI__Clientes::__kpln__Cliente ;  // campo WHERE
        $BrokerId                          // valor WHERE
    ) )
]

If [ not $ExisteEnClientes ]
    # crear registro nuevo
End If
```

Para comprobar existencia por **dos** condiciones AND, usar `SQL.GetColumn2Fields`:

```filemaker
Insert Calculated Result [ $ExisteCCL ;
    not IsEmpty ( SQL.GetColumn2Fields (
        CCL__ContactosClientes::__kpln__ContactoCliente ;
        CCL__ContactosClientes::_kfln__Contacto ; $ContactoId ;
        CCL__ContactosClientes::_kfln__Cliente  ; $FkCliente
    ) )
]
```

### Síntoma si usas `SQL.RecordExists` por error

Bloques de código tipo:

```
Insert Calculated Result [ $Existe ; SQL.RecordExists ( Tabla::Campo ; $Valor ) ]
If [ not $Existe ]
    # crear registro
End If
```

**nunca** crean nada porque `$Existe` es siempre `True`. Los bloques se ejecutan sin errores y sin efectos visibles. Detectado en la tarea 944.8 (Borneo) S4 — la Fase 2 del post-deploy no creaba ningún Cliente Broker pese a pasar validaciones y marcar idempotencia DONE.

### ¿Arreglar upstream?

El fix correcto es una sola línea:

```filemaker
not IsEmpty ( SQL.GetColumn ( WhereField ; WhereField ; WhereValue ) )
```

Pendiente abrir PR en [fm-sql-cfs](https://github.com/karbonfm/fm-sql-cfs). Mientras tanto, **prohibido usar `SQL.RecordExists` en código Taiko** — usar `not IsEmpty ( SQL.GetColumn(…) )` o `SQL.GetColumn2Fields(…)`.
