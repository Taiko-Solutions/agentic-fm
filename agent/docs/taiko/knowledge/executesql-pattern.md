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
Insert Calculated Result [ $Existe ;
    not IsEmpty ( SQL.GetColumn (
        SolutionApp__Tabla::PrimaryKey ;  // columna a seleccionar
        SolutionApp__Tabla::PrimaryKey ;  // campo WHERE
        $ValorBuscado                      // valor WHERE
    ) )
]

If [ not $Existe ]
    # crear registro nuevo
End If
```

Para comprobar existencia por **dos** condiciones AND, usar `SQL.GetColumn2Fields`:

```filemaker
Insert Calculated Result [ $Existe ;
    not IsEmpty ( SQL.GetColumn2Fields (
        SolutionApp__Bridge::PrimaryKey ;
        SolutionApp__Bridge::FK_Parent ; $ParentId ;
        SolutionApp__Bridge::FK_Child  ; $ChildId
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

**nunca** crean nada porque `$Existe` es siempre `True`. Los bloques se ejecutan sin errores y sin efectos visibles. Detectado en un post-deploy de migración — una fase de creación idempotente no creaba ningún registro pese a pasar todas las validaciones intermedias y marcar la idempotencia final como DONE.

### ¿Arreglar upstream?

El fix correcto es una sola línea:

```filemaker
not IsEmpty ( SQL.GetColumn ( WhereField ; WhereField ; WhereValue ) )
```

Pendiente abrir PR en [fm-sql-cfs](https://github.com/karbonfm/fm-sql-cfs). Mientras tanto, **prohibido usar `SQL.RecordExists` en código Taiko** — usar `not IsEmpty ( SQL.GetColumn(…) )` o `SQL.GetColumn2Fields(…)`.

---

## ⚠ Parseo de resultados multi-fila: FileMaker recorta caracteres de control finales

Cuando se ejecuta `ExecuteSQL` con separadores de fila/columna **personalizados** (típicamente `Char(30)` para filas y `Char(29)` para columnas, elegidos porque no aparecen en datos reales) y luego se parsea el resultado para construir un array JSON, hay **dos comportamientos de FileMaker** que rompen los enfoques ingenuos:

1. **`ExecuteSQL` NO añade separador de fila final.** Para N filas hay N−1 separadores de fila. El resultado termina con el último valor (o con el separador de columna que precede a una última columna vacía).

2. **FileMaker recorta los caracteres de control finales (`Char(29)`, `Char(30)`, etc.) al asignar una cadena a una variable `$`** (`Insert Calculated Result`/`Set Variable`). Esto es invisible y NO ocurre con variables locales de `Let()` planas (sin `$`), lo que hace el bug especialmente engañoso al depurar con `Evaluate`.

### Síntoma

Se pierde **la última fila** del resultado (o, con una sola fila, se devuelve un array vacío). Trucos como "añadir un `Char(30)` al final y contar separadores" fallan, porque el `Char(30)` añadido se recorta al guardarlo en la `$variable`:

```filemaker
// MAL — el Char(30) final se recorta al asignar a $Trabajo → cuenta una fila de menos
Insert Calculated Result [ $Trabajo ; $SqlResult & Char ( 30 ) ]
Insert Calculated Result [ $NumFilas ; PatternCount ( $Trabajo ; Char ( 30 ) ) ]   // = N-1, no N
```

Detectado en `task.list` (974, Bloque 3): `del_sprint` devolvía 2 de 3 tareas; la tercera tenía la última columna vacía, así que el resultado terminaba en `Char(29)` y el `Char(30)` añadido desaparecía.

### Patrón correcto

**Contar filas con `PatternCount + 1`** sobre el resultado crudo (los separadores *internos* entre filas no se recortan, sólo los finales), y **extraer la última fila por longitud**, no por separador:

```filemaker
Insert Calculated Result [ $NumFilas ; If ( IsEmpty ( $SqlResult ) ; 0 ; PatternCount ( $SqlResult ; Char ( 30 ) ) + 1 ) ]
// Extracción de la fila $Indice (sin depender de un separador final):
//   ~ini = If ( $Indice = 1 ; 1 ; Position ( $SqlResult ; Char(30) ; 1 ; $Indice - 1 ) + 1 )
//   ~fin = If ( $Indice = $NumFilas ; Length ( $SqlResult ) + 1 ; Position ( $SqlResult ; Char(30) ; 1 ; $Indice ) )
//   $Fila = Middle ( $SqlResult ; ~ini ; ~fin - ~ini )
```

**Columna centinela** para blindar el parseo por columnas: añadir una columna literal no vacía al **final** del `SELECT` (p.ej. `SELECT ..., 'eor' FROM ...`). Así ninguna fila termina en columnas vacías, el separador de la última columna real siempre está presente, y el resultado no termina nunca en un carácter de control que se pueda recortar. La columna centinela se ignora al construir el JSON.

> **Regla práctica:** nunca confíes en un separador final al parsear `ExecuteSQL`. Usa `PatternCount + 1`, extrae la última fila por `Length`, y/o añade una columna centinela `'eor'`.
