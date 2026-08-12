# ADR 0008: en `documentos`, el hash NO es único; la ruta sí

- **Fecha:** 12 de agosto de 2026
- **Encargo:** 2.1 (se corrigen aquí la sección 9 **y la sección 10** de la guía; alcance completo al final)
- **Estado:** aceptada

## Contexto

El DDL de la sección 9 declara `hash_sha256 char(64) NOT NULL UNIQUE` en `documentos`. Suena
razonable —el mismo contenido no debería entrar dos veces— y en la fase 1 hay hasta una regla que lo
apoya, la de *un documento, una fuente*, que evita normalizar el PDF y su gemelo `.odt`.

Al preparar la carga, **29 grupos de documentos comparten hash** (69 documentos, 253 fragmentos).
Y entre ellos está este:

```
plantado=False  corpus/derivado/daw/curso1/bases-de-datos/comesana/BD05.pdf.md
plantado=True   corpus/daw/curso1/programacion/.../BD05_modelo_relacional.md   (motivo: colado)
```

Ese par **no es un accidente: es el encargo 1.7**. El documento colado se planta para medir
contaminación cruzada, y ser una copia exacta de un documento de otra asignatura es exactamente lo
que lo hace útil. Con el UNIQUE, la carga tendría que tirar uno de los dos, y con él, el instrumento
con el que el 3.5 mide contaminación.

Los otros 28 grupos son duplicación real del material de origen: artefactos de compilación
(`obj/Debug/*.g.cs`), dos proyectos de ejemplo de DWES que comparten la mitad de sus clases, y cinco
tutoriales `00-XaY.md` con el mismo contenido y distinto nombre.

## Decisión

**`UNIQUE (ruta)` en lugar de `UNIQUE (hash_sha256)`**, más un índice **no único** sobre el hash.

Lo que identifica a un documento es su **ruta**: es la clave del manifiesto —"una entrada por
fichero", el invariante sobre el que se apoya la puerta del 1.0— y es lo que se le cita a un alumno.
El contenido repetido es un **hallazgo que se mide**, no una condición que se impone: de eso ya se
encarga el detector de conflictos del 1.8, que los marca como casi duplicados y los cuenta.

Una restricción que obliga a **borrar datos para poder cargarlos** está resolviendo el problema en
el sitio equivocado.

## Alcance: todo lo que declaraba el hash como identidad

Esta decisión no se agota en una restricción del DDL. **Cualquier sitio que use el hash para decir
"esto ya está" hereda el mismo error**, así que se listan aquí los tres, y también lo que NO cambia:

| Dónde | Decía | Dice |
|---|---|---|
| Sección 9, DDL de `documentos` | `hash_sha256 ... UNIQUE` | `UNIQUE (ruta)` + índice **no** único sobre el hash |
| Sección 10, `POST /ingesta/documento` | "idempotente por `hash_sha256`" | idempotente por el par **`(ruta, hash_sha256)`** |
| Encargo 2.3, colas | "clave de deduplicación" sin definir | esa clave **es** el par `(ruta, hash_sha256)` |

La regla que los une: **la ruta dice de qué documento hablamos, el hash dice si ha cambiado.** Con
las dos, la ingesta re-procesa una versión nueva y salta una repetida, sin confundir dos documentos
distintos que casualmente coinciden. Con el hash solo, la segunda ingesta del colado del 1.7 se
descartaría en silencio y el 3.5 se quedaría sin instrumento; con la ruta sola, editar un fichero no
dispararía nada.

**Lo que no cambia, y conviene decirlo para que nadie lo "corrija" de rebote:** el verificador del
manifiesto (1.0) sigue comprobando el hash **de cada ruta**, porque ahí el hash no es identidad sino
integridad; `scripts/reparar_nombres.py` sigue emparejando por hash de contenido, porque su problema
era justo el contrario —el nombre estaba destrozado y el contenido era lo único fiable—; y el
detector de casi duplicados del 1.8 sigue contando el contenido repetido como **hallazgo medido**,
que es el sitio correcto para tratarlo.

## Trade-off

Se pierde la garantía automática de "no hay contenido repetido en la base", que nunca fue verdad en
este corpus. A cambio, la carga es fiel al árbol de ficheros y el material plantado sobrevive.

**Deuda declarada, que sale de aquí:** los 25 documentos de `obj/Debug/` son salida de compilación,
no material docente, y están en el índice porque la puerta de admisión **nunca juzga código con
reglas de prosa** —regla correcta, que aquí deja pasar ficheros generados—. No se arregla ahora: el
corpus está cerrado y la fase 1 también. Cuando se reabra, van a la lista de exclusión manual.
