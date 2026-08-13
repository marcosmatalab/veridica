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
from pathlib import Path

import psycopg
import redis as redislib
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.consulta import router as router_consulta
from app.api.navegacion import router as router_navegacion
from app.core.catalogo import CatalogoPostgres
from app.core.colas import celery_app
from app.core.inferencia import Ajustes, ClienteInferencia, ErrorDefinitivo
from app.core.traza import TrazaPostgres

DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
EXTENSIONES_EXIGIDAS = ("vector", "pg_trgm")

app = FastAPI(title="Veridica", summary="Profesor verificado sobre temario real (encargo 2.4)")
app.include_router(router_consulta)
app.include_router(router_navegacion)

class EstaticosQueRevalidan(StaticFiles):
    """Todo lo que cuelga de /estatico se sirve con `Cache-Control: no-cache`.

    No significa "no caches": significa "no uses tu copia sin preguntar antes". El navegador se
    queda el fichero y en la siguiente visita revalida con el ETag que ya servimos, asi que lo
    normal es un 304 sin cuerpo y no una descarga.

    Esta aqui por un fallo real del 12 de agosto de 2026: sin esta cabecera solo iban ETag y
    Last-Modified, y sin instruccion de frescura el navegador la inventa por heuristica y puede
    servir la copia SIN preguntar. Una captura de /estilos hecha asi dictaba un veredicto sobre una
    pagina que ya no existia. Y el caso caro no es la hoja: es render.js, que dibuja las etapas y es
    la capa que NO tiene puerta automatica, porque en el CI no hay motor de JavaScript. Un estilo
    viejo se ve raro; un render.js viejo dibuja otra cosa o no dibuja nada.

    RIESGO RESIDUAL, Y ES EL QUE MUERDE EL DIA DE LA SESION: **esta cabecera NO ES RETROACTIVA.**
    Una copia que el navegador guardo ANTES de que la cabecera existiera se guardo sin instruccion
    de frescura, asi que la sigue sirviendo por heuristica y sin preguntar. Este arreglo protege de
    aqui en adelante; no limpia lo que ya esta guardado en la maquina desde la que se va a ensenar.
    De ahi la regla del 8.4: **el ensayo y la sesion arrancan en ventana limpia -incognito o cache
    vaciada-, nunca en la pestana que lleva abierta desde ayer.** En incognito se ve al instante.

    La respuesta de produccion es otra -URL con marca de version y `max-age` largo con `immutable`-
    y esta declarada en el 8.1, no construida aqui: exige decidir de donde sale la marca, y hoy el
    coste de revalidar es un 304 contra localhost.
    """

    def file_response(self, *args, **kwargs) -> Response:
        respuesta = super().file_response(*args, **kwargs)
        # Se pone sobre la respuesta ya resuelta a proposito: asi la cabecera viaja tambien en el
        # 304, que es donde el navegador refresca las instrucciones que guarda con la copia.
        respuesta.headers["cache-control"] = "no-cache"
        return respuesta


WEB = Path(__file__).resolve().parents[2] / "web"
if WEB.is_dir():
    app.mount("/estatico", EstaticosQueRevalidan(directory=WEB), name="estatico")

app.state.url_base_datos = DATABASE_URL
app.state.traza = TrazaPostgres(DATABASE_URL)
app.state.catalogo = CatalogoPostgres(DATABASE_URL)
# EL EMBEBEDOR SE CARGA AL ARRANCAR, no perezoso, y el coste esta medido: 1,7 s en CPU y 2,3 s en
# GPU. Con carga perezosa esos dos segundos los pagaria la PRIMERA consulta de la sesion, delante
# del cliente. Si no hay torch en este proceso -el contenedor no lo lleva a proposito-, se queda en
# None y /salud lo dice: la recuperacion no existe ahi, y decirlo es mejor que fingirla.
try:
    from app.core.embebedor import Embebedor
    app.state.embebedor = Embebedor()
    app.state.sin_embebedor = ""
except Exception as e:
    app.state.embebedor = None
    app.state.sin_embebedor = f"{type(e).__name__}: {e}"

# EL REORDENADOR ES **GPU O NADA** (3.4, ADR 0015). No cargarlo no es un fallo: es el respaldo
# declarado. En CPU su p95 medido son 13.714 ms, el 274 % del presupuesto de 5.000 ms el paso SOLO,
# y va en la ruta del TTFT, asi que caer a CPU seria cambiar "peor orden" por "catorce segundos de
# pantalla muerta". Sin GPU se sirve el orden de la fusion y /consulta LO DICE en una etapa.
try:
    from app.core.reordenador import para_servicio
    app.state.reordenador = para_servicio()
    app.state.sin_reordenador = ""
except Exception as e:
    app.state.reordenador = None
    app.state.sin_reordenador = f"{type(e).__name__}: {e}"

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


def _embebedor() -> str:
    """El embebedor NO es opcional donde se sirve /consulta con recuperacion, y por eso entra en
    /salud: sin el, la respuesta se genera sin fragmentos y el sistema pasa a ser lo que dice no
    ser. Donde no esta -el contenedor, que no lleva torch- lo dice en vez de callarlo."""
    emb = getattr(app.state, "embebedor", None)
    if emb is None:
        raise RuntimeError(getattr(app.state, "sin_embebedor", "no cargado")
                           + " | sin embebedor no hay recuperacion: /consulta responde sin "
                             "fragmentos y lo declara en la traza")
    return f"{emb.anclaje['modelo']} rev {emb.anclaje['revision'][:12]} en {emb.dispositivo}"


def _reordenador() -> str:
    """El reordenador SI es opcional, y por eso su sonda dice cual de los dos modos esta activo en
    vez de fallar. Es la diferencia con el embebedor: sin embebedor el sistema finge recuperar; sin
    reordenador recupera igual y ordena peor, que es una degradacion honesta si se anuncia.

    En el ritual del 8.4 esta sonda se mira ANTES de empezar la sesion: es donde se ve si la GPU
    responde hoy, y enterarse aqui cuesta un segundo."""
    reo = getattr(app.state, "reordenador", None)
    if reo is None:
        return ("SIN reordenar (respaldo declarado): " + getattr(app.state, "sin_reordenador", "?")
                + " | se sirve el orden de la fusion y /consulta lo anuncia en una etapa")
    e = reo.estado()
    return f"{e['modelo']} rev {e['revision']} en {e['dispositivo']}"


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
def raiz() -> FileResponse:
    """La vista del alumno (encargo 2.4). El JSON de estado que vivia aqui se mudo a /api."""
    return FileResponse(WEB / "index.html")


@app.get("/estilos")
def estilos() -> FileResponse:
    """Muestra de estilos con datos INVENTADOS, en su propia ruta y sin enlace desde la vista del
    alumno: afirmaciones falsas al lado de la salida real serian afirmar en presente lo no
    construido, puesto en pantalla."""
    return FileResponse(WEB / "estilos.html")


@app.get("/api")
def api() -> dict:
    return {
        "servicio": "veridica",
        "encargo": "3.4 (recuperacion con fusion y reordenado; sin verificacion todavia)",
        "construido": ["/", "/estilos", "/salud", "/api", "/consulta", "/titulaciones",
                       "/asignaturas", "/respuestas/{id}/fragmentos/{id}"],
        "no_construido": ["/ingesta/documento", "/eval/correr", "/trazas/{id}", "/metricas"],
        # Corregido en el 3.4: decia "no hay recuperacion (fase 3)" con la fase 3 ya construida,
        # que es exactamente lo que la primera regla del repo prohibe. Lo que SIGUE siendo cierto
        # -y es lo que este aviso existe para decir- es que nadie ha comprobado la VERDAD.
        "aviso": "/consulta recupera del temario y cita fragmentos reales, pero comprueba la FORMA "
                 "del contrato de la seccion 7 y NO la verdad de lo que dice: la verificacion es "
                 "la fase 4 y toda afirmacion viaja con veredicto 'sin_verificar'",
    }


#: LO QUE IMPIDE RESPONDER, QUE ES DISTINTO DE LO QUE FALTA. Sin base no hay temario que citar y sin
#: extensiones no hay ni vectorial ni léxica: ahí no se puede responder y el 503 es correcto. Lo
#: demás **degrada**, y degradar anunciando no es estar roto — es el mismo criterio que el 8.2 aplica
#: al 429 del proveedor.
#:
#: **Y esto era un diagnóstico equivocado, no un detalle de forma.** Con todo en la lista, el
#: contenedor —que no lleva torch a propósito— devolvía **503**, así que `docker compose up --wait`
#: no arrancaba por una capacidad que decidimos no empaquetar. Un 503 dice *"no puedo responder"*;
#: lo que pasaba era *"respondo peor y lo digo"*.
ESENCIALES = ("db", "extensiones")

#: Qué se pierde cuando falta cada una, EN CASTELLANO Y EN LA RESPUESTA. Quien mire este endpoint a
#: las nueve de la mañana del lunes necesita saber si falta el reordenador o falta torch, que son dos
#: conversaciones distintas: un booleano `degradado` no distingue una de otra.
CONSECUENCIA = {
    "db": "no hay temario que citar ni traza que escribir: no se puede responder",
    "extensiones": "sin pg_trgm ni pgvector no hay ninguna búsqueda: no se puede responder",
    "redis": "no hay caché ni cola; /consulta no las usa, así que responde igual",
    "embebedor": "no hay búsqueda por SIGNIFICADO: se recupera solo por palabras y glosario, que el "
                 "3.1 midió en 58 % de recall@6 frente al 80,9 % de la fusión",
    "reordenador": "no se reordena: se sirve el orden de la búsqueda, peor ordenado",
    "worker": "no hay tareas de fondo (ingesta, evaluación); /consulta no las usa",
}


@app.get("/salud")
def salud() -> JSONResponse:
    dependencias = {
        "db": _sonda(_db),
        "extensiones": _sonda(_extensiones),
        "redis": _sonda(_redis),
        "embebedor": _sonda(_embebedor),
        "reordenador": _sonda(_reordenador),
        "worker": _sonda(_worker),
    }
    caidas = [n for n, v in dependencias.items() if v["estado"] != "ok"]
    rotas = [n for n in caidas if n in ESENCIALES]
    degradadas = [n for n in caidas if n not in ESENCIALES]
    cuerpo = {
        "estado": "roto" if rotas else ("degradado" if degradadas else "ok"),
        "puede_responder": not rotas,
        "caidas": caidas,
        "rotas": rotas,
        "degradadas": degradadas,
        # El texto legible: qué falta, qué se pierde por ello, y el detalle crudo de la sonda —que
        # es donde pone "No module named 'torch'"—. Los tres juntos, porque el nombre solo no dice
        # qué hacer y la consecuencia sola no dice qué instalar.
        "que_falta": [f"{n}: {CONSECUENCIA.get(n, 'sin consecuencia declarada')} "
                      f"| {dependencias[n]['detalle']}" for n in caidas],
        "dependencias": dependencias,
    }
    return JSONResponse(cuerpo, status_code=503 if rotas else 200)
