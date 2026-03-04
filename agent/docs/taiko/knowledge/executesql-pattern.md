# ExecuteSQL — Patrón resiliente con SQL.Get*

## Regla

**OBLIGATORIO**: Toda consulta ExecuteSQL en soluciones Taiko debe usar `SQL.GetFieldName()` y `SQL.GetTableName()` para resolver nombres de campos y tablas dinámicamente. **NUNCA** hardcodear nombres de tabla o campo como strings literales en la query SQL.

## Motivación

- Si un campo o tabla se renombra en FileMaker, la query no se rompe — las funciones resuelven el nombre actual.
- Evita problemas con caracteres especiales o nombres reservados en SQL.
- Es autodocumentado: la referencia al campo FileMaker es explícita.

## Custom functions disponibles

| Función | Propósito |
|---------|-----------|
| `SQL.GetTableName ( campo )` | Devuelve el nombre SQL de la tabla base del campo |
| `SQL.GetFieldName ( campo )` | Devuelve el nombre SQL del campo |
| `SQL.GetColumn ( campo ; separadorFila ; separadorColumna ; query... )` | ExecuteSQL con resolución automática |
| `SQL.GetColumn2Fields ( campo1 ; campo2 ; ... )` | Dos columnas con resolución |
| `SQL.GetRecordsAsJSON ( ... )` | Resultado como JSON |

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
