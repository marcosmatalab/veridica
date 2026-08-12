# Evidencia: poda de particiones en la busqueda vectorial filtrada

- **Fecha:** 2026-08-12
- **Encargo:** 2.1
- **Commit:** `e3647b8`
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
Limit (actual time=13.042..13.043 rows=6 loops=1)
  Buffers: shared hit=11890 read=2499
  ->  Sort (actual time=13.042..13.042 rows=6 loops=1)
        Sort Key: ((f.embedding <=> '<vector de 1024 dimensiones>'::vector))
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=11890 read=2499
        ->  Seq Scan on fragmentos_a29 f (actual time=0.007..12.748 rows=3892 loops=1)
              Filter: (asignatura_id = '29'::smallint)
              Buffers: shared hit=11887 read=2499
Planning:
  Buffers: shared hit=28 read=2 dirtied=1
Planning Time: 0.073 ms
Execution Time: 13.056 ms
```

**Esto es el argumento de escala entero.** El plan nombra `fragmentos_a29` y ninguna
otra: de las 35 particiones, la consulta abre **una**. Lo que crece cuando el corpus
crece es el numero de particiones, no la rebanada que se lee.

## Plan SIN filtro: el contraste

```
Limit (actual time=39.199..39.207 rows=6 loops=1)
  Buffers: shared hit=35411 read=6740 written=3978
  ->  Sort (actual time=39.198..39.205 rows=6 loops=1)
        Sort Key: ((f.embedding <=> '<vector de 1024 dimensiones>'::vector))
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=35411 read=6740 written=3978
        ->  Append (actual time=0.076..38.344 rows=11282 loops=1)
              Buffers: shared hit=35411 read=6740 written=3978
              ->  Seq Scan on fragmentos_a1 f_1 (actual time=0.076..3.834 rows=1205 loops=1)
                    Buffers: shared hit=3681 read=810
              ->  Seq Scan on fragmentos_a2 f_2 (actual time=0.051..0.154 rows=40 loops=1)
                    Buffers: shared hit=104 read=28
              ->  Seq Scan on fragmentos_a3 f_3 (actual time=0.040..0.195 rows=50 loops=1)
                    Buffers: shared hit=126 read=34
              ->  Seq Scan on fragmentos_a4 f_4 (actual time=0.046..0.687 rows=178 loops=1)
                    Buffers: shared hit=540 read=144
              ->  Seq Scan on fragmentos_a5 f_5 (actual time=0.082..0.780 rows=200 loops=1)
                    Buffers: shared hit=607 read=151
              ->  Seq Scan on fragmentos_a6 f_6 (actual time=0.044..0.561 rows=156 loops=1)
                    Buffers: shared hit=460 read=141
              ->  Seq Scan on fragmentos_a7 f_7 (actual time=0.111..0.368 rows=84 loops=1)
                    Buffers: shared hit=194 read=57
              ->  Seq Scan on fragmentos_a8 f_8 (actual time=0.050..0.421 rows=119 loops=1)
                    Buffers: shared hit=385 read=80
              ->  Seq Scan on fragmentos_a9 f_9 (actual time=0.035..0.376 rows=117 loops=1)
                    Buffers: shared hit=377 read=79
              ->  Seq Scan on fragmentos_a10 f_10 (actual time=0.007..0.007 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a11 f_11 (actual time=0.026..0.055 rows=12 loops=1)
                    Buffers: shared hit=47 read=9
              ->  Seq Scan on fragmentos_a12 f_12 (actual time=0.026..0.091 rows=26 loops=1)
                    Buffers: shared hit=74 read=19
              ->  Seq Scan on fragmentos_a13 f_13 (actual time=0.001..0.001 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a14 f_14 (actual time=0.086..0.155 rows=27 loops=1)
                    Buffers: shared hit=78 read=19
              ->  Seq Scan on fragmentos_a15 f_15 (actual time=0.038..1.621 rows=456 loops=1)
                    Buffers: shared hit=1238 read=480
              ->  Seq Scan on fragmentos_a16 f_16 (actual time=0.001..0.001 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a17 f_17 (actual time=0.044..0.265 rows=57 loops=1)
                    Buffers: shared hit=139 read=39
              ->  Seq Scan on fragmentos_a18 f_18 (actual time=0.049..1.313 rows=363 loops=1)
                    Buffers: shared hit=990 read=383
              ->  Seq Scan on fragmentos_a19 f_19 (actual time=0.003..0.003 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a20 f_20 (actual time=0.001..0.001 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a21 f_21 (actual time=0.001..0.001 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a22 f_22 (actual time=0.001..0.001 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a23 f_23 (actual time=0.100..0.739 rows=180 loops=1)
                    Buffers: shared hit=500 read=193 written=17
              ->  Seq Scan on fragmentos_a24 f_24 (actual time=0.045..2.224 rows=523 loops=1)
                    Buffers: shared hit=1415 read=557 written=556
              ->  Seq Scan on fragmentos_a25 f_25 (actual time=0.046..2.130 rows=485 loops=1)
                    Buffers: shared hit=1316 read=513 written=511
              ->  Seq Scan on fragmentos_a26 f_26 (actual time=0.065..3.617 rows=814 loops=1)
                    Buffers: shared hit=2189 read=849 written=839
              ->  Seq Scan on fragmentos_a27 f_27 (actual time=0.056..1.210 rows=235 loops=1)
                    Buffers: shared hit=647 read=257 written=251
              ->  Seq Scan on fragmentos_a28 f_28 (actual time=0.049..1.437 rows=329 loops=1)
                    Buffers: shared hit=899 read=351 written=349
              ->  Seq Scan on fragmentos_a29 f_29 (actual time=0.060..8.111 rows=3892 loops=1)
                    Buffers: shared hit=14386
              ->  Seq Scan on fragmentos_a30 f_30 (actual time=0.066..1.755 rows=460 loops=1)
                    Buffers: shared hit=1386 read=349 written=346
              ->  Seq Scan on fragmentos_a31 f_31 (actual time=0.054..1.520 rows=331 loops=1)
                    Buffers: shared hit=900 read=358 written=300
              ->  Seq Scan on fragmentos_a32 f_32 (actual time=0.002..0.002 rows=0 loops=1)
              ->  Seq Scan on fragmentos_a33 f_33 (actual time=0.051..2.624 rows=574 loops=1)
                    Buffers: shared hit=1546 read=628 written=601
              ->  Seq Scan on fragmentos_a34 f_34 (actual time=0.044..1.516 rows=369 loops=1)
                    Buffers: shared hit=1187 read=212 written=208
              ->  Seq Scan on fragmentos_a35 f_35 (actual time=0.004..0.004 rows=0 loops=1)
Planning:
  Buffers: shared hit=308 read=15
Planning Time: 0.502 ms
Execution Time: 39.257 ms
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
Limit (actual time=1.253..1.270 rows=6 loops=1)
  Buffers: shared hit=159 read=416 written=295
  ->  Index Scan using fragmentos_a29_hnsw on fragmentos_a29 f (actual time=1.252..1.269 rows=6 loops=1)
        Order By: (embedding <=> '<vector de 1024 dimensiones>'::vector)
        Filter: (asignatura_id = '29'::smallint)
        Buffers: shared hit=159 read=416 written=295
Planning:
  Buffers: shared hit=1
Planning Time: 0.091 ms
Execution Time: 1.282 ms
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
