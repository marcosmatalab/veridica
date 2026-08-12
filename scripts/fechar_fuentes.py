#!/usr/bin/env python3
"""Pone `fecha_fuente` en el manifiesto (preparacion del encargo 1.8).

Sin fecha por documento, el criterio de "ante un conflicto, se ordena por vigencia" es palabreria:
no habria con que ordenar. Y la fecha no se pone a ojo, sale de evidencia, con el sitio de donde
sale escrito al lado en `fecha_origen`:

  metadatos_pdf   /CreationDate del propio PDF. Es lo mas fiable y cubre casi todo el corpus viejo.
  texto           el documento dice su curso o su año ("curso 2025/2026").
  norma           la fecha de la propia norma del BOE.
  heredada        un derivado toma la de su original (derivado_de).
  (nula)          no se sabe. Se deja vacia y se dice: inventarla seria peor que no tenerla.

Uso:
    python scripts/fechar_fuentes.py            # informe, no escribe
    python scripts/fechar_fuentes.py --escribir
"""
import argparse
import collections
import json
import re
import sys

MANIFIESTO = "corpus/manifiesto.jsonl"

# Fuentes sin metadatos por fichero (markdown de repos), con la evidencia que sostiene la fecha.
POR_SUBARBOL = [
    ("corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs", "2025-09-01",
     "texto: el propio material se declara del curso 2025/2026"),
    ("corpus/asir/apuntes/aberlanas-iso", "2016-01-01", "texto: año citado en el material (2016)"),
    ("corpus/asir/apuntes/lora-2asir", "2020-01-01", "texto: año citado en el material (2020)"),
    ("corpus/familia", "2019-01-01", "texto: año citado en el indice de la familia"),
]
NORMAS = [
    ("RD-686-2010", "2010-06-12"), ("Orden-EDU-2887-2010", "2010-11-11"),
    ("RD-405-2023", "2023-06-03"), ("RD-450-2010", "2010-05-20"), ("RD-1629-2009", "2009-11-18"),
]
RE_FECHA_PDF = re.compile(r"D:(\d{4})(\d{2})(\d{2})")


def fecha_de_pdf(ruta: str):
    try:
        from pypdf import PdfReader
        meta = PdfReader(ruta).metadata or {}
        for clave in ("/CreationDate", "/ModDate"):
            m = RE_FECHA_PDF.match(str(meta.get(clave, "")))
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    except Exception:  # noqa: BLE001 - un PDF ilegible no puede tumbar la pasada
        return None
    return None


def fechar(entradas: list) -> tuple:
    por_ruta = {e["ruta"]: e for e in entradas}
    propuestas = {}
    for e in entradas:
        ruta = e["ruta"]
        for marca, fecha in NORMAS:
            if marca in ruta:
                propuestas[ruta] = (fecha, "norma")
                break
        if ruta in propuestas:
            continue
        if ruta.lower().endswith(".pdf"):
            f = fecha_de_pdf(ruta)
            if f:
                propuestas[ruta] = (f, "metadatos_pdf")
                continue
        for prefijo, fecha, motivo in POR_SUBARBOL:
            if ruta.startswith(prefijo) or ruta.startswith(prefijo.replace("corpus/", "corpus/derivado/")):
                propuestas[ruta] = (fecha, motivo.split(":")[0])
                break

    # Un fichero sin fecha propia toma la de su CARPETA si ahi hay documentos fechados: los .java
    # de "Unidad 7/Solucion Ejercicios" son del mismo paquete de material que ud7_Funciones.pdf.
    # Es inferencia, y por eso se marca como tal en fecha_origen en vez de disfrazarse de dato.
    por_carpeta = collections.defaultdict(collections.Counter)
    for ruta, (fecha, _) in propuestas.items():
        por_carpeta["/".join(ruta.split("/")[:-1])][fecha] += 1
    for e in entradas:
        ruta = e["ruta"]
        if ruta in propuestas:
            continue
        carpeta = "/".join(ruta.split("/")[:-1])
        for arriba in (carpeta, "/".join(carpeta.split("/")[:-1])):
            if por_carpeta.get(arriba):
                propuestas[ruta] = (por_carpeta[arriba].most_common(1)[0][0], "carpeta")
                break

    # Los derivados heredan de su original, y los plantados de aquello de lo que se copiaron.
    for e in entradas:
        ruta = e["ruta"]
        if ruta in propuestas:
            continue
        origen = e.get("derivado_de") or e.get("plantado_origen")
        if origen:
            if origen in propuestas:
                propuestas[ruta] = (propuestas[origen][0], "heredada")
            elif origen in por_ruta and por_ruta[origen].get("fecha_fuente"):
                propuestas[ruta] = (por_ruta[origen]["fecha_fuente"], "heredada")
    return propuestas


def main() -> int:
    p = argparse.ArgumentParser(description="Fecha las fuentes del corpus con evidencia.")
    p.add_argument("--escribir", action="store_true")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    with open(MANIFIESTO, encoding="utf-8") as f:
        entradas = [json.loads(linea) for linea in f if linea.strip()]

    propuestas = fechar(entradas)
    sin_fecha = [e["ruta"] for e in entradas if e["ruta"] not in propuestas]
    origenes = collections.Counter(o for _, o in propuestas.values())
    print(f"entradas: {len(entradas)} | con fecha: {len(propuestas)} | sin fecha: {len(sin_fecha)}")
    for origen, n in origenes.most_common():
        print(f"  {origen:16} {n:5}")
    if sin_fecha:
        print("\nsin fecha conocida (se queda nula, no se inventa):")
        for r in collections.Counter("/".join(x.split("/")[:4]) for x in sin_fecha).most_common(6):
            print(f"  {r[1]:5}  {r[0]}/…")

    if a.escribir:
        for e in entradas:
            if e["ruta"] in propuestas:
                e["fecha_fuente"], e["fecha_origen"] = propuestas[e["ruta"]]
        with open(MANIFIESTO, "w", encoding="utf-8", newline="\n") as f:
            for e in entradas:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        print(f"\nescrito: {len(propuestas)} entradas con fecha_fuente y fecha_origen")
    else:
        print("\n(informe; nada escrito. Usa --escribir)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
