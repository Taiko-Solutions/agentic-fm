# `Go to Layout` por cálculo y el `<Layout>` que falta — navegación silenciosa a ninguna parte

## Síntoma

Un script transaccional que parecía correcto (Go to Layout → New Record / Enter Find Mode → Perform Find → Set Field) **fallaba solo server-side** (vía Data API / OData script bridge):

- `New Record/Request` → **error 106 "Table is missing"**.
- `Perform Find` → **found: 0**, aunque un `ExecuteSQL` previo SÍ veía el registro.

Client-side (FileMaker Pro) el mismo script funcionaba. Otro script con el mismo patrón pero **otro layout** funcionaba también server-side. La diferencia estaba en el step `Go to Layout`.

## Causa

El `Go to Layout` no llevaba destino real: el fmxmlsnippet pegado era

```xml
<Step enable="True" id="6" name="Go to Layout">
  <LayoutDestination value="SelectedLayout"/>   <!-- ❌ sin <Layout> -->
</Step>
```

Sin el elemento `<Layout …>`, `Go to Layout [SelectedLayout]` **no navega a ningún sitio**. La sesión se queda en un contexto sin tabla utilizable; por eso `New Record` da 106 y `Perform Find` no encuentra nada. Client-side a veces "perdona" (el contexto previo de la UI tapa el fallo); server-side no hay contexto previo y el fallo aflora.

## `Go to Layout` tiene 3 formas — y el destino por cálculo es distinto

El SaXML original era un **Go to Layout por cálculo** (`LayoutReferenceContainer value="3"` con una `Calculation` que devuelve el nombre del layout, p.ej. `"Proc_Tareas"`). Su forma fmxmlsnippet correcta es:

```xml
<!-- Por nombre calculado en runtime -->
<Step enable="True" id="6" name="Go to Layout">
  <LayoutDestination value="LayoutNameByCalc"/>
  <Layout>
    <Calculation><![CDATA["Proc_Tareas"]]></Calculation>
  </Layout>
</Step>
```

Equivalentes válidos (cualquiera navega a Proc_Tareas):

```xml
<!-- Por referencia de lista (id + nombre) -->
<Step enable="True" id="6" name="Go to Layout">
  <LayoutDestination value="SelectedLayout"/>
  <Layout id="314" name="Proc_Tareas"/>
</Step>

<!-- Volver al layout donde arrancó el script -->
<Step enable="True" id="6" name="Go to Layout">
  <LayoutDestination value="OriginalLayout"/>
</Step>
```

`LayoutDestination` SIEMPRE debe ir acompañado de su destino concreto: `<Layout id/name>` (lista), `<Layout><Calculation>…</Calculation></Layout>` (cálculo), o nada solo si es `OriginalLayout`/`CurrentLayout`.

## Cómo apareció (974, 2026-06-07)

El conversor `agent/scripts/fm_xml_to_snippet.py` (SaXML → fmxmlsnippet) **no manejaba el destino por cálculo**: al no encontrar un `<LayoutReference>` de lista, emitía `SelectedLayout` sin `<Layout>`. Los 3 scripts de escritura convertidos (`task.create`, `task.update`, `task.changeStatus`) salieron rotos; las lecturas (sin `Go to Layout`) y un script no reconvertido (`task.annotate`) funcionaban. **Fix aplicado al conversor**: detectar la `Calculation` dentro de `LayoutReferenceContainer` y emitir `LayoutNameByCalc`.

## Regla práctica

- Tras convertir un script con `fm_xml_to_snippet.py`, **revisa cada `Go to Layout`**: debe tener un `<Layout>` (id/name o Calculation) salvo destinos Original/Current.
- Si un script transaccional funciona en cliente pero da **106 / found 0 server-side**, sospecha del `Go to Layout` antes que de privilegios o del binding de la fuente externa.
