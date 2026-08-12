#!/usr/bin/env python3
"""Mide la recuperación léxica del 3.1 contra los 100 pares oro. No gasta: todo es SQL local.

    DATABASE_URL=... python scripts/medir_recuperacion.py --evidencia docs/evidencia/<fecha>-lexica.md

EL NÚMERO VA PARTIDO DESDE AQUÍ, NO SOLO EN EL 3.5, y el motivo está en el propio fichero de pares:
los 19 pares `busqueda` se localizaron **buscando términos de la pregunta en el texto**, o sea
compartiendo mecanismo con la búsqueda léxica. Es exactamente donde esta recuperación va a lucir
mejor por construcción. Un número único aquí dejaría el sesgo cocido antes de que nadie lo vea, y
para cuando el 3.5 lo partiera ya se habrían tomado decisiones sobre el global.

Se persiste en `corridas_eval` con su commit y su config, que es la vía declarada del arnés: el
endpoint `POST /eval/correr` está declarado no construido hasta la fase 8 (decisión escrita en 3.5).
"""
import argparse
import collections
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                      # noqa: E402

from app.core.recuperacion import CONFIGURACION, buscar_lexico      # noqa: E402

ORO = "evals/casos/oro_recuperacion.jsonl"
MAPA = "corpus/mapa_asignaturas.jsonl"
CORTES = (5, 20)


def leer_jsonl(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def asignaturas_por_slug(url: str) -> dict:
    """slug del par oro -> asignatura_id, pasando por el mapa del 2.1 y por la base."""
    mapa = {e["clave"]: e for e in leer_jsonl(MAPA) if not e.get("excluido")}
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute("SELECT titulacion, codigo, id FROM asignaturas")
        por_codigo = {(t, c): i for t, c, i in cur.fetchall()}
    salida = {}
    for entrada in mapa.values():
        clave = (entrada["titulacion_duena"], entrada["codigo"])
        if clave in por_codigo:
            salida[entrada["slug"]] = por_codigo[clave]
    return salida


def medir(url: str, k: int) -> dict:
    oro = leer_jsonl(ORO)
    por_slug = asignaturas_por_slug(url)
    aciertos = {c: collections.Counter() for c in CORTES}
    totales = collections.Counter()
    fallos, sin_asignatura = [], []
    t0 = time.perf_counter()
    for caso in oro:
        asignatura_id = por_slug.get(caso["asignatura"])
        if asignatura_id is None:
            sin_asignatura.append(caso["id"])
            continue
        grupo = caso["localizacion"]
        totales[grupo] += 1
        candidatos = buscar_lexico(url, asignatura_id, caso["pregunta"], k=k)
        esperado = (caso["fragmento_oro"]["documento"], caso["fragmento_oro"]["orden"])
        posicion = next((i for i, c in enumerate(candidatos, 1)
                         if (c.documento, c.orden) == esperado), None)
        for corte in CORTES:
            if posicion is not None and posicion <= corte:
                aciertos[corte][grupo] += 1
        if posicion is None or posicion > CORTES[0]:
            fallos.append({"id": caso["id"], "grupo": grupo, "posicion": posicion,
                           "pregunta": caso["pregunta"][:90]})
    return {"aciertos": aciertos, "totales": totales, "fallos": fallos,
            "sin_asignatura": sin_asignatura, "segundos": time.perf_counter() - t0,
            "consultas": sum(totales.values())}


def recall(aciertos: collections.Counter, totales: collections.Counter, grupo=None) -> float:
    if grupo:
        return 100 * aciertos[grupo] / totales[grupo] if totales[grupo] else 0.0
    return 100 * sum(aciertos.values()) / sum(totales.values()) if sum(totales.values()) else 0.0


def persistir(url: str, r: dict, k: int) -> int:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    metricas = {f"recall@{c}": {g: round(recall(r["aciertos"][c], r["totales"], g), 1)
                                for g in sorted(r["totales"])} | {
                    "global": round(recall(r["aciertos"][c], r["totales"]), 1)}
                for c in CORTES}
    metricas["consultas"] = r["consultas"]
    metricas["ms_por_consulta"] = round(1000 * r["segundos"] / max(1, r["consultas"]), 1)
    config = {"encargo": "3.1", "via": "lexica", "configuracion_tsvector": CONFIGURACION,
              "k": k, "reordenador": False, "vectorial": False}
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute("INSERT INTO corridas_eval (commit_sha, config, metricas)"
                    " VALUES (%s,%s,%s) RETURNING id",
                    (commit, json.dumps(config), json.dumps(metricas, ensure_ascii=False)))
        corrida = cur.fetchone()[0]
        con.commit()
    return corrida


def main() -> int:
    p = argparse.ArgumentParser(description="Recall léxico sobre los pares oro (encargo 3.1).")
    p.add_argument("--url", default=os.environ.get("DATABASE_URL"))
    p.add_argument("--k", type=int, default=20)
    p.add_argument("--evidencia")
    p.add_argument("--fecha", default="2026-08-13")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not a.url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2

    r = medir(a.url, a.k)
    if r["sin_asignatura"]:
        print(f"PARES SIN ASIGNATURA EN BASE: {r['sin_asignatura']}", file=sys.stderr)
        return 2

    print(f"consultas: {r['consultas']} | {1000 * r['segundos'] / r['consultas']:.0f} ms cada una\n")
    print(f"{'corte':8s} {'global':>10s} " + " ".join(f"{g:>12s}" for g in sorted(r["totales"])))
    for corte in CORTES:
        fila = f"recall@{corte:<2d}{recall(r['aciertos'][corte], r['totales']):9.1f}% "
        fila += " ".join(f"{recall(r['aciertos'][corte], r['totales'], g):11.1f}%"
                         for g in sorted(r["totales"]))
        print(fila)
    print("\n(los " + " y ".join(f"{n} {g}" for g, n in sorted(r["totales"].items()))
          + ": el sesgo del conjunto, medido en vez de declarado)")

    corrida = persistir(a.url, r, a.k)
    print(f"\npersistido en corridas_eval: id {corrida}")
    if a.evidencia:
        escribir_evidencia(a.evidencia, a.fecha, r, a.k, corrida)
        print(f"evidencia -> {a.evidencia}")
    return 0


def escribir_evidencia(ruta, fecha, r, k, corrida) -> None:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    grupos = sorted(r["totales"])
    filas = []
    for corte in CORTES:
        celdas = " | ".join(f"**{recall(r['aciertos'][corte], r['totales'], g):.1f} %** "
                            f"({r['aciertos'][corte][g]}/{r['totales'][g]})" for g in grupos)
        filas.append(f"| recall@{corte} | {recall(r['aciertos'][corte], r['totales']):.1f} % | "
                     f"{celdas} |")
    peores = "\n".join(
        f"| `{f['id']}` | {f['grupo']} | {'no aparece' if f['posicion'] is None else f['posicion']} "
        f"| {f['pregunta']} |" for f in r["fallos"][:15]) or "| — | — | — | ninguno |"
    texto = f"""# Evidencia: recuperación léxica del 3.1 sobre los 100 pares oro

- **Fecha:** {fecha}
- **Encargo:** 3.1
- **Commit:** `{commit}`
- **Corrida:** `corridas_eval` id **{corrida}**
- **Configuración:** `tsvector` `{CONFIGURACION}`, `websearch_to_tsquery`, `ts_rank_cd`, k={k},
  **siempre con filtro de asignatura**

## El número, partido desde aquí y no solo en el 3.5

| Corte | Global | {" | ".join(g for g in grupos)} |
|---|---|{"---|" * len(grupos)}
{chr(10).join(filas)}

**Por qué va partido ya.** Los pares `busqueda` se localizaron buscando términos de la pregunta en
el texto, o sea **compartiendo mecanismo con la búsqueda léxica**: es donde esta vía luce mejor por
construcción. Un número único en el 3.1 dejaría ese sesgo cocido antes de que nadie lo viera, y para
cuando el 3.5 lo partiera ya se habrían tomado decisiones sobre el global. **El número honesto para
juzgar la recuperación es el de `lectura`.**

## Los que no entran en el top 5

| Par | Grupo | Posición | Pregunta |
|---|---|---|---|
{peores}

## Cómo se reproduce

```bash
DATABASE_URL=... python scripts/medir_recuperacion.py --evidencia {ruta}
```

No gasta dinero: es SQL contra la base local. Antes de correrlo, `python scripts/verificar_oro.py`,
que es la regla del 3.0 —un par oro desplazado no da error, da ruido con aspecto de dato—.
"""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)


if __name__ == "__main__":
    sys.exit(main())
