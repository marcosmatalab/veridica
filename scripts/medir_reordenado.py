#!/usr/bin/env python3
"""Mide la LATENCIA del reordenador del 3.4. No mide su calidad, y eso es a propósito.

    DATABASE_URL=... python scripts/medir_reordenado.py --hilos 2 --evidencia docs/evidencia/...

POR QUÉ SE MIDE LA LATENCIA HOY Y LA CALIDAD NO. La calidad se mide con `recall@6` con y sin
reordenador contra los pares oro, y **el conjunto oro está en reconstrucción** (3.0): medir acierto
contra una vara rota daría un número con toda la pinta de un dato. La latencia no depende de la
vara: depende de treinta candidatos y un reloj. Y es la mitad que puede disparar el plan B, así que
enterarse hoy vale mucho más que enterarse el sábado.

EL NÚMERO QUE SALE DE AQUÍ ES UNA **COTA INFERIOR** DEL DE PRODUCCIÓN, NUNCA UNA ESTIMACIÓN.
No es solo el recuento de hilos. Esta máquina es un Ryzen 9 9950X3D: caché 3D apilada y AVX-512 que
un vCPU compartido de un VPS no tiene, así que **ni siquiera igualando hilos el número es
trasladable**. Un vCPU compartido además compite por el núcleo físico con otros inquilinos, lo que
ensancha la cola justo donde vive el p95. Por eso el plan B se decide con la cifra al **recuento de
hilos del VPS**, no con la mejor: manda el peor número, porque es el único que no depende de dónde
se midió. Misma regla que ya se aplicó a la dispersión del 2.2.

EL CALENTAMIENTO SE DESCARTA Y SE DICE. La primera pasada de un modelo en CPU paga la reserva de
buffers de MKL/oneDNN y la primera resolución de kernels; incluirla inflaría el máximo con un coste
que en servicio se paga una vez al arrancar y nunca más. Se descartan las `--calentamiento` primeras
y **se reportan aparte**, que es lo que impide que "descartar" se convierta en "esconder".
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                            # noqa: E402

from app.core.recuperacion import recuperar                              # noqa: E402
from app.core.reordenador import CANDIDATOS, LARGO_MAXIMO, Reordenador   # noqa: E402

ORO = "evals/casos/oro_recuperacion.jsonl"
MAPA = "corpus/mapa_asignaturas.jsonl"

#: Punta a punta del 3.3 CON recuperación, medido en el propio 3.3. El reordenado aterriza ENCIMA de
#: esto, y el plan B se dispara sobre el tiempo que ve el alumno, no sobre el del paso aislado.
TOTAL_3_3_MS = 3076

#: Presupuesto declarado en la sección 9 (`PRESUPUESTO_CONSULTA_MS`).
PRESUPUESTO_MS = 8000


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
    """p95 por interpolación, sin numpy. Con n=100 el p95 cae entre dos muestras y redondear hacia
    abajo daría un número sistemáticamente optimista, que es justo el sesgo que no queremos aquí."""
    if not valores:
        return 0.0
    orden = sorted(valores)
    k = (len(orden) - 1) * p
    bajo, alto = int(k), min(int(k) + 1, len(orden) - 1)
    return orden[bajo] + (orden[alto] - orden[bajo]) * (k - bajo)


def medir(url: str, hilos: int | None, candidatos: int, largo: int, consultas: int,
          calentamiento: int, dispositivo: str = "cpu") -> dict:
    pares = leer_jsonl(ORO)[:consultas]
    slugs = asignaturas_por_slug(url)

    from app.core.embebedor import Embebedor
    embebedor = Embebedor(dispositivo="cpu")
    reordenador = Reordenador(dispositivo=dispositivo, hilos=hilos, largo_maximo=largo)

    tiempos, tiempos_calientes, truncados, tamanos = [], [], 0, []
    for i, par in enumerate(pares):
        asignatura = slugs.get(par["asignatura"])
        if asignatura is None:
            continue
        vector = embebedor.embeber(par["pregunta"])
        pool = recuperar(url, asignatura, par["pregunta"], vector=vector, k=candidatos)
        if not pool:
            continue
        pool = pool[:candidatos]
        tamanos.append(len(pool))
        truncados += reordenador.truncados(par["pregunta"], [c.texto for c in pool])

        t0 = time.perf_counter()
        reordenador.reordenar(par["pregunta"], pool)
        ms = (time.perf_counter() - t0) * 1000
        (tiempos_calientes if i >= calentamiento else tiempos).append(ms)

    return {"calentamiento": tiempos, "medidos": tiempos_calientes,
            "truncados": truncados, "pool_medio": statistics.mean(tamanos) if tamanos else 0,
            "estado": reordenador.estado()}


def resumen(r: dict) -> dict:
    t = r["medidos"]
    return {"consultas": len(t), "p50": round(percentil(t, 0.50), 1),
            "p95": round(percentil(t, 0.95), 1), "maximo": round(max(t), 1) if t else 0,
            "minimo": round(min(t), 1) if t else 0,
            "media": round(statistics.mean(t), 1) if t else 0,
            "calentamiento_ms": [round(x, 1) for x in r["calentamiento"]],
            "pool_medio": round(r["pool_medio"], 1), "fragmentos_truncados": r["truncados"]}


def persistir(url: str, s: dict, estado: dict) -> int:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    config = {"encargo": "3.4", "paso": "reordenado", "reordenador": True,
              "modelo": estado["modelo"], "revision": estado["revision"],
              "precision": "torch fp32 (int8 NO construido: se mide fp32 primero)",
              "dispositivo": estado["dispositivo"], "hilos": estado["hilos"],
              "largo_maximo": estado["largo_maximo"], "candidatos": s["pool_medio"],
              "maquina": "Ryzen 9 9950X3D 16c (NO es el VPS: el numero es COTA INFERIOR)",
              "conjunto_oro": "roto/en reconstruccion, sirve para tiempo y NO para acierto"}
    metricas = dict(s)
    metricas["total_3_3_ms"] = TOTAL_3_3_MS
    metricas["total_con_reordenado_p95_ms"] = round(TOTAL_3_3_MS + s["p95"], 1)
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
    p.add_argument("--hilos", type=int, default=None)
    p.add_argument("--candidatos", type=int, default=CANDIDATOS)
    p.add_argument("--largo", type=int, default=LARGO_MAXIMO)
    p.add_argument("--consultas", type=int, default=100)
    p.add_argument("--calentamiento", type=int, default=3)
    p.add_argument("--dispositivo", default="cpu", choices=["cpu", "cuda"])
    p.add_argument("--salida-json", default=None)
    p.add_argument("--sin-persistir", action="store_true")
    a = p.parse_args()
    if not a.url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2

    r = medir(a.url, a.hilos, a.candidatos, a.largo, a.consultas, a.calentamiento, a.dispositivo)
    s = resumen(r)
    estado = r["estado"]

    print(f"reordenador: {estado['modelo']} rev {estado['revision']} "
          f"{estado['dispositivo']} hilos={estado['hilos']} largo={estado['largo_maximo']}")
    print(f"carga {estado['segundos_carga']} s | margen de la sonda {estado['margen_sonda']}")
    print(f"pool medio {s['pool_medio']} candidatos | fragmentos truncados {s['fragmentos_truncados']}")
    print(f"calentamiento descartado (ms): {s['calentamiento_ms']}")
    print(f"n={s['consultas']}  p50={s['p50']} ms  p95={s['p95']} ms  "
          f"max={s['maximo']} ms  min={s['minimo']} ms")
    total = TOTAL_3_3_MS + s["p95"]
    print(f"punta a punta: {TOTAL_3_3_MS} ms + {s['p95']} ms = {total:.0f} ms "
          f"({100 * total / PRESUPUESTO_MS:.0f} % del presupuesto de {PRESUPUESTO_MS} ms)")
    print("ESTE NUMERO ES COTA INFERIOR: 9950X3D con cache 3D y AVX-512, no un vCPU de VPS.")

    if a.salida_json:
        with open(a.salida_json, "w", encoding="utf-8") as f:
            json.dump({"resumen": s, "estado": estado}, f, indent=2, ensure_ascii=False)
    if not a.sin_persistir:
        print(f"persistido en corridas_eval: id {persistir(a.url, s, estado)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
