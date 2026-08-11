#!/usr/bin/env python3
"""
Repara los nombres de ficheros y carpetas que el descompresor de Windows
destrozo al extraer el zip (acentos y enes convertidos en basura).

Metodo: NO se fia de los nombres. Empareja por el SHA-256 del CONTENIDO,
que el manifiesto ya guarda para cada fichero. Es inmune a cualquier
codificacion. Solo renombra cuando el hash aparece entre los ficheros que
el manifiesto declara y no estan en disco.

Uso, desde la raiz del repo:
    python scripts/reparar_nombres.py           (simulacro, no toca nada)
    python scripts/reparar_nombres.py --aplicar (renombra de verdad)
"""
import hashlib
import json
import os
import sys

APLICAR = "--aplicar" in sys.argv
MANIFIESTO = "corpus/manifiesto.jsonl"


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main():
    if not os.path.exists(MANIFIESTO):
        print("ERROR: ejecuta esto desde la raiz del repo (donde esta corpus/).")
        return 2

    manifiesto = {}
    with open(MANIFIESTO, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                e = json.loads(linea)
                manifiesto[e["ruta"]] = e["hash_sha256"]

    en_disco = set()
    for base, _, files in os.walk("corpus"):
        for f in files:
            ruta = os.path.join(base, f).replace(os.sep, "/")
            if ruta != MANIFIESTO:
                en_disco.add(ruta)

    sobran = sorted(en_disco - set(manifiesto))
    faltan = set(manifiesto) - en_disco

    if not sobran and not faltan:
        print("Nada que reparar: disco y manifiesto ya coinciden.")
        return 0

    por_hash = {}
    for r in faltan:
        por_hash.setdefault(manifiesto[r], []).append(r)
    for lista in por_hash.values():
        lista.sort()

    print(f"Ficheros con el nombre roto: {len(sobran)} | huecos declarados: {len(faltan)}")
    print("Calculando hashes, esto tarda un poco...")

    arreglados, sin_pareja = 0, []
    for p in sobran:
        h = sha256(p)
        candidatos = por_hash.get(h)
        if candidatos:
            destino = candidatos.pop(0)
            if APLICAR:
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                os.replace(p, destino)
            arreglados += 1
        else:
            sin_pareja.append(p)

    vacios = 0
    if APLICAR:
        for base, dirs, files in os.walk("corpus", topdown=False):
            if not os.listdir(base):
                os.rmdir(base)
                vacios += 1

    modo = "APLICADO" if APLICAR else "SIMULACRO (nada tocado)"
    print(f"[{modo}] ficheros reparados: {arreglados} | carpetas vacias retiradas: {vacios}")
    for p in sin_pareja:
        print("SIN PAREJA por contenido:", p)
    if not APLICAR and arreglados:
        print("\nSi el numero cuadra, repite con:  python scripts/reparar_nombres.py --aplicar")
    return 1 if sin_pareja else 0


if __name__ == "__main__":
    sys.exit(main())
