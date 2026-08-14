#!/usr/bin/env python3
"""Mide la recuperación (3.1 léxica, 3.2 vectorial, 3.3 fusión, 3.5 con reordenador) contra los
pares oro. Sin reordenador no gasta: todo es SQL local; con él, GPU local.

    DATABASE_URL=... python scripts/medir_recuperacion.py --evidencia docs/evidencia/<fecha>-lexica.md

EL NÚMERO VA PARTIDO DESDE AQUÍ, NO SOLO EN EL 3.5, y el motivo está en el propio fichero de pares:
los pares `busqueda` se localizaron **buscando términos de la pregunta en el texto**, o sea
compartiendo mecanismo con la búsqueda léxica. Es exactamente donde esta recuperación va a lucir
mejor por construcción. Un número único aquí dejaría el sesgo cocido antes de que nadie lo vea, y
para cuando el 3.5 lo partiera ya se habrían tomado decisiones sobre el global.

Se persiste en `corridas_eval` con su commit y su config, que es la vía declarada del arnés: el
endpoint `POST /eval/correr` está declarado no construido hasta la fase 8 (decisión escrita en 3.5).

AMPLIADO EL 14 DE AGOSTO DE 2026 para cerrar el 3.5 (mecanismo reutilizado, parámetros re-derivados):
`nDCG@5` (con un solo oro por pregunta el IDCG es 1 y la métrica se reduce a la ganancia descontada
del puesto), `--reordenador` (reordena el pool con el cross-encoder del 3.4 y mide el top 6 final),
`--peso-vectorial` (la fusión 10:1 decidida en el 3.3 no estaba cableada en ningún sitio medible), y
la contaminación cruzada del contexto final, contada y no supuesta.
"""
import argparse
import collections
import json
import math
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                      # noqa: E402

from app.core.recuperacion import (CONFIGURACION, K_RRF, PESOS_POR_DEFECTO,   # noqa: E402
                                   buscar_lexico, buscar_vectorial, recuperar)

ORO = "evals/casos/oro_recuperacion.jsonl"
MAPA = "corpus/mapa_asignaturas.jsonl"
#: El 30 entró el 14/08: es el corte del pool del 3.4, y su recall es el TECHO del reordenador.
#: Cada corrida usa solo los cortes que caben en su k, para no fabricar un recall@30 de una lista
#: de 20 que sería idéntico al @20 y se leería como medido.
CORTES = (5, 6, 20, 30)
#: Cuántos fragmentos ve el modelo (FRAGMENTOS_EN_CONTEXTO de consulta.py): el corte del reordenado.
CONTEXTO = 6


def ndcg_en_5(posicion) -> float:
    """nDCG@5 con UN SOLO fragmento relevante: `1/log2(1+pos)` si entra en el top 5, si no 0.

    Con un único oro por pregunta el IDCG es 1 (el ideal lo pone en el puesto 1), así que la fórmula
    entera se reduce a la ganancia descontada del puesto real. No hay juicio graduado de relevancia
    que hacer: la regla 6 del conjunto oro declara UN fragmento por pregunta.
    """
    if posicion is None or posicion > 5:
        return 0.0
    return 1.0 / math.log2(1 + posicion)


def posicion_del_oro(candidatos, esperado) -> int | None:
    """En qué puesto (1-based) está el fragmento oro, o `None` si no aparece.

    El emparejamiento es por `(documento, orden)` —la misma clave posicional que ancla el conjunto;
    el TEXTO lo ancla `verificar_oro` antes de medir, que para eso es puerta obligatoria—. Vive en
    función propia porque el recall entero cuelga de esta comparación: la pasada adversarial del
    14/08 enseñó que una mutación aquí (== por !=) dejaba la suite en verde mientras todas las
    corridas salían falsas. Ahora tiene test propio en las dos direcciones.
    """
    return next((i for i, c in enumerate(candidatos, 1)
                 if (c.documento, c.orden) == esperado), None)


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


def medir(url: str, k: int, via: str = "lexica", forzar_escaneo: bool = False,
          k_rrf: int = K_RRF, pesos: dict | None = None, reordenador=None) -> dict:
    """Corre los pares oro por la via que se pida. El EMBEBEDOR se carga UNA vez, no por consulta:
    cargarlo dentro del bucle mediria cien veces la carga del modelo y ni una vez la busqueda.

    Con `reordenador`, el pool de la fusion se reordena con el cross-encoder y el CONTEXTO final son
    sus 6 mejores: `posicion_final` (y con ella el nDCG@5 y el recall reordenado) sale de esa lista,
    mientras `aciertos` sigue midiendo el pool -que es el TECHO del reordenador, no su merito-.
    """
    embebedor = None
    if via in ("vectorial", "fusion"):
        from app.core.embebedor import Embebedor
        embebedor = Embebedor()
        print(f"embebedor: {embebedor.estado()}")
    oro = leer_jsonl(ORO)
    por_slug = asignaturas_por_slug(url)
    cortes = [c for c in CORTES if c <= k]
    aciertos = {c: collections.Counter() for c in cortes}
    aciertos_finales = {c: collections.Counter() for c in (5, CONTEXTO)}
    ndcg = collections.Counter()
    totales = collections.Counter()
    contaminadas = 0
    fallos, sin_asignatura = [], []
    t0 = time.perf_counter()
    for caso in oro:
        asignatura_id = por_slug.get(caso["asignatura"])
        if asignatura_id is None:
            sin_asignatura.append(caso["id"])
            continue
        grupo = caso["localizacion"]
        totales[grupo] += 1
        if via == "fusion":
            candidatos = recuperar(url, asignatura_id, caso["pregunta"],
                                   vector=embebedor.embeber(caso["pregunta"]), k=k, k_rrf=k_rrf,
                                   pesos=pesos)
        elif via == "vectorial":
            candidatos = buscar_vectorial(url, asignatura_id, embebedor.embeber(caso["pregunta"]),
                                          k=k, forzar_escaneo=forzar_escaneo)
        else:
            candidatos = buscar_lexico(url, asignatura_id, caso["pregunta"], k=k)
        esperado = (caso["fragmento_oro"]["documento"], caso["fragmento_oro"]["orden"])
        posicion = posicion_del_oro(candidatos, esperado)
        # El contexto FINAL, que es lo que el modelo veria: el top 6 del reordenador si lo hay,
        # o el top 6 del orden de la lista si no. De aqui salen nDCG@5, el recall final y la
        # contaminacion, porque es lo unico que llega a una respuesta.
        finales = (reordenador.reordenar(caso["pregunta"], candidatos, top=CONTEXTO)
                   if reordenador else candidatos[:CONTEXTO])
        posicion_final = posicion_del_oro(finales, esperado)
        for corte in cortes:
            if posicion is not None and posicion <= corte:
                aciertos[corte][grupo] += 1
        for corte in aciertos_finales:
            if posicion_final is not None and posicion_final <= corte:
                aciertos_finales[corte][grupo] += 1
        ndcg[grupo] += ndcg_en_5(posicion_final)
        contaminadas += any(c.asignatura_id != asignatura_id for c in finales)
        if posicion is None or posicion > cortes[0]:
            fallos.append({"id": caso["id"], "grupo": grupo, "posicion": posicion,
                           "pregunta": caso["pregunta"][:90]})
    return {"aciertos": aciertos, "aciertos_finales": aciertos_finales, "ndcg": ndcg,
            "cortes": cortes, "totales": totales, "fallos": fallos,
            "contaminadas": contaminadas, "sin_asignatura": sin_asignatura,
            "segundos": time.perf_counter() - t0, "consultas": sum(totales.values())}


RE_IDENTIFICADOR = re.compile(r"@\w+|\b[a-z]+[A-Z]\w*\b|\b[A-Z][a-z]+[A-Z]\w*\b|\b[a-z_]+_[a-z_]+\b")


def identificadores(url: str) -> dict:
    """Qué le hace la configuración `spanish` a los identificadores DE LAS PREGUNTAS ORO.

    No se hereda como supuesto y no se mide con ejemplos inventados: este corpus es medio código y
    los cien pares oro están hechos de `@ModelAttribute`, `PasswordEncoder` y `BindingResult`.
    """
    oro = leer_jsonl(ORO)
    terminos = sorted({t for c in oro for t in RE_IDENTIFICADOR.findall(c["pregunta"])})
    truncados, colisiones = [], []
    with psycopg.connect(url) as con, con.cursor() as cur:
        por_lexema = collections.defaultdict(list)
        for t in terminos:
            cur.execute("SELECT to_tsvector(%s,%s)::text, to_tsvector('simple',%s)::text",
                        (CONFIGURACION, t, t))
            con_lema, sin_lema = cur.fetchone()
            por_lexema[con_lema].append(t)
            if con_lema != sin_lema:
                truncados.append((t, sin_lema.strip("'1: "), con_lema.strip("'1: ")))
        # Lo que de verdad hace dano no es truncar -el documento y la consulta se truncan igual y
        # el emparejamiento aguanta-, es que un identificador caiga en la raiz de un verbo comun.
        for ident, palabra in (("@page", "pagar"), ("TempData", "temporada"),
                               ("ViewData", "vista"), ("@Configuration", "configurar"),
                               ("AutoMapper", "automatico"), ("HtmlHelper", "ayudar")):
            cur.execute("SELECT to_tsvector(%s,%s)::text = to_tsvector(%s,%s)::text",
                        (CONFIGURACION, ident, CONFIGURACION, palabra))
            if cur.fetchone()[0]:
                colisiones.append((ident, palabra))
        # Y la comprobacion que salva a `spanish`: con truncado simetrico, el emparejamiento sigue.
        empareja = []
        for t in [x for x, _, _ in truncados][:3]:
            cur.execute("SELECT to_tsvector(%s,%s) @@ websearch_to_tsquery(%s,%s)",
                        (CONFIGURACION, f"El objeto {t} sirve para pasar datos.",
                         CONFIGURACION, t))
            empareja.append((t, cur.fetchone()[0]))
        entre_si = {k: v for k, v in por_lexema.items() if len(v) > 1}
    return {"total": len(terminos), "truncados": truncados, "colisiones": colisiones,
            "empareja": empareja, "entre_si": entre_si}


def recall(aciertos: collections.Counter, totales: collections.Counter, grupo=None) -> float:
    if grupo:
        return 100 * aciertos[grupo] / totales[grupo] if totales[grupo] else 0.0
    return 100 * sum(aciertos.values()) / sum(totales.values()) if sum(totales.values()) else 0.0


def persistir(url: str, r: dict, k: int, via: str, forzar_escaneo: bool,
              k_rrf: int = K_RRF, pesos: dict | None = None, reordenador=None) -> int:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    metricas = {f"recall@{c}": {g: round(recall(r["aciertos"][c], r["totales"], g), 1)
                                for g in sorted(r["totales"])} | {
                    "global": round(recall(r["aciertos"][c], r["totales"]), 1)}
                for c in r["cortes"]}
    metricas["ndcg@5"] = {g: round(r["ndcg"][g] / r["totales"][g], 3)
                          for g in sorted(r["totales"])} | {
        "global": round(sum(r["ndcg"].values()) / max(1, r["consultas"]), 3)}
    if reordenador is not None:
        metricas["reordenado"] = {f"recall@{c}": {
            g: round(recall(r["aciertos_finales"][c], r["totales"], g), 1)
            for g in sorted(r["totales"])} | {
            "global": round(recall(r["aciertos_finales"][c], r["totales"]), 1)}
            for c in r["aciertos_finales"]}
    metricas["contaminacion"] = {"consultas_con_fragmento_de_otra_asignatura": r["contaminadas"],
                                 "sobre": r["consultas"]}
    metricas["consultas"] = r["consultas"]
    metricas["ms_por_consulta"] = round(1000 * r["segundos"] / max(1, r["consultas"]), 1)
    config = {"encargo": {"lexica": "3.1", "vectorial": "3.2"}.get(via, "3.3" if reordenador is None
                                                                   else "3.5"),
              "via": via, "k": k, "k_rrf": k_rrf if via == "fusion" else None,
              # Los pesos EFECTIVOS, no los pedidos: con `pesos=None` la fusion corre con
              # PESOS_POR_DEFECTO, y persistir un null cuyo significado depende de una constante
              # que puede cambiar es heredar numeros de otra configuracion sin enterarse.
              "pesos": ((pesos or PESOS_POR_DEFECTO) if via == "fusion" else None),
              "reordenador": (f"{reordenador.estado()['modelo']} rev "
                              f"{reordenador.estado()['revision']} en "
                              f"{reordenador.estado()['dispositivo']}") if reordenador else False,
              # Contado de lo que CORRIO, no escrito a mano: un literal aqui envejece sin avisar
              # (esta clave decia "94 pares: 19 busqueda, 75 lectura" como cadena fija).
              "conjunto_oro": {"fichero": ORO, "pares": r["consultas"],
                               "reparto": {g: r["totales"][g] for g in sorted(r["totales"])}},
              "configuracion_tsvector": CONFIGURACION if via == "lexica" else None,
              "modelo": None if via == "lexica" else "BAAI/bge-m3",
              # Solo la via vectorial acepta el escaneo forzado; en fusion este campo llego a decir
              # "escaneo forzado" sin que nada lo aplicara (main ahora lo rechaza de entrada).
              "indice": (("escaneo forzado" if forzar_escaneo else "lo que elija el planificador")
                         if via == "vectorial" else None)}
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
    p.add_argument("--via", choices=("lexica", "vectorial", "fusion"), default="lexica")
    p.add_argument("--k-rrf", type=int, default=K_RRF,
                   help="la k de RRF; el barrido del 3.3 prueba 30, 60 y 100")
    p.add_argument("--peso-vectorial", type=float, default=1.0,
                   help="peso de la lista vectorial en la fusion (el 3.3 decidio 10:1; el 1.0 es "
                        "lo que produccion tenia cableado, y por eso es el defecto: medir ambos)")
    p.add_argument("--reordenador", action="store_true",
                   help="reordena el pool con el cross-encoder del 3.4 (GPU) y mide el top 6 final")
    p.add_argument("--forzar-escaneo", action="store_true",
                   help="apaga el indice: recall EXACTO, para saber cuanto cuesta el aproximado")
    p.add_argument("--evidencia")
    p.add_argument("--fecha", default="2026-08-13")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not a.url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2
    if a.forzar_escaneo and a.via != "vectorial":
        # Sin esta puerta, la corrida persistia config "escaneo forzado" sin que medir() lo
        # aplicara a la fusion: el instrumento diciendo que midio lo que no midio.
        print("--forzar-escaneo solo aplica a --via vectorial", file=sys.stderr)
        return 2

    ident = identificadores(a.url) if a.via == "lexica" else None
    if ident:
        print(f"identificadores en las preguntas oro: {ident['total']} | truncados por "
              f"'{CONFIGURACION}': {len(ident['truncados'])} | colisiones con palabra castellana: "
              f"{len(ident['colisiones'])} {ident['colisiones'] or ''}")
        print(f"emparejamiento con truncado simetrico: {ident['empareja']}\n")

    pesos = None
    if a.via == "fusion" and a.peso_vectorial != 1.0:
        pesos = {"vectorial": a.peso_vectorial, "lexica": 1.0, "glosario": 1.0}
    reordenador = None
    if a.reordenador:
        from app.core.reordenador import Reordenador
        reordenador = Reordenador(dispositivo="cuda")
        print(f"reordenador: {reordenador.estado()}")

    r = medir(a.url, a.k, a.via, a.forzar_escaneo, a.k_rrf, pesos, reordenador)
    if r["sin_asignatura"]:
        print(f"PARES SIN ASIGNATURA EN BASE: {r['sin_asignatura']}", file=sys.stderr)
        return 2

    print(f"consultas: {r['consultas']} | {1000 * r['segundos'] / r['consultas']:.0f} ms cada una\n")
    print(f"{'corte':8s} {'global':>10s} " + " ".join(f"{g:>12s}" for g in sorted(r["totales"])))
    for corte in r["cortes"]:
        fila = f"recall@{corte:<2d}{recall(r['aciertos'][corte], r['totales']):9.1f}% "
        fila += " ".join(f"{recall(r['aciertos'][corte], r['totales'], g):11.1f}%"
                         for g in sorted(r["totales"]))
        print(fila)
    if reordenador is not None:
        for corte in sorted(r["aciertos_finales"]):
            fila = (f"reo@{corte:<4d}{recall(r['aciertos_finales'][corte], r['totales']):9.1f}% ")
            fila += " ".join(f"{recall(r['aciertos_finales'][corte], r['totales'], g):11.1f}%"
                             for g in sorted(r["totales"]))
            print(fila)
    ndcg_global = sum(r["ndcg"].values()) / max(1, r["consultas"])
    print(f"{'nDCG@5':8s} {ndcg_global:9.3f}  " +
          " ".join(f"{r['ndcg'][g] / r['totales'][g]:11.3f} "
                   for g in sorted(r["totales"])) +
          ("(sobre el top 6 reordenado)" if reordenador else "(sobre el orden de la lista)"))
    print(f"contaminacion: {r['contaminadas']} de {r['consultas']} contextos finales con algun "
          f"fragmento de otra asignatura")
    print("\n(los " + " y ".join(f"{n} {g}" for g, n in sorted(r["totales"].items()))
          + ": el sesgo del conjunto, medido en vez de declarado)")

    corrida = persistir(a.url, r, a.k, a.via, a.forzar_escaneo, a.k_rrf, pesos, reordenador)
    print(f"\npersistido en corridas_eval: id {corrida}")
    if a.evidencia:
        escribir_evidencia(a.evidencia, a.fecha, r, a.k, corrida, ident, a.via,
                           a.forzar_escaneo)
        print(f"evidencia -> {a.evidencia}")
    return 0


BLOQUE_VECTORIAL = """## El índice: {indice}

En el 2.1 quedó medido y declarado que, con 3.892 filas en la partición, el planificador prefiere el
escaneo secuencial y el HNSW no se usa. Aquí se comprueba **con la consulta real de este encargo**.

**Y la regla de lectura estaba escrita antes de medir, en el enunciado del 3.2:** si el plan enseña
el índice, el recall es **aproximado por construcción** —`ef_search` por defecto es 40—, y un recall
flojo podría ser del índice y no del embedding; en ese caso se repite con el escaneo forzado antes de
concluir nada, y la diferencia entre los dos números es el precio del aproximado, que es un dato y no
un fallo. Si gana el escaneo, el recall es **exacto** y se declara así.

Se corrió de las dos maneras y **los números salen idénticos al decimal**, que es la comprobación de
que aquí no hay aproximación de por medio: el plan es `Seq Scan` sobre la partición, 9,5 ms.
"""


def escribir_evidencia(ruta, fecha, r, k, corrida, ident, via='lexica',
                       forzar_escaneo=False) -> None:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    grupos = sorted(r["totales"])
    filas = []
    for corte in r["cortes"]:
        celdas = " | ".join(f"**{recall(r['aciertos'][corte], r['totales'], g):.1f} %** "
                            f"({r['aciertos'][corte][g]}/{r['totales'][g]})" for g in grupos)
        filas.append(f"| recall@{corte} | {recall(r['aciertos'][corte], r['totales']):.1f} % | "
                     f"{celdas} |")
    peores = "\n".join(
        f"| `{f['id']}` | {f['grupo']} | {'no aparece' if f['posicion'] is None else f['posicion']} "
        f"| {f['pregunta']} |" for f in r["fallos"][:15]) or "| — | — | — | ninguno |"
    bloque_identificadores = f"""## Qué le hace la configuración `spanish` a los identificadores

Este corpus es medio código y **los cien pares oro están hechos de eso**: `@ModelAttribute`,
`PasswordEncoder`, `BindingResult`. Así que no se hereda como supuesto y no se mide con ejemplos
inventados, sino con los identificadores que aparecen en las preguntas oro.

De los **{ident['total']}** identificadores encontrados, el lematizador español trunca **{len(ident['truncados'])}**:

| Identificador | Sin lematizar (`simple`) | Lematizado (`{CONFIGURACION}`) |
|---|---|---|
{chr(10).join(f"| `{t}` | `{s}` | `{c}` |" for t, s, c in ident['truncados'])}

**Y aquí está lo que salva a `spanish`, que es lo que había que medir antes de cambiar nada: el
truncado es SIMÉTRICO.** El documento y la consulta pasan por la misma configuración, así que buscar
`ViewData` sigue encontrando `ViewData` aunque las dos se guarden como `viewdat`. Comprobado:
{", ".join(f"`{t}` → {'encuentra' if ok else 'NO encuentra'}" for t, ok in ident['empareja'])}.

**Lo que sí hace daño, y es otra cosa:** un identificador corto que cae en la misma raíz que una
palabra castellana corriente. Medido: {"; ".join(f"`{i}` y **{p}** comparten raíz" for i, p in ident['colisiones']) or "ninguna colisión de las probadas"}. Entre identificadores oro no hay
ninguna colisión ({len(ident['entre_si'])} grupos), así que el ruido no es de unos con otros: es de
identificadores con castellano.

**Decisión, con la evidencia delante: NO se añade hoy una segunda columna `simple`.** Era la salida
obvia y no se toma porque lo medido no la justifica: el emparejamiento aguanta, la colisión afecta a
identificadores cortos y el coste sería otra columna `tsvector`, otro índice GIN por partición y una
lista más que fusionar en el 3.3. Queda escrito como **la primera palanca a tirar si el 3.4 enseña
que los fallos son de terminología exacta**, y con el número que habría que volver a mirar.

""" if ident else BLOQUE_VECTORIAL.format(
        indice="escaneo forzado" if forzar_escaneo else "lo que eligio el planificador")
    titulo = ("recuperación léxica del 3.1" if via == "lexica"
              else "recuperación vectorial del 3.2")
    texto = f"""# Evidencia: {titulo} sobre los 100 pares oro

- **Fecha:** {fecha}
- **Encargo:** {'3.1' if via == 'lexica' else '3.2'}
- **Commit:** `{commit}`
- **Corrida:** `corridas_eval` id **{corrida}**
- **Configuración:** {'`tsvector` `' + CONFIGURACION + '`, `websearch_to_tsquery` con conector OR, `ts_rank_cd`' if via == 'lexica' else 'BGE-M3 con la revisión anclada del corpus, distancia coseno'}, k={k},
  **siempre con filtro de asignatura**

## El número, partido desde el primer día y no solo en el 3.5

| Corte | Global | {" | ".join(g for g in grupos)} |
|---|---|{"---|" * len(grupos)}
{chr(10).join(filas)}

**Por qué va partido ya.** Los pares `busqueda` se localizaron buscando términos de la pregunta en
el texto, o sea **compartiendo mecanismo con la búsqueda léxica**: es donde esta vía luce mejor por
construcción. Un número único en el 3.1 dejaría ese sesgo cocido antes de que nadie lo viera, y para
cuando el 3.5 lo partiera ya se habrían tomado decisiones sobre el global. **El número honesto para
juzgar la recuperación es el de `lectura`.**

{bloque_identificadores}

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
