#!/usr/bin/env python3
"""Encargo 1.0: cruza disco contra manifiesto en las dos direcciones Y comprueba el hash.

Hasta este encargo esto solo comparaba conjuntos de rutas: un fichero truncado, alterado o copiado
a medias pasaba en verde. Un detector que nunca se ha visto disparar sobre el caso que debe cazar
no es un detector, y el precedente esta en el repo: la reparacion de los 249 nombres rotos la
salvo el SHA-256 de scripts/reparar_nombres.py, no el verde de este script.

Cuatro clases de hallazgo, contadas por separado:
  SIN MANIFIESTO  fichero en disco que nadie declaro
  SIN FICHERO     entrada del manifiesto cuyo fichero no esta
  HASH DISTINTO   el fichero existe pero ya no es el que se registro
  RUTA DUPLICADA  la misma ruta declarada dos veces (antes se pisaba en silencio)

El manifiesto NO se supone inmutable: crece (el encargo 1.3 va a registrar los ficheros
normalizados). Por eso las entradas se leen con tolerancia a campos nuevos: aqui solo se exigen
'ruta' y 'hash_sha256', y cualquier otro campo se ignora sin protestar.

Codigos de salida:  0 sin hallazgos | 1 con hallazgos | 2 manifiesto ilegible o mal formado

Uso:
    python scripts/verificar_manifiesto.py
    python scripts/verificar_manifiesto.py --corpus corpus --manifiesto corpus/manifiesto.jsonl
"""
import argparse
import hashlib
import json
import os
import sys
import time

BLOQUE = 1 << 20
CAMPOS_EXIGIDOS = ("ruta", "hash_sha256")


def abortar(mensaje: str):
    """Sale con 2, no con 1: 'no he podido leer el manifiesto' no es 'el corpus esta mal'.
    Confundir las dos cosas haria pasar un manifiesto roto por un hallazgo de integridad."""
    print(mensaje, file=sys.stderr)
    sys.exit(2)


def sha256(ruta: str) -> str:
    """Hash leyendo por bloques: el corpus tiene PDF de decenas de MB y no cabe entero en RAM."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(BLOQUE), b""):
            h.update(bloque)
    return h.hexdigest()


def leer_manifiesto(camino: str) -> tuple[dict, list]:
    """Devuelve (entradas por ruta, rutas duplicadas). Sale con 2 si el manifiesto no es legible."""
    entradas, duplicadas = {}, []
    try:
        with open(camino, encoding="utf-8") as f:
            for numero, linea in enumerate(f, 1):
                if not linea.strip():
                    continue
                try:
                    e = json.loads(linea)
                except json.JSONDecodeError as err:
                    abortar(f"MANIFIESTO MAL FORMADO: linea {numero}: {err}")
                faltan = [c for c in CAMPOS_EXIGIDOS if not e.get(c)]
                if faltan:
                    abortar(f"MANIFIESTO MAL FORMADO: linea {numero} sin {', '.join(faltan)}")
                if e["ruta"] in entradas:
                    duplicadas.append((e["ruta"], numero))
                entradas[e["ruta"]] = e
    except OSError as err:
        abortar(f"MANIFIESTO ILEGIBLE: {err}")
    return entradas, duplicadas


def ficheros_en_disco(raiz: str, manifiesto: str) -> set:
    """Todo lo que hay bajo la raiz del corpus, menos el propio manifiesto."""
    fuera = os.path.abspath(manifiesto)
    encontrados = set()
    for base, _, ficheros in os.walk(raiz):
        for nombre in ficheros:
            camino = os.path.join(base, nombre)
            if os.path.abspath(camino) != fuera:
                encontrados.add(camino.replace(os.sep, "/"))
    return encontrados


def verificar(raiz: str, manifiesto: str) -> int:
    t0 = time.perf_counter()
    entradas, duplicadas = leer_manifiesto(manifiesto)
    disco = ficheros_en_disco(raiz, manifiesto)

    sin_manifiesto = sorted(disco - set(entradas))
    sin_fichero = sorted(set(entradas) - disco)
    hash_distinto = []
    for ruta in sorted(set(entradas) & disco):
        actual = sha256(ruta)
        if actual != entradas[ruta]["hash_sha256"]:
            hash_distinto.append((ruta, entradas[ruta]["hash_sha256"], actual))

    for ruta in sin_manifiesto:
        print("SIN MANIFIESTO:", ruta)
    if sin_manifiesto:
        print("  (se registran con scripts/anadir_al_manifiesto.py; sin entrada no entran al corpus)")
    for ruta in sin_fichero:
        print("SIN FICHERO:", ruta)
    for ruta, esperado, actual in hash_distinto:
        print(f"HASH DISTINTO: {ruta}\n  esperado {esperado}\n  obtenido {actual}")
    for ruta, numero in duplicadas:
        print(f"RUTA DUPLICADA: {ruta} (repetida en la linea {numero} del manifiesto)")

    clases = {
        "sin_manifiesto": len(sin_manifiesto),
        "sin_fichero": len(sin_fichero),
        "hash_distinto": len(hash_distinto),
        "ruta_duplicada": len(duplicadas),
    }
    ocurrencias = sum(clases.values())
    con_hallazgo = sum(1 for n in clases.values() if n)
    print(f"disco={len(disco)} manifiesto={len(entradas)} hashes={len(set(entradas) & disco)} "
          f"en {time.perf_counter() - t0:.1f}s")
    print(f"ocurrencias={ocurrencias} en {con_hallazgo} de {len(clases)} clases " +
          " ".join(f"{k}={v}" for k, v in clases.items()))
    return 1 if ocurrencias else 0


def main() -> int:
    p = argparse.ArgumentParser(description="Verifica el corpus contra su manifiesto (encargo 1.0).")
    p.add_argument("--corpus", default="corpus", help="raiz del corpus a recorrer")
    p.add_argument("--manifiesto", default=None, help="por defecto, <corpus>/manifiesto.jsonl")
    a = p.parse_args()
    return verificar(a.corpus, a.manifiesto or os.path.join(a.corpus, "manifiesto.jsonl"))


if __name__ == "__main__":
    sys.exit(main())
