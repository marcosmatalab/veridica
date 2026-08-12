"""API: /salud del encargo 0.3 y /consulta en SSE del 2.2.

La recuperacion (fase 3) y la verificacion (fase 4) NO estan. /consulta habla con el modelo
pequeno sin fragmentos y comprueba la FORMA del contrato de la seccion 7, no la verdad de lo
que dice: cada afirmacion sale con veredicto 'sin_verificar'. El detalle, en app/api/consulta.py.

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

from app.api.consulta import router as router_consulta
from app.core.colas import celery_app
from app.core.inferencia import Ajustes, ClienteInferencia, ErrorDefinitivo
from app.core.traza import TrazaPostgres

DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
EXTENSIONES_EXIGIDAS = ("vector", "pg_trgm")

app = FastAPI(title="Veridica", summary="Profesor verificado sobre temario real (encargos 0.3 y 2.2)")
app.include_router(router_consulta)

app.state.traza = TrazaPostgres(DATABASE_URL)
try:
    app.state.cliente_inferencia = ClienteInferencia(Ajustes.desde_entorno())
except ErrorDefinitivo as e:
    # Arrancar sin proveedor es legitimo -/salud tiene que poder decir que la base esta bien
    # aunque falte la clave-, pero /consulta lo dice claro en vez de fallar con un AttributeError.
    app.state.cliente_inferencia = None
    app.state.sin_proveedor = str(e)


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
        "encargo": "2.2 (API con SSE; sin recuperacion ni verificacion todavia)",
        "construido": ["/", "/salud", "/consulta"],
        "no_construido": ["/ingesta/documento", "/eval/correr", "/trazas/{id}", "/metricas"],
        "aviso": "/consulta comprueba la FORMA del contrato de la seccion 7, no la verdad de lo "
                 "que dice: no hay recuperacion (fase 3) ni verificacion (fase 4)",
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
