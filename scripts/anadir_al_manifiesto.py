#!/usr/bin/env python3
"""Anade una entrada al manifiesto: ruta fuente licencia densidad plantado(true/false).

La version_corpus NO se escribe a fuego: sale de la variable de entorno VERSION_CORPUS
(seccion 11 de la guia) y, si no esta puesta, de la ultima entrada del propio manifiesto,
que es append-only y por tanto lleva la version vigente.
"""
import hashlib
import json
import os
import sys

MANIFIESTO = "corpus/manifiesto.jsonl"


def version_corpus_vigente():
    v = os.environ.get("VERSION_CORPUS")
    if v:
        return v
    ultima = None
    with open(MANIFIESTO, encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                ultima = json.loads(linea)
    if ultima is None:
        sys.exit(f"{MANIFIESTO} vacio: pon VERSION_CORPUS en el entorno para la primera entrada")
    return ultima["version_corpus"]


ruta, fuente, lic, dens, plantado = sys.argv[1:6]
version = version_corpus_vigente()
h = hashlib.sha256(open(ruta, "rb").read()).hexdigest()
e = {"ruta": ruta, "fuente": fuente, "licencia": lic, "version_corpus": version,
     "hash_sha256": h, "densidad": dens, "plantado": plantado.lower() == "true"}
with open(MANIFIESTO, "a", encoding="utf-8", newline="\n") as f:  # LF siempre, tambien en Windows
    f.write(json.dumps(e, ensure_ascii=False) + "\n")
print(f"anadido ({version}):", ruta)
