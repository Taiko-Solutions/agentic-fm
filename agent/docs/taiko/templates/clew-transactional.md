# Template: Utility + Transactional Pattern

Human-readable script templates for data creation and editing. This pattern involves three scripts working together. Adapt entity names, fields, and parameters from CONTEXT.json.

Replace `[Entity]`, `[Table]`, and field names with actual values.

---

## Script 1: Utility Manager (Interface)

**Name:** `[Entity] Utility | Alta, Editar`

```
Script: [Entity] Utility | Alta, Editar

1.  # =====================================================================================
2.  # Propósito: Orquestar acciones de la tarjeta modal de [Entity]
3.  # Contexto: insensitive
4.  # Capa: Interfaz
5.  # Parámetros Requeridos:
6.  #   - Accion (text): "Nuevo" | "Editar" | "Guardar" | "Cancelar"
7.  # Parámetros Opcionales:
8.  #   - Id (text): Requerido si Accion = "Editar"
9.  # Retorna:
10. #   Éxito: null (cierra ventana)
11. #   Error: Muestra dialog, tarjeta permanece abierta
12. # Historial:
13. #   Creado: YYYY-MM-DD Marco Antonio Pérez
14. # =====================================================================================
15. Allow User Abort [ Off ]
16. Set Error Capture [ On ]
17.
18. Loop
19.     Exit Loop If [ error.CreateVarsFromKeys ( Get ( ScriptParameter ) ; "" ) ]
20.     Insert Calculated Result [ $REQUIRED ; List ( "Accion" ; If ( $Accion = "Editar" ; "Id" ; "" ) ) ]
21.     Exit Loop If [ error.ThrowIfMissingParam ( $REQUIRED ; "" ) ]
22.
23.     # -------------------------------------------------------------------------------------
24.     # EJECUTAR ACCIÓN
25.     # -------------------------------------------------------------------------------------
26.
27.     If [ $Accion = "Editar" ]
28.         Perform Script [ "[Entity] Utility | Initialize Shadow" ; Parameter: Get ( ScriptParameter ) ]
29.         New Window [ Style: Card ; Name: "Editor[Entity]" ; Using layout: "Utility__[Table]" ]
30.
31.     Else If [ $Accion = "Nuevo" ]
32.         Perform Script [ "[Entity] Utility | Initialize Shadow" ]
33.         New Window [ Style: Card ; Name: "Editor[Entity]" ; Using layout: "Utility__[Table]" ]
34.
35.     Else If [ $Accion = "Guardar" ]
36.         Commit Records/Requests [ No dialog ]
37.         Perform Script [ "[Entity] | Alta Modificar [Entity] {json}" ; Parameter: Utility__[Table]::AsJSON ]
38.         Insert Calculated Result [ $Resultado ; Get ( ScriptResult ) ]
39.
40.         If [ error.InSubscript ]
41.             # Loguear error y mostrar al usuario
42.             Perform Script [ "Create Log Clew" ; Parameter: $Resultado ]
43.             Show Custom Dialog [ "Error" ; error.GetHint ]
44.             # Tarjeta permanece abierta para corrección
45.         Else
46.             # Éxito: cerrar tarjeta
47.             Perform Script [ "[Entity] Utility | Alta, Editar" ; Parameter: JSONSetElement ( "{}" ; "Accion" ; "Cancelar" ; JSONString ) ]
48.         End If
49.
50.     Else If [ $Accion = "Cancelar" ]
51.         Close Window [ Name: "Editor[Entity]" ]
52.         Perform Script [ "[Entity] Utility | Initialize Shadow" ]
53.     End If
54.
55.     Exit Loop If [ True ]
56. End Loop
57.
58. If [ error.WasThrown ]
59.     Show Custom Dialog [ "Error" ; error.GetHint ]
60. End If
```

---

## Script 2: Initialize Shadow (Interface)

**Name:** `[Entity] Utility | Initialize Shadow`

```
Script: [Entity] Utility | Initialize Shadow

1.  # =====================================================================================
2.  # Propósito: Rellenar campos globales de Utility desde AsJSON
3.  # Contexto: insensitive
4.  # Capa: Interfaz
5.  # Parámetros Requeridos: ninguno (sin parámetro = limpiar campos)
6.  # Parámetros Opcionales:
7.  #   - AsJSON completo de la tabla principal
8.  # Retorna: nada
9.  # Historial:
10. #   Creado: YYYY-MM-DD Marco Antonio Pérez
11. # =====================================================================================
12.
13. # Parsear JSON en variables (si hay parámetro)
14. Insert Calculated Result [ $Ignore ; error.CreateVarsFromKeys ( Get ( ScriptParameter ) ; "" ) ]
15.
16. # Limpiar campo de control
17. Set Field [ Utility__[Table]::zz__Prompt ; "" ]
18.
19. # Rellenar campos globales desde variables
20. Set Field [ Utility__[Table]::Id ; $Id ]
21. Set Field [ Utility__[Table]::Campo1 ; $Campo1 ]
22. Set Field [ Utility__[Table]::Campo2 ; $Campo2 ]
23. # ... resto de campos ...
24.
25. # Valores por defecto si están vacíos
26. Set Field [ Utility__[Table]::FechaEntrada ; If ( IsEmpty ( $FechaEntrada ) ; Get ( CurrentDate ) ; $FechaEntrada ) ]
27. Set Field [ Utility__[Table]::Estado ; If ( IsEmpty ( $Estado ) ; "Activo" ; $Estado ) ]
```

---

## Script 3: Transactional Controller

**Name:** `[Entity] | Alta Modificar [Entity] {json}`

```
Script: [Entity] | Alta Modificar [Entity] {json}

1.  # =====================================================================================
2.  # Propósito: Aplicar cambios con validación transaccional y rollback automático
3.  # Contexto: [Table]
4.  # Capa: Controlador
5.  # Parámetros Requeridos:
6.  #   - AsJSON completo desde Utility o JSON custom
7.  # Retorna:
8.  #   Éxito: {"result": {...datos...}, "environment": {...}}
9.  #   Error: errorTrace JSON
10. # Historial:
11. #   Creado: YYYY-MM-DD Marco Antonio Pérez
12. # =====================================================================================
13. Allow User Abort [ Off ]
14. Set Error Capture [ On ]
15.
16. # -------------------------------------------------------------------------------------
17. # VERIFICAR ESTADO DE TRANSACCIÓN
18. # -------------------------------------------------------------------------------------
19.
20. Insert Calculated Result [ $TransactionOpenState ; Get ( TransactionOpenState ) ]
21.
22. If [ not $TransactionOpenState ]
23.     Insert Calculated Result [ $WindowName ; Random ]
24.     If [ Get ( WindowStyle ) = 3 ]
25.         New Window [ Style: Document ; Name: $WindowName ]
26.     Else
27.         New Window [ Style: Card ; Name: $WindowName ]
28.     End If
29. End If
30.
31. # -------------------------------------------------------------------------------------
32. # ABRIR TRANSACCIÓN
33. # -------------------------------------------------------------------------------------
34.
35. Open Transaction
36.
37. # -------------------------------------------------------------------------------------
38. # PARSEAR Y VALIDAR PARÁMETROS
39. # -------------------------------------------------------------------------------------
40.
41. Insert Calculated Result [ $Param ; Get ( ScriptParameter ) ]
42. Revert Transaction [ Condition: error.CreateVarsFromKeys ( $Param ; "" ) ]
43. Insert Calculated Result [ $REQUIRED ; List ( "Campo1" ; "Campo2" ) ]
44. Revert Transaction [ Condition: error.ThrowIfMissingParam ( $REQUIRED ; "" ) ]
45.
46. # -------------------------------------------------------------------------------------
47. # VALIDACIONES DE NEGOCIO
48. # -------------------------------------------------------------------------------------
49.
50. Revert Transaction [ Condition: error.ThrowIf ( $Total < 0 ; _error_INVALID_PARAM ; "Total debe ser positivo" ) ]
51.
52. # -------------------------------------------------------------------------------------
53. # LÓGICA PRINCIPAL
54. # -------------------------------------------------------------------------------------
55.
56. Go to Layout [ "[Table]" ([Table]) ]
57.
58. If [ not IsEmpty ( $Id ) ]
59.     # Modo edición: buscar registro existente
60.     Enter Find Mode [ Pause: Off ]
61.     Set Field [ [Table]::Id ; $Id ]
62.     Perform Find []
63.     Revert Transaction [ Condition: error.ThrowIfLast ( "[Entity] no encontrado con ID: " & $Id ) ]
64. Else
65.     # Modo alta: crear nuevo registro
66.     New Record/Request
67.     Set Field [ [Table]::Id ; Get ( UUID ) ]
68. End If
69.
70. # Aplicar cambios
71. Set Field [ [Table]::Campo1 ; $Campo1 ]
72. Set Field [ [Table]::Campo2 ; $Campo2 ]
73.
74. # Subscripts transaccionales (si es necesario)
75. # Perform Script [ "Subscript.Controller" ; Parameter: $SubParams ]
76. # Revert Transaction [ Condition: error.InSubscript ]
77.
78. # -------------------------------------------------------------------------------------
79. # CONSTRUIR RESULTADO
80. # -------------------------------------------------------------------------------------
81.
82. Insert Calculated Result [ $Respuesta ; JSONSetElement ( "{}" ;
83.     [ "Id" ; [Table]::Id ; JSONString ] ;
84.     [ "Campo1" ; [Table]::Campo1 ; JSONString ]
85. ) ]
86.
87. # -------------------------------------------------------------------------------------
88. # CERRAR TRANSACCIÓN
89. # -------------------------------------------------------------------------------------
90.
91. Commit Transaction
92. Insert Calculated Result [ $Nothing ; error.ThrowIfLast ( "Error al cerrar transacción" ) ]
93.
94. Close Window [ Name: $WindowName ]
95. Go to Layout [ original layout ]
96.
97. Exit Script [ JSONSetElement ( error.GetTrace ;
98.     [ "environment" ; getScriptEnvironment.old ; JSONRaw ] ;
99.     [ "result" ; $Respuesta ; JSONRaw ]
100.) ]
```

---

## Notes

- **Line 42 (Transactional):** `Revert Transaction [Condition: ...]` replaces `Exit Loop If` — this is the critical difference from Clew traditional.
- **Line 20-29 (Transactional):** The temporary window isolates the transaction context. Skip if `Get(TransactionOpenState)` is already True.
- **Line 40-44 (Manager):** On error, the card stays open. On success, it calls itself with "Cancelar" to close.
- **Line 14 (Shadow):** `error.CreateVarsFromKeys` result is intentionally ignored — if there's no parameter, variables are simply empty (which clears the globals).
