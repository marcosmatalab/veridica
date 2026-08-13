"""`POST /consulta` en streaming: el eco verificado del contrato (encargo 2.2).

QUÉ ES ESTO Y QUÉ NO ES. Aquí **no hay recuperación todavía** (fase 3) ni **verificación** (fase 4).
Lo único que se demuestra es que el contrato de la sección 7 viaja entero: se le pide al modelo
pequeño con `response_format` de esquema, vuelve como JSON, el servidor comprueba su FORMA con su
propio modelo tipado y lo emite por eventos. Por eso cada afirmación sale con
`veredicto: "sin_verificar"`, que es literalmente lo que es.

LOS DOS TIEMPOS, que es la decisión de diseño de este endpoint (ADR 0009). Con salida tipada hay dos
TTFT distintos y confundirlos es lo que hace que una demo parezca rápida cuando no lo es:

- `ttft_proveedor_ms`: el primer token del JSON. Llega pronto y **no es lo que ve el alumno**: es `{`.
- `ttft_prosa_ms`: el primer carácter de `respuesta_redactada` que sale por el evento `token`. Este
  es el TTFT del alumno, el que manda la sección 10, y el que cuenta el día de la demo.

Se emite SOLO prosa, sacada del JSON parcial según llega (`ProsaEnCurso`). El alumno no ve llaves ni
comillas, y el servidor no espera al objeto entero, que es la alternativa que convertía el TTFT en
el total y dejaba el streaming en adorno.

EL PRECIO DE ESA ELECCIÓN, escrito porque es real: la prosa sale ANTES de que el objeto cierre y se
valide. Si el JSON acaba roto después de haber emitido texto, ese texto ya está en pantalla y el
reintento único de la sección 7 ya no se puede usar sin repetirle al alumno lo que acaba de leer. En
ese caso se emite `abstencion` con su motivo y la interfaz retira lo emitido. El reintento queda
para el caso en que aún no ha salido nada, que es el habitual.
"""
import json
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.inferencia import (ClienteInferencia, ErrorDefinitivo, ErrorTransitorio, Llamada,
                                 Uso)
from app.core.prosa_parcial import ProsaEnCurso
from app.core.recuperacion import buscar_vectorial, confianza_de, recuperar
from app.modelos.contrato import SIN_VERIFICAR, ContratoRoto, response_format, validar_forma

router = APIRouter()

VERSION_PROMPT = "3.3-con-recuperacion"

#: Los que entran en el contexto. El reordenador del 3.4 escogera estos 6 de entre los
#: 30 del pool; hasta que exista, se toman los 6 primeros de la fusion tal cual.
FRAGMENTOS_EN_CONTEXTO = 6
POOL = 30

SISTEMA = "\n".join([
    "Eres un profesor de Formación Profesional de informática. Respondes SIEMPRE con el objeto"
    " JSON del contrato, sin texto fuera de él.",
    "Te doy FRAGMENTOS del temario del alumno, numerados. Responde SOLO desde ellos:",
    " - si copias texto exacto de un fragmento, la afirmación es 'literal', lleva 'cita' con ese"
    " texto COPIADO LETRA A LETRA y 'fragmento_id' con su número;",
    " - si lo reformulas con tus palabras, es 'parafrasis' con su 'fragmento_id';",
    " - lo que digas y NO esté en los fragmentos va como 'conocimiento' con fragmento_id nulo, y"
    " cuanto menos, mejor;",
    " - las transiciones, preguntas al alumno, analogías y resúmenes van como 'andamiaje'.",
    "Si los fragmentos no bastan para responder, dilo en la redacción en vez de rellenar.",
    "'respuesta_redactada' es el texto que lee el alumno y no puede decir nada que no esté en las"
    " afirmaciones. Sé breve: cuatro o cinco frases.",
])

SEPARADOR = "\n\n---\n\n"


def _contexto(candidatos: list) -> str:
    """Los fragmentos, numerados por su id REAL de base, que es el que la afirmación tiene que citar.

    El `fragmento_id` que se le enseña al modelo es el de la fila de `fragmentos`, no un índice de
    la lista: así lo que el modelo escriba en el contrato apunta a algo que existe y que la fase 4
    va a poder abrir para verificar. Un índice local exigiría traducirlo después, y esa traducción
    es justo donde se pierde la trazabilidad.
    """
    return SEPARADOR.join(
        f"[fragmento_id={c.fragmento_id}] ({c.unidad or 'sin unidad'})\n{c.texto}"
        for c in candidatos)


class Consulta(BaseModel):
    texto: str = Field(min_length=1)
    asignatura_id: int | None = None
    modo: str = "responder"
    usuario_id: str | None = None
    #: EL ENGANCHE DE LA ABLACIÓN, reservado en el 2.4 y SIN EFECTO hoy porque no hay capa de
    #: verificación que apagar (fase 4). Está ahora, y no cuando haga falta, porque el guion de la
    #: demo pide correr los mismos casos con la verificación apagada: si la interfaz no tuviera por
    #: dónde, alguien lo injertaría la noche antes encima de lo que hubiera. Se registra en la traza
    #: para que de cada consulta conste qué se pidió, aunque hoy no cambie nada.
    verificacion: bool = True


def _evento(nombre: str, datos: dict) -> str:
    return f"event: {nombre}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"


def _marca(estado: dict, nombre: str, t0: float, detalle: str) -> str:
    """Apunta una etapa REAL y devuelve su evento.

    Las etapas son la respuesta a los 1,6 s de pantalla en blanco, y la condición del encargo es
    que sean **medidas**: cada una se apunta en el momento en que de verdad ocurre y la misma lista
    va a `respuestas.etapas`, para que lo dibujado se pueda cotejar contra la traza. Una barra que
    avanza por temporizador es una barra que miente, y aquí no cabe.
    """
    ms = round((time.perf_counter() - t0) * 1000, 1)
    estado["marcas"].append({"nombre": nombre, "ms": ms})
    return _evento("etapa", {"nombre": nombre, "ms": ms, "detalle": detalle})


def _mensajes(texto: str, contexto: str = "", confianza: str = "baja") -> list:
    """El prompt del 3.3, ya con fragmentos.

    LA CONFIANZA SE LA DICE EL SERVIDOR AL MODELO, y no al revés. `confianza_recuperacion` es un
    hecho sobre la RECUPERACIÓN —cuánto destaca el primer candidato sobre el sexto—, y el modelo no
    tiene forma de saberlo: solo ve seis fragmentos, sin sus distancias ni lo que quedó fuera.
    Dejarle rellenar ese campo sería pedirle una opinión sobre un trabajo que no ha hecho.

    Por eso el campo **salió del esquema** (ADR 0014): aquí se le dice el valor para que AJUSTE SU
    COMPORTAMIENTO —si es baja, que lo diga en vez de rellenar—, pero no puede escribirlo. Que se lo
    dijéramos y luego se lo sobrescribiéramos sería pagar tokens por una opinión que se descarta.
    """
    usuario = texto if not contexto else (
        "FRAGMENTOS DEL TEMARIO:\n\n" + contexto + "\n\n---\n\nPREGUNTA DEL ALUMNO: " + texto)
    sistema = SISTEMA + (
        f"\nLa recuperación tiene confianza '{confianza}', medida por el servidor. Si es 'baja', "
        f"dilo en la redacción en vez de rellenar. Ese dato NO va en el JSON: no es tuyo."
        if contexto else "")
    return [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]


def _generacion(cliente: ClienteInferencia, texto: str, t0: float,
                contexto: str = "", confianza: str = "baja"):
    """Una pasada contra el proveedor. Va emitiendo eventos y DEVUELVE el resultado de la pasada.

    La prosa se emite siempre, también en el reintento, y no hay contradicción: solo se llega al
    reintento cuando la pasada anterior no escribió nada en pantalla. Si escribió, el bucle de
    arriba no vuelve a llamar.
    """
    estado = {"crudo": "", "ttft_prosa_ms": None, "llamada": Llamada(), "uso": Uso(),
              "fin": None, "error": None, "emitido": False, "marcas": []}
    prosa = ProsaEnCurso()
    yield _marca(estado, "peticion_enviada", t0, "consultando al modelo pequeño")
    try:
        for trozo in cliente.stream(_mensajes(texto, contexto, confianza),
                                    response_format(), traza=estado["llamada"]):
            if trozo.uso:
                estado["uso"] = trozo.uso
            if trozo.fin:
                estado["fin"] = trozo.fin
            if not trozo.texto:
                continue
            if not estado["crudo"]:
                yield _marca(estado, "primer_token_proveedor", t0,
                             "el modelo ha empezado a escribir el contrato")
            estado["crudo"] += trozo.texto
            nueva = prosa.alimentar(trozo.texto)
            if not nueva:
                continue
            if estado["ttft_prosa_ms"] is None:
                yield _marca(estado, "primera_prosa", t0, "redactando la respuesta")
                estado["ttft_prosa_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                yield _evento("ttft", {
                    "ttft_prosa_ms": estado["ttft_prosa_ms"],
                    "ttft_proveedor_ms": round(estado["llamada"].ttft_proveedor_ms or 0, 1),
                    "que_es": "prosa_ms es el primer caracter que ve el alumno; proveedor_ms es el "
                              "primer token del JSON, que es '{'",
                })
            estado["emitido"] = True
            yield _evento("token", {"t": nueva})
    except (ErrorTransitorio, ErrorDefinitivo) as e:
        estado["error"] = f"{type(e).__name__}: {e}"
    return estado


def _recuperar(peticion: Consulta, embebedor, url: str, t0: float, reordenador=None):
    """La recuperación del 3.3, emitiendo sus etapas REALES según ocurren.

    Aquí las etapas por fin cubren la espera con trabajo que alimenta la respuesta, que era el
    diseño del 2.4: hasta ahora la pantalla esperaba a que el modelo escribiera, y ahora enseña que
    se está buscando en el temario y cuántos fragmentos han salido.
    """
    marcas, contexto, confianza, detalle = [], "", "baja", {"motivo": "sin recuperacion"}
    if embebedor is None or peticion.asignatura_id is None:
        return marcas, contexto, confianza, detalle, []
    vector = embebedor.embeber(peticion.texto)
    marcas.append({"nombre": "consulta_embebida", "detalle": "pregunta convertida a vector",
                   "ms": round((time.perf_counter() - t0) * 1000, 1)})
    de_recuperacion = []
    candidatos = recuperar(url, peticion.asignatura_id, peticion.texto, vector=vector, k=POOL,
                           marcas=de_recuperacion)
    base = marcas[-1]["ms"]
    for marca in de_recuperacion:
        marcas.append({**marca, "ms": round(base + marca["ms"], 1)})
    # La confianza sale de la lista VECTORIAL, no de la fusion: la puntuacion vectorial es una
    # distancia con significado y la de RRF es una suma de inversos de rangos, que no lo tiene.
    confianza, detalle = confianza_de(buscar_vectorial(url, peticion.asignatura_id, vector,
                                                       k=FRAGMENTOS_EN_CONTEXTO))
    # EL REORDENADO, Y SU RESPALDO ANUNCIADO (3.4, ADR 0015). La fusion aporta COBERTURA y no
    # orden -medido: RRF coloca peor que el vectorial solo-, asi que el orden lo pone el
    # cross-encoder. Cuando no hay GPU no se reordena en CPU: son 13.714 ms de p95 medidos, en la
    # ruta del TTFT, o sea catorce segundos de pantalla muerta delante del alumno. Se sirve el
    # orden de la fusion Y SE DICE, que es el patron del circuit breaker del 8.2.
    if reordenador is not None:
        antes = time.perf_counter()
        elegidos = reordenador.reordenar(peticion.texto, candidatos[:POOL],
                                         top=FRAGMENTOS_EN_CONTEXTO)
        marcas.append({
            "nombre": "reordenado",
            "detalle": f"{len(candidatos[:POOL])} candidatos releidos uno a uno con la pregunta",
            "ms": round((time.perf_counter() - t0) * 1000, 1),
            "reordenado_ms": round((time.perf_counter() - antes) * 1000, 1),
        })
    else:
        elegidos = candidatos[:FRAGMENTOS_EN_CONTEXTO]
        marcas.append({
            "nombre": "sin_reordenar",
            "detalle": "sin GPU: se responde con el orden de la busqueda, sin reordenar",
            "ms": round((time.perf_counter() - t0) * 1000, 1),
        })
    # LA ETAPA QUE LLENA LA ESPERA EN VEZ DE ANUNCIARLA. Las cuatro etapas de recuperación ocurren
    # en los primeros 80 ms y después la pantalla espera al modelo unos dos segundos: medido en el
    # 3.3, cubrían el 3,5 % del tiempo. Enseñar aquí los SEIS FRAGMENTOS con su documento y su
    # unidad no es relleno -es la evidencia de lo que el sistema acaba de recuperar- y leer seis
    # títulos ocupa justo esos dos segundos. Y hace literalmente lo que el 2.4 escribió como
    # objetivo: **el alumno ve las citas antes que el texto**.
    marcas.append({
        "nombre": "fragmentos_recuperados",
        "detalle": f"{len(elegidos)} fragmentos del temario, por orden de relevancia",
        "ms": round((time.perf_counter() - t0) * 1000, 1),
        "fragmentos": [{"id": c.fragmento_id, "documento": c.documento.split("/")[-1],
                        "unidad": c.unidad or "sin unidad",
                        "origen": c.origen} for c in elegidos],
        "confianza": confianza,
    })
    return marcas, _contexto(elegidos), confianza, detalle, elegidos


def _flujo(cliente: ClienteInferencia, peticion: Consulta, traza, consulta_id: int,
           embebedor=None, url: str = "", reordenador=None):
    t0 = time.perf_counter()
    estado, validada, motivo = None, None, None
    marcas = []
    marcas_recuperacion, contexto, confianza, detalle_confianza, elegidos = _recuperar(
        peticion, embebedor, url, t0, reordenador)
    for marca in marcas_recuperacion:
        # A la traza va el nombre y el milisegundo; los fragmentos ya viajan en etapas.recuperacion,
        # asi que repetirlos aqui seria guardar dos veces lo mismo.
        marcas.append({"nombre": marca["nombre"], "ms": marca["ms"]})
        yield _evento("etapa", marca)
    for intento in (1, 2):
        estado = yield from _generacion(cliente, peticion.texto, t0, contexto, confianza)
        marcas.extend(estado["marcas"])   # las de las DOS pasadas: la traza cuenta lo que paso
        if estado["error"]:
            motivo = estado["error"]
        else:
            try:
                validada = validar_forma(json.loads(estado["crudo"]))
                motivo = None
                estado["marcas"].append({"nombre": "contrato_validado",
                                         "ms": round((time.perf_counter() - t0) * 1000, 1)})
                marcas.append(estado["marcas"][-1])
                yield _evento("etapa", {"nombre": "contrato_validado", "ms": marcas[-1]["ms"],
                                        "detalle": "el contrato llego bien formado (forma, no "
                                                   "verdad: la verificacion es la fase 4)"})
                break
            except (json.JSONDecodeError, ContratoRoto) as e:
                motivo = f"{type(e).__name__}: {e}"
                if estado["fin"] == "length":
                    motivo += (f" | el modelo llego al tope de {cliente.a.max_tokens} tokens: JSON "
                               f"cortado, que es la firma del bucle degenerado")
        # El reintento unico de la seccion 7, con su limite honesto: si ya salio prosa, no se
        # repite la llamada, porque repetirla le repetiria el texto al alumno.
        if intento == 2 or estado["emitido"]:
            break

    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    uso, llamada = estado["uso"], estado["llamada"]
    afirmaciones = []
    if validada is not None:
        # UNA AFIRMACION NO PUEDE CITAR UN FRAGMENTO QUE NO SE LE DIO. Es comprobable sin modelo y
        # sin umbral -el servidor sabe exactamente que seis mando-, y si no se comprueba, el sistema
        # se estaria fabricando la procedencia: una `literal` que apunta a un id que no estuvo en el
        # contexto es una cita inventada con aspecto de verificable. Aqui solo se MARCA, porque la
        # decision de podar es del 4.5; marcarlo ya evita que llegue a la fase 4 disfrazado.
        en_contexto = {c.fragmento_id for c in elegidos}
        afirmaciones = [{"tipo": a.tipo, "texto": a.texto,
                         "fragmento_id": getattr(a, "fragmento_id", None),
                         "veredicto": SIN_VERIFICAR,
                         "detalle": {"cita": getattr(a, "cita", None),
                                     "expresion": getattr(a, "expresion", None),
                                     "andamiaje": getattr(a, "andamiaje", None),
                                     "id_en_contrato": a.id,
                                     "fragmento_en_contexto": (
                                         None if getattr(a, "fragmento_id", None) is None
                                         else a.fragmento_id in en_contexto)}}
                        for a in validada.afirmaciones]
        yield _evento("afirmaciones", {
            "afirmaciones": afirmaciones,
            "modo": validada.modo,
            # `ref` la pone el servidor y hoy va nula, declarada: resolverla contra el arbol es el
            # 5.4. Lo que NO se hace es dejar que la escriba el modelo, que no ve el arbol.
            "siguiente_paso": validada.siguiente_paso.model_dump() | {
                "ref": None, "ref_la_resuelve": "servidor (encargo 5.4)"},
            # Del SERVIDOR, no del modelo: el campo salio del esquema en el 3.3 (ADR 0014).
            "confianza_recuperacion": confianza,
            "aviso": "veredicto 'sin_verificar': el 2.2 comprueba la FORMA del contrato, no la "
                     "verdad de lo que dice. La verificacion es la fase 4.",
        })
    else:
        marcas.append({"nombre": "abstencion", "ms": total_ms})
        yield _evento("etapa", {"nombre": "abstencion", "ms": total_ms,
                                "detalle": "el contrato no llego bien formado"})
        yield _evento("abstencion", {
            "motivo": motivo,
            "que_significa": "el proveedor no devolvio el contrato de la seccion 7; se abstiene en "
                             "vez de ensenar algo sin forma conocida",
            # Las dos abstenciones NO se dibujan igual, y por eso viaja este campo. En falso, no ha
            # salido nada y la abstencion es limpia. En verdadero, el alumno YA tiene texto en
            # pantalla y hay que marcarlo como RETIRADO: no se borra a la callada, porque borrar sin
            # decir nada le deja pensando que lo leyo mal.
            "ya_habia_prosa_en_pantalla": estado["emitido"],
        })

    etapas = {
        "marcas": marcas,
        "generacion": {
            "ttft_proveedor_ms": round(llamada.ttft_proveedor_ms, 1) if llamada.ttft_proveedor_ms
            else None,
            "ttft_prosa_ms": estado["ttft_prosa_ms"],
            "total_ms": total_ms,
            "intentos_http": llamada.intentos,
            "esperas_s": llamada.esperas,
            # EL CODIGO DE CADA TRANSITORIO, no solo cuantos hubo: un 429 se espera y se reintenta,
            # un 503 puede ser una caida. Sin esto, una corrida con reintentos obliga a adivinar.
            "codigos_transitorios": llamada.codigos,
            "fin": estado["fin"],
        },
        "recuperacion": {"construido": bool(elegidos), "pool": POOL,
                         "en_contexto": [c.fragmento_id for c in elegidos],
                         "confianza": confianza, "detalle_confianza": detalle_confianza},
        # `solicitada` es el enganche de la ablacion: se registra lo que se pidio aunque hoy no
        # cambie nada, para que el dia que la fase 4 exista se pueda distinguir una corrida con
        # verificacion de una sin ella mirando la traza, y no la memoria de quien la lanzo.
        "verificacion": {"construido": False, "encargo": "fase 4",
                         "solicitada": peticion.verificacion},
    }
    respuesta_id = traza.cerrar_respuesta(
        consulta_id=consulta_id, afirmaciones=afirmaciones, modelo=cliente.a.modelo,
        ttft_ms=int(estado["ttft_prosa_ms"]) if estado["ttft_prosa_ms"] else None,
        total_ms=int(total_ms), tokens_entrada=uso.tokens_entrada,
        tokens_salida=uso.tokens_salida, coste_eur=uso.coste_eur(), etapas=etapas,
        abstencion=validada is None)

    yield _evento("fin", {
        "respuesta_id": respuesta_id, "consulta_id": consulta_id,
        "abstencion": validada is None, "motivo": motivo,
        "ttft_prosa_ms": estado["ttft_prosa_ms"], "total_ms": total_ms,
        "ttft_proveedor_ms": round(llamada.ttft_proveedor_ms, 1) if llamada.ttft_proveedor_ms
        else None,
        "tokens_entrada": uso.tokens_entrada, "tokens_salida": uso.tokens_salida,
        "coste_eur": uso.coste_eur(), "version_prompt": VERSION_PROMPT,
        "confianza_recuperacion": confianza, "detalle_confianza": detalle_confianza,
        "fragmentos_en_contexto": [c.fragmento_id for c in elegidos],
        "verificacion": {"solicitada": peticion.verificacion, "construido": False,
                         "aviso": "el interruptor no hace nada todavia: no hay capa de "
                                  "verificacion que apagar hasta la fase 4"},
    })


@router.post("/consulta")
def consulta(peticion: Consulta, request: Request) -> StreamingResponse:
    traza = request.app.state.traza
    cliente = request.app.state.cliente_inferencia
    if cliente is None:
        raise HTTPException(503, "sin proveedor de inferencia: "
                                 + getattr(request.app.state, "sin_proveedor", "no configurado"))
    consulta_id = traza.abrir_consulta(texto=peticion.texto, asignatura_id=peticion.asignatura_id,
                                       modo=peticion.modo, usuario_id=peticion.usuario_id)
    return StreamingResponse(_flujo(cliente, peticion, traza, consulta_id,
                                    getattr(request.app.state, "embebedor", None),
                                    request.app.state.url_base_datos,
                                    getattr(request.app.state, "reordenador", None)),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
