#!/usr/bin/env python3
"""Encargo 3.0: cruza los pares oro contra el indice de fragmentos, por posicion Y por contenido.

Un par oro apunta a un fragmento por (documento, orden), y `orden` es POSICIONAL dentro del
documento. Si el corpus se vuelve a trocear, ese mismo par sigue apuntando a algo -otro texto- y
no protesta: el recall@6 pasa a medir otra cosa y nadie se entera, porque un par desplazado no
rompe nada, solo miente. Es el fallo del verificador de solo rutas del 1.0 repetido en el conjunto
de evaluacion, y por eso cada par trae ademas el SHA-256 del texto que se etiqueto.

Cinco clases de hallazgo, contadas por separado:
  NO EXISTE          (documento, orden) que no esta en el indice
  DESPLAZADO         el fragmento existe pero ya NO es el que se etiqueto (hash distinto)
  NO ADMITIDO        el documento, o el fragmento, se cae por la puerta del 1.4
  CIRCULAR           el oro sale de practicas/, que es de donde salen las PREGUNTAS
  DISCREPANTE        la asignatura declarada en el par no es la del fragmento

Lo circular es el hallazgo que mas engaña si se cuela: un fragmento de practicas/ como oro
significa que la pregunta se responde a si misma, y el recall sale perfecto sin merito.

La puerta del 1.4 se IMPORTA de admitir.py, no se reimplanta: una copia de las reglas aqui daria
verde el dia que alla cambien (principio 6 al reves, que tambien pasa - el que comprueba no puede
divergir en silencio del que produce).

Este script NO repara. Anclar un par desplazado es volver a leer el fragmento y decidir si sigue
respondiendo la pregunta, que es trabajo de persona; un verificador que sabe reescribir el fichero
que verifica puede ponerse verde solo, y entonces no verifica nada (ADR 0010).

Codigos de salida:  0 sin hallazgos | 1 con hallazgos | 2 casos o indice ilegibles o mal formados

Uso:
    python scripts/verificar_oro.py
    python scripts/verificar_oro.py --casos evals/casos/oro_recuperacion.jsonl
"""
import argparse
import collections
import hashlib
import json
import sys

import admitir

CASOS = "evals/casos/oro_recuperacion.jsonl"
FRAGMENTOS = "corpus/fragmentos.jsonl"
CAMPOS_PAR = ("id", "pregunta", "localizacion", "asignatura")
CAMPOS_ORO = ("documento", "orden", "hash_texto")
# De donde salen las preguntas del profesor. Un oro aqui dentro es la pregunta respondiendose sola.
PREGUNTAS = "/practicas/"


def abortar(mensaje: str):
    """Sale con 2, no con 1: 'no he podido leer el indice' no es 'los pares oro estan mal'.
    En este script la distincion importa el doble, porque el indice NO esta en git (ADR 0001):
    en el runner de CI falta siempre, y eso no es un hallazgo de integridad del conjunto oro."""
    print(mensaje, file=sys.stderr)
    sys.exit(2)


def leer_jsonl(camino: str, que: str) -> list:
    lineas = []
    try:
        with open(camino, encoding="utf-8") as f:
            for numero, linea in enumerate(f, 1):
                if not linea.strip():
                    continue
                try:
                    lineas.append(json.loads(linea))
                except json.JSONDecodeError as err:
                    abortar(f"{que} MAL FORMADO: linea {numero}: {err}")
    except OSError as err:
        abortar(f"{que} ILEGIBLE: {err}")
    return lineas


def leer_casos(camino: str) -> list:
    """Los pares, con los campos que se exigen. Un par sin hash_texto no es un par mal etiquetado:
    es un fichero de otra epoca, de antes de que el ancla existiera, y hay que saberlo al leerlo."""
    pares = leer_jsonl(camino, "CASOS")
    for numero, par in enumerate(pares, 1):
        faltan = [c for c in CAMPOS_PAR if not par.get(c)]
        oro = par.get("fragmento_oro") or {}
        faltan += [f"fragmento_oro.{c}" for c in CAMPOS_ORO if oro.get(c) is None]
        if faltan:
            abortar(f"CASOS MAL FORMADO: linea {numero} sin {', '.join(faltan)}")
    return pares


def indice_de(camino: str) -> tuple[dict, dict]:
    """Devuelve (fragmentos por (documento, orden), fragmentos por documento)."""
    por_clave, por_documento = {}, collections.defaultdict(list)
    for f in leer_jsonl(camino, "INDICE"):
        por_clave[(f["documento"], f["orden"])] = f
        por_documento[f["documento"]].append(f)
    if not por_clave:
        abortar(f"INDICE MAL FORMADO: {camino} no tiene fragmentos")
    return por_clave, por_documento


def sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def verificar(casos: str, fragmentos: str) -> int:
    pares = leer_casos(casos)
    por_clave, por_documento = indice_de(fragmentos)

    # La puerta del 1.4 es cara y se repite: un documento juzgado una vez vale para sus 30 pares.
    juicio_documento = {}

    no_existe, desplazado, no_admitido, circular, discrepante = [], [], [], [], []
    for par in pares:
        oro = par["fragmento_oro"]
        documento, orden = oro["documento"], oro["orden"]

        if PREGUNTAS in documento:
            circular.append((par["id"], documento))

        fragmento = por_clave.get((documento, orden))
        if fragmento is None:
            no_existe.append((par["id"], documento, orden))
            continue

        actual = sha256(fragmento["texto"])
        if actual != oro["hash_texto"]:
            desplazado.append((par["id"], documento, orden, oro["hash_texto"], actual))

        if documento not in juicio_documento:
            juicio_documento[documento] = admitir.juzgar_documento(documento,
                                                                   por_documento[documento])
        motivo = juicio_documento[documento]
        if motivo:
            no_admitido.append((par["id"], documento, f"documento: {motivo}"))
        else:
            motivo = admitir.juzgar_fragmento(fragmento)
            if motivo:
                no_admitido.append((par["id"], documento, f"fragmento: {motivo}"))

        if fragmento.get("asignatura") != par["asignatura"]:
            discrepante.append((par["id"], par["asignatura"], fragmento.get("asignatura")))

    for id_par, documento, orden in no_existe:
        print(f"NO EXISTE: {id_par} -> {documento} orden {orden}")
    for id_par, documento, orden, esperado, actual in desplazado:
        print(f"DESPLAZADO: {id_par} -> {documento} orden {orden}\n"
              f"  etiquetado {esperado}\n  ahora      {actual}")
    if desplazado:
        print("  (el fragmento existe pero ya no es el que se etiqueto: hay que releer el par,"
              " no re-anclarlo a ciegas)")
    for id_par, documento, motivo in no_admitido:
        print(f"NO ADMITIDO: {id_par} -> {documento} ({motivo})")
    for id_par, documento in circular:
        print(f"CIRCULAR: {id_par} -> {documento} (el oro sale de donde salen las preguntas)")
    for id_par, declarada, real in discrepante:
        print(f"DISCREPANTE: {id_par} declara {declarada} y el fragmento es {real}")

    clases = {
        "no_existe": len(no_existe),
        "desplazado": len(desplazado),
        "no_admitido": len(no_admitido),
        "circular": len(circular),
        "discrepante": len(discrepante),
    }
    ocurrencias = sum(clases.values())
    con_hallazgo = sum(1 for n in clases.values() if n)

    # Notas: no son hallazgos, son lo que hay que poder leer de un vistazo para saber si la
    # comprobacion ha tenido de que agarrarse. Un corpus sin practicas/ dejaria la clase circular
    # vacua y en verde, que es la forma mas silenciosa de no comprobar nada.
    reparto = collections.Counter(p["localizacion"] for p in pares)
    repetidos = [c for c, n in collections.Counter(
        (p["fragmento_oro"]["documento"], p["fragmento_oro"]["orden"]) for p in pares).items()
        if n > 1]
    print(f"\npares={len(pares)} indice={len(por_clave)} fragmentos en "
          f"{len(por_documento)} documentos, de ellos "
          f"{sum(1 for d in por_documento if PREGUNTAS in d)} bajo practicas/")
    print("localizacion: " + " ".join(f"{k}={v}" for k, v in sorted(reparto.items())) +
          "  (el 3.5 reporta recall@6 y nDCG@5 por separado en los dos)")
    for documento, orden in repetidos:
        print(f"NOTA, oro repetido en mas de una pregunta: {documento} orden {orden}")
    print(f"ocurrencias={ocurrencias} en {con_hallazgo} de {len(clases)} clases " +
          " ".join(f"{k}={v}" for k, v in clases.items()))
    return 1 if ocurrencias else 0


def main() -> int:
    p = argparse.ArgumentParser(description="Verifica los pares oro contra el indice (encargo 3.0).")
    p.add_argument("--casos", default=CASOS)
    p.add_argument("--fragmentos", default=FRAGMENTOS)
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    return verificar(a.casos, a.fragmentos)


if __name__ == "__main__":
    sys.exit(main())
