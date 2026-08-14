#!/usr/bin/env python3
"""Calibración del umbral NLI y del suelo de cobertura (encargo 4.6). UNA corrida, plano después.

    DATABASE_URL=... python scripts/calibrar_nli.py

Método, escrito ANTES de correr (docs/evidencia/2026-08-14-calibracion-4.6.md):

- POSITIVOS: las afirmaciones `literal` con veredicto `verificada` (pasaron el 4.2) contra SU
  fragmento — entailed por su CITA, por construcción. Y la corrección del propietario: al NLI no se
  le da el fragmento sino la FRASE SELECCIONADA, así que cada positivo comprueba si esa frase
  CONTIENE la cita; si no la contiene, su fallo es de SELECCIÓN (suelo), no de umbral, y se cuenta
  aparte para que el barrido no mueva el umbral compensando un problema de selección.
- NEGATIVOS: la misma afirmación contra OTRO fragmento de su asignatura, excluyendo (a) el mismo
  documento —el solape de 64 tokens fabrica casi-duplicados por construcción— y (b) los pares que
  la lista de casi-duplicados del 1.8 (corpus/conflictos.jsonl, 858 medidos) relaciona con el
  fragmento verdadero: un negativo que en realidad sostiene la afirmación empuja el umbral hacia
  arriba por el motivo equivocado. El emparejado es DETERMINISTA (no hay azar que no se pueda
  reproducir).
- UNA corrida: se consulta el NLI una vez por par —también por debajo de cualquier suelo candidato,
  porque aquí se calibra el termómetro, no se usa— guardando cobertura y puntuación; el plano
  (suelo × umbral) se calcula después sin volver a llamar al modelo.
- La tubería es LA DE SERVICIO: `premisa_para` (ventana anclada o selección por frases, lo que el
  servicio haría), `parece_codigo` y `clasificar` importados del verificador, no reimplantados (el
  que comprueba no puede divergir en silencio del que produce).

El desempate está pre-escrito en la evidencia y este script SOLO lo aplica: entre los puntos con
CERO negativos aprobados, el que más positivos verifica; empate → umbral más bajo, luego suelo más
bajo. Los positivos perdidos del punto elegido se imprimen con su número, no se esconden.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                        # noqa: E402

from app.core.verificador_nli import (COBERTURA_MINIMA, UMBRAL, VerificadorNLI,   # noqa: E402
                                      localizar, parece_codigo, premisa_para)

CONFLICTOS = "corpus/conflictos.jsonl"
SUELOS = [round(0.05 * i, 2) for i in range(0, 11)]          # 0,00 .. 0,50
UMBRALES = [round(0.60 + 0.025 * i, 3) for i in range(15)]   # 0,60 .. 0,95

POSITIVOS = """
SELECT a.id, a.texto, a.detalle->>'cita' AS cita, a.fragmento_id,
       f.texto AS fragmento, f.asignatura_id, d.ruta AS documento, f.orden
  FROM afirmaciones a
  JOIN fragmentos f ON f.id = a.fragmento_id
  JOIN documentos d ON d.id = f.documento_id
 WHERE a.tipo = 'literal' AND a.veredicto = 'verificada' AND a.detalle->>'cita' IS NOT NULL
   -- 39 filas reales llevan texto='literal' (el generador emitio el TIPO como texto, era 13/08+):
   -- su hipotesis no es una frase y no miden ni seleccion ni umbral. Excluidas y DECLARADAS.
   AND a.texto <> 'literal'
   -- Y EL VEREDICTO TIENE QUE SER EL DEL 4.2, no el del NLI (cazado en la corrida 37 mirando a
   -- ojo los 12 positivos que no anclaban): desde que el NLI esta enchufado, una literal DEGRADADA
   -- que el NLI verifico tambien persiste 'verificada' -el mismo valor, otro verificador-, y su
   -- cita NO esta en el fragmento por construccion (por eso se degrado). Usarla de positivo seria
   -- calibrar el NLI con la garantia del propio NLI: el que comprueba compartiendo el supuesto.
   -- `nivel` solo lo escribe la comparacion de cadenas: es la firma del verificador correcto.
   AND a.detalle->'verificacion'->>'nivel' IS NOT NULL
 ORDER BY a.id
"""

CANDIDATOS = """
SELECT f.id, f.texto, d.ruta AS documento, f.orden
  FROM fragmentos f JOIN documentos d ON d.id = f.documento_id
 WHERE f.asignatura_id = %s
 ORDER BY f.id
"""


def casi_duplicados() -> set:
    """Pares (documento, orden) <-> (documento, orden) que el 1.8 midió como casi-duplicados."""
    enlaces = set()
    with open(CONFLICTOS, encoding="utf-8") as f:
        for linea in f:
            if not linea.strip():
                continue
            c = json.loads(linea)
            if c.get("tipo") != "casi_duplicado":
                continue
            a, b = c["a"], c["b"]
            enlaces.add(frozenset(((a["documento"], a["orden"]), (b["documento"], b["orden"]))))
    return enlaces


def negativo_para(indice: int, positivo: dict, candidatos: list, duplicados: set) -> dict | None:
    """El fragmento emparejado, DETERMINISTA: se recorre desde una posición que depende del índice
    y se acepta el primero que no comparta documento ni esté enlazado como casi-duplicado."""
    clave_real = (positivo["documento"], positivo["orden"])
    n = len(candidatos)
    for salto in range(n):
        c = candidatos[(indice * 7 + salto) % n]
        if c["documento"] == positivo["documento"]:
            continue
        if frozenset((clave_real, (c["documento"], c["orden"]))) in duplicados:
            continue
        return c
    return None


def medir_par(nli: VerificadorNLI, hipotesis: str, fragmento: str, cita: str | None = None) -> dict:
    # V3 (14/08, la ventana): la premisa la construye `premisa_para`, LA MISMA tuberia que el
    # servicio -con cita localizable, ventana anclada en su span; sin ella, la seleccion por
    # frases-. Se calibra sobre el instrumento arreglado, nunca sobre el roto, por tercera vez.
    # Los negativos van sin cita: su fragmento no la contiene por construccion.
    frase, cobertura, seleccion = premisa_para(fragmento, hipotesis, cita)
    # La contencion se comprueba con `localizar` y NO con `in` a pelo: la ventana contiene el span
    # CRUDO (con sus saltos de linea), y la cita viene con espacios simples, asi que el `in` crudo
    # diria "no la contiene" justo en los casos que la ventana arregla -el contador de la corrida
    # 34 otra vez, con otra cara-. Y sobre la premisa ENTERA, antes del recorte a 200.
    fila = {"cobertura": round(cobertura, 4), "frase": (frase or "")[:200],
            "seleccion": seleccion,
            "premisa_ancla_cita": bool(frase) and bool((cita or "").strip())
            and localizar(frase, cita) is not None}
    if frase is None:
        return {**fila, "etiqueta": None, "prob": None, "es_codigo": False}
    if parece_codigo(frase):
        return {**fila, "etiqueta": None, "prob": None, "es_codigo": True}
    etiqueta, prob = nli.clasificar(frase, hipotesis)
    return {**fila, "etiqueta": etiqueta, "prob": round(prob, 4), "es_codigo": False}


def celda(filas: list, suelo: float, umbral: float) -> dict:
    """Qué haría el servicio en (suelo, umbral) con cada fila ya medida. Sin volver al modelo."""
    pos = [f for f in filas if f["control"] == "positivo" and f["cuenta_para_umbral"]]
    neg = [f for f in filas if f["control"] == "negativo"]

    def juzgado(f):
        return f["etiqueta"] is not None and f["cobertura"] >= suelo

    def verificada(f):
        return juzgado(f) and f["etiqueta"] == "entailment" and f["prob"] >= umbral
    return {
        "pos_verificados": sum(1 for f in pos if verificada(f)),
        "pos_perdidos": sum(1 for f in pos if juzgado(f) and not verificada(f)),
        "pos_bajo_suelo": sum(1 for f in pos if f["etiqueta"] is not None and f["cobertura"] < suelo),
        "neg_aprobados": sum(1 for f in neg if verificada(f)),
    }


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")

    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute(POSITIVOS)
        columnas = [d.name for d in cur.description]
        positivos = [dict(zip(columnas, fila)) for fila in cur.fetchall()]
        candidatos_por_asig = {}
        for p in positivos:
            if p["asignatura_id"] not in candidatos_por_asig:
                cur.execute(CANDIDATOS, (p["asignatura_id"],))
                cols = [d.name for d in cur.description]
                candidatos_por_asig[p["asignatura_id"]] = [dict(zip(cols, f))
                                                           for f in cur.fetchall()]
    duplicados = casi_duplicados()
    print(f"positivos: {len(positivos)} | enlaces casi-duplicado del 1.8: {len(duplicados)}")

    nli = VerificadorNLI()
    filas = []
    for i, p in enumerate(positivos):
        fila = medir_par(nli, p["texto"], p["fragmento"], p["cita"])
        fila.update({"control": "positivo", "afirmacion_id": p["id"],
                     # LA SEPARACION SELECCION/UMBRAL: si la premisa elegida no ancla la cita,
                     # el fallo de este par es del suelo/seleccion y NO cuenta para el umbral.
                     # Sobre la premisa ENTERA (ver medir_par), no sobre el recorte persistido.
                     "cuenta_para_umbral": fila["premisa_ancla_cita"]})
        filas.append(fila)
        negativo = negativo_para(i, p, candidatos_por_asig[p["asignatura_id"]], duplicados)
        if negativo is None:
            continue
        filas.append({**medir_par(nli, p["texto"], negativo["texto"]),
                      "control": "negativo", "afirmacion_id": p["id"],
                      "fragmento_negativo": negativo["id"], "cuenta_para_umbral": True})

    pos = [f for f in filas if f["control"] == "positivo"]
    seleccion_mal = [f for f in pos if not f["cuenta_para_umbral"]]
    print(f"pares medidos: {len(filas)} ({len(pos)} positivos, {len(filas)-len(pos)} negativos)")
    print(f"positivos cuya premisa NO ancla la cita (fallo de SELECCION, no de "
          f"umbral): {len(seleccion_mal)} de {len(pos)}")
    por_seleccion = {}
    for f in pos:
        por_seleccion[f["seleccion"]] = por_seleccion.get(f["seleccion"], 0) + 1
    print(f"positivos por origen de la premisa: {por_seleccion}")

    plano = {}
    for s in SUELOS:
        for u in UMBRALES:
            plano[(s, u)] = celda(filas, s, u)
    factibles = {k: v for k, v in plano.items() if v["neg_aprobados"] == 0}
    if factibles:
        # El desempate PRE-ESCRITO: mas positivos verificados; luego umbral mas bajo; luego suelo.
        elegido = max(factibles, key=lambda k: (factibles[k]["pos_verificados"], -k[1], -k[0]))
    else:
        # Tampoco esta rama elige por resultado: manda no aprobar negativos, asi que se coge el
        # punto con MENOS negativos aprobados y, entre esos, mas positivos verificados.
        peor = min(v["neg_aprobados"] for v in plano.values())
        casi = {k: v for k, v in plano.items() if v["neg_aprobados"] == peor}
        elegido = max(casi, key=lambda k: (casi[k]["pos_verificados"], -k[1], -k[0]))
    s, u = elegido
    r = plano[elegido]
    print(f"\nELEGIDO (desempate pre-escrito): suelo={s} umbral={u}")
    print(f"  positivos verificados: {r['pos_verificados']} | perdidos por umbral: "
          f"{r['pos_perdidos']} | bajo el suelo: {r['pos_bajo_suelo']} | negativos aprobados: "
          f"{r['neg_aprobados']}")
    # La celda que se imprime es LA MISMA que dice el rotulo: la primera version indexaba (.., 0.8)
    # con una etiqueta que decia umbral=0.6 -el rotulo mintiendo sobre que celda enseña-.
    print(f"  (en servicio: suelo={COBERTURA_MINIMA} umbral={UMBRAL} -> "
          f"{plano[(COBERTURA_MINIMA, UMBRAL)]})")

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute("INSERT INTO corridas_eval (commit_sha, config, metricas) VALUES (%s,%s,%s)"
                    " RETURNING id",
                    (commit,
                     json.dumps({"encargo": "4.6", "que": "plano suelo x umbral del NLI",
                                 "seleccion": "v3: ventana anclada en el span de la cita "
                                              "(premisa_para, la misma tuberia que el servicio)",
                                 "modelo": nli.modelo.config._name_or_path,
                                 "controles": {"positivos": len(pos),
                                               "negativos": len(filas) - len(pos),
                                               "seleccion_mal": len(seleccion_mal)},
                                 "desempate": "pre-escrito en la evidencia: 0 negativos, max "
                                              "positivos, umbral bajo, suelo bajo"}),
                     json.dumps({"elegido": {"suelo": s, "umbral": u, **r},
                                 "plano": [{"suelo": k[0], "umbral": k[1], **v}
                                           for k, v in sorted(plano.items())],
                                 "filas": filas}, ensure_ascii=False)))
        print(f"persistido en corridas_eval: id {cur.fetchone()[0]}")
        con.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
