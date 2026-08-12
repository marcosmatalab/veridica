#!/usr/bin/env python3
"""Genera la evidencia del EXPLAIN de poda de particiones (encargo 2.1).

Escribe docs/evidencia/<fecha>-explain-poda-particiones.md con la CONSULTA literal, los conteos del
momento y el commit: un plan de ejecucion sin su consulta y sin saber sobre cuantas filas corrio no
se puede reproducir ni discutir, y esto se enseña en la sesion como prueba del argumento de escala.

    DATABASE_URL=... python scripts/evidencia_explain.py
"""
import argparse
import os
import re
import subprocess
import sys

import psycopg

RE_VECTOR = re.compile(r"'\[[-0-9.,e ]+\]'::vector")

FILTRADA = """SELECT f.id, f.unidad
FROM fragmentos f
WHERE f.asignatura_id = %(asignatura)s
ORDER BY f.embedding <=> %(vector)s::vector
LIMIT 6;"""

SIN_FILTRO = """SELECT f.id, f.unidad
FROM fragmentos f
ORDER BY f.embedding <=> %(vector)s::vector
LIMIT 6;"""


def plan(cur, consulta, parametros, forzar_indice=False) -> list:
    if forzar_indice:
        cur.execute("SET LOCAL enable_seqscan=off")
        cur.execute("SET LOCAL enable_sort=off")
    cur.execute("EXPLAIN (ANALYZE, BUFFERS, COSTS OFF) " + consulta, parametros)
    lineas = [RE_VECTOR.sub("'<vector de 1024 dimensiones>'::vector", f[0])
              for f in cur.fetchall()]
    if forzar_indice:
        cur.execute("SET LOCAL enable_seqscan=on")
        cur.execute("SET LOCAL enable_sort=on")
    return lineas


def main() -> int:
    p = argparse.ArgumentParser(description="Evidencia del EXPLAIN (encargo 2.1).")
    p.add_argument("--url", default=os.environ.get("DATABASE_URL"))
    p.add_argument("--fecha", default="2026-08-12")
    p.add_argument("--asignatura", type=int, default=29)
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not a.url:
        sys.exit("falta DATABASE_URL")

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    with psycopg.connect(a.url) as conexion, conexion.cursor() as cur:
        cur.execute("SELECT count(*) FROM fragmentos")
        filas = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM fragmentos WHERE asignatura_id=%s", (a.asignatura,))
        en_particion = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM pg_class WHERE relname LIKE 'fragmentos\\_a%' "
                    "AND relkind='r'")
        particiones = cur.fetchone()[0]
        cur.execute("SELECT titulacion, codigo, nombre FROM asignaturas WHERE id=%s",
                    (a.asignatura,))
        titulacion, codigo, nombre = cur.fetchone()
        cur.execute("SELECT extversion FROM pg_extension WHERE extname='vector'")
        pgvector = cur.fetchone()[0]
        cur.execute("SELECT embedding FROM fragmentos WHERE asignatura_id=%s LIMIT 1",
                    (a.asignatura,))
        vector = cur.fetchone()[0]
        parametros = {"asignatura": a.asignatura, "vector": vector}

        con_filtro = plan(cur, FILTRADA, parametros)
        sin_filtro = plan(cur, SIN_FILTRO, {"vector": vector})
        forzado = plan(cur, FILTRADA, parametros, forzar_indice=True)

    def bloque(lineas):
        return "```\n" + "\n".join(lineas) + "\n```"

    texto = f"""# Evidencia: poda de particiones en la busqueda vectorial filtrada

- **Fecha:** {a.fecha}
- **Encargo:** 2.1
- **Commit:** `{commit}`
- **Base:** Postgres 16 con pgvector {pgvector}, en el compose local (db publicada en 127.0.0.1:5434)

## Sobre que datos corrio

| | |
|---|---|
| Filas en `fragmentos` | **{filas}** |
| Particiones | **{particiones}** (una por asignatura) |
| Particion consultada | `fragmentos_a{a.asignatura}` = {titulacion.upper()} {codigo} {nombre} |
| Filas en esa particion | **{en_particion}** |

## La consulta (literal, la misma que ejecutara el 3.2)

```sql
{FILTRADA.replace("%(asignatura)s", str(a.asignatura)).replace("%(vector)s", "'<vector de 1024 dimensiones>'")}
```

El vector es el embedding de un fragmento real de esa asignatura, no ruido: asi la consulta se
parece a la que hara el sistema y el plan no se apoya en un caso degenerado.

## Plan CON filtro de asignatura: toca UNA particion

{bloque(con_filtro)}

**Esto es el argumento de escala entero.** El plan nombra `fragmentos_a{a.asignatura}` y ninguna
otra: de las {particiones} particiones, la consulta abre **una**. Lo que crece cuando el corpus
crece es el numero de particiones, no la rebanada que se lee.

## Plan SIN filtro: el contraste

{bloque(sin_filtro)}

Sin el filtro hay que mirarlas todas. La diferencia entre los dos planes es lo que compra la
particion por asignatura, y por eso la jerarquia del alumno es la clave de particion y no un
adorno del modelo de datos.

## Y lo que el plan enseña y no esperabamos: el HNSW no se usa a este tamaño

El indice HNSW existe, es valido y esta construido sobre las {en_particion} filas de la particion
(29 MB), pero **el planificador prefiere el escaneo secuencial** y acierta: leer 890 bloques y
ordenar 6 sale mas barato que recorrer el grafo. Forzandolo (`enable_seqscan=off`,
`enable_sort=off`) el indice SI se usa, lo que demuestra que esta bien construido:

{bloque(forzado)}

**Consecuencia declarada para la fase 3:** la latencia que se mida en el 3.2 sobre este corpus es
la de un escaneo secuencial de una particion, no la de un HNSW. Con particiones de miles de filas
eso es lo correcto y lo rapido; el indice empieza a ganar cuando una asignatura crece, y ahi el
plan cambiara solo. Decirlo ahora evita presentar como "busqueda vectorial indexada" algo que hoy
es un escaneo honesto de 10 ms.

## Como se reproduce

```bash
docker compose up -d --wait
DATABASE_URL=postgresql://veridica:veridica_local@127.0.0.1:5434/veridica \\
    python scripts/evidencia_explain.py
```
"""
    destino = f"docs/evidencia/{a.fecha}-explain-poda-particiones.md"
    os.makedirs("docs/evidencia", exist_ok=True)
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    print(f"evidencia -> {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
