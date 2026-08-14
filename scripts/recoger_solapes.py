#!/usr/bin/env python3
"""Recoge la distribución de solapes del portero (4.5) con consultas REALES, para el barrido del 4.6.

    DATABASE_URL=... python scripts/recoger_solapes.py --base http://127.0.0.1:8000 [--limite 40]

## POR QUÉ HACEN FALTA CONSULTAS NUEVAS Y NO VALE LO GUARDADO

El umbral del portero decide, frase a frase, si la prosa va **marcada**. Barrerlo pide la
distribución de solapes de **todas** las frases juzgadas, y las respuestas anteriores al 2.5 solo
guardaban el de las **podadas** (hasta cinco por respuesta). Con esa mitad se puede contestar *"¿qué
volvería si bajo el umbral?"* y **no** *"¿qué se marcaría si lo subo?"*, que es justo la pregunta de
hoy: desde que el portero marca en vez de podar, el error caro es el falso positivo y la dirección
de calibración es **hacia arriba** (ADR 0021).

## DE DÓNDE SALEN LAS PREGUNTAS, y por qué de ahí

De los **conjuntos congelados** del 4.0/5.x (`fuga_de_solucion`, `fuera_de_temario`,
`premisas_falsas`) y del **conjunto oro** del 3.0. Dos motivos: son preguntas reales del temario, y
—el que decide— **están congeladas con su sha**, así que el conjunto sobre el que se calibra no lo
elige quien calibra. Se corren, no se ajustan al resultado.

El script **no decide ningún umbral**: recoge y persiste. El barrido y su desempate van aparte, con
el criterio escrito antes de mirar la tabla.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                       # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parents[1]
CONGELADOS = ("fuga_de_solucion", "fuera_de_temario", "premisas_falsas")
ORO = RAIZ / "evals" / "casos" / "oro_recuperacion.jsonl"


#: La asignatura de los pares oro, que los guardan por NOMBRE y no por id. 29 es DWES, que es la
#: asignatura del conjunto oro corregido al 100 % (limitación declarada en el 4.6).
ASIGNATURA_ORO = 29


def _texto_del_caso(caso: dict) -> str:
    """La pregunta que se le hace al sistema, según cómo la guarde cada conjunto.

    **Los tres conjuntos no comparten esquema y eso NO se uniformiza aquí**: `fuga_de_solucion`
    lleva `ejercicio` + `turno_alumno` porque su caso es una conversación; los otros dos llevan
    `pregunta`. Tocar los ficheros para igualarlos rompería su sha congelado, que es justo la
    promesa que los hace útiles.
    """
    if caso.get("turno_alumno"):
        ejercicio = caso.get("ejercicio") or ""
        return f"{ejercicio}\n\n{caso['turno_alumno']}".strip()
    return caso.get("pregunta") or caso.get("texto") or ""


def preguntas(limite: int) -> list:
    """Las preguntas de los conjuntos congelados y del oro, en orden estable y sin azar."""
    salida = []
    for nombre in CONGELADOS:
        ruta = RAIZ / "evals" / "casos" / f"{nombre}.jsonl"
        if not ruta.exists():
            continue
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            caso = json.loads(linea)
            texto = _texto_del_caso(caso)
            if texto:
                salida.append({"origen": nombre, "texto": texto,
                               # `asignatura` en estos conjuntos ya es el id numerico.
                               "asignatura_id": caso.get("asignatura") or ASIGNATURA_ORO,
                               "modo": caso.get("modo") or "responder"})
    if ORO.exists():
        for linea in ORO.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            caso = json.loads(linea)
            if caso.get("pregunta"):
                # El oro guarda la asignatura por NOMBRE; el endpoint quiere el id.
                salida.append({"origen": "oro", "texto": caso["pregunta"],
                               "asignatura_id": ASIGNATURA_ORO, "modo": "responder"})
    return salida[:limite]


def consultar(base: str, pregunta: dict, timeout: float = 120.0):
    """Una consulta por el camino REAL. Devuelve `(respuesta_id, tramos)`.

    **LOS TRAMOS SE GUARDAN AQUI, CON SU TEXTO, Y NO EN EL SERVICIO.** La primera version de este
    script recogia solo los NUMEROS que la traza persiste, y al barrer el umbral resulto que no se
    podian mirar los casos: el criterio elegia 0,70 y no habia forma de ver si las frases que 0,70
    marca de mas son prosa legitima o no. Un agregado no miente, promedia — y al promediar disuelve
    justo la estructura que señala la causa. El arnes de evaluacion se queda el texto (lo lee del
    SSE de todas formas) y el servicio sigue persistiendo lo mismo que antes.
    """
    cuerpo = json.dumps({"texto": pregunta["texto"], "asignatura_id": pregunta.get("asignatura_id"),
                         "modo": pregunta.get("modo", "responder")}).encode()
    peticion = urllib.request.Request(f"{base}/consulta", data=cuerpo,
                                      headers={"Content-Type": "application/json"})
    tramos = []
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as flujo:
            for linea in flujo:
                linea = linea.decode("utf-8", "replace").strip()
                if not linea.startswith("data: "):
                    continue
                datos = json.loads(linea[6:])
                if "respaldada" in datos and "t" in datos:
                    tramos.append({"texto": datos["t"].strip(), "respaldada": datos["respaldada"],
                                   "solape": datos["solape"]})
                elif "respuesta_id" in datos:
                    return datos.get("respuesta_id"), tramos
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        # UNA CONSULTA QUE FALLA NO PARA LA RECOGIDA, PERO SE CUENTA: si se descartara en silencio,
        # la muestra quedaria elegida por el exito, que es el sesgo que este repo persigue.
        print(f"  fallo: {type(e).__name__}: {e}", file=sys.stderr)
    return None, tramos


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://127.0.0.1:8000")
    p.add_argument("--limite", type=int, default=40)
    a = p.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")

    casos = preguntas(a.limite)
    print(f"preguntas: {len(casos)} (congelados + oro, en orden estable)")
    ids, fallos, frases = [], 0, []
    for i, caso in enumerate(casos, 1):
        t0 = time.perf_counter()
        rid, tramos = consultar(a.base, caso)
        if rid is None:
            fallos += 1
        else:
            ids.append(rid)
        frases.extend({**t, "respuesta_id": rid, "origen": caso["origen"]}
                      for t in tramos if t["texto"])
        print(f"  {i}/{len(casos)} [{caso['origen']}] respuesta={rid} "
              f"({(time.perf_counter()-t0)*1000:.0f} ms)")

    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute("SELECT id, etapas->'generacion'->'cobertura', etapas->'generacion'->'ritmo',"
                    "       abstencion FROM respuestas WHERE id = ANY(%s) ORDER BY id", (ids,))
        filas = cur.fetchall()

    solapes, ritmos = [], []
    for rid, cobertura, ritmo, abstencion in filas:
        for s in ((cobertura or {}).get("solapes") or []):
            solapes.append({**s, "respuesta_id": rid})
        if ritmo and ritmo.get("minimo_observado") is not None:
            ritmos.append({"respuesta_id": rid, "minimo_observado": ritmo["minimo_observado"],
                           "tokens": ritmo.get("tokens"), "abstencion": abstencion})

    juzgadas = [s for s in solapes if not s["corta"]]
    print(f"\nrespuestas leidas: {len(filas)} | consultas fallidas: {fallos}")
    print(f"frases con solape: {len(solapes)} (de ellas {len(solapes)-len(juzgadas)} pasaron por "
          f"CORTAS, que es un pase por diseño y no una medida del umbral)")
    print(f"frases CON SU TEXTO, para poder mirarlas a ojo: {len(frases)}")
    print(f"ritmos con peor momento: {len(ritmos)}")

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute("INSERT INTO corridas_eval (commit_sha, config, metricas) VALUES (%s,%s,%s)"
                    " RETURNING id",
                    (commit,
                     json.dumps({"encargo": "4.6", "que": "recogida de solapes del portero y del "
                                                          "peor ritmo, con consultas reales",
                                 "fuente": "conjuntos congelados + oro (no los elige quien calibra)",
                                 "consultas": len(casos), "fallidas": fallos,
                                 "portero": "MARCA (ADR 0021): la direccion de calibracion es "
                                            "hacia ARRIBA"}),
                     json.dumps({"solapes": solapes, "ritmos": ritmos, "frases": frases},
                                ensure_ascii=False)))
        print(f"persistido en corridas_eval: id {cur.fetchone()[0]}")
        con.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
