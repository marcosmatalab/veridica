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


def _evento(nombre: str, datos: dict) -> str:
    return f"event: {nombre}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"


def _mensajes(texto: str) -> list:
    return [{"role": "system", "content": SISTEMA}, {"role": "user", "content": texto}]


def _generacion(cliente: ClienteInferencia, texto: str, t0: float):
    """Una pasada contra el proveedor. Va emitiendo eventos y DEVUELVE el resultado de la pasada.

    La prosa se emite siempre, también en el reintento, y no hay contradicción: solo se llega al
    reintento cuando la pasada anterior no escribió nada en pantalla. Si escribió, el bucle de
    arriba no vuelve a llamar.
    """
    estado = {"crudo": "", "ttft_prosa_ms": None, "llamada": Llamada(), "uso": Uso(),
              "fin": None, "error": None, "emitido": False}
    prosa = ProsaEnCurso()
    try:
        for trozo in cliente.stream(_mensajes(texto), response_format(), traza=estado["llamada"]):
            if trozo.uso:
                estado["uso"] = trozo.uso
            if trozo.fin:
                estado["fin"] = trozo.fin
            if not trozo.texto:
                continue
            estado["crudo"] += trozo.texto
            nueva = prosa.alimentar(trozo.texto)
            if not nueva:
                continue
            if estado["ttft_prosa_ms"] is None:
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
    for intento in (1, 2):
        estado = yield from _generacion(cliente, peticion.texto, t0)
        if estado["error"]:
            motivo = estado["error"]
        else:
            try:
                validada = validar_forma(json.loads(estado["crudo"]))
                motivo = None
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
        yield _evento("abstencion", {
            "motivo": motivo,
            "que_significa": "el proveedor no devolvio el contrato de la seccion 7; se abstiene en "
                             "vez de ensenar algo sin forma conocida",
            "ya_habia_prosa_en_pantalla": estado["emitido"],
        })

    etapas = {
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
        "verificacion": {"construido": False, "encargo": "fase 4"},
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
