# `List()` con un solo argumento devuelve `?` — custom function que tapa la nativa

## Regla

**En las soluciones Taiko, `List()` con UN SOLO argumento devuelve el literal `?` (error), no el valor.** Existe una **custom function `List` de aridad ≥2** que tapa el comportamiento de la función nativa. Para un conjunto de un solo valor:

- ✅ Usar el **literal de cadena directamente**: `$Var = "valor"`
- ✅ O `List` con un segundo valor vacío: `List ( "valor" ; "" )`
- ❌ **Nunca** `List ( "valor" )` con un único argumento → evalúa a `?`

`FilterValues`, `ValueCount`, `GetValue`, etc. funcionan igual contra un valor de una sola línea, así que el literal directo es la opción más limpia.

## Síntoma

El `?` es **silencioso a nivel de sintaxis** (fmlint no lo detecta; FileMaker no lanza error) y **se propaga**: cualquier función que envuelva un `List()` de un argumento hereda el `?`. El bug aparece en runtime como una comparación que "nunca encaja".

Detectado en `task.list` (974, Bloque 6, 2026-05-31): la lista de vistas stub se definía como

```filemaker
Insert Calculated Result [ $VistasStub ; List ( "bloqueadas" ) ]   // ← evalúa a "?"
```

Como `$VistasStub` valía `"?"` en lugar de `"bloqueadas"`, esta validación posterior fallaba:

```filemaker
// Primer guard: ¿vista desconocida? (ni implementada ni stub)
error.ThrowIf (
    IsEmpty ( FilterValues ( $vista ; $VistasImplementadas ) ) and IsEmpty ( FilterValues ( $vista ; $VistasStub ) ) ;
    _error_INVALID_PARAM ;
    "Vista no reconocida: " & $vista
)
```

Para `$vista = "bloqueadas"`: `FilterValues ( "bloqueadas" ; "?" )` = vacío → el guard saltaba con **`validation/INVALID_PARAM`** ("Vista no reconocida") en lugar del segundo guard, que debía devolver **`business_rule/FAILED_CONDITION`** ("vista no implementada todavía").

Lo engañoso: las demás vistas funcionaban porque viajan por la cadena `If [ $vista = "X" ]` (independiente de los enums) y porque `$VistasImplementadas` tenía 6 argumentos (≥2 → `List` OK). Solo la lista de **un** elemento estaba rota.

## Fix aplicado

```filemaker
Insert Calculated Result [ $VistasStub ; "bloqueadas" ]   // literal directo
```

## Comportamiento verificado (motor FM en vivo, vía AGFMEvaluation)

| Expresión | Resultado |
|---|---|
| `List ( "a" )` | `?` |
| `List ( $x )` | `?` |
| `List ( "a" ; "b" )` | `a⏎b` |
| `List ( "a" ; "b" ; "c" )` | `a⏎b⏎c` |
| `List ( "valor" ; "" )` | `valor` |
| `ValueCount ( List ( "uno" ) )` | `?` (se propaga) |
| `ValueCount ( List ( "uno" ; "" ) )` | `1` |
| `"bloqueadas"` (literal) | `bloqueadas` |

El `?` con 1 argumento y el resultado correcto con 2+ es la firma exacta de una **custom function de aridad fija ≥2** que tapa el nombre `List`. (FileMaker moderno bloquea nombrar una CF igual que una nativa; lo más probable es que esta `List` venga de un import/herencia antigua y conviva con la nativa.)

## Por qué importa más allá de este caso

Cualquier patrón que construya una lista de **un solo valor conocido** con `List(...)` está roto en estas soluciones. Casos típicos:

- Listas de validación de enums con un único valor permitido.
- `FilterValues ( x ; List ( unicoValor ) )` para comprobar pertenencia.
- Construcción incremental donde el primer paso arranca con un solo elemento.

**Regla práctica:** si el número de argumentos de `List()` puede ser 1 en algún camino de ejecución, usa el literal directo o añade `; ""`.

## Técnica de depuración usada — evaluar calcs en el motor FM en vivo

Para diagnosticar esto sin tocar la UI de FileMaker, se evaluó la expresión directamente contra el motor con `AGFMEvaluation`, invocada **a través** de `AGFMScriptBridge` (doble envoltorio):

```python
import json, base64, urllib.request, urllib.parse
CFG = json.load(open("agent/config/automation.json"))["solutions"]["TaikoDevAI"]["odata"]
URL  = f'{CFG["base_url"]}/{urllib.parse.quote(CFG["database"])}/Script.AGFMScriptBridge'
AUTH = base64.b64encode(f'{CFG["username"]}:{CFG["password"]}'.encode()).decode()

def ev(calc):
    inner = json.dumps({"script": "AGFMEvaluation", "parameter": json.dumps({"expression": calc})})
    body  = json.dumps({"scriptParameterValue": inner}).encode()
    req   = urllib.request.Request(URL, data=body, method="POST",
              headers={"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.load(r)
    outer = json.loads(resp["scriptResult"]["resultParameter"])   # {result, script, success}
    env   = json.loads(outer["result"]) if "result" in outer else outer
    return env.get("result")   # {expression, result, error_code, layout, success}

print(ev('List ( "a" )'))   # -> '?'
```

`AGFMEvaluation` evalúa sobre el layout `Inicio` y devuelve `{expression, result, error_code, layout, success}`. Útil para probar cualquier calc FileMaker desde Python en segundos.

> **Nota sobre el doble envoltorio de `AGFMScriptBridge`:** la respuesta NO es el envelope Clew directo. `scriptResult.resultParameter` parsea a `{"result": "<envelope-como-string>", "script": ..., "success": ...}`; el envelope real (`{ok,data}` | `{ok:false,category,...}`) está anidado en `.result` como string y requiere un **segundo** `json.loads`. Cualquier runner de pruebas que consuma esta vía debe hacer el doble parseo (ver `agent/sandbox/_run_task_list_tests.py`).
