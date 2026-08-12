#!/usr/bin/env python3
"""Comprobacion de la carga del 2.1. Salida 0 si todo cuadra, 1 si algo no.

Cuatro comprobaciones, y las dos primeras son las que de verdad pueden fallar en silencio:

1. FILAS EXACTAS: 11.483 embebidos menos 201 sin asignatura declarada (ADR 0007). Un numero
   redondo "parecido" no vale: se exige la resta exacta.
2. VECTOR CONTRA .NPY POR CLAVE: se toman k fragmentos al azar, se busca su fila en ids.jsonl por
   (documento, orden) y se compara el vector de la base con el del fichero. Es LA comprobacion de
   este encargo: la carga es de un subconjunto, asi que un casado por posicion habria pegado cada
   vector a otro fragmento sin que nada protestara.
3. CONTEO POR TITULACION A TRAVES DE LA PUENTE, no sumando filas de asignaturas: los transversales
   se cargan UNA vez bajo su dueña, asi que contar filas daria 13/9/13 en vez de 13/14/14.
4. Ninguna fila sin asignatura con codigo del BOE detras.

    python scripts/comprobar_carga.py                 # comprobacion normal
    python scripts/comprobar_carga.py --trucar        # trucar un id: la 2 DEBE ponerse roja
"""
import argparse
import json
import os
import sys

import numpy as np
import psycopg

IDS = "corpus/embeddings/ids.jsonl"
VECTORES = "corpus/embeddings/vectores.npy"
ARBOL = "corpus/arbol_oficial.jsonl"
FRAGMENTOS_EMBEBIDOS = 11483
FUERA_POR_ADR_0007 = 201


def leer_jsonl(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def main() -> int:
    p = argparse.ArgumentParser(description="Comprueba la carga del 2.1.")
    p.add_argument("--url", default=os.environ.get("DATABASE_URL"))
    p.add_argument("--muestra", type=int, default=25)
    p.add_argument("--trucar", action="store_true",
                   help="compara contra el vector de OTRO fragmento: la comprobacion 2 debe fallar")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not a.url:
        sys.exit("falta DATABASE_URL")

    claves = leer_jsonl(IDS)
    matriz = np.load(VECTORES)
    por_clave = {(c["documento"], c["orden"]): i for i, c in enumerate(claves)}
    hallazgos = []

    with psycopg.connect(a.url) as conexion, conexion.cursor() as cur:
        # 1. filas exactas
        cur.execute("SELECT count(*) FROM fragmentos")
        filas = cur.fetchone()[0]
        esperadas = FRAGMENTOS_EMBEBIDOS - FUERA_POR_ADR_0007
        print(f"1) filas en fragmentos: {filas} | esperadas {FRAGMENTOS_EMBEBIDOS} - "
              f"{FUERA_POR_ADR_0007} = {esperadas}")
        if filas != esperadas:
            hallazgos.append(f"filas cargadas {filas}, esperadas {esperadas}")

        # 2. el vector de la base contra el del .npy, buscado POR CLAVE
        cur.execute("""SELECT d.ruta, f.orden, f.embedding FROM fragmentos f
                       JOIN documentos d ON d.id = f.documento_id
                       ORDER BY random() LIMIT %s""", (a.muestra,))
        filas_muestra = cur.fetchall()
        distintos = 0
        for i, (ruta, orden, embedding) in enumerate(filas_muestra):
            fila = por_clave.get((ruta, orden))
            if fila is None:
                hallazgos.append(f"fragmento en base sin clave en ids.jsonl: {ruta}#{orden}")
                continue
            if a.trucar and i == 0:
                fila = (fila + 1) % len(matriz)      # el id trucado: OTRO fragmento
            en_base = np.array(json.loads(embedding), dtype=np.float32)
            if not np.allclose(en_base, matriz[fila], atol=1e-5):
                distintos += 1
                hallazgos.append(f"vector distinto del .npy en {ruta}#{orden}")
        print(f"2) vectores comprobados por clave: {len(filas_muestra)} | distintos: {distintos}"
              + ("   <- con --trucar, este 1 es la prueba de que la comprobacion sirve"
                 if a.trucar else ""))

        # 3. conteo por titulacion A TRAVES DE LA PUENTE
        arbol = [n for n in leer_jsonl(ARBOL) if n.get("nivel") == "asignatura"]
        del_fichero = {}
        for n in arbol:
            del_fichero[n["titulacion"]] = del_fichero.get(n["titulacion"], 0) + 1
        cur.execute("SELECT titulacion, count(*) FROM titulacion_asignaturas GROUP BY titulacion")
        en_base = dict(cur.fetchall())
        print(f"3) asignaturas por titulacion (via puente): base {en_base} | fichero {del_fichero}")
        if en_base != del_fichero:
            hallazgos.append(f"la puente dice {en_base} y el arbol {del_fichero}")
        cur.execute("SELECT count(*) FROM asignaturas")
        print(f"   filas en asignaturas: {cur.fetchone()[0]} (menos que la suma: los transversales"
              f" se cargan una vez bajo su dueña)")

        # 4. ninguna fila huerfana
        cur.execute("""SELECT count(*) FROM fragmentos f
                       LEFT JOIN asignaturas a ON a.id = f.asignatura_id WHERE a.id IS NULL""")
        huerfanos = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM fragmentos WHERE embedding IS NULL OR tsv IS NULL")
        sin_indexar = cur.fetchone()[0]
        print(f"4) fragmentos sin asignatura: {huerfanos} | sin vector o sin tsv: {sin_indexar}")
        if huerfanos or sin_indexar:
            hallazgos.append(f"{huerfanos} huerfanos, {sin_indexar} sin vector o tsv")

    print(f"\nhallazgos: {len(hallazgos)}")
    for h in hallazgos:
        print("  -", h)
    return 1 if hallazgos else 0


if __name__ == "__main__":
    sys.exit(main())
