"""API del encargo 0.3: hola mundo y /salud. Nada mas.

/consulta, SSE, recuperacion y verificacion son de las fases 2 en adelante. Aqui lo unico
que hay es el esqueleto que demuestra que los servicios se levantan y se ven entre ellos.

/salud comprueba las dependencias UNA A UNA (como pide la seccion 10 de la guia) y devuelve
503 si alguna falla. Comprueba tambien que las extensiones de Postgres estan creadas: el script
de docker-entrypoint-initdb.d solo corre con el volumen vacio, asi que un volumen viejo no las
tendria y nadie se enteraria. Lo que se supone, no se sabe.
"""
import os
import time

import psycopg
import redis as redislib
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.colas import celery_app

DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
EXTENSIONES_EXIGIDAS = ("vector", "pg_trgm")

app = FastAPI(title="Veridica", summary="Profesor verificado sobre temario real (encargo 0.3)")


def _sonda(fn) -> dict:
    """Corre una comprobacion y devuelve su veredicto con lo que tardo. Nunca lanza."""
    t0 = time.perf_counter()
    try:
        detalle = fn()
        estado = "ok"
    except Exception as e:
        detalle = f"{type(e).__name__}: {e}"
        estado = "fallo"
    return {"estado": estado, "detalle": detalle, "ms": round((time.perf_counter() - t0) * 1000, 1)}


def _db() -> str:
    with psycopg.connect(DATABASE_URL, connect_timeout=3) as con:
        with con.cursor() as cur:
            cur.execute("SELECT version()")
            return cur.fetchone()[0].split(" on ")[0]


def _extensiones() -> str:
    with psycopg.connect(DATABASE_URL, connect_timeout=3) as con:
        with con.cursor() as cur:
            cur.execute("SELECT extname FROM pg_extension WHERE extname = ANY(%s)",
                        (list(EXTENSIONES_EXIGIDAS),))
            presentes = {fila[0] for fila in cur.fetchall()}
    faltan = [e for e in EXTENSIONES_EXIGIDAS if e not in presentes]
    if faltan:
        raise RuntimeError(
            f"faltan extensiones: {', '.join(faltan)}. El volumen se creo sin pasar por "
            f"deploy/initdb/01-extensiones.sql; se arregla con 'docker compose down -v' "
            f"(OJO: eso borra los datos) o creandolas a mano."
        )
    return "presentes: " + ", ".join(sorted(presentes))


def _redis() -> str:
    cli = redislib.Redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
    cli.ping()
    return f"pong de {cli.connection_pool.connection_kwargs.get('host', '?')}"


def _worker() -> str:
    respuestas = celery_app.control.ping(timeout=2.0) or []
    if not respuestas:
        raise RuntimeError("ningun worker respondio al ping en 2 s")
    nodos = sorted(nombre for r in respuestas for nombre in r)
    return f"{len(nodos)} worker(s): {', '.join(nodos)}"


@app.get("/")
def raiz() -> dict:
    return {
        "servicio": "veridica",
        "encargo": "0.3 (esqueleto de servicios)",
        "construido": ["/", "/salud"],
        "no_construido": ["/consulta", "/ingesta/documento", "/eval/correr", "/trazas/{id}",
                          "/metricas"],
        "aviso": "sin corpus cargado: la fase 1 es la que lo carga",
    }


@app.get("/salud")
def salud() -> JSONResponse:
    dependencias = {
        "db": _sonda(_db),
        "extensiones": _sonda(_extensiones),
        "redis": _sonda(_redis),
        "worker": _sonda(_worker),
    }
    caidas = [n for n, v in dependencias.items() if v["estado"] != "ok"]
    cuerpo = {
        "estado": "ok" if not caidas else "degradado",
        "caidas": caidas,
        "dependencias": dependencias,
    }
    return JSONResponse(cuerpo, status_code=200 if not caidas else 503)
