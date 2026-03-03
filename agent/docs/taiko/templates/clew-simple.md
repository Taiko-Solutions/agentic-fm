# Template: Clew Simple (Traditional)

Human-readable script template for read-only operations, queries, navigation, and Interface scripts that do not edit data. Use this as a structural reference — adapt field names, parameters, and logic to the specific task.

Replace `[Entity]` and `[Table]` with the actual entity and table names from CONTEXT.json.

---

## Controller Script: `Buscar[Entity].Controller`

```
Script: Buscar[Entity].Controller

1.  # =====================================================================================
2.  # Propósito: [Descripción del propósito]
3.  # Contexto: [Table]
4.  # Capa: Controlador
5.  # Parámetros Requeridos:
6.  #   - [ParamName] (tipo): descripción
7.  # Parámetros Opcionales:
8.  #   ninguno
9.  # Retorna:
10. #   Éxito: {"campo": valor, "success": true}
11. #   Error: errorTrace JSON
12. # Historial:
13. #   Creado: YYYY-MM-DD Marco Antonio Pérez
14. # =====================================================================================
15. Allow User Abort [ Off ]
16. Set Error Capture [ On ]
17.
18. # ──────────────────────────────────────────
19. # INICIO DEL BLOQUE TRY
20. # ──────────────────────────────────────────
21.
22. Loop
23.     # ──────────────────────────────────────────
24.     # PARSEAR Y VALIDAR PARÁMETROS
25.     # ──────────────────────────────────────────
26.     Exit Loop If [ error.CreateVarsFromKeys ( Get ( ScriptParameter ) ; "" ) ]
27.     Insert Calculated Result [ $REQUIRED ; List ( "ParamName1" ; "ParamName2" ) ]
28.     Exit Loop If [ error.ThrowIfMissingParam ( $REQUIRED ; "" ) ]
29.
30.     # ──────────────────────────────────────────
31.     # VALIDAR CONTEXTO
32.     # ──────────────────────────────────────────
33.     Exit Loop If [ error.ThrowIfWrongContext ( GetFieldName ( [Table]::Id ) ) ]
34.
35.     # ──────────────────────────────────────────
36.     # LÓGICA PRINCIPAL
37.     # ──────────────────────────────────────────
38.     Go to Layout [ "[Table]" ([Table]) ]
39.     Enter Find Mode [ Pause: Off ]
40.     Set Field [ [Table]::Campo ; $ParamName1 ]
41.     Perform Find []
42.     Exit Loop If [ error.ThrowIfLast ( "No se encontraron registros para: " & $ParamName1 ) ]
43.
44.     # Validaciones de negocio adicionales
45.     Exit Loop If [ error.ThrowIf ( Get ( FoundCount ) > 1 ; _error_MULTIPLE_RECORDS_FOUND ; "Se encontraron múltiples registros" ) ]
46.
47.     # ──────────────────────────────────────────
48.     # LLAMAR SUBSCRIPTS (si es necesario)
49.     # ──────────────────────────────────────────
50.     # Perform Script [ "OtroScript.Controller" ; Parameter: $Params ]
51.     # Exit Loop If [ error.InSubscriptThrow ]
52.
53.     # ──────────────────────────────────────────
54.     # CONSTRUIR RESULTADO
55.     # ──────────────────────────────────────────
56.     Insert Calculated Result [ $Result ; JSONSetElement ( "{}" ;
57.         [ "campo1" ; [Table]::Campo1 ; JSONString ] ;
58.         [ "campo2" ; [Table]::Campo2 ; JSONString ] ;
59.         [ "success" ; True ; JSONBoolean ]
60.     ) ]
61.
62.     Exit Loop If [ True ]
63. End Loop
64.
65. # ──────────────────────────────────────────
66. # BLOQUE CATCH
67. # ──────────────────────────────────────────
68.
69. If [ error.WasThrown ]
70.     Exit Script [ error.GetTrace ]
71. End If
72.
73. Exit Script [ $Result ]
```

## Notes

- Line 26: `error.CreateVarsFromKeys` parses JSON into `$variables` and returns True on error.
- Line 28: `$REQUIRED` is a return-delimited list of variable names to validate.
- Line 33: Context validation is optional — omit for scripts marked as "insensitive".
- Line 42: `error.ThrowIfLast` checks `Get(LastError)` — use immediately after risky steps.
- Line 62: The final `Exit Loop If [True]` terminates the loop on success.
- Line 69-71: The catch block runs only if an error was thrown during the try block.
