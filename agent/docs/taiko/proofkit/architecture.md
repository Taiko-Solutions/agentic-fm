# ProofKit Web Viewer — modelo mental (Vía 3)

> Una app **React que corre dentro de un Web Viewer de FileMaker**, con datos vía la Data API. Es la **Vía 3** de [../fm-access.md](../fm-access.md) y el **motor web por defecto** de Taiko.
>
> ⚠️ No confundir con el webviewer/editor Monaco de agentic-fm.

## Las 4 piezas

```
  App React  ──Layout.find()──►  fmFetch  ──HTTP/WS──►  bridge  ──►  FileMaker
 (Web Viewer)                   (petición)          (localhost:1365)  (corre script)
       ▲                                                                   │
       └────────  "Perform JavaScript in Web Viewer" (el callback)  ◄───────┘
```

| Pieza | Qué es |
|---|---|
| **typegen** (`@proofkit/typegen`) | Genera esquema TS + cliente por cada layout — una "foto" congelada de los campos del layout. Regenerar tras tocar campos. |
| **esquema zod** | Contrato estricto que valida los datos en runtime; si falta un campo, **rechaza toda la lectura**. |
| **bridge** | Servicio local HTTP+WebSocket (`localhost:1365`) que une Web Viewer y FileMaker. Mismo puente que la Vía 1. |
| **fmFetch + callback** | La petición sale por `fmFetch`; el resultado vuelve por *Perform JavaScript in Web Viewer*. La promesa solo resuelve cuando vuelve el callback. |

**Frase clave:** la mayoría de los fallos viven en la frontera **fmFetch / callback / validación de esquema**. Cuando algo falle, sospecha de aquí — **no** de "la red". El síntoma típico (spinner infinito) casi nunca es un problema de red real.

## Stack generado (por `setup_proofkit_project`)

React + TypeScript + Vite + Tailwind + shadcn/ui + TanStack Query + TypeGen. Ver el flujo paso a paso en [webviewer-build.md](webviewer-build.md).

## Estado y procedencia

Vía 3 estuvo **aparcada** por la fragilidad del puente (field report de **Eikonsys — Ibrahim Bittar**, 2026-06-16, sobre una solución de 1.300+ layouts). **Ahora está reactivada como motor web por defecto**, pero se construye **con guardarraíles**: los 11 hallazgos son de aplicación obligatoria. Ver [gotchas.md](gotchas.md), [troubleshooting.md](troubleshooting.md) y [conventions.md](conventions.md).
