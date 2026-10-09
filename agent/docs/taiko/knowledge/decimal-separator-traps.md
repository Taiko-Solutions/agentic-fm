# Trampas del separador decimal (archivos con coma decimal)

Las soluciones Taiko usan **coma** como separador decimal. ExecuteSQL y JSON usan siempre **punto**. Al pasar un número de un lado a otro hay tres trampas que no dan ningún error y cambian el valor en silencio.

Origen: proyecto cliente (2026-10). Un MCP devolvía importes ×10 y ×100 (677,60 € → `6776`; 1.470,15 € → `147015`) y un precio de 1.234,56 se guardaba como 1.234.

## 1. `GetAsNumber` sobre texto de ExecuteSQL

`ExecuteSQL` devuelve los números como **texto con punto** (`"677.6"`). En un archivo con coma decimal, `GetAsNumber` trata el punto como un carácter más y lo ignora:

| Valor real | Texto de ExecuteSQL | `GetAsNumber ( texto )` |
|---|---|---|
| 1.470,15 | `1470.15` | 147015 (×100) |
| 677,60 | `677.6` | 6776 (×10) |
| 1.210,00 | `1210` | 1210 (correcto) |

El «multiplicador» cambia según los decimales, así que **no se puede corregir por magnitud** y parece un problema de datos. No lo es.

**Solución:** convertir con el separador del archivo. Si no existe, crear la función personalizada `num.DesdeTextoPunto ( texto )`:

```
If ( IsEmpty ( texto ) ; "" ;
  GetAsNumber ( Substitute ( texto ; "." ; JSONGetElement ( Get ( FileLocaleElements ) ; "Num.Decimal" ) ) )
)
```

Úsala en cada número que venga de ExecuteSQL y en cada texto con punto que llegue de fuera (API, OData, ficheros). Los enteros (recuentos) no lo necesitan, pero tampoco les hace daño.

## 2. `JSONRaw` con un número de FileMaker

`JSONGetElement` sobre un número JSON devuelve un **número de FileMaker**, no texto: `JSONGetElement ( "{\"a\":1234.56}" ; "a" )` → `1234,56`. Si luego ese valor se mete en otro JSON con `JSONRaw`, se serializa con coma (`{"PVP":1234,56}`): el JSON queda roto y el número se trunca a `1234`.

```
# MAL: trunca 1234,56 a 1234
[ "PVP" ; JSONGetElement ( $Linea ; "precio" ) ; JSONRaw ]

# BIEN: JSONNumber serializa con punto. Si el valor puede venir vacío, cambia de tipo (ver trampa 3)
[ "PVP" ; JSONGetElement ( $Linea ; "precio" ) ; If ( IsEmpty ( JSONGetElement ( $Linea ; "precio" ) ) ; JSONString ; JSONNumber ) ]
```

Aplica a todo parámetro que un orquestador pase a un worker con números (precios, cantidades, descuentos).

## 3. `JSONNumber` con valor vacío serializa `0`

`JSONSetElement ( "" ; "PVD" ; "" ; JSONNumber )` produce `{"PVD":0}`, no un campo vacío. Al leerlo, el destino no distingue «vacío» de «cero». Los `AsJSON`/`AsJson` de las utilities que serializan campos numéricos con `JSONNumber` mandan `0` en los campos vacíos.

**Solución:** cuando importe la diferencia, usar `If ( IsEmpty ( valor ) ; JSONString ; JSONNumber )` como tipo, o tratar `0` como «no informado» en el receptor.

## Cómo comprobarlo

Evalúa en el motor (AGFMEvaluation o Visor de datos) antes de pegar:

```
GetAsNumber ( "677.6" )                                        → 6776     (trampa 1)
num.DesdeTextoPunto ( "677.6" )                                → 677,6
JSONGetElement ( JSONSetElement ( "{}" ; "x" ; 1234,56 ; JSONRaw ) ; "x" )  → 1234  (trampa 2)
JSONSetElement ( "" ; "a" ; "" ; JSONNumber )                  → {"a":0}  (trampa 3)
```

Recuerda también la regla de pegado: **sin literales decimales con punto en los cálculos** (`21 / 100`, no `0.21`). En un archivo con coma, FileMaker los comenta al pegar.

Relacionado: `json-defensive-patterns.md` (JSONNumber con texto rompe toda la llamada) y `executesql-pattern.md`.
