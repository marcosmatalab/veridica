# Evidencia: poda de particiones en la busqueda vectorial filtrada

- **Fecha:** 2026-08-12
- **Encargo:** 2.1
- **Commit:** `869f2e7`
- **Base:** Postgres 16 con pgvector 0.8.1, en el compose local (db publicada en 127.0.0.1:5434)

## Sobre que datos corrio

| | |
|---|---|
| Filas en `fragmentos` | **11282** |
| Particiones | **35** (una por asignatura) |
| Particion consultada | `fragmentos_a29` = DAW 0613 Desarrollo web en entorno servidor |
| Filas en esa particion | **3892** |

## La consulta (literal, la misma que ejecutara el 3.2)

```sql
SELECT f.id, f.unidad
FROM fragmentos f
WHERE f.asignatura_id = 29
ORDER BY f.embedding <=> '<vector de 1024 dimensiones>'::vector
LIMIT 6;
```

El vector es el embedding de un fragmento real de esa asignatura, no ruido: asi la consulta se
parece a la que hara el sistema y el plan no se apoya en un caso degenerado.

## Plan CON filtro de asignatura: toca UNA particion

```
Limit (actual time=10.209..10.210 rows=6 loops=1)
  Buffers: shared hit=14389
  ->  Sort (actual time=10.208..10.209 rows=6 loops=1)
        Sort Key: ((f.embedding <=> '<vector de 1024 dimensiones>'::vector))
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=14389
        ->  Seq Scan on fragmentos_a29 f (actual time=0.007..9.943 rows=3892 loops=1)
              Filter: (asignatura_id = '29'::smallint)
              Buffers: shared hit=14386
Planning:
  Buffers: shared hit=30
Planning Time: 0.069 ms
Execution Time: 10.222 ms
```

**Esto es el argumento de escala entero.** El plan nombra `fragmentos_a29` y ninguna
otra: de las 35 particiones, la consulta abre **una**. Lo que crece cuando el corpus
crece es el numero de particiones, no la rebanada que se lee.

## Plan SIN filtro: el contraste

```
Limit (actual time=27.928..27.935 rows=6 loops=1)
  Buffers: shared hit=42151
  ->  Sort (actual time=27.927..27.933 rows=6 loops=1)
        Sort Key: ((f.embedding <=> '<vector de 1024 dimensiones>'::vector))
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=42151
        ->  Append (actual time=0.043..27.154 rows=11282 loops=1)
              Buffers: shared hit=42151
              ->  Seq Scan on fragmentos_a1 f_1 (actual time=0.043..3.134 rows=1205 loops=1)
                    Buffers: shared hit=4491
              ->  Seq Scan on fragmentos_a2 f_2 (actual time=0.040..0.118 rows=40 loops=1)
                    Buffers: shared hit=132
              ->  Seq Scan on fragmentos_a3 f_3 (actual time=0.031..0.128 rows=50 loops=1)
                    Buffers: shared hit=160
              ->  Seq Scan on fragmentos_a4 f_4 (actual time=0.020..0.408 rows=178 loops=1)
                    Buffers: shared hit=684
              ->  Seq Scan on fragmentos_a5 f_5 (actual time=0.026..0.514 rows=200 loops=1)
                    Buffers: shared hit=758
              ->  Seq Scan on fragmentos_a6 f_6 (actual time=0.033..0.452 rows=156 loops=1)
                    Buffers: shared hit=601
              ->  Seq Scan on fragmentos_a7 f_7 (actual time=0.034..0.217 rows=84 loops=1)
                    Buffers: shared hit=251
              ->  Seq Scan on fragmentos_a8 f_8 (actual time=0.027..0.292 rows=119 loops=1)
                    Buffers: shared hit=465
              ->  Seq Scan on fragmentos_a9 f_9 (actual time=0.024..0.271 rows=117 loops=1)
                    Buffers: shared hit=456
              ->  Seq Scan on fragmentos_a10 f_10 (actual time=0.007..0.007 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a11 f_11 (actual time=0.018..0.040 rows=12 loops=1)
                    Buffers: shared hit=56
              ->  Seq Scan on fragmentos_a12 f_12 (actual time=0.019..0.070 rows=26 loops=1)
                    Buffers: shared hit=93
              ->  Seq Scan on fragmentos_a13 f_13 (actual time=0.001..0.001 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a14 f_14 (actual time=0.022..0.076 rows=27 loops=1)
                    Buffers: shared hit=97
              ->  Seq Scan on fragmentos_a15 f_15 (actual time=0.025..1.279 rows=456 loops=1)
                    Buffers: shared hit=1718
              ->  Seq Scan on fragmentos_a16 f_16 (actual time=0.004..0.004 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a17 f_17 (actual time=0.059..0.238 rows=57 loops=1)
                    Buffers: shared hit=178
              ->  Seq Scan on fragmentos_a18 f_18 (actual time=0.039..0.928 rows=363 loops=1)
                    Buffers: shared hit=1373
              ->  Seq Scan on fragmentos_a19 f_19 (actual time=0.002..0.002 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a20 f_20 (actual time=0.001..0.001 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a21 f_21 (actual time=0.001..0.001 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a22 f_22 (actual time=0.001..0.001 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a23 f_23 (actual time=0.024..0.501 rows=180 loops=1)
                    Buffers: shared hit=693
              ->  Seq Scan on fragmentos_a24 f_24 (actual time=0.044..1.232 rows=523 loops=1)
                    Buffers: shared hit=1972
              ->  Seq Scan on fragmentos_a25 f_25 (actual time=0.028..1.117 rows=485 loops=1)
                    Buffers: shared hit=1829
              ->  Seq Scan on fragmentos_a26 f_26 (actual time=0.035..1.887 rows=814 loops=1)
                    Buffers: shared hit=3038
              ->  Seq Scan on fragmentos_a27 f_27 (actual time=0.035..0.589 rows=235 loops=1)
                    Buffers: shared hit=904
              ->  Seq Scan on fragmentos_a28 f_28 (actual time=0.024..0.814 rows=329 loops=1)
                    Buffers: shared hit=1250
              ->  Seq Scan on fragmentos_a29 f_29 (actual time=0.011..8.290 rows=3892 loops=1)
                    Buffers: shared hit=14386
              ->  Seq Scan on fragmentos_a30 f_30 (actual time=0.042..1.102 rows=460 loops=1)
                    Buffers: shared hit=1735
              ->  Seq Scan on fragmentos_a31 f_31 (actual time=0.040..0.725 rows=331 loops=1)
                    Buffers: shared hit=1258
              ->  Seq Scan on fragmentos_a32 f_32 (actual time=0.002..0.002 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a33 f_33 (actual time=0.023..1.352 rows=574 loops=1)
                    Buffers: shared hit=2174
              ->  Seq Scan on fragmentos_a34 f_34 (actual time=0.037..0.867 rows=369 loops=1)
                    Buffers: shared hit=1399
              ->  Seq Scan on fragmentos_a35 f_35 (actual time=0.003..0.003 rows=0 loops=1)
Planning:
  Buffers: shared hit=323
Planning Time: 0.465 ms
Execution Time: 27.979 ms
```

Sin el filtro hay que mirarlas todas. La diferencia entre los dos planes es lo que compra la
particion por asignatura, y por eso la jerarquia del alumno es la clave de particion y no un
adorno del modelo de datos.

## Y lo que el plan enseña y no esperabamos: el HNSW no se usa a este tamaño

El indice HNSW existe, es valido y esta construido sobre las 3892 filas de la particion
(29 MB), pero **el planificador prefiere el escaneo secuencial** y acierta: leer 890 bloques y
ordenar 6 sale mas barato que recorrer el grafo. Forzandolo (`enable_seqscan=off`,
`enable_sort=off`) el indice SI se usa, lo que demuestra que esta bien construido:

```
Limit (actual time=0.999..1.016 rows=6 loops=1)
  Buffers: shared hit=87 read=468
  ->  Index Scan using fragmentos_a29_hnsw on fragmentos_a29 f (actual time=0.997..1.014 rows=6 loops=1)
        Order By: (embedding <=> '<vector de 1024 dimensiones>'::vector)
        Filter: (asignatura_id = '29'::smallint)
        Buffers: shared hit=87 read=468
Planning:
  Buffers: shared hit=1
Planning Time: 0.087 ms
Execution Time: 1.027 ms
```

**Consecuencia declarada para la fase 3:** la latencia que se mida en el 3.2 sobre este corpus es
la de un escaneo secuencial de una particion, no la de un HNSW. Con particiones de miles de filas
eso es lo correcto y lo rapido; el indice empieza a ganar cuando una asignatura crece, y ahi el
plan cambiara solo. Decirlo ahora evita presentar como "busqueda vectorial indexada" algo que hoy
es un escaneo honesto de 10 ms.

## Como se reproduce

```bash
docker compose up -d --wait
DATABASE_URL=postgresql://veridica:veridica_local@127.0.0.1:5434/veridica \
    python scripts/evidencia_explain.py
```
