#!/usr/bin/env python3
"""Encargo 1.2: cruza disco contra manifiesto en las dos direcciones. Sale distinto de cero ante cualquier hueco."""
import os, sys, json
man = {}
with open("corpus/manifiesto.jsonl", encoding="utf-8") as f:
    for linea in f:
        e = json.loads(linea)
        man[e["ruta"]] = e
disco = set()
for base, _, files in os.walk("corpus"):
    for x in files:
        p = os.path.join(base, x).replace(os.sep, "/")
        if p != "corpus/manifiesto.jsonl":
            disco.add(p)
sin_manifiesto = sorted(disco - set(man))
sin_fichero = sorted(set(man) - disco)
for p in sin_manifiesto: print("SIN MANIFIESTO:", p)
for p in sin_fichero: print("SIN FICHERO:", p)
print(f"disco={len(disco)} manifiesto={len(man)} huecos={len(sin_manifiesto)+len(sin_fichero)}")
sys.exit(1 if (sin_manifiesto or sin_fichero) else 0)
