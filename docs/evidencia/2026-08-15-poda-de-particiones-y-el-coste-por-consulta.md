# Evidencia: el coste por consulta no crece con el corpus (y dónde deja de ser verdad)

**Fecha:** 15 de agosto de 2026 · **Base:** Postgres 16 + pgvector, `fragmentos` particionada por
asignatura (**35** particiones, 11.483 fragmentos) · **Medido con** `EXPLAIN (ANALYZE, BUFFERS)`
dentro del contenedor `db`, con un vector literal en el `ORDER BY`.

## Por qué esta medida y no la extrapolación

El argumento de escala de este proyecto **no es** "hemos calculado que un tera daría 28,8 millones
de fragmentos". Eso es una estimación, y una estimación no dice nada sobre si el sistema aguanta.
El argumento es más simple y es comprobable: **una consulta va siempre acotada a una asignatura, y
la tabla está particionada por asignatura, así que la consulta nunca lee el corpus — lee una
partición.** Lo que crece cuando crece el corpus es el **número** de particiones, no la rebanada que
se lee. Eso se enseña con el plan delante.

## La medida

| Filtro que manda el código | Particiones leídas (de 35) | Bloques | Tiempo |
|---|---:|---:|---:|
| **Una asignatura** — `f.asignatura_id = 29` | **1** | 14.412 | **9,8 ms** |
| Trece (lista literal) — el paso de *elegir asignatura* | **13** | 30.663 | 21,3 ms |
| Trece **por subconsulta** — `IN (SELECT … )` | **35** | 31.801 | 22,3 ms |
| Sin filtro | 35 | 41.895 | 25,8 ms |

La primera fila es el camino normal: **de 35 particiones se abre una.** El corpus podría tener mil
asignaturas y esa consulta seguiría leyendo una.

## LA TERCERA FILA ES EL HALLAZGO, y es de la familia del instrumento que miente

**La poda no la da el `WHERE`: la da que el planificador pueda RESOLVER el filtro antes de elegir el
plan.** Con una lista literal de trece ids poda a trece; con la **misma** lista traída por una
subconsulta (`IN (SELECT asignatura_id FROM titulacion_asignaturas WHERE titulacion='daw')`) el
planificador no sabe todavía qué ids van a salir, **abre las 35** y filtra después. Mismo resultado,
mismo `WHERE` aparente, **35 particiones en vez de 13**.

Nuestro código está en la fila buena y **no por casualidad**: `recuperacion.asignaturas_de()`
materializa la lista en Python y la manda como parámetro (`AND f.asignatura_id = ANY(%(asignaturas)s)`),
así que el plan la ve. **Si alguien "simplifica" eso a un `IN (SELECT …)` para ahorrarse una consulta,
la poda se apaga sin que nada se ponga rojo**: la respuesta es idéntica y solo cambia el plan. Es
exactamente la avería de siempre —el aparato deja de medir lo que su nombre dice y no avisa—, aquí
dentro del planificador.

## El coste del paso nuevo, declarado

Desde el 15/08 la asignatura **no es obligatoria**: si no viene elegida, se hace una búsqueda ancha
sobre las asignaturas de la titulación **solo para quedarse con la etiqueta del primer candidato**, y
después corre la recuperación normal dentro de esa asignatura. O sea que una consulta sin asignatura
elegida paga **13 particiones (21,3 ms) una vez** y a partir de ahí es la consulta de siempre. Se
dice porque es una regresión real de latencia en el camino por defecto, medida y aceptada: 21 ms
sobre un presupuesto de 8.000.

## DÓNDE DEJA DE VALER ESTE ARGUMENTO, que es lo que lo hace creíble

**Hoy la búsqueda vectorial es un escaneo secuencial honesto**, no un HNSW. El índice HNSW existe y
es válido, y **el planificador no lo usa** a este tamaño: ordenar 6 filas de 3.892 sale más barato
que recorrer el grafo, y acierta (forzándolo baja a 1,3 ms, que es la prueba de que está bien
construido).

A la escala de la extrapolación —**28,8 millones de fragmentos por TB**— eso deja de ser cierto: con
particiones de cientos de miles de vectores el escaneo secuencial ya no vale y **el índice vectorial
tendría que configurarse de verdad (IVFFlat, o HNSW con `m` y `ef_construction` afinados)**. pgvector
lo soporta y **aquí no está configurado, porque con 11.483 vectores no hace falta**. La poda de
particiones seguiría dando lo que da —una consulta lee una partición— pero *dentro* de esa partición
habría que buscar de otra manera.

## Cómo reproducirlo

```bash
docker compose exec -T db psql -U veridica -d veridica -f - < scripts/sql/poda_de_particiones.sql
```

Se cuentan los `Seq Scan on fragmentos_aNN` que **no** dicen `never executed`: esa es la cifra de
particiones leídas de verdad, y no la que el `WHERE` sugiere.
