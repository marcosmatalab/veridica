# ADR 0007: los fragmentos sin asignatura declarada no se cargan en la base

- **Fecha:** 12 de agosto de 2026
- **Encargo:** 2.1 (decidido ANTES de migrar, no descubierto al cargar)
- **Estado:** aceptada

## Contexto

El índice tiene 11.483 fragmentos y su campo `asignatura` es un slug de carpeta o una sigla del
material. La base los quiere por `asignatura_id`, que sale del árbol oficial del BOE. El mapa
`corpus/mapa_asignaturas.jsonl` traduce las 31 parejas `(titulación de la carpeta, slug)` a
`(titulación dueña, código)`, una a una y con su evidencia.

**Tres parejas no se pueden traducir sin inventarse el código**, y suman **201 fragmentos**
(el 1,8 % del índice):

| Pareja | Fragmentos | Qué es |
|---|---:|---|
| `asir/` (slug vacío) | 118 | ficheros sueltos en la raíz del repositorio `lora-2asir`, sin carpeta de asignatura |
| `asir/hlc` | 71 | "horas de libre configuración" del centro: no es un módulo del RD 1629/2009 |
| `asir/talleres` | 12 | carpeta `Talleres` del mismo repositorio, que no corresponde a ningún módulo |

Son material técnico legítimo (OpenStack, ZFS, iSCSI, Docker): el problema no es su calidad, es que
**de qué módulo son no consta**, y en este proyecto eso no se deduce por lo que hablan (misma regla
que el `curso` nulo de DAM y ASIR).

## Decisión

**No se cargan.** El mapa los marca `excluido` con su motivo, el cargador los cuenta y los declara,
y `corpus/COBERTURA.md` lleva el número.

**El motivo es la alcanzabilidad, no la contaminación.** El selector del alumno lista asignaturas
por la puente `titulacion_asignaturas`; una partición que no está en ninguna asignatura del árbol no
la puede elegir nadie, así que **ningún alumno llegaría jamás a esos fragmentos**. Cargarlos sería
peso muerto: infla los conteos, obliga a explicar una partición huérfana en cada verificación y no
compra nada. Y conviene decir lo que **no** es el motivo: una partición residual que el filtro nunca
selecciona tampoco contaminaría los resultados del 3.5, así que el argumento de la contaminación
—que es el que se me ocurrió primero— no se sostiene.

## Alternativa descartada, escrita para que nadie la reabra sin encontrar el porqué

**Partición residual declarada** (`asir-sin-modulo-declarado`), cargada pero no mapeada en la puente.
Tiene una ventaja real: el conteo de la base cuadraría con el del índice sin restas, y el material
quedaría a un `UPDATE` de distancia si mañana alguien declara su módulo. Se descarta porque
introduce una asignatura que no existe en ninguna norma dentro de la tabla cuya razón de ser es
tener referencia legal por fila, y porque obliga a que **toda** consulta y **toda** verificación
lleve para siempre su excepción — el coste no es cargarla, es acordarse de ella cada vez.

## Trade-off

Se pierde el 1,8 % del material del índice en la base, y la resta 11.483 − 201 = 11.282 hay que
explicarla cada vez que alguien compare los dos números; por eso está escrita aquí y en COBERTURA.
A cambio, **toda fila de `fragmentos` tiene una asignatura con código del BOE detrás**, que es la
propiedad de la que dependen el filtro por titulación, la puente de transversales y la medida de
contaminación cruzada.

**La exclusión es de CARGA, no de esquema:** revertirla es declarar las tres parejas en el mapa y
volver a cargar, sin tocar ninguna migración.
