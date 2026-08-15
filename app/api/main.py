"""API: /salud del encargo 0.3 y /consulta en SSE del 2.2.

La recuperacion (fase 3) y la verificacion (fase 4) NO estan. /consulta habla con el modelo
pequeno sin fragmentos y comprueba la FORMA del contrato de la seccion 7, no la verdad de lo
que dice: cada afirmacion sale con veredicto 'sin_verificar'. El detalle, en app/api/consulta.py.

/salud comprueba las dependencias UNA A UNA (como pide la seccion 10 de la guia) y devuelve
503 si alguna falla. Comprueba tambien que las extensiones de Postgres estan creadas: el script
de docker-entrypoint-initdb.d solo corre con el volumen vacio, asi que un volumen viejo no las
tendria y nadie se enteraria. Lo que se supone, no se sabe.
"""
import contextlib
import os
import time
from pathlib import Path

import psycopg
import redis as redislib
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.consulta import router as router_consulta
from app.api.navegacion import router as router_navegacion
from app.api.trazas import router as router_trazas
from app.core import autenticacion
from app.core.catalogo import CatalogoPostgres
from app.core.colas import celery_app
from app.core.inferencia import Ajustes, ClienteInferencia, ErrorDefinitivo
from app.core.traza import TrazaPostgres

DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
EXTENSIONES_EXIGIDAS = ("vector", "pg_trgm")


@contextlib.asynccontextmanager
async def ciclo_de_vida(_app):
    """Lo que se fija al arrancar el proceso que sirve. Hoy, el techo del threadpool (0.4)."""
    fijar_el_threadpool()
    yield


app = FastAPI(title="Veridica", summary="Profesor verificado sobre temario real (encargo 2.4)",
              lifespan=ciclo_de_vida)
app.include_router(router_consulta)
app.include_router(router_navegacion)
app.include_router(router_trazas)


@app.middleware("http")
async def puerta_del_token(peticion: Request, siguiente):
    """LA PUERTA, Y VA EN UN MIDDLEWARE PARA QUE NO SE PUEDA OLVIDAR.

    Una dependencia por ruta protege las rutas donde alguien se acordó de ponerla; un middleware
    protege **todas**, y la ruta nueva que nazca mañana nace protegida. La lista que se mantiene es
    la de lo ABIERTO (`autenticacion.ABIERTAS`), así que el olvido falla ruidoso en la primera
    petición en vez de callar.

    Sin `VERIDICA_TOKEN` en el entorno la puerta no existe, para que la demo local y los tests
    corran sin ceremonia — y eso se declara en `/salud`, en `/api` y, sobre todo, en
    `servir_anfitrion.py`, que **se niega a dar el comando del túnel** sin token.
    """
    if not autenticacion.autorizada(peticion.url.path, peticion.headers):
        return JSONResponse(
            {"error": "falta el token o no es el correcto",
             "como": f"manda la cabecera {autenticacion.CABECERA}: <token>, o "
                     f"Authorization: Bearer <token>",
             "por_que": "esta instancia esta publicada y /consulta gasta saldo del proveedor"},
            status_code=401)
    return await siguiente(peticion)


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
# meter un tercer modelo alli bajaria otra vez el techo de concurrencia. En CPU son 59,6 ms por par
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
    """Corre una comprobacion y devuelve su veredicto con lo que tardo. Nunca lanza.

    **EL DETALLE PASA POR EL REDACTOR, y no es una precaución de manual.** `/salud` se queda ABIERTA
    a propósito —el healthcheck y `servir_anfitrion.py` la llaman sin cabeceras— y desde el 15/08 se
    publica en internet por el túnel. El detalle crudo de una sonda es texto de excepción ajeno: una
    `OperationalError` de psycopg puede arrastrar la cadena de conexión con su contraseña dentro.
    Es literalmente la regla que este repo tiene desde que su propio auditor de configuración
    imprimió una clave entera por pantalla, aplicada al sitio donde más caro sale: **una salida que
    se consulta a menudo, se pega en informes y se guarda en logs no filtra una vez, filtra cada
    vez.** Se sigue diciendo QUÉ falló y contra qué host; lo que no sale es el secreto.
    """
    t0 = time.perf_counter()
    try:
        detalle = fn()
        estado = "ok"
    except Exception as e:
        detalle = f"{type(e).__name__}: {e}"
        estado = "fallo"
    return {"estado": estado, "detalle": autenticacion.redactar(detalle),
            "ms": round((time.perf_counter() - t0) * 1000, 1)}


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
        "autenticacion": ("con token en la cabecera " + autenticacion.CABECERA
                          if autenticacion.token_configurado()
                          else "ABIERTA: sin VERIDICA_TOKEN en el entorno no hay puerta"),
        "proceso": {
            "arrancado_en": (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(arrancado))
                             if arrancado else None),
            "lleva_segundos": round(time.time() - arrancado) if arrancado else None,
            "para_que": "si esto es mas viejo que tu ultimo reinicio, el que contesta NO es tu "
                        "proceso: hay uno anterior ocupando el puerto",
        },
        "encargo": "2.5 (traza completa) sobre la fase 4 enchufada (4.2-4.5) y el 5.3",
        "construido": ["/", "/estilos", "/salud", "/api", "/consulta", "/titulaciones",
                       "/asignaturas", "/respuestas/{id}/fragmentos/{id}", "/trazas/{id}"],
        # LEÍDO DE `NO_CONSTRUIDO` Y NO ESCRITO A MANO: la misma lista decide en `/salud` si una
        # pieza caída degrada algo o no tiene consumidor, así que dos copias de esto se separarían
        # y una copia desactualizada cambiaría un diagnóstico, no solo un texto.
        "no_construido": list(NO_CONSTRUIDO),
        # Corregido DOS VECES, y la segunda es la que enseña algo. En el 3.4 decia "no hay
        # recuperacion (fase 3)" con la fase 3 construida; hasta el 2.5 decia que la verificacion
        # era la fase 4 y que toda afirmacion viajaba `sin_verificar`, con el 4.2, el 4.3, el 4.4 y
        # el 4.5 corriendo en cada consulta. **Un aviso envejece igual que un documento**, y este
        # ademas se sirve por HTTP: quien lo leyera dejaba de mirar. Lo que sigue siendo cierto se
        # dice, y lo que ya no, se quita.
        "aviso": "/consulta recupera del temario, cita fragmentos reales y VERIFICA lo que afirma "
                 "(4.2 cita literal, 4.3 parafrasis por NLI, 4.4 recalculo, 4.5 cobertura de la "
                 "prosa); cada veredicto viaja con la firma de su instrumento y la traza entera "
                 "se lee en /trazas/{id}. Del inventario del 4.6 queda SIN CALIBRAR uno de seis, "
                 "el anclaje de operandos, que necesita diseño antes que barrido",
    }


#: EL LÍMITE DEL THREADPOOL, DECLARADO (0.4, 15 de agosto de 2026) — con su número **medido dentro
#: del proceso**, no leído de la documentación de nadie.
#:
#: **POR QUÉ ESTE NÚMERO NOS IMPORTA MÁS QUE A UNA API NORMAL: todas nuestras rutas son `def` y no
#: `async def`.** Starlette corre una ruta síncrona en su threadpool, así que cada petición ocupa
#: uno de estos huecos mientras dura. Y `/consulta` es lo peor de los dos mundos: su generador
#: **también** es síncrono, o sea que cada `next()` —cada trozo que se espera del proveedor— vuelve
#: al mismo pozo. Una consulta que tarda segundos en generar tiene un hueco cogido casi todo ese
#: tiempo. El techo de consultas simultáneas **es este número**, no la GPU ni la cuota.
#:
#: **Y `/salud` comparte el pozo**, que es la parte incómoda: bajo carga, la sonda que dice si el
#: sistema está bien hace cola detrás de las consultas que quiere diagnosticar.
#:
#: **SE FIJA EN VEZ DE HEREDARSE, y esa es toda la decisión.** El valor medido dentro de este
#: proceso —`anyio.to_thread.current_default_thread_limiter().total_tokens`— es **40**, y ese 40 es
#: el defecto de anyio 4.12, no una promesa suya: una actualización de la librería puede moverlo y
#: **nuestro techo de concurrencia cambiaría sin que nadie tocara este repo ni se pusiera nada
#: rojo**. Es la misma familia que los valores del despliegue elegidos antes de que existiera lo que
#: hoy depende de ellos. Fijarlo al mismo 40 **no cambia nada hoy** y hace que mañana sea una
#: decisión y no una herencia; el número se publica en `/salud`, que es donde se comprueba lo que
#: de verdad corre.
HILOS_DE_BLOQUEO = int(os.environ.get("HILOS_DE_BLOQUEO") or 40)


def fijar_el_threadpool() -> None:
    """Se llama desde el `lifespan`, o sea DENTRO del bucle de eventos que va a servir, y **guarda
    el limitador** en vez de limitarse a tocarlo.

    Las dos cosas tienen que ser aquí y no al importar: `current_default_thread_limiter()` va por
    bucle de eventos, al importar todavía no hay ninguno, y —lo que costó una vuelta— **tampoco lo
    hay dentro de una ruta síncrona**, porque esa corre en un hilo del pozo y allí `sniffio` no
    encuentra biblioteca asíncrona. O sea que el sitio donde el número interesa es justo donde no se
    puede preguntar por él. Se guarda el objeto y se lee de ahí.
    """
    import anyio.to_thread
    limitador = anyio.to_thread.current_default_thread_limiter()
    limitador.total_tokens = HILOS_DE_BLOQUEO
    app.state.limitador = limitador


def hilos_de_bloqueo_vivos() -> dict:
    """Lo que el proceso tiene DE VERDAD, no lo que la constante dice que quería.

    Se lee del limitador **vivo** a propósito: es la regla de la casa sobre los valores por defecto
    que el entorno puede pisar —se comprueba dentro del proceso que sirve, no leyendo el módulo—.
    """
    limitador = getattr(app.state, "limitador", None)
    if limitador is None:
        # Sin `lifespan` no se ha fijado nada: se dice, en vez de enseñar la constante como si
        # fuera el valor vivo. Pasa en un `TestClient` usado sin `with`, y pasaría en produccion si
        # alguien montara la app sin ciclo de vida — que es justo lo que habria que ver.
        return {"declarados": HILOS_DE_BLOQUEO, "vivos": None,
                "aviso": "el ciclo de vida no ha corrido: el pozo tiene el defecto de la libreria"}
    return {"declarados": HILOS_DE_BLOQUEO, "vivos": limitador.total_tokens,
            "en_uso": limitador.borrowed_tokens,
            "que_significa": "todas las rutas son sincronas: este es el techo de peticiones "
                             "simultaneas, y /salud hace cola en el mismo sitio"}


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

#: LO QUE TODAVÍA NO EXISTE, en un solo sitio. `/api` lo servía escrito a mano en su respuesta y
#: ahora lo lee de aquí: dos listas de lo mismo se separan, y esta además decide una clasificación
#: de `/salud`, así que una copia desactualizada cambiaría un diagnóstico.
NO_CONSTRUIDO = ("/ingesta/documento", "/eval/correr", "/metricas",
                 "cache semantica", "cola de tareas de fondo")

#: QUIÉN USA CADA PIEZA — y esto es lo que separa **una avería** de **una capacidad que hoy no usa
#: nadie**.
#:
#: EL CASO QUE LO PIDE: la cabecera de la interfaz **enlaza `/salud`** y el cartel invita a pulsarlo
#: diciendo que ahí está lo que la instancia sabe hacer. En el anfitrión (ADR 0023) `redis` y
#: `worker` salen en rojo porque `redis:6379` es un nombre de la red de compose que fuera no
#: resuelve — **y ninguna ruta construida los usa**: la caché semántica y la cola están declaradas y
#: no construidas. O sea que quien pulse el enlace vería dos rojos que no impiden nada, justo en la
#: pantalla donde se está enseñando otra cosa.
#:
#: **Un rojo que no impide nada no es un rojo, y una sonda que los mezcla obliga a explicarse.** Es
#: la misma familia que el cartel de la cabecera: la pantalla afirmando algo sobre el estado del
#: proceso que no es lo que parece.
#:
#: **Y no es cosmética, que es la trampa evidente aquí:** la clasificación no sale de una lista de
#: "los que me molesta ver en rojo", sale de **quién los consumiría**, y cada consumidor tiene que
#: estar en `NO_CONSTRUIDO`. En cuanto la caché semántica exista, `redis` deja de ser
#: `sin_consumidor` **por construcción** y vuelve a `degradadas` sin que nadie se acuerde de nada.
#: Su test lo ancla en las dos direcciones.
CONSUMIDOR = {
    "redis": ("cache semantica", "cola de tareas de fondo"),
    "worker": ("/ingesta/documento", "/eval/correr"),
}

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


def sin_consumidor_construido() -> set:
    """Las piezas cuyo consumidor entero está declarado y NO construido.

    Se calcula al llamar y no al importar para que siga saliendo de `CONSUMIDOR` × `NO_CONSTRUIDO`:
    en cuanto la caché semántica exista, `redis` deja de estar aquí **por construcción**.
    """
    return {n for n, cs in CONSUMIDOR.items() if all(c in NO_CONSTRUIDO for c in cs)}


#: LO QUE CUESTA PREGUNTAR, MEDIDO, y es lo que decide que por defecto no se pregunte (15/08/2026).
#:
#: | sonda | contenedor (sana) | anfitrión (caída) |
#: |---|---:|---:|
#: | db + extensiones + embebedor + reordenador + nli | ~10 ms | ~23 ms |
#: | **redis** | 2,3 ms | **2.697 ms** |
#: | **worker** | **2.089 ms** | **7.404 ms** |
#: | **TOTAL** | **2.117 s** | **10.129 s** |
#:
#: **Y LA CABECERA DE LA INTERFAZ ENLAZA ESTO**, así que quien lo pulse el lunes se queda diez
#: segundos mirando una pantalla quieta — en el sitio donde se está enseñando que el sistema es
#: rápido y honesto.
#:
#: **Las dos cifras que deciden, y ninguna es la que uno esperaría:** el `worker` cuesta **2 s
#: incluso ESTANDO SANO**, porque `control.ping` es un *broadcast* que espera su ventana entera; y
#: **caído se va a 7,4 s con un plazo nominal de 2**, o sea que su propio `timeout` no lo sujeta —
#: la familia del tope expresado en la unidad que la avería infla, otra vez.
#:
#: Eso descarta la opción "plazo corto": cualquier plazo menor que 2 s daría por **caído un worker
#: sano**, que es inventarse una avería. Así que **no se sondean por defecto**, y eso no es
#: esconderlas: es la consecuencia de lo que la clasificación de al lado ya decía —**nada
#: construido las usa**—. Se dicen con su estado `no_sondeada` y su porqué, y `/salud?todo=1` las
#: sondea para cuando de verdad interese.
NO_SE_SONDEA_POR_DEFECTO = ("no se sonda por defecto: nada construido la usa, y preguntarle cuesta "
                            "entre 2,1 s (sana) y 7,4 s (caida). Usa /salud?todo=1 para sondearla")


#: EL INVENTARIO DE SONDAS, EN EL MÓDULO Y NO DENTRO DE LA FUNCIÓN. Vive aquí para que su test
#: pueda recorrerlo —comprobar que cada sonda declara qué se pierde sin ella— **mirando la
#: estructura y no el texto del fuente**. La versión anterior de ese test hacía `'"db": _sonda' in
#: inspect.getsource(salud)`, o sea que comprobaba cómo estaba escrita la función: se puso rojo al
#: reordenar el código sin que nada cambiara de comportamiento, que es la definición de test frágil.
#: Guarda el NOMBRE de la función y no la función: si guardara la referencia, quedaría capturada al
#: importar y `monkeypatch.setattr(main, "_db", ...)` —que es como se prueba cada avería de
#: `/salud`— dejaría de tener efecto **en silencio**, con la suite en verde probando las sondas
#: reales en vez de las falsas. Se resuelve al llamar.
SONDAS = {"db": "_db", "extensiones": "_extensiones", "redis": "_redis", "embebedor": "_embebedor",
          "reordenador": "_reordenador", "nli": "_nli", "worker": "_worker"}


@app.get("/salud")
def salud(todo: bool = False) -> JSONResponse:
    sondas = {n: globals()[atributo] for n, atributo in SONDAS.items()}
    saltadas = set() if todo else sin_consumidor_construido()
    dependencias = {
        n: ({"estado": "no_sondeada", "detalle": NO_SE_SONDEA_POR_DEFECTO, "ms": 0.0}
            if n in saltadas else _sonda(fn))
        for n, fn in sondas.items()}
    # `no_sondeada` NO es `fallo`: no se sabe, y no saberlo de una pieza que nadie usa no es una
    # caida. Por eso se compara contra "fallo" en vez de contra "ok", que era lo de antes.
    caidas = [n for n, v in dependencias.items() if v["estado"] == "fallo"]
    rotas = [n for n in caidas if n in ESENCIALES]
    # SIN CONSUMIDOR CONSTRUIDO: abajo o sin preguntar, pero TODO lo que la usaría está declarado y
    # no construido. No puede degradar nada que se sirva hoy, así que no cuenta como degradación.
    sin_consumidor = [n for n in sondas
                      if n not in ESENCIALES and n in sin_consumidor_construido()
                      and dependencias[n]["estado"] != "ok"]
    degradadas = [n for n in caidas if n not in ESENCIALES and n not in sin_consumidor]
    arrancado = getattr(app.state, "arrancado_en", None)
    cuerpo = {
        "estado": "roto" if rotas else ("degradado" if degradadas else "ok"),
        # SE DICE EN VOZ ALTA CUANDO NO HAY PUERTA. Un defecto abierto que nadie ve es la avería que
        # este repo persigue; publicarlo aquí lo convierte en una decision que se puede mirar.
        "autenticacion": "con token" if autenticacion.token_configurado() else "ABIERTA",
        # El techo de concurrencia real de este proceso, leido del limitador VIVO (0.4).
        "hilos_de_bloqueo": hilos_de_bloqueo_vivos(),
        # La misma marca que en /api: "¿es el mio?" se contesta mirando.
        "arrancado_en": (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(arrancado))
                         if arrancado else None),
        "puede_responder": not rotas,
        "caidas": caidas,
        "rotas": rotas,
        "degradadas": degradadas,
        # Se listan APARTE y no se esconden: siguen estando abajo y sigue diciéndose. Lo que cambia
        # es que no se presentan como una degradación de lo que se sirve, porque no lo son.
        "sin_consumidor": [
            {"pieza": n,
             "esta": "sin preguntar" if dependencias[n]["estado"] == "no_sondeada" else "abajo",
             "por_que_no_degrada": f"lo unico que la usaria esta declarado y NO construido: "
                                   f"{', '.join(CONSUMIDOR[n])}",
             "detalle": dependencias[n]["detalle"]}
            for n in sin_consumidor],
        # El texto legible: qué falta, qué se pierde por ello, y el detalle crudo de la sonda —que
        # es donde pone "No module named 'torch'"—. Los tres juntos, porque el nombre solo no dice
        # qué hacer y la consecuencia sola no dice qué instalar.
        # `que_falta` habla solo de lo que FALTA DE VERDAD: lo esencial roto y lo que degrada. Lo
        # que no tiene consumidor tiene su propia clave arriba, con su porqué.
        "que_falta": [f"{n}: {CONSECUENCIA.get(n, 'sin consecuencia declarada')} "
                      f"| {dependencias[n]['detalle']}"
                      for n in caidas if n not in sin_consumidor],
        "dependencias": dependencias,
    }
    return JSONResponse(cuerpo, status_code=503 if rotas else 200)
