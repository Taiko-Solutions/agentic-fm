# Template: Clew Completo

Human-readable script template showing the **complete** Clew pattern with all subscript handling scenarios. This is the reference for scripts that call subscripts and need to handle or suppress errors from those subscripts.

---

## When to use each subscript error handler

| Function | Behaviour | Use case |
|----------|-----------|----------|
| `error.InSubscriptThrow` | Checks + re-throws → exits loop | Default: propagate subscript errors upward |
| `error.InSubscript` | Checks only (True/False) → no throw | Handle error locally, decide what to do |
| `error.DeleteTrace` | Clears active error state | After handling an error that should NOT propagate |

---

## Controller Script: `[Entity].Controller`

```
Script: [Entity].Controller

1.  # =====================================================================================
2.  # Propósito: [Descripción del propósito]
3.  # Contexto: [Table] o insensitive
4.  # Capa: Controlador
5.  # -------------------------------------------------------------------------------------
6.  # Parámetros Requeridos:
7.  #   - paramName (tipo): descripción
8.  # -------------------------------------------------------------------------------------
9.  # Retorna:
10. #   Éxito: {"success": true}
11. #   Error: errorTrace JSON
12. # -------------------------------------------------------------------------------------
13. # Historial:
14. #   Creado: YYYY-MM-DD Marco Antonio Pérez
15. # =====================================================================================
16. #
17. Allow User Abort [ Off ]
18. Set Error Capture [ On ]
19. #
20. # Este bucle es un bloque pseudo try-catch
21. Loop
22.     # -------------------------------------------------------------------------------------
23.     # PARSEAR Y VALIDAR PARÁMETROS
24.     #
25.     Exit Loop If [ error.CreateVarsFromKeys ( Get ( ScriptParameter ) ; "" ) ]
26.     Insert Calculated Result [ $REQUIRED ; List ( "paramName" ) ]
27.     Exit Loop If [ error.ThrowIfMissingParam ( $REQUIRED ; "" ) ]
28.     #
29.     # -------------------------------------------------------------------------------------
30.     # LÓGICA PRINCIPAL
31.     #
32.     # ... operaciones del script ...
33.     #
34.     # -------------------------------------------------------------------------------------
35.     # SUBSCRIPT CON PROPAGACIÓN AUTOMÁTICA (caso más común)
36.     #
37.     # Si el subscript falla, el error se propaga automáticamente
38.     # y la ejecución salta al bloque catch
39.     Perform Script [ "OtroScript.Controller" ; Parameter: $Params ]
40.     Exit Loop If [ error.InSubscriptThrow ]
41.     #
42.     # -------------------------------------------------------------------------------------
43.     # SUBSCRIPT CON MANEJO LOCAL (error no crítico)
44.     #
45.     # Si el subscript falla, manejamos el error sin propagarlo.
46.     # Útil cuando el fallo del subscript no debe abortar el flujo principal.
47.     Perform Script [ "ScriptOpcional.Controller" ; Parameter: $Params ]
48.     #
49.     If [ error.InSubscript ]
50.         # Registrar el error o tomar acción alternativa
51.         Set Field [ Table::ErrorLog ; error.GetHint ]
52.         # Limpiar error — no debe propagarse al llamador
53.         Set Variable [ $_Void ; Value: error.DeleteTrace ]
54.     Else
55.         # Subscript ejecutó correctamente
56.         Set Field [ Table::Estado ; "completado" ]
57.     End If
58.     #
59.     # -------------------------------------------------------------------------------------
60.     # CONSTRUIR RESULTADO
61.     #
62.     Insert Calculated Result [ $Result ; JSONSetElement ( "{}" ; "success" ; True ; JSONBoolean ) ]
63.     #
64.     Exit Loop If [ True ]
65. End Loop
66. #
67. # BLOQUE CATCH
68. If [ error.WasThrown ]
69.     Exit Script [ error.GetTrace ]
70. End If
71. #
72. Exit Script [ $Result ]
```

## Key patterns explained

### Propagación automática (líneas 39-40)

El caso más común. `error.InSubscriptThrow` hace dos cosas:
1. Verifica si el subscript devolvió un errorTrace
2. Si hay error, lo re-lanza al estado de error actual

Esto hace que `Exit Loop If` salte al bloque catch automáticamente.

### Manejo local (líneas 47-57)

Para subscripts cuyo fallo no es crítico:
1. `error.InSubscript` solo VERIFICA — devuelve True/False sin lanzar
2. Dentro del `If`, manejas el error como necesites (log, acción alternativa, etc.)
3. `error.DeleteTrace` LIMPIA el error para que no se propague

**IMPORTANTE:** `error.DeleteTrace` debe llamarse con `Set Variable` (id="141"), no con `Insert Calculated Result`:

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

## XML formatting reminders

- Cada línea `# texto` es un `<Step id="89">` separado (ver `CODING_CONVENTIONS.md`)
- Separadores de sección: guiones `----...----` (no box-drawing `────`)
- Líneas `#` solas → `<Step id="89" name="# (comment)"/>` (self-closing)
- Usar IDs de paso reales (ver tabla en `CODING_CONVENTIONS.md`)
