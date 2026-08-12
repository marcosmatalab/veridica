# ADR 0008: en `documentos`, el hash NO es único; la ruta sí

- **Fecha:** 12 de agosto de 2026
- **Encargo:** 2.1 (el DDL de referencia de la sección 9 se corrige aquí)
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

## Trade-off

Se pierde la garantía automática de "no hay contenido repetido en la base", que nunca fue verdad en
este corpus. A cambio, la carga es fiel al árbol de ficheros y el material plantado sobrevive.

**Deuda declarada, que sale de aquí:** los 25 documentos de `obj/Debug/` son salida de compilación,
no material docente, y están en el índice porque la puerta de admisión **nunca juzga código con
reglas de prosa** —regla correcta, que aquí deja pasar ficheros generados—. No se arregla ahora: el
corpus está cerrado y la fase 1 también. Cuando se reabra, van a la lista de exclusión manual.
