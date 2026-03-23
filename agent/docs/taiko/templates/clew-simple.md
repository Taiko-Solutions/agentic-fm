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
5.  # -------------------------------------------------------------------------------------
6.  # Parámetros Requeridos:
7.  #   - [ParamName] (tipo): descripción
8.  # Parámetros Opcionales:
9.  #   ninguno
10. # -------------------------------------------------------------------------------------
11. # Retorna:
12. #   Éxito: {"campo": valor, "success": true}
13. #   Error: errorTrace JSON
14. # -------------------------------------------------------------------------------------
15. # Historial:
16. #   Creado: YYYY-MM-DD Marco Antonio Pérez
17. # =====================================================================================
18. #
19. Allow User Abort [ Off ]
20. Set Error Capture [ On ]
21. #
22. # Este bucle es un bloque pseudo try-catch
23. Loop
24.     # -------------------------------------------------------------------------------------
25.     # PARSEAR Y VALIDAR PARÁMETROS
26.     #
27.     Exit Loop If [ error.CreateVarsFromKeys ( Get ( ScriptParameter ) ; "" ) ]
28.     Insert Calculated Result [ $REQUIRED ; List ( "ParamName1" ; "ParamName2" ) ]
29.     Exit Loop If [ error.ThrowIfMissingParam ( $REQUIRED ; "" ) ]
30.     #
31.     # -------------------------------------------------------------------------------------
32.     # VALIDAR CONTEXTO
33.     #
34.     Exit Loop If [ error.ThrowIfWrongContext ( GetFieldName ( [Table]::Id ) ) ]
35.     #
36.     # -------------------------------------------------------------------------------------
37.     # LÓGICA PRINCIPAL
38.     #
39.     Go to Layout [ "[Table]" ([Table]) ]
40.     Enter Find Mode [ Pause: Off ]
41.     Set Field [ [Table]::Campo ; $ParamName1 ]
42.     Perform Find []
43.     Exit Loop If [ error.ThrowIfLast ( "No se encontraron registros para: " & $ParamName1 ) ]
44.     #
45.     # Validaciones de negocio adicionales
46.     Exit Loop If [ error.ThrowIf ( Get ( FoundCount ) > 1 ; _error_MULTIPLE_RECORDS_FOUND ; "Se encontraron múltiples registros" ) ]
47.     #
48.     # -------------------------------------------------------------------------------------
49.     # CONSTRUIR RESULTADO
50.     #
51.     Insert Calculated Result [ $Result ; JSONSetElement ( "{}" ;
52.         [ "campo1" ; [Table]::Campo1 ; JSONString ] ;
53.         [ "campo2" ; [Table]::Campo2 ; JSONString ] ;
54.         [ "success" ; True ; JSONBoolean ]
55.     ) ]
56.     #
57.     Exit Loop If [ True ]
58. End Loop
59. #
60. # BLOQUE CATCH
61. If [ error.WasThrown ]
62.     Exit Script [ error.GetTrace ]
63. End If
64. #
65. Exit Script [ $Result ]
```

## Comment formatting rules

Each line shown as `# texto` becomes a **separate** `<Step id="89" name="# (comment)">` in the XML output. Never combine multiple lines into one comment step — this is unreadable in FileMaker's Script Workspace.

- Header separators use `====...====` (equals signs)
- Section separators use `----...----` (dashes, NOT box-drawing `────`)
- Lines showing just `#` become empty/self-closing comment steps: `<Step id="89" name="# (comment)"/>`

See `CODING_CONVENTIONS.md` for the complete XML formatting rules and step ID reference.

## Notes

- Line 27: `error.CreateVarsFromKeys` parses JSON into `$variables` and returns True on error.
- Line 29: `$REQUIRED` is a return-delimited list of variable names to validate.
- Line 34: Context validation is optional — omit for scripts marked as "insensitive".
- Line 43: `error.ThrowIfLast` checks `Get(LastError)` — use immediately after risky steps.
- Line 57: The final `Exit Loop If [True]` terminates the loop on success.
- Line 61-63: The catch block runs only if an error was thrown during the try block.
