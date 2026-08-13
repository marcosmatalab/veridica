#!/usr/bin/env python3
"""Cuántas citas pasan en cada nivel de normalización (encargo 4.2). No gasta: todo es SQL local.

    DATABASE_URL=... python scripts/barrer_normalizacion.py

**LA CARGA DE LA PRUEBA LA TIENE CADA PASO QUE SE AÑADA, no al revés**, porque cada uno cambia un
falso negativo por un falso positivo y en un verificador el falso positivo es el caro. Así que este
barrido no busca "cuál es mejor": busca **cuál demuestra que compra algo**. Un paso que no lo
demuestre no entra, y con una n pequeña eso empuja hacia el verificador más conservador, que es el
lado seguro. **Una n pequeña no deja sin decisión: decide hacia la prudencia.**

EL DENOMINADOR VA DECLARADO Y INCLUYE LO QUE NO PASÓ NINGÚN NIVEL, que es la regla que este repo
acaba de escribir: contar solo sobre las citas que llegaron a compararse sería medir sobre el
subconjunto que salió bien. Aquí el denominador son **todas las citas emitidas**, y las que se caen
por la puerta de procedencia se cuentan aparte en vez de desaparecer.
"""
import argparse
import json
import os
import statistics
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.conexion import conectar                                    # noqa: E402
from app.core.verificador_literal import (NIVELES, PODADA, VERIFICADA,    # noqa: E402
                                          hay_acentos_perdidos, verificar)


def citas_con_su_fragmento(url: str) -> list:
    """Cada afirmación `literal` con cita, su fragmento y si ese fragmento estuvo en el contexto.

    El contexto sale de `respuestas.etapas.recuperacion.en_contexto`, que es lo que el servidor
    mandó de verdad: no se reconstruye ni se supone."""
    with conectar(url) as con, con.cursor() as cur:
        cur.execute("""
            SELECT a.id, a.fragmento_id, a.detalle->>'cita' AS cita,
                   r.etapas->'recuperacion'->'en_contexto' AS en_contexto
            FROM afirmaciones a JOIN respuestas r ON r.id = a.respuesta_id
            WHERE a.tipo = 'literal' AND a.detalle->>'cita' IS NOT NULL
        """)
        filas = cur.fetchall()
        ids = {f[1] for f in filas if f[1] is not None}
        for fila in filas:
            for x in (fila[3] or []):
                ids.add(x)
        cur.execute("SELECT id, texto FROM fragmentos WHERE id = ANY(%s)", (list(ids),))
        textos = dict(cur.fetchall())
    return [{"id": i, "fragmento_id": fid, "cita": cita,
             "en_contexto": {x: textos[x] for x in (ctx or []) if x in textos}}
            for i, fid, cita, ctx in filas]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=os.environ.get("DATABASE_URL"))
    p.add_argument("--salida-json", default=None)
    a = p.parse_args()
    if not a.url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2

    filas = citas_con_su_fragmento(a.url)
    if not filas:
        print("no hay citas literales en la traza: nada que barrer", file=sys.stderr)
        return 2

    # EL DENOMINADOR, PARTIDO Y DECLARADO.
    fuera = [f for f in filas if f["fragmento_id"] not in f["en_contexto"]]
    comparables = [f for f in filas if f["fragmento_id"] in f["en_contexto"]]
    largos = [len(f["cita"]) for f in filas]

    print(f"CITAS LITERALES EMITIDAS (denominador): {len(filas)}")
    print(f"  podadas por procedencia fabricada, sin llegar a comparar: {len(fuera)}")
    print(f"  comparables: {len(comparables)}")
    print(f"  longitud de la cita: mediana {statistics.median(largos):.0f}  "
          f"min {min(largos)}  max {max(largos)}\n")

    resultados = {}
    for nivel in NIVELES:
        vs = [verificar(f, f["en_contexto"], nivel=nivel) for f in comparables]
        pasan = sum(1 for v in vs if v["veredicto"] == VERIFICADA)
        resultados[nivel] = pasan
        # SOBRE EL DENOMINADOR ENTERO, no solo sobre las comparables: si se reportara sobre las
        # comparables, cada poda por procedencia SUBIRIA el porcentaje de aciertos.
        print(f"{nivel:<34} {pasan:>3}/{len(comparables):<3} comparables  "
              f"({100 * pasan / len(filas):>5.1f} % del denominador entero)")

    print("\nGANANCIA DE CADA PASO SOBRE EL ANTERIOR (la carga de la prueba es suya):")
    orden = list(NIVELES)
    for previo, nivel in zip(orden, orden[1:]):
        gana = resultados[nivel] - resultados[previo]
        veredicto = "ENTRA" if gana > 0 else "NO ENTRA: no demostro ganancia"
        print(f"  {previo:<34} -> {nivel:<34} {gana:+d}  {veredicto}")

    # LA INTERACCION QUE MERECE MIRARSE: una cita mas larga tiene mas superficie donde equivocarse.
    # Si sale, el tope de 120 hace DOBLE trabajo -latencia y verificabilidad-. Es correlacion, no
    # experimento, y se dice.
    print("\nLONGITUD FRENTE A FALLO (correlacion, NO experimento):")
    nivel = "espacios+tipograficos"
    ok = [len(f["cita"]) for f in comparables
          if verificar(f, f["en_contexto"], nivel)["veredicto"] == VERIFICADA]
    mal = [len(f["cita"]) for f in comparables
           if verificar(f, f["en_contexto"], nivel)["veredicto"] != VERIFICADA]
    for etiqueta, grupo in (("pasan", ok), ("fallan", mal)):
        if grupo:
            print(f"  {etiqueta:<7} n={len(grupo):<3} mediana {statistics.median(grupo):>5.0f} car"
                  f"   >120 car: {sum(1 for x in grupo if x > 120)}")
        else:
            print(f"  {etiqueta:<7} n=0")

    tildes = sum(1 for f in comparables
                 if verificar(f, f["en_contexto"], nivel)["veredicto"] != VERIFICADA
                 and hay_acentos_perdidos(f["cita"], f["en_contexto"][f["fragmento_id"]]))
    print(f"\nde las que fallan, casarian SOLO quitando tildes: {tildes} "
          f"(no cambia el veredicto: es señal de REESCRITURA, no ruido)")

    motivos = Counter(verificar(f, f["en_contexto"], nivel)["motivo"] for f in filas
                      if verificar(f, f["en_contexto"], nivel)["veredicto"] == PODADA)
    if motivos:
        print(f"podas por motivo: {dict(motivos)}")

    if a.salida_json:
        with open(a.salida_json, "w", encoding="utf-8") as f:
            json.dump({"denominador": len(filas), "fuera_de_contexto": len(fuera),
                       "comparables": len(comparables), "por_nivel": resultados},
                      f, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
