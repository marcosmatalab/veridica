#!/usr/bin/env python3
"""Encargo 2.1: carga el arbol oficial, los documentos y los fragmentos con sus vectores.

Corre desde Windows contra el contenedor (por eso la db esta publicada en 127.0.0.1:5434):

    DATABASE_URL=postgresql://veridica:veridica_local@127.0.0.1:5434/veridica \\
        python scripts/cargar_base.py

LO QUE ESTE FICHERO NO HACE, Y ES SU DECISION MAS IMPORTANTE: no casa los vectores por POSICION DE
FILA. La carga es de un SUBCONJUNTO -11.282 de los 11.483 embebidos, porque 201 no tienen asignatura
declarada (ADR 0007)-, asi que leer el .npy en orden y pegarlo a los fragmentos que entran daria un
desplazamiento a partir del primer hueco: cada vector quedaria pegado a OTRO fragmento, la base
tendria el numero de filas correcto y nada protestaria. Es el mismo fallo que ya tuvo el reanudador
de embeddings y que hoy tapa con salida 2. Aqui cada vector se busca por su CLAVE (documento, orden)
en ids.jsonl, y si falta una, se para.

Las particiones se crean ANTES de cargar y los indices DESPUES: construir un HNSW vacio y luego
insertar 11.282 filas cuesta mas que insertarlas y construirlo una vez, y ademas se puede medir.
"""
import argparse
import collections
import json
import os
import sys
import time

import numpy as np
import psycopg

FRAGMENTOS = "corpus/fragmentos.jsonl"
IDS = "corpus/embeddings/ids.jsonl"
VECTORES = "corpus/embeddings/vectores.npy"
ARBOL = "corpus/arbol_oficial.jsonl"
MAPA = "corpus/mapa_asignaturas.jsonl"
MANIFIESTO = "corpus/manifiesto.jsonl"


def leer_jsonl(ruta: str) -> list:
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def abortar(mensaje: str):
    print(f"CARGA ABORTADA: {mensaje}", file=sys.stderr)
    sys.exit(2)


# --- arbol y mapa ------------------------------------------------------------------------------

def asignaturas_a_cargar(arbol: list) -> tuple:
    """Devuelve (filas, puente). Los transversales se cargan UNA vez bajo su titulacion dueña.

    La dueña de los cinco transversales (0373, 0483, 0484, 0485, 0487) es DAW: es donde hay densidad
    completa y es la unica titulacion cuyo arbol trae curso y horas, porque solo de DAW tenemos
    orden de curriculo. Las otras dos los alcanzan por la puente.
    """
    duenas = {}
    for nodo in arbol:
        if nodo.get("nivel") != "asignatura":
            continue
        clave = nodo["codigo"]
        if clave in duenas:
            # Ya cargado bajo otra titulacion: transversal. Solo se anota en la puente.
            continue
        duenas[clave] = nodo
    filas = sorted(duenas.values(), key=lambda n: (n["titulacion"], n["codigo"]))
    puente = [(n["titulacion"], n["codigo"]) for n in arbol if n.get("nivel") == "asignatura"]
    return filas, puente


def cargar_mapa() -> dict:
    return {e["clave"]: e for e in leer_jsonl(MAPA)}


# --- vectores por clave, jamas por posicion ------------------------------------------------------

def vectores_por_clave() -> tuple:
    claves = leer_jsonl(IDS)
    matriz = np.load(VECTORES)
    if len(claves) != len(matriz):
        abortar(f"ids.jsonl tiene {len(claves)} claves y vectores.npy {len(matriz)} filas")
    indice = {(c["documento"], c["orden"]): i for i, c in enumerate(claves)}
    if len(indice) != len(claves):
        abortar("hay claves (documento, orden) repetidas en ids.jsonl: el casado seria ambiguo")
    return indice, matriz


def main() -> int:
    p = argparse.ArgumentParser(description="Carga el corpus en Postgres (encargo 2.1).")
    p.add_argument("--url", default=os.environ.get("DATABASE_URL"))
    p.add_argument("--sin-indices", action="store_true", help="no crea HNSW ni GIN (para pruebas)")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not a.url:
        abortar("falta DATABASE_URL")

    arbol = leer_jsonl(ARBOL)
    mapa = cargar_mapa()
    manifiesto = {e["ruta"]: e for e in leer_jsonl(MANIFIESTO)}
    fragmentos = leer_jsonl(FRAGMENTOS)
    indice_vec, matriz = vectores_por_clave()

    # Reparto por el mapa: o esta declarado, o esta excluido. No hay tercera opcion.
    admitidos, fuera = [], collections.Counter()
    for fr in fragmentos:
        clave = f"{fr['titulacion']}/{fr['asignatura']}"
        entrada = mapa.get(clave)
        if entrada is None:
            abortar(f"slug sin declarar en {MAPA}: {clave}. Se declara o se excluye, a mano.")
        if entrada.get("excluido"):
            fuera[clave] += 1
        else:
            admitidos.append((fr, entrada))
    print(f"fragmentos: {len(fragmentos)} | se cargan {len(admitidos)} | "
          f"fuera {sum(fuera.values())} (ADR 0007): {dict(fuera)}")

    with psycopg.connect(a.url, autocommit=False) as conexion, conexion.cursor() as cur:
        # 1) asignaturas y puente
        filas, puente = asignaturas_a_cargar(arbol)
        for n in filas:
            cur.execute(
                "INSERT INTO asignaturas (titulacion, curso, nombre, codigo) VALUES (%s,%s,%s,%s)"
                " ON CONFLICT (titulacion, codigo) DO NOTHING",
                (n["titulacion"], n.get("curso"), n["nombre"], n["codigo"]))
        cur.execute("SELECT id, titulacion, codigo FROM asignaturas")
        por_codigo = {(t, c): i for i, t, c in cur.fetchall()}
        for titulacion, codigo in puente:
            dueña = next(k for k in por_codigo if k[1] == codigo)
            cur.execute("INSERT INTO titulacion_asignaturas (titulacion, asignatura_id)"
                        " VALUES (%s,%s) ON CONFLICT DO NOTHING",
                        (titulacion, por_codigo[dueña]))
        print(f"asignaturas: {len(filas)} filas | puente: {len(puente)} mapeos")

        # 2) una particion por asignatura, ANTES de cargar
        for (titulacion, codigo), asignatura_id in sorted(por_codigo.items()):
            cur.execute(f"CREATE TABLE IF NOT EXISTS fragmentos_a{asignatura_id} "
                        f"PARTITION OF fragmentos FOR VALUES IN ({asignatura_id})")
        print(f"particiones creadas: {len(por_codigo)}")

        # 3) documentos
        vistos = {}
        for fr, entrada in admitidos:
            ruta = fr["documento"]
            if ruta in vistos:
                continue
            meta = manifiesto.get(ruta)
            if meta is None:
                abortar(f"documento sin entrada de manifiesto: {ruta}")
            asignatura_id = por_codigo[(entrada["titulacion_duena"], entrada["codigo"])]
            cur.execute(
                "INSERT INTO documentos (asignatura_id, unidad, titulo, fuente, licencia,"
                " version_corpus, hash_sha256, densidad, ruta) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                " RETURNING id",
                (asignatura_id, fr.get("unidad"), fr["contexto"].split(" · ")[-1][:200],
                 meta.get("fuente", ""), meta.get("licencia", ""), meta.get("version_corpus", ""),
                 meta["hash_sha256"], meta.get("densidad", "parcial"), ruta))
            vistos[ruta] = cur.fetchone()[0]
        print(f"documentos: {len(vistos)}")

        # 4) fragmentos con su vector BUSCADO POR CLAVE
        t0 = time.perf_counter()
        sin_vector = []
        with cur.copy("COPY fragmentos (documento_id, asignatura_id, unidad, orden,"
                      " tipo_contenido, texto, contexto, tokens, embedding) FROM STDIN") as copia:
            for fr, entrada in admitidos:
                fila = indice_vec.get((fr["documento"], fr["orden"]))
                if fila is None:
                    sin_vector.append((fr["documento"], fr["orden"]))
                    continue
                vector = "[" + ",".join(f"{v:.7g}" for v in matriz[fila]) + "]"
                copia.write_row((
                    vistos[fr["documento"]],
                    por_codigo[(entrada["titulacion_duena"], entrada["codigo"])],
                    fr.get("unidad"), fr["orden"], fr["tipo_contenido"], fr["texto"],
                    fr["contexto"], fr.get("tokens"), vector))
        if sin_vector:
            abortar(f"{len(sin_vector)} fragmentos sin vector en ids.jsonl, p.ej. {sin_vector[:3]}")
        print(f"fragmentos cargados en {time.perf_counter()-t0:.1f}s")

        cur.execute("UPDATE fragmentos SET tsv = to_tsvector('spanish', contexto || ' ' || texto)")
        print("tsv calculado")

        # 5) indices POR PARTICION, despues de cargar
        if not a.sin_indices:
            t1 = time.perf_counter()
            for asignatura_id in sorted(por_codigo.values()):
                cur.execute(f"CREATE INDEX IF NOT EXISTS fragmentos_a{asignatura_id}_hnsw ON "
                            f"fragmentos_a{asignatura_id} USING hnsw (embedding vector_cosine_ops)"
                            f" WITH (m=16, ef_construction=64)")
                cur.execute(f"CREATE INDEX IF NOT EXISTS fragmentos_a{asignatura_id}_gin ON "
                            f"fragmentos_a{asignatura_id} USING gin (tsv)")
            print(f"indices HNSW y GIN por particion en {time.perf_counter()-t1:.1f}s")
        conexion.commit()

    # ANALYZE fuera de la transaccion de carga y SIEMPRE: sin estadisticas, el planificador estima
    # a ciegas y el EXPLAIN que se guarda como evidencia no dice nada del sistema real, dice lo que
    # Postgres se imagina de una tabla que acaba de ver por primera vez.
    with psycopg.connect(a.url, autocommit=True) as conexion, conexion.cursor() as cur:
        cur.execute("ANALYZE fragmentos")
        cur.execute("ANALYZE documentos")
        print("ANALYZE hecho")

    print("\ncarga terminada. Comprobacion: python scripts/comprobar_carga.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
