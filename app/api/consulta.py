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
from app.modelos.contrato import SIN_VERIFICAR, ContratoRoto, response_format, validar_forma

router = APIRouter()

VERSION_PROMPT = "2.2-eco-sin-recuperacion"

SISTEMA = (
    "Eres un profesor de Formación Profesional de informática. Respondes SIEMPRE con el objeto JSON "
    "del contrato, sin texto fuera de él.\n"
    "AVISO IMPORTANTE PARA ESTA VERSIÓN: no se te han dado fragmentos del temario, así que NO puedes "
    "citar. Toda afirmación factual va con tipo 'conocimiento' y 'fragmento_id' nulo; las "
    "transiciones, preguntas al alumno, analogías y resúmenes van con tipo 'andamiaje' y su clase. "
    "No uses 'literal' ni 'parafrasis': no tienes de dónde. "
    "'confianza_recuperacion' es 'baja', porque no ha habido recuperación.\n"
    "'respuesta_redactada' es el texto que lee el alumno y no puede decir nada que no esté en las "
    "afirmaciones. Sé breve: cuatro o cinco frases."
)


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


def _mensajes(texto: str) -> list:
    return [{"role": "system", "content": SISTEMA}, {"role": "user", "content": texto}]


def _generacion(cliente: ClienteInferencia, texto: str, t0: float):
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
        for trozo in cliente.stream(_mensajes(texto), response_format(), traza=estado["llamada"]):
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


def _flujo(cliente: ClienteInferencia, peticion: Consulta, traza, consulta_id: int):
    t0 = time.perf_counter()
    estado, validada, motivo = None, None, None
    marcas = []
    for intento in (1, 2):
        estado = yield from _generacion(cliente, peticion.texto, t0)
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
        afirmaciones = [{"tipo": a.tipo, "texto": a.texto,
                         "fragmento_id": getattr(a, "fragmento_id", None),
                         "veredicto": SIN_VERIFICAR,
                         "detalle": {"cita": getattr(a, "cita", None),
                                     "expresion": getattr(a, "expresion", None),
                                     "andamiaje": getattr(a, "andamiaje", None),
                                     "id_en_contrato": a.id}}
                        for a in validada.afirmaciones]
        yield _evento("afirmaciones", {
            "afirmaciones": afirmaciones,
            "modo": validada.modo,
            "siguiente_paso": validada.siguiente_paso.model_dump(),
            "confianza_recuperacion": validada.confianza_recuperacion,
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
            "fin": estado["fin"],
        },
        "recuperacion": {"construido": False, "encargo": "fase 3"},
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
    return StreamingResponse(_flujo(cliente, peticion, traza, consulta_id),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
