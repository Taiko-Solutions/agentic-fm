# Template: Clew Transactional Dual — Worker

Plantilla canónica del patrón Clew transaccional **dual padre/hijo**: el mismo script funciona como *root* (abre su propia transacción) o como *hijo* (hereda la del padre), propagando el error a través del `Revert` anidado vía la variable global `$$ClewError`. Soporta N niveles de anidamiento y rollback total. Validada con 6 casos en `Clew | Runner Pruebas`.

**Name:** `Clew | Template Dual {json}`

> Patrón completo, reglas de oro y validación empírica en [`../knowledge/clew-transactional-dual.md`](../knowledge/clew-transactional-dual.md).

## Script (human-readable)

```
1	# # =====================================================================================
# Propósito: Plantilla canónica Clew transaccional dual padre/hijo con propagación
#            robusta de errores vía variable global $$ClewError.
#            El root limpia la global al terminar. Los intermedios solo leen y propagan.
#            Soporta N niveles de anidamiento y rollback total transparente.
# Contexto: insensible (crea Proc_Globales en ventana tmp si es root)
# Capa: Template (BPController2025)
# -------------------------------------------------------------------------------------
# Parámetros Requeridos:
#   - Marca (string): etiqueta identificadora (p.ej. "C1", "Test.1.2")
# Parámetros Opcionales:
#   - SimularError (boolean, default false)
#   - Momento (string, default "despues"): "antes" | "despues" del Set Field transaccional
# -------------------------------------------------------------------------------------
# Retorna:
#   Éxito: { result: {Marca, IsRoot, TransactionOpenStateEntrada}, environment: {...} }
#   Error: errorTrace JSON Clew (vía $$ClewError si el subscript fue abortado por Revert)
# -------------------------------------------------------------------------------------
# Historial:
#   2026-04-23 Marco / Claude Code — v2 canónico con $$ClewError
# =====================================================================================
2	Allow User Abort [ Off ]
3	Set Error Capture [ On ]
4	
5	# # DETECTAR ESTADO TRANSACCIONAL
6	Insert Calculated Result [ Select: On ; Target: $TransactionOpenState ; Get ( TransactionOpenState ) ]
7	Insert Calculated Result [ Select: On ; Target: $IsRoot ; not $TransactionOpenState ]
8	
9	# # SI SOY RAÍZ: preparar entorno aislado (reset log + global error + window temporal)
10	If [ $IsRoot ]
11	    Insert Calculated Result [ Select: On ; Target: $null ; Log.Reset ]
12	    Insert Calculated Result [ Select: On ; Target: $null ; Clew.ClearError ]
13	    Commit Records/Requests [ With dialog: Off ]
14	    Insert Calculated Result [ Select: On ; Target: $WindowName ; "tmp_" & Get ( UUID ) ]
15	    New Window [ Name: $WindowName ; Layout: "Proc_Globales" ]
16	End If
17	
18	# # ABRIR TRANSACCIÓN (FM anida automáticamente si ya hay padre)
19	Open Transaction [ Skip auto-enter options: Off ; Skip data entry validation: Off ; Override ESS locking conflicts: Off ; Off ]
20	
21	# # BLOQUE TRY — pseudo try-catch con Loop [Flush: Always]
22	Loop
23	    Exit Loop If [ error.CreateVarsFromKeys ( Get ( ScriptParameter ) ; "" ) ]
24	    Insert Calculated Result [ Select: On ; Target: $REQUIRED ; "Marca" ]
25	    Exit Loop If [ error.ThrowIfMissingParam ( $REQUIRED ; "" ) ]
26	    Insert Calculated Result [ Select: On ; Target: $SimularError ; If ( IsEmpty ( $SimularError ) ; False ; GetAsBoolean ( $SimularError ) ) ]
27	    Insert Calculated Result [ Select: On ; Target: $Momento ; If ( IsEmpty ( $Momento ) ; "despues" ; $Momento ) ]
28	    Set Field [ GLOBALES::zzTestClew_Trace__gxt ; List ( GLOBALES::zzTestClew_Trace__gxt ;
	"[" & $Marca & "] inicio · IsRoot=" & $IsRoot & " · TxnStateEntrada=" & $TransactionOpenState
) ]
29	    Insert Calculated Result [ Select: On ; Target: $null ; Log.Entry ( 1 ; "Template Dual inicio: " & $Marca ; "" ) ]
30	    If [ $SimularError and $Momento = "antes" ]
31	        Set Field [ GLOBALES::zzTestClew_Trace__gxt ; List ( GLOBALES::zzTestClew_Trace__gxt ;
	"[" & $Marca & "] ← simulando error ANTES del Set Field transaccional"
) ]
32	        Exit Loop If [ error.Throw ( _error_UNEXPECTED ; "Error simulado antes del Set Field en " & $Marca ) ]
33	    End If
34	    Set Field [ GLOBALES::zzTestClew_Valor__lxt ; $Marca ]
35	    Set Field [ GLOBALES::zzTestClew_Trace__gxt ; List ( GLOBALES::zzTestClew_Trace__gxt ;
	"[" & $Marca & "] Set Field zzTestClew_Valor__lxt = '" & $Marca & "'"
) ]
36	    If [ $SimularError and $Momento = "despues" ]
37	        Set Field [ GLOBALES::zzTestClew_Trace__gxt ; List ( GLOBALES::zzTestClew_Trace__gxt ;
	"[" & $Marca & "] ← simulando error DESPUÉS del Set Field transaccional"
) ]
38	        Exit Loop If [ error.Throw ( _error_UNEXPECTED ; "Error simulado después del Set Field en " & $Marca ) ]
39	    End If
40	    Insert Calculated Result [ Select: On ; Target: $Respuesta ; JSONSetElement ( "{}" ;
	[ "Marca" ; $Marca ; JSONString ] ;
	[ "IsRoot" ; $IsRoot ; JSONBoolean ] ;
	[ "TransactionOpenStateEntrada" ; $TransactionOpenState ; JSONNumber ]
) ]
41	    Insert Calculated Result [ Select: On ; Target: $null ; Log.Entry ( 1 ; "Template Dual fin: " & $Marca ; $Respuesta ) ]
42	    Exit Loop If [ True ]
43	End Loop
44	
45	# # PERSISTIR ERROR LOCAL EN GLOBAL (sobrevive aunque nos maten con Revert anidado)
46	If [ error.WasThrown ]
47	    Insert Calculated Result [ Select: On ; Target: $null ; Clew.SetError ( error.GetTrace ) ]
48	End If
49	
50	# # REVERT condicional + COMMIT lineal (emparejado con Open Transaction)
51	Revert Transaction [ Condition: Clew.HasError ]
52	Commit Transaction
53	Insert Calculated Result [ Select: On ; Target: $ErrorCommit ; Get ( LastError ) ]
54	# # Error de commit: ignorar el 3 si es nested (commit anidado sin cambios propios)
55	If [ $ErrorCommit ≠ 0
	and not ( $ErrorCommit = 3 and not $IsRoot )
	and not Clew.HasError ]
56	    Insert Calculated Result [ Select: On ; Target: $null ; error.Throw ( $ErrorCommit ; "Error al confirmar transacción en " & $Marca ) ]
57	    Insert Calculated Result [ Select: On ; Target: $null ; Clew.SetError ( error.GetTrace ) ]
58	End If
59	Set Field [ GLOBALES::zzTestClew_Trace__gxt ; List ( GLOBALES::zzTestClew_Trace__gxt ;
	"[" & $Marca & "] fin · Clew.HasError=" & Clew.HasError & " · ErrorCommit=" & $ErrorCommit
) ]
60	
61	# # SALIDA — si hay error (global), propagar. Si soy root, persistir log y limpiar global.
62	If [ Clew.HasError ]
63	    Insert Calculated Result [ Select: On ; Target: $ErrorTrace ; Clew.GetError ]
64	    If [ $IsRoot ]
65	        Perform Script [ From list ; "Create Log Clew" ; Parameter: $ErrorTrace ]
66	        Close Window [ Name: $WindowName ]
67	        Insert Calculated Result [ Select: On ; Target: $null ; Clew.ClearError ]
68	    End If
69	    Exit Script [ Text Result: $ErrorTrace ]
70	End If
71	If [ $IsRoot ]
72	    Close Window [ Name: $WindowName ]
73	End If
74	Exit Script [ Text Result: JSONSetElement ( error.GetTrace ;
	[ "result" ; $Respuesta ; JSONRaw ] ;
	[ "environment" ; getScriptEnvironment ; JSONRaw ]
) ]
```

## fmxmlsnippet (pegable en FileMaker)

> El HR de arriba es **solo-lectura** (no hay conversor HR → fmxmlsnippet). Este bloque es la fuente pegable: vuélcalo al portapapeles con `python3 agent/scripts/clipboard.py write <archivo>` y pégalo en Script Workspace.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<fmxmlsnippet type="FMObjectList">
  <Step enable="True" id="89" name="# (comment)">
    <Text># =====================================================================================
# Propósito: Plantilla canónica Clew transaccional dual padre/hijo con propagación
#            robusta de errores vía variable global $$ClewError.
#            El root limpia la global al terminar. Los intermedios solo leen y propagan.
#            Soporta N niveles de anidamiento y rollback total transparente.
# Contexto: insensible (crea Proc_Globales en ventana tmp si es root)
# Capa: Template (BPController2025)
# -------------------------------------------------------------------------------------
# Parámetros Requeridos:
#   - Marca (string): etiqueta identificadora (p.ej. "C1", "Test.1.2")
# Parámetros Opcionales:
#   - SimularError (boolean, default false)
#   - Momento (string, default "despues"): "antes" | "despues" del Set Field transaccional
# -------------------------------------------------------------------------------------
# Retorna:
#   Éxito: { result: {Marca, IsRoot, TransactionOpenStateEntrada}, environment: {...} }
#   Error: errorTrace JSON Clew (vía $$ClewError si el subscript fue abortado por Revert)
# -------------------------------------------------------------------------------------
# Historial:
#   2026-04-23 Marco / Claude Code — v2 canónico con $$ClewError
# =====================================================================================</Text>
  </Step>
  <Step enable="True" id="85" name="Allow User Abort">
    <Set state="False"/>
  </Step>
  <Step enable="True" id="86" name="Set Error Capture">
    <Set state="True"/>
  </Step>
  <Step enable="True" id="89" name="# (comment)"/>
  <Step enable="True" id="89" name="# (comment)">
    <Text># DETECTAR ESTADO TRANSACCIONAL</Text>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[Get ( TransactionOpenState )]]></Calculation>
    <Text/>
    <Field>$TransactionOpenState</Field>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[not $TransactionOpenState]]></Calculation>
    <Text/>
    <Field>$IsRoot</Field>
  </Step>
  <Step enable="True" id="89" name="# (comment)"/>
  <Step enable="True" id="89" name="# (comment)">
    <Text># SI SOY RAÍZ: preparar entorno aislado (reset log + global error + window temporal)</Text>
  </Step>
  <Step enable="True" id="68" name="If">
    <Calculation><![CDATA[$IsRoot]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[Log.Reset]]></Calculation>
    <Text/>
    <Field>$null</Field>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[Clew.ClearError]]></Calculation>
    <Text/>
    <Field>$null</Field>
  </Step>
  <Step enable="True" id="75" name="Commit Records/Requests">
    <NoInteract state="True"/>
    <Option state="False"/>
    <ESSForceCommit state="False"/>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA["tmp_" & Get ( UUID )]]></Calculation>
    <Text/>
    <Field>$WindowName</Field>
  </Step>
  <Step enable="True" id="122" name="New Window">
    <LayoutDestination value="SelectedLayout"/>
    <Name>
      <Calculation><![CDATA[$WindowName]]></Calculation>
    </Name>
    <Height>
      <Calculation><![CDATA[]]></Calculation>
    </Height>
    <Width>
      <Calculation><![CDATA[]]></Calculation>
    </Width>
    <DistanceFromTop>
      <Calculation><![CDATA[]]></Calculation>
    </DistanceFromTop>
    <DistanceFromLeft>
      <Calculation><![CDATA[]]></Calculation>
    </DistanceFromLeft>
    <NewWndStyles DimParentWindow="No" Toolbars="No" MenuBar="No" Style="Document" Close="Yes" Minimize="No" Maximize="No" Resize="No" Styles="1076299266"/>
    <Layout id="224" name="Proc_Globales"/>
  </Step>
  <Step enable="True" id="70" name="End If"/>
  <Step enable="True" id="89" name="# (comment)"/>
  <Step enable="True" id="89" name="# (comment)">
    <Text># ABRIR TRANSACCIÓN (FM anida automáticamente si ya hay padre)</Text>
  </Step>
  <Step enable="True" id="205" name="Open Transaction">
    <Option state="False"/>
    <ESSForceCommit state="False"/>
    <SkipAutoEntry state="False"/>
    <Restore state="False"/>
  </Step>
  <Step enable="True" id="89" name="# (comment)"/>
  <Step enable="True" id="89" name="# (comment)">
    <Text># BLOQUE TRY — pseudo try-catch con Loop [Flush: Always]</Text>
  </Step>
  <Step enable="True" id="71" name="Loop">
    <Flush state="Always"/>
  </Step>
  <Step enable="True" id="72" name="Exit Loop If">
    <Calculation><![CDATA[error.CreateVarsFromKeys ( Get ( ScriptParameter ) ; "" )]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA["Marca"]]></Calculation>
    <Text/>
    <Field>$REQUIRED</Field>
  </Step>
  <Step enable="True" id="72" name="Exit Loop If">
    <Calculation><![CDATA[error.ThrowIfMissingParam ( $REQUIRED ; "" )]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[If ( IsEmpty ( $SimularError ) ; False ; GetAsBoolean ( $SimularError ) )]]></Calculation>
    <Text/>
    <Field>$SimularError</Field>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[If ( IsEmpty ( $Momento ) ; "despues" ; $Momento )]]></Calculation>
    <Text/>
    <Field>$Momento</Field>
  </Step>
  <Step enable="True" id="76" name="Set Field">
    <Field table="GLOBALES" id="89" name="zzTestClew_Trace__gxt"/>
    <Calculation><![CDATA[List ( GLOBALES::zzTestClew_Trace__gxt ;
	"[" & $Marca & "] inicio · IsRoot=" & $IsRoot & " · TxnStateEntrada=" & $TransactionOpenState
)]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[Log.Entry ( 1 ; "Template Dual inicio: " & $Marca ; "" )]]></Calculation>
    <Text/>
    <Field>$null</Field>
  </Step>
  <Step enable="True" id="68" name="If">
    <Calculation><![CDATA[$SimularError and $Momento = "antes"]]></Calculation>
  </Step>
  <Step enable="True" id="76" name="Set Field">
    <Field table="GLOBALES" id="89" name="zzTestClew_Trace__gxt"/>
    <Calculation><![CDATA[List ( GLOBALES::zzTestClew_Trace__gxt ;
	"[" & $Marca & "] ← simulando error ANTES del Set Field transaccional"
)]]></Calculation>
  </Step>
  <Step enable="True" id="72" name="Exit Loop If">
    <Calculation><![CDATA[error.Throw ( _error_UNEXPECTED ; "Error simulado antes del Set Field en " & $Marca )]]></Calculation>
  </Step>
  <Step enable="True" id="70" name="End If"/>
  <Step enable="True" id="76" name="Set Field">
    <Field table="GLOBALES" id="90" name="zzTestClew_Valor__lxt"/>
    <Calculation><![CDATA[$Marca]]></Calculation>
  </Step>
  <Step enable="True" id="76" name="Set Field">
    <Field table="GLOBALES" id="89" name="zzTestClew_Trace__gxt"/>
    <Calculation><![CDATA[List ( GLOBALES::zzTestClew_Trace__gxt ;
	"[" & $Marca & "] Set Field zzTestClew_Valor__lxt = '" & $Marca & "'"
)]]></Calculation>
  </Step>
  <Step enable="True" id="68" name="If">
    <Calculation><![CDATA[$SimularError and $Momento = "despues"]]></Calculation>
  </Step>
  <Step enable="True" id="76" name="Set Field">
    <Field table="GLOBALES" id="89" name="zzTestClew_Trace__gxt"/>
    <Calculation><![CDATA[List ( GLOBALES::zzTestClew_Trace__gxt ;
	"[" & $Marca & "] ← simulando error DESPUÉS del Set Field transaccional"
)]]></Calculation>
  </Step>
  <Step enable="True" id="72" name="Exit Loop If">
    <Calculation><![CDATA[error.Throw ( _error_UNEXPECTED ; "Error simulado después del Set Field en " & $Marca )]]></Calculation>
  </Step>
  <Step enable="True" id="70" name="End If"/>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[JSONSetElement ( "{}" ;
	[ "Marca" ; $Marca ; JSONString ] ;
	[ "IsRoot" ; $IsRoot ; JSONBoolean ] ;
	[ "TransactionOpenStateEntrada" ; $TransactionOpenState ; JSONNumber ]
)]]></Calculation>
    <Text/>
    <Field>$Respuesta</Field>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[Log.Entry ( 1 ; "Template Dual fin: " & $Marca ; $Respuesta )]]></Calculation>
    <Text/>
    <Field>$null</Field>
  </Step>
  <Step enable="True" id="72" name="Exit Loop If">
    <Calculation><![CDATA[True]]></Calculation>
  </Step>
  <Step enable="True" id="73" name="End Loop"/>
  <Step enable="True" id="89" name="# (comment)"/>
  <Step enable="True" id="89" name="# (comment)">
    <Text># PERSISTIR ERROR LOCAL EN GLOBAL (sobrevive aunque nos maten con Revert anidado)</Text>
  </Step>
  <Step enable="True" id="68" name="If">
    <Calculation><![CDATA[error.WasThrown]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[Clew.SetError ( error.GetTrace )]]></Calculation>
    <Text/>
    <Field>$null</Field>
  </Step>
  <Step enable="True" id="70" name="End If"/>
  <Step enable="True" id="89" name="# (comment)"/>
  <Step enable="True" id="89" name="# (comment)">
    <Text># REVERT condicional + COMMIT lineal (emparejado con Open Transaction)</Text>
  </Step>
  <Step enable="True" id="207" name="Revert Transaction">
    <Option state="False"/>
    <Condition>
      <Calculation><![CDATA[Clew.HasError]]></Calculation>
    </Condition>
  </Step>
  <Step enable="True" id="206" name="Commit Transaction"/>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[Get ( LastError )]]></Calculation>
    <Text/>
    <Field>$ErrorCommit</Field>
  </Step>
  <Step enable="True" id="89" name="# (comment)">
    <Text># Error de commit: ignorar el 3 si es nested (commit anidado sin cambios propios)</Text>
  </Step>
  <Step enable="True" id="68" name="If">
    <Calculation><![CDATA[$ErrorCommit ≠ 0
	and not ( $ErrorCommit = 3 and not $IsRoot )
	and not Clew.HasError]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[error.Throw ( $ErrorCommit ; "Error al confirmar transacción en " & $Marca )]]></Calculation>
    <Text/>
    <Field>$null</Field>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[Clew.SetError ( error.GetTrace )]]></Calculation>
    <Text/>
    <Field>$null</Field>
  </Step>
  <Step enable="True" id="70" name="End If"/>
  <Step enable="True" id="76" name="Set Field">
    <Field table="GLOBALES" id="89" name="zzTestClew_Trace__gxt"/>
    <Calculation><![CDATA[List ( GLOBALES::zzTestClew_Trace__gxt ;
	"[" & $Marca & "] fin · Clew.HasError=" & Clew.HasError & " · ErrorCommit=" & $ErrorCommit
)]]></Calculation>
  </Step>
  <Step enable="True" id="89" name="# (comment)"/>
  <Step enable="True" id="89" name="# (comment)">
    <Text># SALIDA — si hay error (global), propagar. Si soy root, persistir log y limpiar global.</Text>
  </Step>
  <Step enable="True" id="68" name="If">
    <Calculation><![CDATA[Clew.HasError]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[Clew.GetError]]></Calculation>
    <Text/>
    <Field>$ErrorTrace</Field>
  </Step>
  <Step enable="True" id="68" name="If">
    <Calculation><![CDATA[$IsRoot]]></Calculation>
  </Step>
  <Step enable="True" id="1" name="Perform Script">
    <Calculation><![CDATA[$ErrorTrace]]></Calculation>
    <Script id="1291" name="Create Log Clew"/>
  </Step>
  <Step enable="True" id="121" name="Close Window">
    <LimitToWindowsOfCurrentFile state="True"/>
    <Window value="ByName"/>
    <Name>
      <Calculation><![CDATA[$WindowName]]></Calculation>
    </Name>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[Clew.ClearError]]></Calculation>
    <Text/>
    <Field>$null</Field>
  </Step>
  <Step enable="True" id="70" name="End If"/>
  <Step enable="True" id="103" name="Exit Script">
    <Calculation><![CDATA[$ErrorTrace]]></Calculation>
  </Step>
  <Step enable="True" id="70" name="End If"/>
  <Step enable="True" id="68" name="If">
    <Calculation><![CDATA[$IsRoot]]></Calculation>
  </Step>
  <Step enable="True" id="121" name="Close Window">
    <LimitToWindowsOfCurrentFile state="True"/>
    <Window value="ByName"/>
    <Name>
      <Calculation><![CDATA[$WindowName]]></Calculation>
    </Name>
  </Step>
  <Step enable="True" id="70" name="End If"/>
  <Step enable="True" id="103" name="Exit Script">
    <Calculation><![CDATA[JSONSetElement ( error.GetTrace ;
	[ "result" ; $Respuesta ; JSONRaw ] ;
	[ "environment" ; getScriptEnvironment ; JSONRaw ]
)]]></Calculation>
  </Step>
</fmxmlsnippet>
```
