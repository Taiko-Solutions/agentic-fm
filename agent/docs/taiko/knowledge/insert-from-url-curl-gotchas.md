# Insert from URL con cURL: tres trampas silenciosas

Comprobado en FileMaker 2026 llamando a un servicio Node.js (Express + multer) desde un proyecto cliente (2026-10).
Ninguna de las tres da error al pegar ni al ejecutar: el resultado sale mal sin aviso.

## 1. `-F "campo=@$Variable"` sube el fichero con el nombre de la VARIABLE

Con un contenedor en `$Contenedor`, `-F "file=@$Contenedor"` manda el fichero como **`Contenedor`**, sin extensión, aunque
el contenedor se llame `factura.pdf`. El servidor guarda ese nombre y el destinatario recibe un adjunto «Contenedor».
La documentación de Claris (*Supported cURL options*) no lo menciona.

Fijar nombre y tipo con la sintaxis de curl (FileMaker la respeta):

```
"-X POST -F " & Quote ( "file=@$Contenedor;filename=" & Substitute ( $Nombre ; [ ";" ; "_" ] ; [ "\"" ; "_" ] ) & ";type=application/pdf" )
```

Sanea el nombre: un `;` o una comilla dentro rompen la opción `-F`.

## 2. Un 401 de la respuesta llega como error del PASO

Si el servidor contesta `401` (clave mala), `Get ( LastError )` ≠ 0 después de `Insert from URL`. Un
`Exit Loop If [ error.ThrowIfLast ( "No se pudo contactar…" ) ]` justo después da un mensaje falso («no hay conexión»)
y nunca llega a leer el código. Patrón correcto:

```
Insert from URL [ … ; cURL: "… -D $Cabeceras" ]
Insert Calculated Result [ $ErrorURL ; Get ( LastError ) ]
Insert Calculated Result [ $Codigo ; Let ( ~p = Position ( $Cabeceras ; "HTTP/" ; Length ( $Cabeceras ) ; -1 ) ;
    If ( ~p = 0 ; 0 ; GetAsNumber ( Middle ( $Cabeceras ; Position ( $Cabeceras ; " " ; ~p ; 1 ) + 1 ; 3 ) ) ) ) ]
Exit Loop If [ error.ThrowIf ( $ErrorURL ≠ 0 and $Codigo < 100 ; _error_FAILED_CONDITION ; "No se pudo contactar…" ) ]
# a partir de aquí, decidir por $Codigo (401/403 clave, 400 validación, 413 tamaño, 429 límite…)
```

Se busca el **último** `HTTP/` de las cabeceras porque puede haber un `100 Continue` delante.

## 3. Sin `--max-time`, un corte de red puede duplicar envíos

Si el servidor acepta la petición pero la respuesta no llega, el usuario ve un error y reintenta. En llamadas que
**envían** algo (correo, cobro), poner `--connect-timeout` y `--max-time`, y que el mensaje de error de red diga que
puede haber salido y dónde comprobarlo antes de reintentar.

## Relacionado

- `silent-discard-params.md` — parámetros que FileMaker descarta en silencio al pegar.
- `clew-pattern.md` — `error.ThrowIf`, `error.ThrowIfLast`.
