#!/usr/bin/env python3
"""Genera `evals/casos/conflicto.jsonl`, el conjunto de casos de conflicto (1.10, repartido al 2.6).

    DATABASE_URL=... python scripts/conjunto_conflicto.py

Tres orígenes, y cada caso dice el suyo, porque no valen lo mismo:

- `glosario`: términos que el 2.6 encuentra definidos más de una vez con palabras distintas y en
  documentos distintos. Son candidatos a contradicción, **no contradicciones**: que dos definiciones
  diverjan es un hecho que sale de un `GROUP BY`; que se contradigan lo juzga el NLI de la fase 4.
- `plantado`: la contradicción sintética del 1.7, declarada como plantada en el manifiesto.
- `conocido`: el par REAL de MVC, que existe en el corpus y **hoy el sistema no encuentra**. Se
  incluye a propósito: un conjunto de evaluación que solo trae lo que ya sale bien no mide nada. Este
  caso se espera en rojo, con su motivo escrito, y se pondrá verde cuando el 1.4 mejore la detección
  de frase definitoria.

El fichero se CONGELA al crearse (regla del 1.10): un conjunto que se retoca al ver los fallos deja
de medir al sistema y pasa a medir cuánto se ha adaptado el conjunto.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glosario import conflictos                                      # noqa: E402

DESTINO = "evals/casos/conflicto.jsonl"
FRAGMENTOS = "corpus/fragmentos.jsonl"


def leer_jsonl(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def buscar(fragmentos, *agujas) -> list:
    """Fragmentos cuyo texto contiene TODAS las agujas. Sin modelo y reproducible."""
    return [f for f in fragmentos
            if all(a.lower() in f["texto"].lower() for a in agujas)]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2
    fragmentos = leer_jsonl(FRAGMENTOS)
    casos = []

    # 1) Lo que el glosario destapa al ejecutarse.
    for c in conflictos(url):
        casos.append({
            "id": f"glosario-{c['codigo']}-{c['termino'].replace(' ', '_')}",
            "origen": "glosario",
            "codigo": c["codigo"],
            "termino": c["termino"],
            "pregunta": f"¿Qué es {c['termino']}?",
            "esperado": "aviso_de_definiciones_divergentes",
            "definiciones": [d for d in c["definiciones"]],
            "documentos": [d for d in c["documentos"]],
            "detectado_hoy": True,
            "nota": "divergencia medida por consulta SQL sobre el glosario; que se contradigan lo "
                    "juzga el NLI de la fase 4, no este conjunto",
        })

    # 2) La contradicción sintética del 1.7, que el detector del 1.8 sí caza (NLI 0,99).
    plantados = buscar(fragmentos, "paso por referencia")
    casos.append({
        "id": "plantado-java-paso-por-valor",
        "origen": "plantado",
        "codigo": "0485",
        "termino": "paso de parámetros en java",
        "pregunta": "¿Los objetos en Java se pasan por referencia?",
        "esperado": "aviso_de_conflicto_con_las_dos_versiones",
        "documentos": sorted({f["documento"] for f in plantados})[:6],
        "detectado_hoy": True,
        "nota": "contradicción PLANTADA en el 1.7 y declarada como plantada en el manifiesto. En "
                "este par el material plantado es el técnicamente correcto y el temario oficial es "
                "el que va suelto: por eso el sistema ordena por vigencia y no dictamina",
    })

    # 3) El par REAL de MVC, que hoy NO se detecta. Va con su motivo.
    vista = buscar(fragmentos, "mvc", "vista")
    antiguo = [f for f in vista if "antiguo" in f["documento"] or "comesana" in f["documento"]]
    moderno = [f for f in vista if f not in antiguo]
    casos.append({
        "id": "conocido-mvc-vista",
        "origen": "conocido",
        "codigo": "0613",
        "termino": "vista (mvc)",
        "pregunta": "¿Qué es la Vista en el patrón MVC?",
        "esperado": "aviso_de_conflicto_con_las_dos_versiones",
        "documentos": sorted({f["documento"] for f in antiguo[:3] + moderno[:3]}),
        "detectado_hoy": False,
        "nota": "EL CASO QUE HOY SE ESPERA EN ROJO. El par existe en el corpus y el sistema no lo "
                "encuentra: de los 260 fragmentos del 0613 que mencionan MVC, solo 16 llevan "
                "frase_definitoria y ninguno define la Vista, así que las dos definiciones nunca "
                "llegan a ser candidatas del glosario. El fallo está en la detección de frase "
                "definitoria del 1.4, no en el 2.6. Se pondrá verde cuando aquello mejore",
    })

    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    with open(DESTINO, "w", encoding="utf-8", newline="\n") as f:
        for c in casos:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    verdes = sum(1 for c in casos if c["detectado_hoy"])
    print(f"{DESTINO}: {len(casos)} casos | {verdes} que hoy se detectan | "
          f"{len(casos) - verdes} que hoy se esperan en rojo, con su motivo escrito")
    for c in casos:
        print(f"  [{c['origen']:9s}] {c['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
