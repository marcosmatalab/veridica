# ADR 0004: los ficheros normalizados entran como entrada propia, en árbol espejo

- **Fecha:** 11 de agosto de 2026
- **Encargo:** 1.3 (decidido antes de empezarlo)
- **Estado:** aceptada

## Contexto

El encargo 1.3 convierte a markdown o texto limpio lo que hoy es PDF y ODT. Eso genera ficheros
nuevos, y el manifiesto —que exige una entrada por fichero en disco— tiene que crecer con ellos. La
decisión quedó planteada en el encargo 1.1 y sin resolver, con tres opciones sobre la mesa.

## Decisión

**Cada fichero convertido tiene su propia entrada en el manifiesto, con un campo `derivado_de` que
apunta a la ruta del original**, y el original se conserva intacto con su entrada y su hash.

Descartadas, con su porqué:

- **Que el convertido sustituya al original.** Se perdería la evidencia (el PDF del que salió el
  texto, que es lo que permite comprobar una cita si alguien discute) y se perdería su licencia
  declarada, que va atada al documento original y es lo que autoriza a tenerlo.
- **Que el hash del convertido viaje dentro de la entrada del original.** Rompe la regla de una
  entrada por fichero en disco, que es justo el invariante sobre el que se apoya el verificador del
  encargo 1.0, y obligaría a complicar una puerta que acaba de quedar simple y probada.

### Condición 1: la entrada del derivado registra la herramienta y su versión exacta

Campos `herramienta` y `herramienta_version` (por ejemplo `pypdf` y `6.4.0`). La conversión de PDF a
texto **no es determinista entre versiones**: una librería nueva cambia espaciados, guiones o el
orden de bloques, y el hash del derivado cambia sin que nadie haya tocado el corpus. Sin ese dato,
el hash del derivado es irreproducible y **la puerta del 1.0 se pondría roja sola el día que se
actualice una dependencia**, sin poder distinguir eso de una corrupción real. Con el dato, la
diferencia se explica en un vistazo: mismo original, distinta herramienta, hash nuevo esperado.

### Condición 2: los derivados van en un árbol espejo, no junto al original

Ruta propuesta: `corpus/derivado/<misma ruta relativa que el original>` con extensión `.md`. Dos
motivos: lo derivado tiene que ser **borrable y regenerable entero** (un `rm -rf corpus/derivado` y
volver a generar, sin miedo a llevarse una fuente por delante), y la **fuente queda intacta**, sin
ficheros nuevos mezclados entre el material original. De regalo, la ingesta sabe sin ambigüedad qué
árbol leer.

El derivado **hereda la licencia, la densidad y la marca `plantado` del original**: un texto extraído
de un documento CC BY-NC-SA sigue siendo CC BY-NC-SA, y un derivado de basura plantada sigue siendo
basura plantada.

## Trade-off

Se paga: el manifiesto casi duplica sus entradas en la parte convertida, hay dos árboles que
mantener, y regenerar derivados obliga a re-registrar hashes de forma explícita (con
`scripts/actualizar_hash_manifiesto.py`, que exige las rutas una a una a propósito).

Se gana: la cadena original → derivado es auditable documento a documento, la evidencia y su
licencia sobreviven, y el invariante "un fichero, una entrada" —del que depende la única puerta de
integridad del corpus— se queda como está.

## Estado de preparación

El verificador del encargo 1.0 ya tolera campos nuevos en las entradas (solo exige `ruta` y
`hash_sha256`) y hay un test que lo fija precisamente con `derivado_de` y `origen`. Esta decisión no
obliga a tocarlo: era lo que se quería decir con "el manifiesto no se supone inmutable".
