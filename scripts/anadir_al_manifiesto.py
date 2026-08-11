#!/usr/bin/env python3
"""Anade una entrada al manifiesto: ruta fuente licencia densidad plantado(true/false)."""
import sys, json, hashlib
ruta, fuente, lic, dens, plantado = sys.argv[1:6]
h = hashlib.sha256(open(ruta, 'rb').read()).hexdigest()
e = {"ruta": ruta, "fuente": fuente, "licencia": lic, "version_corpus": "v1-2026-08-11",
     "hash_sha256": h, "densidad": dens, "plantado": plantado.lower() == "true"}
with open("corpus/manifiesto.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(e, ensure_ascii=False) + "\n")
print("anadido:", ruta)
