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

#: CUANDO ARRANCO ESTE PROCESO, y no es un adorno: contesta de un vistazo a "¿el que responde es el
#: MIO?". El 14 de agosto de 2026 un uvicorn viejo llevaba horas ocupando el puerto, cada reinicio
#: moria con `[Errno 10048] bind` en un log que nadie miraba, y la espera de arranque decia "arriba"
#: porque contestaba el viejo: media tarde midiendo codigo anterior a los arreglos que se median.
#: **Ese fallo no falla, contesta**, que es lo que lo hace traicionero. Con esta marca, el paso 2 del
#: ritual del 8.4 se comprueba mirando en vez de suponiendo.
app.state.arrancado_en = time.time()
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

# EL REORDENADOR ESTA DESCARTADO POR SU PROPIO CRITERIO (3.4, cerrado el 14/08/2026; ADR 0019).
# El criterio se escribio como formula ANTES de medir -se queda si cierra mas de la mitad del hueco
# entre la fusion sola y el techo del pool- y el numero salio al otro lado: sobre el conjunto oro
# corregido, en `lectura`, reordenar da recall@6 56,0 % contra 58,7 % de la fusion sin reordenar
# (liston: 70,0 %). No es que no llegue: EMPEORA. Y descartarlo devuelve gratis la divergencia
# arquitectonica (era la unica pieza GPU-o-nada), el techo de concurrencia (~1,9 consultas/s) y la
# perdida de reordenado desde 5 alumnos.
#
# El codigo, sus tests y su respaldo anunciado SE CONSERVAN, y el interruptor invierte su sentido:
# REORDENADOR_ACTIVO=1 lo reenciende para ablacion o para re-medirlo si cambia el conjunto o el
# modelo. Lo que era "GPU o nada" (ADR 0015) sigue valiendo cuando esta encendido.
try:
    if os.environ.get("REORDENADOR_ACTIVO", "0") != "1":
        raise RuntimeError("REORDENADOR_ACTIVO!=1: descartado por su criterio el 14/08/2026 "
                           "(recall@6 lectura 56,0 % contra 58,7 % sin reordenar; ADR 0019)")
    from app.core.reordenador import para_servicio
    app.state.reordenador = para_servicio()
    app.state.sin_reordenador = ""
except Exception as e:
    app.state.reordenador = None
    app.state.sin_reordenador = f"{type(e).__name__}: {e}"

# EL NLI DEL 4.3, ENCHUFADO EN EL 4.4 Y EN CPU A PROPOSITO. Sin esto estaba construido, con sus
# tests, y NO LO LLAMABA NADIE: toda afirmacion `parafrasis` salia `sin_verificar`, o sea que el
# sistema comprobaba lo que se copiaba y no lo que se reformulaba -la mitad dificil, y una de las
# cuatro frases del README-.
#
# CPU y no GPU: la GPU ya es el cuello (embebedor y reordenador serializan desde el quinto alumno) y
# meter un tercer modelo alli bajaria otra vez el techo de concurrencia. En CPU son 216 ms por par
# medidos, y como corre en un hilo aparte solapa con la prosa en vez de sumarse.
#
# Donde no haya torch se queda en None y /salud lo dice, igual que el embebedor: es la MISMA decision
# de empaquetado del 8.1, y se declara igual en vez de mezclarla con esto.
# Y CON INTERRUPTOR, que no es un lujo: la ablacion del 7.3 mide la configuracion candidata con la
# capa de verificacion APAGADA, y sin una via de apagarla habria que medirla en otro proceso -o sea,
# cambiando mas de una variable a la vez, que es como se heredan numeros de otra configuracion-.
try:
    if os.environ.get("NLI_ACTIVO", "1") == "0":
        raise RuntimeError("NLI_ACTIVO=0: apagado a proposito (ablacion del 7.3)")
    from app.core.verificador_nli import VerificadorNLI
    app.state.nli = VerificadorNLI()
    app.state.sin_nli = ""
except Exception as e:
    app.state.nli = None
    app.state.sin_nli = f"{type(e).__name__}: {e}"

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
    """La sonda distingue TRES estados, porque desde el 14/08/2026 (ADR 0019) el reordenador no es
    un respaldo que falta sino una pieza DESCARTADA por su propio criterio: (1) descartado, que es
    el defecto y no una averia -el orden de la fusion ES la configuracion, medida mejor-; (2)
    reencendido y cargado (ablacion); (3) reencendido y caido, que es el unico estado donde el
    texto viejo de 'respaldo' vuelve a ser verdad. Antes decia 'respaldo declarado' y 'ordena
    peor' para el estado (1), o sea contaba la historia de antes del descarte: lo cazo la pasada
    adversarial del cierre."""
    reo = getattr(app.state, "reordenador", None)
    if reo is None:
        if os.environ.get("REORDENADOR_ACTIVO", "0") != "1":
            return ("DESCARTADO por su propio criterio (ADR 0019, 14/08/2026): el orden de la "
                    "fusion ES la configuracion por defecto, medida mejor que reordenar "
                    "(58,7 % contra 56,0 % en lectura); REORDENADOR_ACTIVO=1 lo reenciende "
                    "para ablacion")
        return ("REENCENDIDO y NO cargado: " + getattr(app.state, "sin_reordenador", "?")
                + " | se sirve el orden de la fusion y /consulta lo anuncia en una etapa")
    e = reo.estado()
    return f"{e['modelo']} rev {e['revision']} en {e['dispositivo']} (reencendido: ablacion)"


def _nli() -> str:
    """El verificador de paráfrasis. **Opcional en el sentido de `/salud`, no en el del proyecto:**
    sin él se responde igual, pero se responde SIN comprobar lo que el modelo reformuló, que es la
    mitad difícil de la tesis. Por eso su consecuencia está escrita con todas las letras."""
    v = getattr(app.state, "nli", None)
    if v is None:
        raise RuntimeError(getattr(app.state, "sin_nli", "no cargado")
                           + " | sin NLI, toda afirmacion 'parafrasis' sale sin_verificar")
    return f"{v.__class__.__name__} en {v.dispositivo}, umbral {v.umbral}"


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
    arrancado = getattr(app.state, "arrancado_en", None)
    return {
        "servicio": "veridica",
        "proceso": {
            "arrancado_en": (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(arrancado))
                             if arrancado else None),
            "lleva_segundos": round(time.time() - arrancado) if arrancado else None,
            "para_que": "si esto es mas viejo que tu ultimo reinicio, el que contesta NO es tu "
                        "proceso: hay uno anterior ocupando el puerto",
        },
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
    "nli": "no se verifica la PARÁFRASIS: toda afirmación reformulada sale 'sin_verificar', y con "
           "ella la mitad difícil de la tesis del proyecto",
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
        "nli": _sonda(_nli),
        "worker": _sonda(_worker),
    }
    caidas = [n for n, v in dependencias.items() if v["estado"] != "ok"]
    rotas = [n for n in caidas if n in ESENCIALES]
    degradadas = [n for n in caidas if n not in ESENCIALES]
    arrancado = getattr(app.state, "arrancado_en", None)
    cuerpo = {
        "estado": "roto" if rotas else ("degradado" if degradadas else "ok"),
        # La misma marca que en /api: "¿es el mio?" se contesta mirando.
        "arrancado_en": (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(arrancado))
                         if arrancado else None),
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
