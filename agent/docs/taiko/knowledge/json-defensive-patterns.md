# Manejo Defensivo de JSON en FileMaker

FileMaker tiene comportamientos específicos al trabajar con JSON que pueden causar errores silenciosos si no se manejan correctamente. Este documento recoge patrones defensivos aprendidos al integrar datos de fuentes externas (APIs, IA, etc.).

## JSONGetElement devuelve "null" literal

Cuando un valor JSON es `null`, `JSONGetElement` devuelve la cadena literal `"null"` (no vacío, no 0).

```
// JSON: { "NumeroAlbaran": null }
JSONGetElement ( $json ; "NumeroAlbaran" )  // → "null" (texto)
```

**Patrón defensivo:** Filtrar el literal `"null"` antes de usar el valor:

```
~AlbaranRaw = JSONGetElement ( ~json ; "NumeroAlbaran" ) ;
~Albaran = If ( ~AlbaranRaw ≠ "null" ; ~AlbaranRaw ; "" )
```

## JSONSetElement con JSONNumber rompe toda la llamada

Si CUALQUIER valor en una llamada multi-par `JSONSetElement` no es numérico y se usa `JSONNumber` como tipo, **toda la función devuelve `"?"`** y se pierden TODOS los campos — no solo el que falló.

```
// PELIGROSO: si $EsAbono = "false", toda la llamada devuelve "?"
JSONSetElement ( "{}" ;
  ["ImporteNeto" ; $ImporteNeto ; JSONNumber] ;
  ["EsAbono" ; $EsAbono ; JSONNumber]    // ← "false" no es numérico → TODO falla
)
```

**Patrón defensivo:** Usar `GetAsNumber()` para valores numéricos y `JSONString` para el resto:

```
~ImporteNetoRaw = JSONGetElement ( ~json ; "ImporteNeto" ) ;
~ImporteNeto = GetAsNumber ( ~ImporteNetoRaw ) ;

// EsAbono es booleano JSON → convertir a texto FileMaker
~EsAbonoRaw = JSONGetElement ( ~json ; "EsAbono" ) ;
~EsAbono = Case (
    ~EsAbonoRaw = "true" or ~EsAbonoRaw = 1 ; "Si" ;
    ~EsAbonoRaw = "false" or ~EsAbonoRaw = 0 ; "No" ;
    not IsEmpty ( ~EsAbonoRaw ) and ~EsAbonoRaw ≠ "null" ; ~EsAbonoRaw ;
    ""
)
```

## Booleanos JSON en FileMaker

JSON usa `true`/`false` (sin comillas). FileMaker los recibe como texto `"true"` / `"false"` vía `JSONGetElement`. Estos textos:

- **No son numéricos** → `JSONSetElement` con `JSONNumber` falla
- **No son booleanos FileMaker** → `"false"` evalúa como True en FileMaker (es un texto no vacío)

**Regla:** Siempre convertir booleanos JSON a valores FileMaker explícitos ("Si"/"No", 1/0, o True/False) inmediatamente después de extraerlos.

## Campos numéricos opcionales

Cuando un campo numérico puede venir vacío o null desde JSON, `GetAsNumber("")` devuelve 0, lo cual puede no ser el comportamiento deseado.

**Patrón defensivo:**

```
~ValorRaw = JSONGetElement ( ~json ; "Descuento" ) ;
~Descuento = Case (
    IsEmpty ( ~ValorRaw ) or ~ValorRaw = "null" ; "" ;
    GetAsNumber ( ~ValorRaw )
)
```

## Resumen de reglas

| Situación | Riesgo | Defensa |
|-----------|--------|---------|
| Valor JSON `null` | Se obtiene texto `"null"` | Filtrar con `≠ "null"` |
| JSONSetElement + JSONNumber con texto | Toda la llamada devuelve `"?"` | `GetAsNumber()` o usar `JSONString` |
| Booleano JSON `true`/`false` | `"false"` evalúa como True | Convertir a "Si"/"No" o 1/0 |
| Campo numérico vacío/null | `GetAsNumber("")` = 0 | Verificar vacío antes de convertir |
| Múltiples pares en JSONSetElement | Un fallo rompe todos | Validar cada valor antes o separar en llamadas individuales |
