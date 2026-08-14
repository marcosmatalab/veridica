#!/usr/bin/env python3
"""Distribución de veredictos ANTES/DESPUÉS de la ventana anclada, sobre las filas reales.

    DATABASE_URL=... python scripts/comparar_instrumentos_nli.py

Es el número que decide cuánto se ganó con la ventana (orden del propietario, 14/08/2026): no el
plano de controles —que mide sobre positivos por construcción— sino qué habría dicho el verificador
sobre las afirmaciones REALES de la base con el instrumento viejo y con el nuevo.

QUÉ SE COMPARA, y las dos declaraciones que hacen el número honesto:

- **ANTES** es el instrumento v2 (selección por frases con ancla de cita, ADR 0020 v2): ya no
  existe en el código, así que su política se RECONSTRUYE aquí —premisa de `seleccionar_frase`,
  las cuatro salidas de `verificar` copiadas con su suelo y su umbral de servicio (0,10 / 0,60)—.
  La reconstrucción es un espejo declarado, no el código que corrió: el número "antes" lleva esa
  coletilla.
- **DESPUÉS** es `verificar()` DE VERDAD, el que queda desplegado: ninguna reconstrucción en el
  lado que se publica.
- Las `parafrasis` almacenadas NO llevan `apoyo` —el campo nace con la ventana—, así que su
  ganancia NO SE PUEDE MEDIR sobre datos almacenados: el instrumento no lo permite y se escribe,
  no se estima (la misma regla que la limitación DWES del 4.6). Lo que sí se mide en ellas es que
  el instrumento nuevo no las EMPEORA: sin ancla, `premisa_para` cae a la selección de siempre.
- Las filas rotas del generador (`texto = 'literal'`, 39 declaradas en el 4.6) se excluyen aquí
  igual que en la calibración, con su cuenta impresa.

El conjunto elegible se RECOMPUTA con la maquinaria del 4.2 (¿la cita casa en nivel de servicio?)
en vez de leerse de los veredictos persistidos: los veredictos viejos salieron de instrumentos
viejos, y elegir la muestra por el veredicto sería elegirla por el síntoma (principio 11).
"""
import json
import os
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                        # noqa: E402

from app.core.verificador_literal import NIVEL_POR_DEFECTO, NIVELES   # noqa: E402
from app.core.verificador_nli import (COBERTURA_MINIMA, UMBRAL,       # noqa: E402
                                      VerificadorNLI, parece_codigo, seleccionar_frase)

#: Los parámetros del instrumento v2 EN SERVICIO cuando se ordenó esta medida (ADR 0020 v2,
#: corrida 36). Fijados aquí como literales a propósito: si el plano v3 mueve las constantes del
#: módulo, el "antes" tiene que seguir siendo el de ayer, no moverse con ellas.
SUELO_V2, UMBRAL_V2 = 0.10, 0.60

FILAS = """
SELECT a.id, a.tipo, a.texto, a.detalle->>'cita' AS cita, f.texto AS fragmento
  FROM afirmaciones a
  JOIN fragmentos f ON f.id = a.fragmento_id
 WHERE a.tipo IN ('parafrasis', 'literal')
 ORDER BY a.id
"""


def politica(etiqueta, prob, umbral):
    """Las cuatro salidas de `verificar`, sin el objeto: para el espejo v2."""
    if etiqueta == "contradiction":
        return "podada"
    if etiqueta == "entailment" and prob >= umbral:
        return "verificada"
    return "reintento_con_señal"


def veredicto_v2(nli, cache, hipotesis, fragmento, cita):
    frase, cobertura = seleccionar_frase(fragmento, hipotesis, cita)
    if frase is None or cobertura < SUELO_V2:
        return "no_verificable"
    if parece_codigo(frase):
        return "no_verificable"
    if (frase, hipotesis) not in cache:
        cache[(frase, hipotesis)] = nli.clasificar(frase, hipotesis)
    return politica(*cache[(frase, hipotesis)], UMBRAL_V2)


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")
    normalizar = NIVELES[NIVEL_POR_DEFECTO]

    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute(FILAS)
        columnas = [d.name for d in cur.description]
        filas = [dict(zip(columnas, f)) for f in cur.fetchall()]

    rotas = [f for f in filas if f["texto"] == "literal"]
    filas = [f for f in filas if f["texto"] != "literal"]
    elegibles = []
    for f in filas:
        if f["tipo"] == "parafrasis":
            elegibles.append({**f, "clase": "parafrasis", "cita_nli": None})
        elif (f["cita"] or "").strip() and normalizar(f["cita"]) not in normalizar(f["fragmento"]):
            # La degradada del 4.2, recomputada: cita presente que NO casa en nivel de servicio.
            elegibles.append({**f, "clase": "literal_degradada", "cita_nli": f["cita"]})
    print(f"filas leidas: {len(filas) + len(rotas)} | rotas texto='literal' excluidas: {len(rotas)}")
    print(f"elegibles para NLI: {len(elegibles)} "
          f"({sum(1 for e in elegibles if e['clase'] == 'parafrasis')} parafrasis, "
          f"{sum(1 for e in elegibles if e['clase'] == 'literal_degradada')} degradadas)")

    nli = VerificadorNLI()
    cache = {}
    resultado = []
    for e in elegibles:
        antes = veredicto_v2(nli, cache, e["texto"], e["fragmento"], e["cita_nli"])
        d = nli.verificar(e["texto"], e["fragmento"], e["cita_nli"])
        resultado.append({"afirmacion_id": e["id"], "clase": e["clase"], "antes": antes,
                          "despues": d["veredicto"], "seleccion": d.get("seleccion")})

    for clase in ("parafrasis", "literal_degradada"):
        del_grupo = [r for r in resultado if r["clase"] == clase]
        print(f"\n{clase} (n={len(del_grupo)})")
        print(f"  antes  : {dict(Counter(r['antes'] for r in del_grupo))}")
        print(f"  despues: {dict(Counter(r['despues'] for r in del_grupo))}")
        print(f"  premisa por: {dict(Counter(r['seleccion'] for r in del_grupo))}")
        cambios = Counter((r["antes"], r["despues"]) for r in del_grupo
                          if r["antes"] != r["despues"])
        print(f"  cambios de veredicto: {dict(cambios) or 'ninguno'}")

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute("INSERT INTO corridas_eval (commit_sha, config, metricas) VALUES (%s,%s,%s)"
                    " RETURNING id",
                    (commit,
                     json.dumps({"que": "distribucion de veredictos antes/despues de la ventana",
                                 "antes": {"instrumento": "v2 reconstruido (espejo declarado)",
                                           "suelo": SUELO_V2, "umbral": UMBRAL_V2},
                                 "despues": {"instrumento": "verificar() real",
                                             "suelo": COBERTURA_MINIMA, "umbral": UMBRAL},
                                 "limite": "las parafrasis almacenadas no llevan apoyo (el campo "
                                           "nace con la ventana): su ganancia no es medible sobre "
                                           "datos almacenados y se declara en vez de estimarse",
                                 "excluidas_texto_literal": len(rotas)}),
                     json.dumps({"filas": resultado}, ensure_ascii=False)))
        print(f"\npersistido en corridas_eval: id {cur.fetchone()[0]}")
        con.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
