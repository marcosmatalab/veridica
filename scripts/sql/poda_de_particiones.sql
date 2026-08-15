-- LA PODA DE PARTICIONES, MEDIDA Y NO SUPUESTA.
--
-- Lo que se lee NO es el `WHERE`: es cuantos `Seq Scan on fragmentos_aNN` salen SIN el
-- `never executed`. Un plan que abre las 35 y filtra despues devuelve exactamente el mismo
-- resultado que uno que abre una, asi que la unica forma de saber cual de los dos corrio es
-- mirar el plan. Ver docs/evidencia/2026-08-15-poda-de-particiones-y-el-coste-por-consulta.md
\set QUIET on
\pset pager off
\pset tuples_only on

SELECT embedding::text AS v FROM fragmentos WHERE embedding IS NOT NULL LIMIT 1 \gset e_
SELECT id AS id FROM asignaturas WHERE codigo = '0613' \gset a_
SELECT '{' || string_agg(asignatura_id::text, ',') || '}' AS ids
  FROM titulacion_asignaturas WHERE titulacion = 'daw' \gset daw_

\echo ===UNA=== el camino normal: una asignatura elegida
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT f.id FROM fragmentos f WHERE f.asignatura_id = :a_id
 ORDER BY f.embedding <=> :'e_v'::vector LIMIT 6;

\echo ===TRECE_LISTA=== el paso de elegir asignatura, como lo manda el codigo
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT f.id FROM fragmentos f WHERE f.asignatura_id = ANY (:'daw_ids'::int[])
 ORDER BY f.embedding <=> :'e_v'::vector LIMIT 6;

\echo ===TRECE_SUBCONSULTA=== el mismo filtro que APAGA la poda: 35 particiones
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT f.id FROM fragmentos f
 WHERE f.asignatura_id IN (SELECT asignatura_id FROM titulacion_asignaturas WHERE titulacion = 'daw')
 ORDER BY f.embedding <=> :'e_v'::vector LIMIT 6;

\echo ===TODAS=== sin filtro
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT f.id FROM fragmentos f ORDER BY f.embedding <=> :'e_v'::vector LIMIT 6;
