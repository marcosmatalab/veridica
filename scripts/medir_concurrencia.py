#!/usr/bin/env python3
"""Punta a punta con n≥20, y el techo de consultas simultáneas (requisitos de producto del 3.4).

    DATABASE_URL=... python scripts/medir_concurrencia.py --api http://127.0.0.1:8001 --n 20
    DATABASE_URL=... python scripts/medir_concurrencia.py --api http://127.0.0.1:8001 --concurrencia 1,2,5,10

**ESTE SCRIPT GASTA: cada consulta es una llamada real al proveedor.** Está fuera de la puerta por
eso, igual que `humo_proveedor.py`. Coste medido por consulta en el 3.3: 0,000584 EUR.

DOS PREGUNTAS DISTINTAS, Y POR ESO DOS MODOS.

**1) El p95 de punta a punta, que hasta hoy NO EXISTÍA.** Los 3.076 ms del 3.3 eran una media de
pocas corridas, y el requisito de producto —5 segundos— **se cumple en p95, no en p50**. El tiempo
del modelo varía mucho más que el nuestro (la recuperación entera son 79 ms de los 2.267 del TTFT),
así que sin p95 la frase "cabemos en 5 s" es una afirmación sobre el caso bueno.

**2) Si algo BLOQUEA el bucle de eventos, que es lo urgente.** `/consulta` es un `def` síncrono que
devuelve un `StreamingResponse` sobre un generador síncrono; FastAPI y Starlette llevan los dos al
threadpool, así que **en teoría** no bloquean. Pero "en teoría" es exactamente lo que este repo no
acepta: un reordenado de 419 ms corriendo en el bucle congelaría a TODOS los alumnos que ya están
recibiendo texto, y eso no se ve con una sola petición. La firma que lo delata: **si el p95 crece
linealmente desde N=2, hay serialización; si se mantiene plano hasta saturar, no la hay.**

Se mide el TTFT del alumno además del total, porque son cosas distintas bajo carga: el total puede
crecer por la cola de la GPU (legítimo y esperado) mientras el TTFT se mantiene, y confundirlos haría
culpar al bucle de eventos de lo que es el reordenador.
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx        # noqa: E402
import psycopg      # noqa: E402

ORO = "evals/casos/oro_recuperacion.jsonl"
MAPA = "corpus/mapa_asignaturas.jsonl"
PRESUPUESTO_MS = int(os.environ.get("PRESUPUESTO_CONSULTA_MS") or 5000)


def leer_jsonl(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def asignaturas_por_slug(url: str) -> dict:
    mapa = {e["clave"]: e for e in leer_jsonl(MAPA) if not e.get("excluido")}
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute("SELECT titulacion, codigo, id FROM asignaturas")
        por_codigo = {(t, c): i for t, c, i in cur.fetchall()}
    return {e["slug"]: por_codigo[(e["titulacion_duena"], e["codigo"])]
            for e in mapa.values() if (e["titulacion_duena"], e["codigo"]) in por_codigo}


def percentil(valores: list, p: float) -> float:
    if not valores:
        return 0.0
    orden = sorted(valores)
    k = (len(orden) - 1) * p
    bajo, alto = int(k), min(int(k) + 1, len(orden) - 1)
    return orden[bajo] + (orden[alto] - orden[bajo]) * (k - bajo)


def una_consulta(api: str, texto: str, asignatura_id: int) -> dict:
    """Una consulta SSE completa. Devuelve los tiempos que importan, en milisegundos.

    `ttft_alumno` es hasta el primer trozo de PROSA -no hasta la primera etapa-, que es la definición
    del ADR 0009 y lo único que el alumno percibe como "ha empezado a responder"."""
    t0 = time.perf_counter()
    salida = {"primer_evento_ms": None, "ttft_alumno_ms": None, "total_ms": None,
              "etapas": {}, "error": None, "sin_reordenar": None}
    try:
        with httpx.Client(timeout=120.0) as cli:
            with cli.stream("POST", f"{api}/consulta",
                            json={"texto": texto, "asignatura_id": asignatura_id}) as r:
                if r.status_code != 200:
                    r.read()
                    salida["error"] = f"HTTP {r.status_code}"
                    return salida
                nombre = None
                for linea in r.iter_lines():
                    if salida["primer_evento_ms"] is None and linea.strip():
                        salida["primer_evento_ms"] = (time.perf_counter() - t0) * 1000
                    if linea.startswith("event: "):
                        nombre = linea[7:].strip()
                    elif linea.startswith("data: "):
                        ahora = (time.perf_counter() - t0) * 1000
                        if nombre == "etapa":
                            try:
                                etapa = json.loads(linea[6:])
                                salida["etapas"][etapa["nombre"]] = ahora
                                # LA DEGRADACION DE CALIDAD NO SE VE EN LA LATENCIA: la respuesta
                                # llega, llega antes incluso, y solo aqui consta que salio sin
                                # reordenar. Decir "aguanta diez alumnos" seria cierto en tiempo y
                                # falso en calidad si no se contara esto.
                                if etapa["nombre"] == "sin_reordenar":
                                    salida["sin_reordenar"] = etapa.get("motivo", "?")
                            except Exception:
                                pass
                        elif nombre == "token" and salida["ttft_alumno_ms"] is None:
                            salida["ttft_alumno_ms"] = ahora
    except Exception as e:
        salida["error"] = f"{type(e).__name__}: {e}"
    salida["total_ms"] = (time.perf_counter() - t0) * 1000
    return salida


def tanda(api: str, casos: list, concurrencia: int) -> list:
    """Lanza `concurrencia` consultas A LA VEZ y espera a todas. Hilos y no asyncio a propósito: el
    cliente tiene que ser tonto y no compartir bucle con nada, o mediría su propio planificador."""
    with ThreadPoolExecutor(max_workers=concurrencia) as pool:
        futuros = [pool.submit(una_consulta, api, t, a) for t, a in casos[:concurrencia]]
        return [f.result() for f in futuros]


def resumir(rs: list, clave: str) -> dict:
    """`clave` puede ser un campo suelto o `etapas:<nombre>`.

    LO NUESTRO Y LO DEL PROVEEDOR SE MIDEN POR SEPARADO, y no es un lujo: medido en secuencial, el
    p95 de punta a punta (63.853 ms) está dominado por la variabilidad del proveedor —dos de veinte
    consultas generaron a 4-11 tokens/s en vez de a ~105—, mientras nuestra recuperación entera se
    mantuvo entre 525 y 896 ms en las VEINTE. Si se mira solo el total, cualquier medida de
    concurrencia acaba diciendo más de Scaleway que de nuestro bucle de eventos, que es justo lo que
    esta corrida tiene que responder."""
    if clave.startswith("etapas:"):
        nombre = clave.split(":", 1)[1]
        vals = [r["etapas"][nombre] for r in rs if r.get("etapas", {}).get(nombre) is not None]
    else:
        vals = [r[clave] for r in rs if r.get(clave) is not None]
    if not vals:
        return {"n": 0}
    return {"n": len(vals), "p50": round(percentil(vals, 0.50), 1),
            "p95": round(percentil(vals, 0.95), 1), "max": round(max(vals), 1),
            "min": round(min(vals), 1), "media": round(statistics.mean(vals), 1)}


def persistir(url: str, config: dict, metricas: dict) -> int:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute("INSERT INTO corridas_eval (commit_sha, config, metricas)"
                    " VALUES (%s,%s,%s) RETURNING id",
                    (commit, json.dumps(config), json.dumps(metricas, ensure_ascii=False)))
        corrida = cur.fetchone()[0]
        con.commit()
    return corrida


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=os.environ.get("DATABASE_URL"))
    p.add_argument("--api", default="http://127.0.0.1:8001")
    p.add_argument("--n", type=int, default=0, help="consultas SECUENCIALES para el p95 de punta a punta")
    p.add_argument("--concurrencia", default="", help="lista tipo 1,2,5,10")
    p.add_argument("--sin-persistir", action="store_true")
    a = p.parse_args()
    if not a.url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2

    slugs = asignaturas_por_slug(a.url)
    pares = leer_jsonl(ORO)
    casos = [(x["pregunta"], slugs[x["asignatura"]]) for x in pares if x["asignatura"] in slugs]

    salud = httpx.get(f"{a.api}/salud", timeout=30.0).json()
    reo = salud["dependencias"].get("reordenador", {}).get("detalle", "?")
    print(f"api={a.api} | reordenador: {reo}\n")

    if a.n:
        print(f"=== PUNTA A PUNTA, {a.n} consultas SECUENCIALES ===")
        rs = [una_consulta(a.api, t, s) for t, s in casos[:a.n]]
        fallos = [r["error"] for r in rs if r["error"]]
        total, ttft = resumir(rs, "total_ms"), resumir(rs, "ttft_alumno_ms")
        print(f"  total    n={total['n']}  p50={total['p50']} ms  p95={total['p95']} ms  max={total['max']} ms")
        print(f"  TTFT     n={ttft['n']}  p50={ttft['p50']} ms  p95={ttft['p95']} ms  max={ttft['max']} ms")
        print(f"  presupuesto {PRESUPUESTO_MS} ms -> p95 al {100 * total['p95'] / PRESUPUESTO_MS:.0f} %"
              f"  {'CABE' if total['p95'] <= PRESUPUESTO_MS else 'NO CABE'}")
        if fallos:
            print(f"  FALLOS: {len(fallos)} -> {fallos[:3]}")
        if not a.sin_persistir:
            print("  corrida", persistir(a.url, {"encargo": "3.4", "paso": "punta a punta",
                                                 "secuencial": True, "reordenador": reo},
                                         {"total": total, "ttft": ttft,
                                          "presupuesto_ms": PRESUPUESTO_MS,
                                          "fallos": len(fallos)}))
        print()

    if a.concurrencia:
        niveles = [int(x) for x in a.concurrencia.split(",")]
        print("=== CONCURRENCIA ===")
        print("NUESTRO tramo = hasta la etapa `reordenado` (embebido + 3 vias + fusion + reordenado).")
        print("Es el que responde si algo serializa; el total lleva dentro la varianza del proveedor.\n")
        print(f"{'N':>3} | {'nuestro p50':>11} {'nuestro p95':>11} | {'total p50':>10} "
              f"| {'SIN REORDENAR':>14} {'motivos':>26}")
        filas = []
        for n in niveles:
            t0 = time.perf_counter()
            rs = tanda(a.api, casos, n)
            pared = time.perf_counter() - t0
            nuestro = resumir(rs, "etapas:reordenado")
            total, ttft = resumir(rs, "total_ms"), resumir(rs, "ttft_alumno_ms")
            fallos = sum(1 for r in rs if r["error"])
            motivos = {}
            for r in rs:
                if r.get("sin_reordenar"):
                    motivos[r["sin_reordenar"]] = motivos.get(r["sin_reordenar"], 0) + 1
            saltados = sum(motivos.values())
            fila = {"n": n, "nuestro": nuestro, "total": total, "ttft": ttft, "fallos": fallos,
                    "pared_s": round(pared, 2), "sin_reordenar": saltados, "motivos": motivos,
                    "consultas_por_s": round(n / pared, 2) if pared else 0}
            filas.append(fila)
            print(f"{n:>3} | {nuestro.get('p50', 0):>11} {nuestro.get('p95', 0):>11} "
                  f"| {total.get('p50', 0):>10} "
                  f"| {saltados:>4}/{n:<3} ({100 * saltados / n:>3.0f}%) "
                  f"{','.join(f'{k}={v}' for k, v in motivos.items()) or '-':>26}")
        base = filas[0]["nuestro"].get("p95") or 1
        print("\nLECTURA: si NUESTRO p95 crece ~lineal con N desde N=2, hay serializacion en el")
        print("camino de peticion. Si se mantiene plano, no la hay y el techo lo pone otra cosa.")
        for f in filas:
            factor = (f["nuestro"].get("p95", 0)) / base
            veredicto = "plano" if factor < 1.5 else ("lineal" if factor > f["n"] * 0.6 else "parcial")
            print(f"  N={f['n']:>3}  nuestro p95 x{factor:>5.2f}  (lineal seria x{f['n']:.0f})  -> {veredicto}")
        if not a.sin_persistir:
            print("corrida", persistir(a.url, {"encargo": "3.4", "paso": "concurrencia",
                                               "niveles": niveles, "reordenador": reo},
                                       {"filas": filas, "presupuesto_ms": PRESUPUESTO_MS}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
