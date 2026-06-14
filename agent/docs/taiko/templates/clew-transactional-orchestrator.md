# Template: Clew Transactional Dual — Orchestrator

Orquestador del patrón Clew transaccional dual: ejecuta N workers (o sub-orquestadores) bajo una única transacción agregada, con *fail-fast* (`Clew.HasError`) y rollback total a N niveles. Es la variante con loop de subscripts del Worker (`clew-transactional-dual.md`, mismo directorio).

**Name:** `Clew | Template Orchestrator {json}`

> Patrón completo, reglas de oro y validación empírica en [`../knowledge/clew-transactional-dual.md`](../knowledge/clew-transactional-dual.md).

## Script (human-readable)

```
1	# # =====================================================================================
# Propósito: Controller canónico Clew. Orquesta N workers (o sub-orquestadores) bajo
#            una única transacción agregada. Propaga errores vía $$ClewError.
#            Soporta N niveles de anidamiento y rollback total transparente.
# Contexto: insensible (crea Proc_Globales en ventana tmp si es root)
# Capa: Template (BPController2025)
# -------------------------------------------------------------------------------------
# Parámetros Requeridos:
#   - MarcaPrefix (string)
#   - NumWorkers (number)
# Parámetros Opcionales:
#   - WorkerConErrorIdx (number, 1-indexed): qué worker debe fallar
#   - MomentoError (string, default "despues"): "antes" | "despues"
#   - RecursionPendiente (number, default 0): niveles de orquestadores adicionales
# -------------------------------------------------------------------------------------
# Retorna:
#   Éxito: { result: {MarcaPrefix, NumWorkersLlamados, IsRoot}, environment: {...} }
#   Error: errorTrace JSON Clew propagado hasta la raíz vía $$ClewError
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
9	# # SI SOY RAÍZ: preparar entorno aislado
10	If [ $IsRoot ]
11	    Insert Calculated Result [ Select: On ; Target: $null ; Log.Reset ]
12	    Insert Calculated Result [ Select: On ; Target: $null ; Clew.ClearError ]
13	    Commit Records/Requests [ With dialog: Off ]
14	    Insert Calculated Result [ Select: On ; Target: $WindowName ; "tmp_" & Get ( UUID ) ]
15	    New Window [ Name: $WindowName ; Layout: "Proc_Globales" ]
16	End If
17	
18	# # ABRIR TRANSACCIÓN
19	Open Transaction [ Skip auto-enter options: Off ; Skip data entry validation: Off ; Override ESS locking conflicts: Off ; Off ]
20	
21	# # BLOQUE TRY — pseudo try-catch con Loop
22	Loop
23	    Exit Loop If [ error.CreateVarsFromKeys ( Get ( ScriptParameter ) ; "" ) ]
24	    Insert Calculated Result [ Select: On ; Target: $REQUIRED ; List ( "MarcaPrefix" ; "NumWorkers" ) ]
25	    Exit Loop If [ error.ThrowIfMissingParam ( $REQUIRED ; "" ) ]
26	    Insert Calculated Result [ Select: On ; Target: $NumWorkers ; GetAsNumber ( $NumWorkers ) ]
27	    Insert Calculated Result [ Select: On ; Target: $WorkerConErrorIdx ; If ( IsEmpty ( $WorkerConErrorIdx ) ; 0 ; GetAsNumber ( $WorkerConErrorIdx ) ) ]
28	    Insert Calculated Result [ Select: On ; Target: $MomentoError ; If ( IsEmpty ( $MomentoError ) ; "despues" ; $MomentoError ) ]
29	    Insert Calculated Result [ Select: On ; Target: $RecursionPendiente ; If ( IsEmpty ( $RecursionPendiente ) ; 0 ; GetAsNumber ( $RecursionPendiente ) ) ]
30	    Set Field [ GLOBALES::zzTestClew_Trace__gxt ; List ( GLOBALES::zzTestClew_Trace__gxt ;
	"<" & $MarcaPrefix & "> Orchestrator inicio · IsRoot=" & $IsRoot
		& " · TxnState=" & $TransactionOpenState
		& " · NumWorkers=" & $NumWorkers
		& " · RecursionPendiente=" & $RecursionPendiente
) ]
31	    Insert Calculated Result [ Select: On ; Target: $null ; Log.Entry ( 1 ; "Orchestrator inicio: " & $MarcaPrefix ; "" ) ]
32	    
33	    # # LOOP de workers — fail-fast con Clew.HasError
34	    Insert Calculated Result [ Select: On ; Target: $i ; "" ]
35	    Loop
36	        Exit Loop If [ Let (
	[
		$i = $i + 1
	] ;
	If (
		$i > $NumWorkers ;
			Let ( [ $i = "" ] ; True )
	)
) ]
37	        Exit Loop If [ Clew.HasError ]
38	        Insert Calculated Result [ Select: On ; Target: $EsWorkerConFallo ; $i = $WorkerConErrorIdx ]
39	        If [ $RecursionPendiente > 0 ]
40	            Insert Calculated Result [ Select: On ; Target: $JsonSub ; JSONSetElement ( "{}" ;
	[ "MarcaPrefix" ; $MarcaPrefix & ".L" & $RecursionPendiente & "." & $i ; JSONString ] ;
	[ "NumWorkers" ; 1 ; JSONNumber ] ;
	[ "WorkerConErrorIdx" ; If ( $EsWorkerConFallo ; 1 ; "" ) ; JSONNumber ] ;
	[ "MomentoError" ; $MomentoError ; JSONString ] ;
	[ "RecursionPendiente" ; $RecursionPendiente - 1 ; JSONNumber ]
) ]
41	            Perform Script [ From list ; "Clew | Template Orchestrator {json}" ; Parameter: $JsonSub ]
42	        Else
43	            Insert Calculated Result [ Select: On ; Target: $JsonSub ; JSONSetElement ( "{}" ;
	[ "Marca" ; $MarcaPrefix & "." & $i ; JSONString ] ;
	[ "SimularError" ; $EsWorkerConFallo ; JSONBoolean ] ;
	[ "Momento" ; $MomentoError ; JSONString ]
) ]
44	            Perform Script [ From list ; "Clew | Template Dual {json}" ; Parameter: $JsonSub ]
45	        End If
46	        # # Tras el sub: si dejó error en global, propagar al estado local
47	        If [ Clew.HasError and not error.WasThrown ]
48	            Insert Calculated Result [ Select: On ; Target: $null ; error.Throw ( _error_UNEXPECTED ;
	"Error en subscript: " & JSONGetElement ( Clew.GetError ; "errorTrace[0].hint" )
) ]
49	        End If
50	    End Loop
51	    Insert Calculated Result [ Select: On ; Target: $Respuesta ; JSONSetElement ( "{}" ;
	[ "MarcaPrefix" ; $MarcaPrefix ; JSONString ] ;
	[ "NumWorkersLlamados" ; $NumWorkers ; JSONNumber ] ;
	[ "RecursionPendiente" ; $RecursionPendiente ; JSONNumber ] ;
	[ "IsRoot" ; $IsRoot ; JSONBoolean ]
) ]
52	    Insert Calculated Result [ Select: On ; Target: $null ; Log.Entry ( 1 ; "Orchestrator fin: " & $MarcaPrefix ; $Respuesta ) ]
53	    Exit Loop If [ True ]
54	End Loop
55	
56	# # PERSISTIR ERROR LOCAL EN GLOBAL (defensivo — si alguna validación local falló)
57	If [ error.WasThrown ]
58	    Insert Calculated Result [ Select: On ; Target: $null ; Clew.SetError ( error.GetTrace ) ]
59	End If
60	
61	# # REVERT condicional + COMMIT lineal
62	Revert Transaction [ Condition: Clew.HasError ]
63	Commit Transaction
64	Insert Calculated Result [ Select: On ; Target: $ErrorCommit ; Get ( LastError ) ]
65	If [ $ErrorCommit ≠ 0
	and not ( $ErrorCommit = 3 and not $IsRoot )
	and not Clew.HasError ]
66	    Insert Calculated Result [ Select: On ; Target: $null ; error.Throw ( $ErrorCommit ; "Error al confirmar transacción en Orchestrator " & $MarcaPrefix ) ]
67	    Insert Calculated Result [ Select: On ; Target: $null ; Clew.SetError ( error.GetTrace ) ]
68	End If
69	Set Field [ GLOBALES::zzTestClew_Trace__gxt ; List ( GLOBALES::zzTestClew_Trace__gxt ;
	"<" & $MarcaPrefix & "> Orchestrator fin · Clew.HasError=" & Clew.HasError & " · ErrorCommit=" & $ErrorCommit
) ]
70	
71	# # SALIDA
72	If [ Clew.HasError ]
73	    Insert Calculated Result [ Select: On ; Target: $ErrorTrace ; Clew.GetError ]
74	    If [ $IsRoot ]
75	        Perform Script [ From list ; "Create Log Clew" ; Parameter: $ErrorTrace ]
76	        Close Window [ Name: $WindowName ]
77	        Insert Calculated Result [ Select: On ; Target: $null ; Clew.ClearError ]
78	    End If
79	    Exit Script [ Text Result: $ErrorTrace ]
80	End If
81	If [ $IsRoot ]
82	    Close Window [ Name: $WindowName ]
83	End If
84	Exit Script [ Text Result: JSONSetElement ( error.GetTrace ;
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
# Propósito: Controller canónico Clew. Orquesta N workers (o sub-orquestadores) bajo
#            una única transacción agregada. Propaga errores vía $$ClewError.
#            Soporta N niveles de anidamiento y rollback total transparente.
# Contexto: insensible (crea Proc_Globales en ventana tmp si es root)
# Capa: Template (BPController2025)
# -------------------------------------------------------------------------------------
# Parámetros Requeridos:
#   - MarcaPrefix (string)
#   - NumWorkers (number)
# Parámetros Opcionales:
#   - WorkerConErrorIdx (number, 1-indexed): qué worker debe fallar
#   - MomentoError (string, default "despues"): "antes" | "despues"
#   - RecursionPendiente (number, default 0): niveles de orquestadores adicionales
# -------------------------------------------------------------------------------------
# Retorna:
#   Éxito: { result: {MarcaPrefix, NumWorkersLlamados, IsRoot}, environment: {...} }
#   Error: errorTrace JSON Clew propagado hasta la raíz vía $$ClewError
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
    <Text># SI SOY RAÍZ: preparar entorno aislado</Text>
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
    <Text># ABRIR TRANSACCIÓN</Text>
  </Step>
  <Step enable="True" id="205" name="Open Transaction">
    <Option state="False"/>
    <ESSForceCommit state="False"/>
    <SkipAutoEntry state="False"/>
    <Restore state="False"/>
  </Step>
  <Step enable="True" id="89" name="# (comment)"/>
  <Step enable="True" id="89" name="# (comment)">
    <Text># BLOQUE TRY — pseudo try-catch con Loop</Text>
  </Step>
  <Step enable="True" id="71" name="Loop">
    <Flush state="Always"/>
  </Step>
  <Step enable="True" id="72" name="Exit Loop If">
    <Calculation><![CDATA[error.CreateVarsFromKeys ( Get ( ScriptParameter ) ; "" )]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[List ( "MarcaPrefix" ; "NumWorkers" )]]></Calculation>
    <Text/>
    <Field>$REQUIRED</Field>
  </Step>
  <Step enable="True" id="72" name="Exit Loop If">
    <Calculation><![CDATA[error.ThrowIfMissingParam ( $REQUIRED ; "" )]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[GetAsNumber ( $NumWorkers )]]></Calculation>
    <Text/>
    <Field>$NumWorkers</Field>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[If ( IsEmpty ( $WorkerConErrorIdx ) ; 0 ; GetAsNumber ( $WorkerConErrorIdx ) )]]></Calculation>
    <Text/>
    <Field>$WorkerConErrorIdx</Field>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[If ( IsEmpty ( $MomentoError ) ; "despues" ; $MomentoError )]]></Calculation>
    <Text/>
    <Field>$MomentoError</Field>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[If ( IsEmpty ( $RecursionPendiente ) ; 0 ; GetAsNumber ( $RecursionPendiente ) )]]></Calculation>
    <Text/>
    <Field>$RecursionPendiente</Field>
  </Step>
  <Step enable="True" id="76" name="Set Field">
    <Field table="GLOBALES" id="89" name="zzTestClew_Trace__gxt"/>
    <Calculation><![CDATA[List ( GLOBALES::zzTestClew_Trace__gxt ;
	"<" & $MarcaPrefix & "> Orchestrator inicio · IsRoot=" & $IsRoot
		& " · TxnState=" & $TransactionOpenState
		& " · NumWorkers=" & $NumWorkers
		& " · RecursionPendiente=" & $RecursionPendiente
)]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[Log.Entry ( 1 ; "Orchestrator inicio: " & $MarcaPrefix ; "" )]]></Calculation>
    <Text/>
    <Field>$null</Field>
  </Step>
  <Step enable="True" id="89" name="# (comment)"/>
  <Step enable="True" id="89" name="# (comment)">
    <Text># LOOP de workers — fail-fast con Clew.HasError</Text>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[""]]></Calculation>
    <Text/>
    <Field>$i</Field>
  </Step>
  <Step enable="True" id="71" name="Loop">
    <Flush state="Always"/>
  </Step>
  <Step enable="True" id="72" name="Exit Loop If">
    <Calculation><![CDATA[Let (
	[
		$i = $i + 1
	] ;
	If (
		$i > $NumWorkers ;
			Let ( [ $i = "" ] ; True )
	)
)]]></Calculation>
  </Step>
  <Step enable="True" id="72" name="Exit Loop If">
    <Calculation><![CDATA[Clew.HasError]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[$i = $WorkerConErrorIdx]]></Calculation>
    <Text/>
    <Field>$EsWorkerConFallo</Field>
  </Step>
  <Step enable="True" id="68" name="If">
    <Calculation><![CDATA[$RecursionPendiente > 0]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[JSONSetElement ( "{}" ;
	[ "MarcaPrefix" ; $MarcaPrefix & ".L" & $RecursionPendiente & "." & $i ; JSONString ] ;
	[ "NumWorkers" ; 1 ; JSONNumber ] ;
	[ "WorkerConErrorIdx" ; If ( $EsWorkerConFallo ; 1 ; "" ) ; JSONNumber ] ;
	[ "MomentoError" ; $MomentoError ; JSONString ] ;
	[ "RecursionPendiente" ; $RecursionPendiente - 1 ; JSONNumber ]
)]]></Calculation>
    <Text/>
    <Field>$JsonSub</Field>
  </Step>
  <Step enable="True" id="1" name="Perform Script">
    <Calculation><![CDATA[$JsonSub]]></Calculation>
    <Script id="0" name="Clew | Template Orchestrator {json}"/>
  </Step>
  <Step enable="True" id="69" name="Else"/>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[JSONSetElement ( "{}" ;
	[ "Marca" ; $MarcaPrefix & "." & $i ; JSONString ] ;
	[ "SimularError" ; $EsWorkerConFallo ; JSONBoolean ] ;
	[ "Momento" ; $MomentoError ; JSONString ]
)]]></Calculation>
    <Text/>
    <Field>$JsonSub</Field>
  </Step>
  <Step enable="True" id="1" name="Perform Script">
    <Calculation><![CDATA[$JsonSub]]></Calculation>
    <Script id="0" name="Clew | Template Dual {json}"/>
  </Step>
  <Step enable="True" id="70" name="End If"/>
  <Step enable="True" id="89" name="# (comment)">
    <Text># Tras el sub: si dejó error en global, propagar al estado local</Text>
  </Step>
  <Step enable="True" id="68" name="If">
    <Calculation><![CDATA[Clew.HasError and not error.WasThrown]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[error.Throw ( _error_UNEXPECTED ;
	"Error en subscript: " & JSONGetElement ( Clew.GetError ; "errorTrace[0].hint" )
)]]></Calculation>
    <Text/>
    <Field>$null</Field>
  </Step>
  <Step enable="True" id="70" name="End If"/>
  <Step enable="True" id="73" name="End Loop"/>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[JSONSetElement ( "{}" ;
	[ "MarcaPrefix" ; $MarcaPrefix ; JSONString ] ;
	[ "NumWorkersLlamados" ; $NumWorkers ; JSONNumber ] ;
	[ "RecursionPendiente" ; $RecursionPendiente ; JSONNumber ] ;
	[ "IsRoot" ; $IsRoot ; JSONBoolean ]
)]]></Calculation>
    <Text/>
    <Field>$Respuesta</Field>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[Log.Entry ( 1 ; "Orchestrator fin: " & $MarcaPrefix ; $Respuesta )]]></Calculation>
    <Text/>
    <Field>$null</Field>
  </Step>
  <Step enable="True" id="72" name="Exit Loop If">
    <Calculation><![CDATA[True]]></Calculation>
  </Step>
  <Step enable="True" id="73" name="End Loop"/>
  <Step enable="True" id="89" name="# (comment)"/>
  <Step enable="True" id="89" name="# (comment)">
    <Text># PERSISTIR ERROR LOCAL EN GLOBAL (defensivo — si alguna validación local falló)</Text>
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
    <Text># REVERT condicional + COMMIT lineal</Text>
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
  <Step enable="True" id="68" name="If">
    <Calculation><![CDATA[$ErrorCommit ≠ 0
	and not ( $ErrorCommit = 3 and not $IsRoot )
	and not Clew.HasError]]></Calculation>
  </Step>
  <Step enable="True" id="77" name="Insert Calculated Result">
    <SelectAll state="True"/>
    <Calculation><![CDATA[error.Throw ( $ErrorCommit ; "Error al confirmar transacción en Orchestrator " & $MarcaPrefix )]]></Calculation>
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
	"<" & $MarcaPrefix & "> Orchestrator fin · Clew.HasError=" & Clew.HasError & " · ErrorCommit=" & $ErrorCommit
)]]></Calculation>
  </Step>
  <Step enable="True" id="89" name="# (comment)"/>
  <Step enable="True" id="89" name="# (comment)">
    <Text># SALIDA</Text>
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
