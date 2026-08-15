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
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturoAgotado
import json
import os
import re
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.inferencia import (ClienteInferencia, ErrorDefinitivo, ErrorTransitorio, Llamada,
                                 Uso)
from app.core.afirmaciones_en_curso import extraer
from app.core.cobertura import PorteroDeFrases
from app.core.modo import clasificar_modo
# La version del prompt sale del modulo que lo escribe, no de una constante suelta que nadie
# toca al cambiar el texto: eso es lo que la convertia en un campo con nombre de
# trazabilidad y contenido de adorno.
from app.core.prompts import sistema as prompt_sistema
from app.core.prompts import version as version_prompt
from app.core.prosa_parcial import ProsaEnCurso
from app.core.recuperacion import PESOS_FUSION, buscar_vectorial, confianza_de, recuperar
from app.core.ritmo import RitmoCaido, VigilanteDeRitmo
from app.core.verificador_calculo import operandos_sin_fuente
from app.core.verificador_calculo import verificar as verificar_calculo
from app.core.verificador_calculo import verificar_texto
from app.core.verificador_calculo import INSTRUMENTO as INSTRUMENTO_CALCULO
from app.core.verificador_literal import DEGRADADA
from app.core.verificador_literal import INSTRUMENTO as INSTRUMENTO_LITERAL
from app.core.verificador_literal import verificar
from app.core.verificador_nli import COBERTURA_MINIMA as COBERTURA_MINIMA_NLI
from app.core.verificador_nli import INSTRUMENTO as INSTRUMENTO_NLI
from app.core.verificador_nli import NO_VERIFICABLE, PODADA, REINTENTO
from app.modelos.contrato import (SIN_VERIFICAR, ContratoRoto, numero_de_referencia,
                                  response_format, validar_forma)

router = APIRouter()

#: Los que entran en el contexto. El reordenador del 3.4 escogera estos 6 de entre los
#: 30 del pool; hasta que exista, se toman los 6 primeros de la fusion tal cual.
FRAGMENTOS_EN_CONTEXTO = 6
POOL = 30

#: DOS NUMEROS Y NO UNO, Y LA DISTINCION ES LA DECISION DEL 14 DE AGOSTO DE 2026.
#:
#: `OBJETIVO_MS` es el REQUISITO DE PRODUCTO de la seccion 11: la consulta no deberia pasar de 5 s.
#: Sigue siendo el objetivo y **no se baja de ahi**; lo que cambia es que ahora tiene su brecha
#: medida al lado en vez de fingirse cumplido.
#:
#: `PRESUPUESTO_MS` es el PLAZO OPERATIVO: donde se corta de verdad. Sube a 8 s, y no es mover la
#: porteria: **el 5 s se fijo SIN la medida**, y medido resulta que el p50 de la configuracion
#: completa -embebedor, vectorial, reordenador y NLI- lo roza. Un tope por debajo de la mediana del
#: sistema no es un objetivo, es garantia de fallo: no produce un sistema mas rapido, produce uno
#: que corta el 30 % de sus respuestas. Y cortar una respuesta entera a los 5 s es peor experiencia
#: que entregarla a los 6 con la pantalla llena desde los 700 ms -fragmentos, afirmaciones y
#: veredictos apareciendo-, que es justo para lo que se construyo el solape.
#:
#: LA BRECHA, DESGLOSADA (evidencia del 14 de agosto): +1,3 s la via vectorial completa frente a
#: solo lexica, +0,4 s el reordenador. **La latencia esta en la GENERACION, no en la recuperacion**,
#: asi que las palancas son la longitud de la respuesta o el modelo — nunca recortar el contexto.
#:
#: Y LA TASA DE CORTE SE REPORTA A LOS DOS PRESUPUESTOS, siempre, para que nadie lea el numero bueno
#: sin ver el otro (`scripts/medir_abstencion.py`).
OBJETIVO_MS = int(os.environ.get("OBJETIVO_CONSULTA_MS") or 5000)
PRESUPUESTO_MS = int(os.environ.get("PRESUPUESTO_CONSULTA_MS") or 8000)


#: Caracteres por token del tokenizador de Mistral en castellano. Sale de las corridas reales: en la
#: muestra del 13 de agosto, `tokens_salida` frente a la longitud del JSON crudo da del orden de 3,6.
#: Es una APROXIMACION y por eso lo estimado se marca como estimado.
CARACTERES_POR_TOKEN = 3.6


#: Cuanto del JSON crudo se guarda cuando el contrato NO valida. Con `max_tokens` en 900, el peor
#: caso ronda los 3.500 caracteres, asi que 6.000 cabe entero casi siempre y acota el disco si algun
#: dia el modelo se desboca. Se guarda tambien SI se trunco: un registro recortado que no dice que lo
#: esta es peor que ninguno, porque invita a contar sobre el creyendolo completo.
LARGO_CRUDO_GUARDADO = 6000


#: Cuenta afirmaciones y caracteres de `cita` sobre el JSON CRUDO, que es la unica via de saberlo en
#: las consultas CORTADAS: si el contrato no llega a validar, no se guarda ni una afirmacion en la
#: tabla, asi que justo las respuestas que hay que explicar son las que no dejan rastro. Contar sobre
#: el texto recibido es aproximado -la ultima afirmacion puede venir a medias- y por eso se declara.
RE_TIPO = re.compile(r'"tipo"\s*:')
RE_CITA = re.compile(r'"cita"\s*:\s*"((?:[^"\\]|\\.)*)"')


def _contar_en_crudo(crudo: str) -> dict:
    """Afirmaciones empezadas y caracteres de cita, del JSON tal como llegó."""
    citas = [m.group(1) for m in RE_CITA.finditer(crudo)]
    return {"afirmaciones_contadas": len(RE_TIPO.findall(crudo)),
            "citas_contadas": len(citas),
            "cita_caracteres": sum(len(c) for c in citas),
            "cita_caracteres_max": max((len(c) for c in citas), default=0)}


#: EL NLI CORRE EN UN HILO, Y ESA ES LA DECISIÓN DE DISEÑO DEL ENCHUFE.
#:
#: El 4.3 midió **216 ms por par en CPU a 16 hilos** y dijo que cabía en los ~823 ms en que el modelo todavía
#: escribe la prosa. **Eso es verdad si SOLAPA, y falso si se llama a pelo desde el bucle**: este
#: bucle consume trozos del proveedor, así que 400 ms de inferencia dentro de él no se superponen a
#: nada — bloquean la lectura, encogen el presupuesto de 5 s en su misma cantidad y, de paso, pueden
#: hacer que el vigilante de ritmo vea un flujo lento que no lo está.
#:
#: Con hilo sí solapa de verdad: torch suelta el GIL durante la inferencia, así que el bucle sigue
#: leyendo mientras mDeBERTa piensa. Dos obreros porque una respuesta trae 1-2 paráfrasis; más sería
#: pelearse con el embebedor por los mismos núcleos.
_OBREROS_NLI = ThreadPoolExecutor(max_workers=2, thread_name_prefix="nli")

#: Presupuesto de verificación de la sección 8. Lo que no llega a tiempo NO se espera: se declara
#: `sin_verificar` con su motivo, que es lo que es. Un veredicto tarde no sirve para nada porque la
#: respuesta ya se ha ido.
PRESUPUESTO_NLI_S = float(os.environ.get("PRESUPUESTO_NLI_MS") or 2000) / 1000


def _lanzar_nli(estado: dict, textos_en_contexto: dict, nli):
    """Manda al NLI las que le tocan. Devuelve `(futuros, eventos_ya_resueltos)`; no espera a nadie.

    **Le tocan dos clases, y la segunda es la que cierra el circuito del 4.2:** las `parafrasis`, y
    las `literal` que la comparación de cadenas **degradó a paráfrasis** porque su cita no aparecía
    letra a letra. Esas segundas llevaban desde el 4.2 saliendo `sin_verificar` con una nota que
    decía "ya lo verificará el NLI"; desde hoy lo verifica.
    """
    if nli is None:
        return {}, []
    futuros, ya = {}, []
    for a in extraer(estado["crudo"]) or []:
        if not isinstance(a, dict):
            continue
        previo = (estado.get("veredictos") or {}).get(a.get("id")) or {}
        toca = a.get("tipo") == "parafrasis" or previo.get("veredicto") == DEGRADADA
        if not toca:
            continue
        numerico = numero_de_referencia(a.get("fragmento_id"))
        fragmento = textos_en_contexto.get(numerico)
        if not fragmento:
            # La misma puerta que el 4.2: sin el fragmento en el contexto no se compara nada. Un
            # `fragmento_id` inventado no se juzga, se poda por procedencia.
            v = {"veredicto": PODADA, "motivo": "procedencia_fabricada",
                 # La puerta la aplica ESTE modulo, no el NLI: si firmara como 4.3, una consulta
                 # que contara podas del NLI incluiria podas que el NLI nunca vio.
                 "instrumento": "4.3/puerta_de_procedencia",
                 "detalle": f"el fragmento {a.get('fragmento_id')} no estuvo en el contexto: "
                            f"no hay premisa que comparar, asi que no se pregunta"}
            estado.setdefault("veredictos", {})[a.get("id")] = v
            # SE EMITE, no solo se guarda: una poda que no sale por el flujo es una poda que el
            # alumno no ve y que ningun test del camino real puede comprobar.
            ya.append(_evento("veredicto", {
                "id_en_contrato": a.get("id"), "tipo": a.get("tipo"),
                "veredicto": v["veredicto"], "motivo": v["motivo"], "detalle": v["detalle"],
                "nli": None, "probabilidad": None, "durante_la_redaccion": True}))
            continue
        hipotesis = a.get("texto") or ""
        # EL ANCLA VIAJA HASTA LA PREMISA (14/08): una literal degradada conoce su cita exacta y
        # una parafrasis puede declarar su apoyo; con cualquiera de las dos, la premisa del NLI es
        # la ventana anclada en el span -si el ancla casa literalmente, que es lo que la hace
        # infabricable-. Sin ancla o sin casar, la seleccion por frases de siempre.
        futuros[_OBREROS_NLI.submit(nli.verificar, hipotesis, fragmento,
                                    a.get("cita"), a.get("apoyo"))] = a
    return futuros, ya


def _cosechar_nli(estado: dict, futuros: dict, esperar_hasta: float | None = None):
    """Emite los veredictos del NLI que ya estén listos. Sin bloquear, salvo al final."""
    for futuro in list(futuros):
        if esperar_hasta is None and not futuro.done():
            continue
        a = futuros.pop(futuro)
        try:
            margen = None if esperar_hasta is None else max(0.0, esperar_hasta - time.perf_counter())
            v = futuro.result(timeout=margen)
        except FuturoAgotado:
            futuros[futuro] = a          # se devuelve a la lista: quizá llegue en la cosecha final
            continue
        except Exception as e:           # noqa: BLE001 - un NLI que revienta no tumba la respuesta
            v = {"veredicto": NO_VERIFICABLE, "motivo": "el_nli_fallo",
                 "instrumento": "4.3/nli:caido",
                 "detalle": f"{type(e).__name__}: {e}"}
        estado.setdefault("veredictos", {})[a.get("id")] = v
        yield _evento("veredicto", {
            "id_en_contrato": a.get("id"),
            "tipo": a.get("tipo"),
            "veredicto": v["veredicto"],
            "motivo": v.get("motivo"),
            "detalle": v.get("detalle"),
            "nli": v.get("nli"),
            "probabilidad": v.get("probabilidad"),
            "durante_la_redaccion": esperar_hasta is None,
            # UN VEREDICTO QUE PIDE REINTENTO Y NO PUEDE TENERLO, DICHO ASI Y NO CALLADO. La seccion
            # 8 manda que `neutral` dispare el reintento unico con la señal; verificar EN CURSO se lo
            # come, porque cuando el NLI contesta la prosa ya esta en pantalla y repetirla seria
            # reescribirle al alumno lo que acaba de leer (la misma regla del 2.2). O sea que este
            # veredicto se resuelve por la politica del 4.5 -poda o degradacion- y NO por un segundo
            # intento. Es el precio del solape, y va en el evento para que la tasa de `neutral` del
            # 4.6 no se lea como "se reintento y siguio mal".
            "reintento_disponible": False if v["veredicto"] == REINTENTO else None,
            "por_que_no": ("la prosa ya estaba en pantalla cuando llego el veredicto: verificar "
                           "mientras se escribe gasta la posibilidad de reintentar"
                           if v["veredicto"] == REINTENTO else None),
        })


def _veredictos_en_curso(estado: dict, textos_en_contexto: dict, pregunta: str = ""):
    """Verifica las afirmaciones ya cerradas y emite un evento `veredicto` por cada una.

    Solo se ocupa de lo que **no necesita modelo**: la puerta de procedencia y la comparación
    literal del 4.2, y el recálculo del 4.4. Los dos son comparaciones —de cadenas uno, de números el
    otro— así que caben enteros en el hueco en el que el modelo todavía está escribiendo la prosa. Lo
    que degrada a `parafrasis` queda pendiente del NLI del 4.3, y se dice.
    """
    array = extraer(estado["crudo"])
    if not array:
        return
    estado["veredictos"] = {}
    resultados_previos = []
    for a in array:
        if not isinstance(a, dict) or a.get("tipo") not in ("literal", "calculo", "conocimiento",
                                                            "andamiaje"):
            continue
        if a.get("tipo") == "calculo":
            v = verificar_calculo(a)
            # EL RECALCULO COMPRUEBA LA OPERACION, NO LOS OPERANDOS: un operando inventado con
            # aritmetica correcta sale `verificada`, y ese es el modo de fallo MAS probable de un
            # modelo -inventar la premisa, no sumar mal-. Atar los operandos al temario es una
            # verificacion nueva, declarada y NO construida; esto es su CONTADOR, no su puerta:
            # mide cuantas veces el sistema calcula sobre cifras que no estan ni en el fragmento
            # citado, ni en la pregunta, ni en un resultado anterior de esta misma respuesta.
            v["operandos_sin_fuente"] = operandos_sin_fuente(
                a.get("expresion") or "",
                [textos_en_contexto.get(numero_de_referencia(a.get("fragmento_id"))) or "",
                 pregunta, *resultados_previos])
            resultados_previos += [str(a.get("resultado_afirmado") or ""),
                                   str(v.get("recalculado") or "")]
        elif a.get("tipo") != "literal":
            # EL TIPO LO ELIGE QUIEN PRODUCE, ASI QUE NO DECIDE QUIEN COMPRUEBA. Una cuenta escrita
            # en el texto de un `conocimiento` o de un `andamiaje` se recalcula igual: fiarse de la
            # etiqueta para decidir SI se verifica es pedirle al modelo que diga cuando hay que
            # comprobarlo, que es el eco que el principio 6 rechaza.
            v = verificar_texto(a.get("texto") or "", a.get("tipo") or "?")
            if v is None:
                continue
        else:
            numerico = numero_de_referencia(a.get("fragmento_id"))
            v = verificar({"cita": a.get("cita"), "fragmento_id": numerico}, textos_en_contexto)
        estado["veredictos"][a.get("id")] = v
        yield _evento("veredicto", {
            "id_en_contrato": a.get("id"),
            "tipo": a.get("tipo"),
            "veredicto": v["veredicto"],
            "motivo": v["motivo"],
            "detalle": v["detalle"],
            # Se dice CUANDO se emitio: la gracia es que sea ANTES de que la prosa termine, y eso
            # tiene que poder comprobarse en la traza y no solo verse en pantalla.
            "durante_la_redaccion": True,
            # Se distingue de un `calculo` en regla: son la misma comprobacion sobre dos situaciones
            # distintas, y contarlas juntas esconderia justo la que interesa.
            "calculo_no_declarado": v.get("calculo_no_declarado", False),
            # El contador de operandos: presente (aunque vacio) en todo `calculo`, para que el
            # denominador de la medida se lea de la propia traza y no de la memoria de nadie.
            "operandos_sin_fuente": v.get("operandos_sin_fuente"),
        })


def _desglose(estado: dict, total_ms: float) -> dict:
    """Los tres tramos de la espera, con su duración, sus tokens y su ritmo.

    Existe porque el diagnóstico "el 30 % se corta por culpa de las afirmaciones" era **plausible y
    no medido**, y los tres tramos tienen palancas distintas: el prefill se baja con menos contexto,
    las afirmaciones con el prompt o con el orden del contrato, y el ritmo del proveedor no se baja
    con nada nuestro. Decidir sin partirlo sería elegir palanca a ojo.
    """
    proveedor = estado["llamada"].ttft_proveedor_ms
    prosa = estado["ttft_prosa_ms"]
    hasta_prosa = estado["tokens_hasta_prosa"]
    total_tokens = estado["vigilante"].total if estado["vigilante"] else None

    def ritmo(tokens, ms):
        if not tokens or not ms or ms <= 0:
            return None
        return round(tokens / (ms / 1000), 1)

    ms_afirmaciones = (prosa - proveedor) if (prosa and proveedor) else None
    ms_prosa = (total_ms - prosa) if prosa else None
    tokens_prosa = (total_tokens - hasta_prosa) if (total_tokens and hasta_prosa) else None
    return {
        # El prefill NO se puede separar de la cola del proveedor desde aquí, y decirlo es parte del
        # dato: los dos viven dentro del mismo "tiempo hasta el primer token".
        "prefill_y_cola_ms": round(proveedor, 1) if proveedor else None,
        "afirmaciones_ms": round(ms_afirmaciones, 1) if ms_afirmaciones else None,
        "afirmaciones_tokens": hasta_prosa,
        "afirmaciones_tokens_por_s": ritmo(hasta_prosa, ms_afirmaciones),
        "prosa_ms": round(ms_prosa, 1) if ms_prosa else None,
        "prosa_tokens": tokens_prosa,
        "prosa_tokens_por_s": ritmo(tokens_prosa, ms_prosa),
        "tokens_totales": total_tokens,
        # EL 56 % MAS DE TOKENS DE LAS CORTADAS, PARTIDO POR CAUSA. Sin esto no se puede elegir
        # palanca: si escriben MAS afirmaciones, el arreglo esta en el prompt del 4.1 -cuantas hacen
        # falta de verdad- y acortar la cita no arreglaria nada; si las escriben mas LARGAS, la
        # palanca es la cita. Son dos numeros y deciden cosas distintas.
        **_contar_en_crudo(estado["crudo"]),
    }


def _estimar_uso(estado: dict) -> None:
    """Cuando se CORTA el flujo, el trozo con `usage` no llega nunca y el uso se queda en cero.

    **Un cero ahi no es "no costo": es "no me entere", y son cosas distintas.** El proveedor generó
    esos tokens y los factura igual; dejarlos en cero metería un hueco silencioso en la contabilidad
    del 2.6 y de la fase 6, justo en las consultas que peor van —o sea sesgando el coste medio hacia
    abajo—. Medido el 13 de agosto: con el plazo puesto, **6 de 20 consultas** acaban aquí, así que
    el hueco sería del 30 % y no una rareza.

    Se estima por longitud del JSON recibido y **se marca como estimado**, que es la diferencia entre
    un número aproximado y un número inventado.
    """
    if estado["uso"].tokens_salida:
        return
    estado["uso"] = Uso(tokens_entrada=estado["uso"].tokens_entrada,
                        tokens_salida=int(len(estado["crudo"]) / CARACTERES_POR_TOKEN))
    estado["uso_estimado"] = True


class PlazoAgotado(RuntimeError):
    """Se agotó el presupuesto de la consulta con la respuesta a medias. No se reintenta: se corta
    y se dice, porque volver a pedir solo puede llegar más tarde todavía."""

    def __init__(self, ms: float, presupuesto_ms: int):
        super().__init__(f"la respuesta no llego en {presupuesto_ms} ms (van {ms:.0f})")
        self.ms = ms
        self.presupuesto_ms = presupuesto_ms

SEPARADOR = "\n\n---\n\n"


def _contexto(candidatos: list) -> str:
    """Los fragmentos, numerados por su id REAL de base, que es el que la afirmación tiene que citar.

    El `fragmento_id` que se le enseña al modelo es el de la fila de `fragmentos`, no un índice de
    la lista: así lo que el modelo escriba en el contrato apunta a algo que existe y que la fase 4
    va a poder abrir para verificar. Un índice local exigiría traducirlo después, y esa traducción
    es justo donde se pierde la trazabilidad.
    """
    return SEPARADOR.join(
        f"[fragmento_id=F{c.fragmento_id}] ({c.unidad or 'sin unidad'})\n{c.texto}"
        for c in candidatos)


class Consulta(BaseModel):
    texto: str = Field(min_length=1)
    asignatura_id: int | None = None
    #: LA TITULACIÓN, que hasta hoy no viajaba porque nada la necesitaba: con la cascada del
    #: encargo de producto sí, porque *"el resto de asignaturas que cursa"* solo se puede contestar
    #: sabiendo por cuál de las tres titulaciones se pregunta. Una asignatura transversal vive en
    #: varias, así que deducirla del `asignatura_id` daría la titulación EQUIVOCADA justo en las
    #: transversales — y las transversales son las que más se comparten. Va explícita: la puente ya
    #: la conoce y el selector ya la tiene elegida.
    titulacion: str | None = None
    #: EL MODO YA NO LO ELIGE QUIEN PREGUNTA POR DEFECTO: `None` significa **que lo decida el
    #: sistema**, y lo decide el clasificador del 5.1 (`app/core/modo.py`), que llevaba desde el
    #: 14/08 construido, congelado y medido a ciegas (44/45 contra la rúbrica) **sin que nadie lo
    #: llamara**. Un valor explícito sigue mandando, y ese es el camino del "cambiar en un clic":
    #: el alumno ve qué modo se ha elegido y, si no es el que quería, pide otro.
    #:
    #: **EL DEFECTO ERA `"responder"` Y ESO NO ERA NEUTRAL**: significaba que un turno que traía un
    #: intento ("me sale 64 y no sé si está bien") se contestaba con el prompt de responder, o sea
    #: sin la derivación desde el temario que `corregir` obliga a construir. No fallaba nada; salía
    #: otra cosa.
    modo: str | None = None
    usuario_id: str | None = None
    #: EL ENGANCHE DE LA ABLACIÓN, reservado en el 2.4 y SIN EFECTO hoy porque no hay capa de
    #: verificación que apagar (fase 4). Está ahora, y no cuando haga falta, porque el guion de la
    #: demo pide correr los mismos casos con la verificación apagada: si la interfaz no tuviera por
    #: dónde, alguien lo injertaría la noche antes encima de lo que hubiera. Se registra en la traza
    #: para que de cada consulta conste qué se pidió, aunque hoy no cambie nada.
    verificacion: bool = True


def resolver_modo(peticion: Consulta) -> dict:
    """QUIÉN ELIGE EL MODO, Y LA FIRMA DE QUIEN LO ELIGIÓ.

    **`consultas.modo` pasa a tener DOS productores** —el clasificador del 5.1 y quien pregunta— y
    ese es exactamente el caso de la regla del veredicto sin firma: en cuanto un segundo productor
    puede escribir el mismo valor, ese valor deja de significar *"esto pasó"* y pasa a significar
    *"alguien concluyó esto"*. Una consulta futura que agrupe por `modo` mezclaría los dos
    instrumentos sin saberlo.

    La firma va, **hoy y sin migración**, en `respuestas.etapas.modo` —que es JSON, ya se persiste y
    ya lo sirve `/trazas/{id}`—, y se declara en ESTADO. Es el mismo trato que `cache_hit`: no se
    gasta una migración solo para esto, pero **el campo existe desde el primer día en que hay dos
    productores**, no desde el día en que alguien nota la mezcla.
    """
    if peticion.modo is not None:
        return {"modo": peticion.modo, "elegido_por": "peticion",
                "clausula": None, "rasgos": None, "examen_no_construido": False,
                "motivo": "lo pidio quien pregunta: el clasificador no se consulta"}
    d = clasificar_modo(peticion.texto)
    return {"modo": d["modo"], "elegido_por": "clasificador_5.1",
            "clausula": d["clausula"], "rasgos": d["rasgos"],
            "examen_no_construido": d["examen_no_construido"], "motivo": d["motivo"]}


#: Lo que se le enseña al alumno de cada modo, en su idioma y no en el nuestro. `modo.py` devuelve
#: la cláusula de la rúbrica (`R1 + D1`), que es la firma correcta para la traza y jerga en pantalla.
COMO_SE_DICE_EL_MODO = {
    "responder": ("Te lo explico", "he entendido que preguntas por un concepto"),
    "acompanar": ("Te guío sin dártelo", "he entendido que quieres resolverlo tú"),
    "corregir": ("Reviso lo que traes", "he entendido que traes un intento o un resultado"),
}


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


def _mensajes(texto: str, contexto: str = "", confianza: str = "baja",
              modo: str = "responder") -> list:
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
    return [{"role": "system", "content": prompt_sistema(modo, bool(contexto), confianza)},
            {"role": "user", "content": usuario}]


def _generacion(cliente: ClienteInferencia, texto: str, t0: float,
                contexto: str = "", confianza: str = "baja",
                textos_en_contexto: dict | None = None, modo: str = "responder", nli=None):
    """Una pasada contra el proveedor. Va emitiendo eventos y DEVUELVE el resultado de la pasada.

    La prosa se emite siempre, también en el reintento, y no hay contradicción: solo se llega al
    reintento cuando la pasada anterior no escribió nada en pantalla. Si escribió, el bucle de
    arriba no vuelve a llamar.
    """
    estado = {"crudo": "", "ttft_prosa_ms": None, "llamada": Llamada(), "uso": Uso(),
              "fin": None, "error": None, "emitido": False, "marcas": [],
              "ritmo_caido": None, "plazo_agotado": None, "vigilante": None, "portero": None,
              "uso_estimado": False, "tokens_hasta_prosa": None}
    prosa = ProsaEnCurso()
    futuros_nli = {}
    vigilante = VigilanteDeRitmo()
    estado["vigilante"] = vigilante
    yield _marca(estado, "peticion_enviada", t0, "consultando al modelo pequeño")
    try:
        for trozo in cliente.stream(_mensajes(texto, contexto, confianza, modo),
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
            # EL VIGILANTE DE RITMO. Las dos consultas de 60 s del 13 de agosto ARRANCARON BIEN y se
            # hundieron despues, asi que lo que hay que mirar no es el arranque sino el ritmo, y el
            # ritmo solo se puede mirar mientras llega. Levanta RitmoCaido, que es transitorio.
            vigilante.anota()
            vigilante.comprobar()
            # EL PRESUPUESTO COMO PLAZO DE VERDAD, no como numero en la configuracion. Un tope que
            # nadie hace cumplir es una aspiracion; aqui se corta y se anuncia.
            if (time.perf_counter() - t0) * 1000 > PRESUPUESTO_MS:
                raise PlazoAgotado(round((time.perf_counter() - t0) * 1000, 1), PRESUPUESTO_MS)
            nueva = prosa.alimentar(trozo.texto)
            if not nueva:
                continue
            if estado["ttft_prosa_ms"] is None:
                yield _marca(estado, "primera_prosa", t0, "redactando la respuesta")
                estado["ttft_prosa_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                # EL DESGLOSE DE LA ESPERA HASTA LA PROSA, que es lo que decide si el 30 % de cortes
                # se arregla en el contexto, en el prompt o no se arregla. Sin este numero, "son las
                # afirmaciones" es una conjetura plausible: aqui queda medido cuantos tokens ocupan.
                estado["tokens_hasta_prosa"] = vigilante.total
                # VERIFICAR MIENTRAS EL MODELO SIGUE ESCRIBIENDO. En este instante el array de
                # `afirmaciones` ya esta CERRADO -va antes que la prosa en el contrato-, y la prosa
                # tardara ~823 ms mas en terminar. La comparacion literal es instantanea, asi que
                # los veredictos salen a pantalla DURANTE la redaccion: el alumno ve el sistema
                # comprobandose a si mismo en vez de un rotulo encendido.
                #
                # Es casi todo lo que buscaba partir la generacion en dos llamadas (salida (c) del
                # 3.4), sin partir nada y sin pagar un segundo prefill.
                for evento in _veredictos_en_curso(estado, textos_en_contexto or {}, texto):
                    yield evento
                # Y EL NLI DEL 4.3, ENCHUFADO AQUI Y EN UN HILO (encargo 4.4). El literal y el
                # calculo son comparaciones y salen ya resueltos; la parafrasis necesita ~60 ms de
                # mDeBERTa, asi que se LANZA aqui y se cosecha segun termine, sin bloquear el bucle
                # que lee del proveedor. Solapa de verdad con la prosa en vez de sumarse a ella.
                futuros_nli, ya_resueltos = _lanzar_nli(estado, textos_en_contexto or {}, nli)
                for evento in ya_resueltos:
                    yield evento
                # EL PORTERO DE FRASES (4.5). Se puede construir justo aqui y no antes: las
                # afirmaciones ya estan cerradas -van antes que la prosa en el contrato- asi que la
                # cobertura se comprueba FRASE A FRASE segun se escriben, en vez de al final. Cuesta
                # una frase de retraso; la alternativa era retirar texto ya leido.
                estado["portero"] = PorteroDeFrases(extraer(estado["crudo"]) or [])
                yield _evento("ttft", {
                    "ttft_prosa_ms": estado["ttft_prosa_ms"],
                    "ttft_proveedor_ms": round(estado["llamada"].ttft_proveedor_ms or 0, 1),
                    "que_es": "prosa_ms es el primer caracter que ve el alumno; proveedor_ms es el "
                              "primer token del JSON, que es '{'",
                })
            # Los veredictos del NLI que ya esten listos salen AQUI, entre token y token, que es
            # justo lo que hace que el alumno vea el sistema comprobandose mientras escribe.
            for evento in _cosechar_nli(estado, futuros_nli):
                yield evento
            portero = estado.get("portero")
            if portero is None:
                if nueva:
                    estado["emitido"] = True
                    yield _evento("token", {"t": nueva})
                continue
            # EL PORTERO MARCA Y NO PODA (14/08): cada frase sale con su veredicto pegado, para que
            # la interfaz pueda pintarla distinta. Antes se emitia solo lo que sobrevivia y la
            # respuesta llegaba con agujeros; marcar es etiquetar, que es la promesa del proyecto,
            # y podar ademas ocultaba que el modelo lo habia dicho.
            for tramo in portero.alimentar(nueva):
                estado["emitido"] = True
                yield _evento("token", {"t": tramo["texto"], "respaldada": tramo["respaldada"],
                                        "solape": tramo["solape"]})
    except RitmoCaido as e:
        # No es un fallo del proveedor: responde, solo que a un ritmo que no llega. Se corta aqui y
        # el que decide si se reintenta es `_flujo`, que es quien sabe si ya habia prosa en pantalla.
        estado["ritmo_caido"] = {"tokens_por_segundo": round(e.ritmo, 1), "minimo": e.minimo}
        estado["error"] = f"RitmoCaido: {e}"
        _estimar_uso(estado)
    except PlazoAgotado as e:
        # LOS DOS PRESUPUESTOS EN LA TRAZA, y `paso_del_objetivo` aparte: una respuesta que tarda
        # 6,2 s se ENTREGA -no se corta- pero incumple el objetivo de producto, y esas dos cosas se
        # cuentan por separado o el 4.6 leera "0 % de cortes" como "cumplimos los 5 s".
        estado["plazo_agotado"] = {"ms": e.ms, "presupuesto_ms": e.presupuesto_ms,
                                   "objetivo_ms": OBJETIVO_MS}
        estado["error"] = f"PlazoAgotado: {e}"
        _estimar_uso(estado)
    except (ErrorTransitorio, ErrorDefinitivo) as e:
        estado["error"] = f"{type(e).__name__}: {e}"
    # LA COSECHA FINAL DEL NLI, con el presupuesto de verificacion de la seccion 8 por delante. Lo
    # que no llegue NO se espera mas: se queda `sin_verificar` con su motivo, porque un veredicto que
    # llega despues de la respuesta no sirve para nada.
    if futuros_nli:
        for evento in _cosechar_nli(estado, futuros_nli,
                                    esperar_hasta=time.perf_counter() + PRESUPUESTO_NLI_S):
            yield evento
        if futuros_nli:
            estado["nli_sin_tiempo"] = len(futuros_nli)

    # LA ULTIMA FRASE, que casi nunca trae punto final. Se juzga igual que las demas: una frase sin
    # cerrar no es una excepcion a la regla de cobertura, solo es una que el modelo no termino.
    if estado.get("portero"):
        for tramo in estado["portero"].cerrar():
            estado["emitido"] = True
            yield _evento("token", {"t": tramo["texto"], "respaldada": tramo["respaldada"],
                                    "solape": tramo["solape"]})
        if estado["portero"].huerfanas:
            # SE DICE, y ademas se dice CUANTAS. Lo que cambia desde que el portero marca: ya no se
            # avisa de un agujero -no lo hay- sino de que parte de lo que el alumno esta leyendo va
            # SEÑALADO. El aviso sigue haciendo falta: la marca esta junto a cada frase, y el
            # recuento contesta a "¿cuanto de esta respuesta no estaba declarado?".
            yield _evento("cobertura", {
                "frases_marcadas": len(estado["portero"].huerfanas),
                "frases_emitidas": estado["portero"].emitidas,
                "que_significa": "hay frases de la redaccion que NINGUNA afirmacion declarada "
                                 "respalda: se enseñan igual, marcadas, porque ocultarlas seria "
                                 "esconder que el modelo las dijo",
                "ejemplos": estado["portero"].huerfanas[:3],
            })
    return estado


#: El orden de los tres niveles de `confianza_recuperacion`, para poder COMPARAR dos recuperaciones.
#: No es un umbral nuevo: es el orden de los que ya existen, y por eso la cascada no introduce
#: ningún número que calibrar.
NIVELES_DE_CONFIANZA = {"baja": 0, "media": 1, "alta": 2}


def _elegir_asignatura(peticion: Consulta, catalogo, url: str, vector, marcas: list, t0: float):
    """LA ASIGNATURA DEJA DE SER OBLIGATORIA, y quien cubre el hueco es LA CASCADA, no un barrido.

    ## Por qué, y qué había antes

    Antes, `asignatura_id is None` devolvía **cero fragmentos** y el sistema respondía de memoria —lo
    que este proyecto dice no ser—, así que la interfaz tenía que obligar a elegir una de trece antes
    de dejar escribir. Un alumno de segundo no sabe si *"¿por qué se me pierde la sesión al
    recargar?"* es de DWES o de DAW: **elegir el módulo es parte de lo que viene a preguntar**.

    ## LA PRIMERA VERSIÓN DE ESTO SE ESCRIBIÓ COMO BARRIDO Y SE TIRÓ, y el motivo se deja escrito

    Hacía una búsqueda ancha sobre las trece asignaturas de la titulación y se quedaba con la del
    primer candidato. Medida, costaba 21,3 ms y abría **13 particiones de 35** — y el propietario la
    paró con el argumento correcto: **los márgenes de confianza del 4.6 (corrida 33) se calibraron
    DENTRO de una asignatura**, así que meter un mecanismo nuevo delante para esquivar eso es
    resolver con código un problema que ya tenía dueño. Y los datos le dieron la razón: en las veinte
    preguntas ordinarias, el argmax mandó `ord-06` (*conectar a MySQL desde PHP*) a **Programación**,
    que contestó —correctamente— *"eso no está en tu temario"*, con DWES03 titulado literalmente
    *"Acceso a bases de datos desde PHP"*. El barrido no falló: **acertó su pregunta y era la
    pregunta equivocada.**

    ## Lo que hace ahora: NADA nuevo

    Se empieza por **el módulo con más material del ciclo** —un dato que el catálogo ya devuelve, sin
    una sola consulta más y sin un solo umbral— y **la cascada hace el resto**: si ahí la confianza
    sale baja, `_cascada` busca en las demás de la titulación, adopta solo si sube de nivel, y lo
    dice en pantalla. Ese mecanismo existe, está medido y ya resuelve exactamente este caso.

    O sea que "cualquiera de mi ciclo" **no es buscar en las trece**: es *empieza por donde hay más y
    sigue por donde haga falta*, que es lo acordado.
    """
    if not (catalogo and peticion.titulacion):
        return None
    try:
        asignaturas = catalogo.asignaturas(peticion.titulacion)
    except Exception:                        # noqa: BLE001 - titulacion inventada o base caida
        return None
    # Los modulos SIN material se descartan aqui: empezar por uno vacio garantiza confianza baja y
    # una cascada que se podia haber ahorrado. `fragmentos` lo trae el catalogo desde el 2.1.
    con_material = [a for a in asignaturas if a.get("fragmentos")]
    if not con_material:
        return None
    elegida = max(con_material, key=lambda a: a["fragmentos"])
    marcas.append({
        "nombre": "asignatura_elegida",
        "detalle": f"no habias elegido modulo: se empieza por {elegida['nombre']}, y si ahi no hay "
                   f"material se busca en el resto de tu ciclo",
        "ms": round((time.perf_counter() - t0) * 1000, 1),
        "asignatura_id": elegida["id"], "asignatura": elegida["nombre"],
        "entre": len(con_material),
        "como": "el modulo con mas material del ciclo, sin ninguna consulta extra; quien corrige "
                "una eleccion mala es la cascada, que ya existe y ya esta medida",
    })
    return elegida["id"]


def _cascada(peticion: Consulta, catalogo, url: str, vector, confianza: str, candidatos: list,
             marcas: list, t0: float, asignatura_id: int | None = None):
    """LA SEGUNDA VUELTA: si en la asignatura elegida no hay material, se busca en el RESTO DE LA
    TITULACIÓN antes de rendirse a `conocimiento`.

    ## Por qué existe, con la corrección del propietario dentro

    La primera versión de esto era **orientación**: *"esto no está aquí, está en Bases de Datos"*, y
    ahí se quedaba. **La orientación sola es un muro con buenos modales**: obliga al alumno a cambiar
    de asignatura en el selector y a repreguntar, o sea a hacer él el trabajo que el sistema acaba de
    demostrar que sabe hacer. Se responde, y se dice de dónde sale.

    ## Cuándo dispara, y por qué NO hay un umbral nuevo aquí

    Dispara cuando la primera vuelta da confianza **baja**, que es el nivel que ya significa *"los
    seis primeros valen casi lo mismo y ninguno encaja"* — el mecanismo calibrado en el 4.6 (corrida
    33), reutilizado tal cual. **Lo que se compara son NIVELES, no puntuaciones**, así que esta
    cascada no añade ni un número que calibrar: si la segunda vuelta no sube de nivel, no se adopta.

    **Y el empate se resuelve a favor de la asignatura elegida**, que no es una preferencia estética:
    el alumno preguntó ahí, así que traerle material de al lado hace falta justificarlo, no
    empatarlo.

    ## Los dos límites, declarados

    1. **Los márgenes de `confianza_de` se calibraron DENTRO de una asignatura y sobre DWES**
       (limitación del §6 del 4.6). Usarlos para comparar dos recuperaciones de asignaturas
       distintas es reutilizar el mecanismo en una pregunta nueva: el nivel sigue significando lo
       mismo —cuánto destaca la cabeza—, pero **que el corte esté igual de bien puesto aquí no está
       medido**, y se declara en vez de suponerse.
    2. **Sin vector no hay confianza que comparar** (la confianza sale de la lista vectorial). En ese
       caso la cascada solo dispara si la primera vuelta trajo **cero** candidatos, que es el único
       "no hay material" que se puede afirmar sin medir nada.
    """
    if not (catalogo and peticion.titulacion):
        return None
    otras = [a["id"] for a in catalogo.asignaturas(peticion.titulacion)
             if a["id"] != (asignatura_id if asignatura_id is not None
                            else peticion.asignatura_id)]
    if not otras:
        return None
    t_cascada = time.perf_counter()
    de_cascada = []
    candidatos_2 = recuperar(url, otras, peticion.texto, vector=vector, k=POOL,
                             marcas=de_cascada, pesos=PESOS_FUSION)
    if not candidatos_2:
        return None
    if vector is None:
        # Sin vector no se puede comparar: solo se adopta si la primera vuelta no trajo NADA.
        if candidatos:
            return None
        confianza_2, detalle_2 = "baja", {"motivo": "sin vector: la confianza no se puede medir"}
    else:
        confianza_2, detalle_2 = confianza_de(
            buscar_vectorial(url, otras, vector, k=FRAGMENTOS_EN_CONTEXTO))
        if NIVELES_DE_CONFIANZA[confianza_2] <= NIVELES_DE_CONFIANZA[confianza]:
            return None
    detalle_2 = {**detalle_2, "de_otra_asignatura": True,
                 "asignaturas_buscadas": len(otras),
                 "limite": "los margenes de confianza se calibraron DENTRO de una asignatura y "
                           "sobre DWES (4.6 §6): el nivel se reutiliza, su corte aqui NO esta "
                           "medido"}
    marcas.append({
        "nombre": "segunda_recuperacion",
        "detalle": (f"no habia material en la asignatura elegida: se ha buscado en las {len(otras)} "
                    f"restantes de {peticion.titulacion} y la respuesta sale de ahi"),
        "ms": round((time.perf_counter() - t0) * 1000, 1),
        "coste_ms": round((time.perf_counter() - t_cascada) * 1000, 1),
        "confianza_antes": confianza, "confianza_despues": confianza_2,
    })
    return candidatos_2, confianza_2, detalle_2


def _recuperar(peticion: Consulta, embebedor, url: str, t0: float, reordenador=None,
               catalogo=None):
    """La recuperación del 3.3, emitiendo sus etapas REALES según ocurren.

    Aquí las etapas por fin cubren la espera con trabajo que alimenta la respuesta, que era el
    diseño del 2.4: hasta ahora la pantalla esperaba a que el modelo escribiera, y ahora enseña que
    se está buscando en el temario y cuántos fragmentos han salido.
    """
    marcas, contexto, confianza, detalle = [], "", "baja", {"motivo": "sin recuperacion"}

    # SIN EMBEBEDOR SE RECUPERA IGUAL, POR LEXICA Y GLOSARIO, y esto es un arreglo del 4.4 que
    # salio de revisar /salud: hasta hoy, `embebedor is None` devolvia CERO fragmentos, o sea que
    # el sistema respondia de memoria y era exactamente lo que dice no ser. Que la caida del
    # embebedor se lleve por delante TAMBIEN la busqueda por palabras no es una consecuencia
    # tecnica: es que nadie escribio el respaldo, porque `recuperar()` ya acepta `vector=None`
    # desde el 3.3 y hace las otras dos listas.
    #
    # Y la diferencia importa para diagnosticar: con respaldo, quedarse sin torch es DEGRADACION
    # ANUNCIADA -se recupera peor, y el 3.1 midio cuanto: 58 % de la lexica sola- y no una caida.
    # Sin respaldo era una caida disfrazada de respuesta.
    vector = None
    if embebedor is not None:
        vector = embebedor.embeber(peticion.texto)
        marcas.append({"nombre": "consulta_embebida", "detalle": "pregunta convertida a vector",
                       "ms": round((time.perf_counter() - t0) * 1000, 1)})
    else:
        marcas.append({
            "nombre": "sin_embebedor",
            "detalle": "no hay busqueda por significado: se busca solo por palabras y glosario",
            "ms": round((time.perf_counter() - t0) * 1000, 1)})
    # (5) EL CICLO ES LO UNICO OBLIGATORIO. Si no viene asignatura, la elige la pregunta; si no se
    # puede elegir -sin catalogo, sin titulacion o sin un solo candidato en las trece-, se responde
    # sin fragmentos Y SE DICE, que es lo que hacia antes en silencio para TODA consulta sin
    # asignatura.
    asignatura_id = peticion.asignatura_id
    if asignatura_id is None:
        asignatura_id = _elegir_asignatura(peticion, catalogo, url, vector, marcas, t0)
    if asignatura_id is None:
        marcas.append({
            "nombre": "sin_asignatura",
            "detalle": "no habia asignatura elegida y no se ha podido deducir de la pregunta: se "
                       "responde sin temario delante",
            "ms": round((time.perf_counter() - t0) * 1000, 1)})
        return marcas, contexto, confianza, detalle, []
    de_recuperacion = []
    # `pesos=PESOS_FUSION`: la fusion 10:1 decidida en el 3.3 y cableada el 14/08 -hasta entonces
    # produccion fusionaba a 1:1 sin que nadie lo hubiera decidido-. El numero, en la constante.
    candidatos = recuperar(url, asignatura_id, peticion.texto, vector=vector, k=POOL,
                           marcas=de_recuperacion, pesos=PESOS_FUSION)
    base = marcas[-1]["ms"]
    for marca in de_recuperacion:
        marcas.append({**marca, "ms": round(base + marca["ms"], 1)})
    # La confianza sale de la lista VECTORIAL, no de la fusion: la puntuacion vectorial es una
    # distancia con significado y la de RRF es una suma de inversos de rangos, que no lo tiene.
    # Sin vector no hay lista vectorial, y entonces la confianza es `baja` POR NO PODER MEDIRLA,
    # que es distinto de medirla y que salga baja; se dice en el detalle para que el 4.6 no cuente
    # las dos juntas.
    confianza, detalle = ("baja", {"motivo": "sin vector: la confianza no se puede medir"}) \
        if vector is None else \
        confianza_de(buscar_vectorial(url, asignatura_id, vector,
                                      k=FRAGMENTOS_EN_CONTEXTO))
    # LA CASCADA: si aqui no hay material, se mira el RESTO DE LA TITULACION antes de rendirse.
    if confianza == "baja":
        segunda = _cascada(peticion, catalogo, url, vector, confianza, candidatos, marcas, t0,
                           asignatura_id=asignatura_id)
        if segunda is not None:
            candidatos, confianza, detalle = segunda
    # EL REORDENADO ES OPCIONAL Y DESDE EL 14/08/2026 ARRANCA DESCARTADO (ADR 0019): medido sobre
    # el conjunto corregido, reordenar EMPEORA la cabeza en `lectura` (56,0 % contra 58,7 %), asi
    # que el orden de la fusion 10:1 ES la configuracion por defecto, no un respaldo. Si esta
    # reencendido (REORDENADOR_ACTIVO=1, ablacion) rigen el ADR 0015 y la degradacion anunciada de
    # siempre: GPU o nada, y si no contesta se sirve el orden de la fusion Y SE DICE (8.2).
    motivo_reo = None
    if reordenador is not None:
        antes = time.perf_counter()
        # `reordenar_o_rendirse` y no `reordenar`: una operacion de GPU no se puede CANCELAR, pero
        # si se puede dejar de ESPERAR. Si no contesta en su plazo, devuelve None y se degrada por
        # la misma via que si no hubiera GPU. El hilo queda colgado hasta que CUDA vuelva -residuo
        # declarado en el modulo-, pero la peticion no depende de el.
        elegidos, motivo_reo = reordenador.reordenar_o_rendirse(
            peticion.texto, candidatos[:POOL], top=FRAGMENTOS_EN_CONTEXTO)
    if reordenador is not None and elegidos is not None:
        marcas.append({
            "nombre": "reordenado",
            "detalle": f"{len(candidatos[:POOL])} candidatos releidos uno a uno con la pregunta",
            "ms": round((time.perf_counter() - t0) * 1000, 1),
            "reordenado_ms": round((time.perf_counter() - antes) * 1000, 1),
        })
    elif reordenador is not None:
        elegidos = candidatos[:FRAGMENTOS_EN_CONTEXTO]
        # TRES MOTIVOS, no dos: no hay hardware / el hardware no responde / hay COLA. El alumno ve
        # lo mismo, la traza no: confundir saturacion con averia es diagnosticar mal, y con el
        # circuit breaker del 8.2 delante seria abrir el circuito por una punta de trafico.
        marcas.append({
            "nombre": "sin_reordenar",
            "detalle": ("hay varias consultas por delante: se responde con el orden de la busqueda"
                        if motivo_reo == "reordenador_saturado" else
                        "el reordenador no contesto a tiempo: se responde con el orden de la busqueda"),
            "ms": round((time.perf_counter() - t0) * 1000, 1),
            "motivo": motivo_reo or "gpu_no_contesta",
        })
    else:
        # SIN REORDENADOR CONFIGURADO NO HAY DEGRADACION QUE ANUNCIAR. Esta rama emitia una etapa
        # `sin_reordenar` con detalle "sin GPU...", y desde el descarte del ADR 0019 eso era falso
        # DOS veces en cada consulta: hay GPU (es una decision, no una averia) y no hay degradacion
        # (la fusion sin reordenar mide MEJOR: 58,7 % contra 56,0 % en lectura). El orden de la
        # fusion es la configuracion por defecto; la etapa queda para las ramas de arriba, donde el
        # reordenador esta ENCENDIDO y falla o se satura, que si son degradaciones y se anuncian.
        # Cazado por la pasada adversarial del cierre de fase.
        elegidos = candidatos[:FRAGMENTOS_EN_CONTEXTO]
    # LA ETAPA QUE LLENA LA ESPERA EN VEZ DE ANUNCIARLA. Las cuatro etapas de recuperación ocurren
    # en los primeros 80 ms y después la pantalla espera al modelo unos dos segundos: medido en el
    # 3.3, cubrían el 3,5 % del tiempo. Enseñar aquí los SEIS FRAGMENTOS con su documento y su
    # unidad no es relleno -es la evidencia de lo que el sistema acaba de recuperar- y leer seis
    # títulos ocupa justo esos dos segundos. Y hace literalmente lo que el 2.4 escribió como
    # objetivo: **el alumno ve las citas antes que el texto**.
    # LA PROCEDENCIA VIAJA CON CADA FRAGMENTO, y solo cuando NO es la asignatura elegida. Ponerla
    # siempre seria ruido -"de Programacion" en una consulta de Programacion no informa de nada- y
    # no ponerla nunca es el fallo que este encargo arregla: el alumno tiene que poder leer "esto es
    # de Bases de datos, que tambien cursas" sin abrir la traza. La mitad del cambio es responder;
    # la otra mitad es decir de donde sale, y sin esta linea solo estaria hecha la primera.
    nombres = {}
    if catalogo and peticion.titulacion:
        nombres = {a["id"]: a["nombre"] for a in catalogo.asignaturas(peticion.titulacion)}
    marcas.append({
        "nombre": "fragmentos_recuperados",
        "detalle": f"{len(elegidos)} fragmentos del temario, por orden de relevancia",
        "ms": round((time.perf_counter() - t0) * 1000, 1),
        "fragmentos": [{"id": c.fragmento_id, "documento": c.documento.split("/")[-1],
                        "unidad": c.unidad or "sin unidad",
                        "origen": c.origen,
                        **({"asignatura": nombres.get(c.asignatura_id, "otra asignatura")}
                           if c.asignatura_id != asignatura_id else {})}
                       for c in elegidos],
        "confianza": confianza,
    })
    return marcas, _contexto(elegidos), confianza, detalle, elegidos


def _flujo(cliente: ClienteInferencia, peticion: Consulta, traza, consulta_id: int,
           embebedor=None, url: str = "", reordenador=None, nli=None, catalogo=None,
           eleccion: dict | None = None):
    t0 = time.perf_counter()
    estado, validada, motivo = None, None, None
    marcas = []
    # EL MODO SE RESUELVE UNA VEZ Y VIAJA RESUELTO. Llega decidido desde `consulta()` porque la
    # traza se abre ANTES que el flujo y tiene que abrirse con el modo de verdad: recalcularlo aqui
    # daria dos oportunidades de que `consultas.modo` y el prompt que se usa dejen de coincidir.
    # El defecto es para las llamadas directas a `_flujo` de los tests, no para produccion.
    if eleccion is None:
        eleccion = resolver_modo(peticion)
    titulo, porque = COMO_SE_DICE_EL_MODO.get(
        eleccion["modo"], COMO_SE_DICE_EL_MODO["responder"])
    # EL PRIMER EVENTO DEL FLUJO, y va antes de la recuperacion porque no depende de nada: es texto
    # sobre el turno que el alumno acaba de escribir. Que salga el primero es la mitad del encargo
    # -"el modo elegido se ENSEÑA"-, porque un modo que aparece al final ya no se puede cambiar sin
    # haber leido la respuesta equivocada entera.
    yield _evento("modo", {
        "modo": eleccion["modo"], "titulo": titulo, "porque": porque,
        "elegido_por": eleccion["elegido_por"], "clausula": eleccion["clausula"],
        "motivo": eleccion["motivo"],
        # D6: `examinar` esta DISEÑADO Y NO CONSTRUIDO. Sin esta bandera, "ponme un ejercicio" sale
        # como una consulta normal y el alumno no se entera de que ha pedido algo que no hay.
        "examen_no_construido": eleccion["examen_no_construido"],
        "otros": [{"modo": m, "titulo": COMO_SE_DICE_EL_MODO[m][0]}
                  for m in COMO_SE_DICE_EL_MODO if m != eleccion["modo"]],
    })
    # LA RECUPERACION QUE FALLA DEGRADA, NO REVIENTA. Antes del respaldo lexico del 4.4, sin
    # embebedor no se tocaba la base y esta ruta no podia fallar; ahora si la toca, asi que una base
    # caida se llevaria la peticion entera con una excepcion cruda a mitad del SSE. Lo honesto es lo
    # mismo que hace el reordenador cuando no contesta: seguir sin ella Y DECIRLO, con el motivo en
    # la traza. Que la base sea ESENCIAL en /salud y aun asi se degrade aqui no es contradiccion:
    # /salud dice que el sistema no puede responder BIEN, y esto evita que ademas responda con un
    # 500 en mitad de una frase.
    try:
        marcas_recuperacion, contexto, confianza, detalle_confianza, elegidos = _recuperar(
            peticion, embebedor, url, t0, reordenador, catalogo)
    except Exception as e:  # noqa: BLE001 - psycopg, red, o lo que la base decida hoy
        marcas_recuperacion, contexto, confianza, elegidos = [], "", "baja", []
        detalle_confianza = {"motivo": f"la recuperacion fallo: {type(e).__name__}: {e}"[:300]}
        marcas_recuperacion.append({
            "nombre": "sin_recuperacion",
            "detalle": "no se pudo consultar el temario: se responde sin fragmentos y se dice",
            "ms": round((time.perf_counter() - t0) * 1000, 1)})
    for marca in marcas_recuperacion:
        # A la traza va el nombre y el milisegundo; los fragmentos ya viajan en etapas.recuperacion,
        # asi que repetirlos aqui seria guardar dos veces lo mismo.
        marcas.append({"nombre": marca["nombre"], "ms": marca["ms"]})
        yield _evento("etapa", marca)
    for intento in (1, 2):
        estado = yield from _generacion(cliente, peticion.texto, t0, contexto, confianza,
                                        {c.fragmento_id: c.texto for c in elegidos},
                                        eleccion["modo"], nli)
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
        # EL PLAZO NO SE REINTENTA. Si ya se agotaron los 5 s, volver a pedir solo puede empeorar:
        # se corta y se degrada anunciandolo, que es el punto entero de tener un plazo.
        if estado["plazo_agotado"]:
            break
        # El reintento unico de la seccion 7, con su limite honesto: si ya salio prosa, no se
        # repite la llamada, porque repetirla le repetiria el texto al alumno.
        #
        # **CON UNA EXCEPCION, Y ES LA DEL RITMO CAIDO.** La regla de "emitido no se reintenta"
        # protege al alumno de ver el texto dos veces; pero cuando el ritmo se hunde, la alternativa
        # a reintentar NO es una respuesta correcta: es un minuto de pantalla congelada y luego, con
        # suerte, la misma respuesta. Entre repetir texto avisando y congelar en silencio, gana lo
        # primero -y por eso el reintento va ANUNCIADO y lo emitido se marca como retirado, que es
        # el mecanismo que el 2.4 ya dejo construido para la abstencion sucia-.
        if intento == 2 or (estado["emitido"] and not estado["ritmo_caido"]):
            break
        if estado["ritmo_caido"]:
            marcas.append({"nombre": "reintento_por_ritmo",
                           "ms": round((time.perf_counter() - t0) * 1000, 1)})
            yield _evento("etapa", {
                "nombre": "reintento_por_ritmo", "ms": marcas[-1]["ms"],
                "detalle": f"la respuesta llegaba a "
                           f"{estado['ritmo_caido']['tokens_por_segundo']:.0f} palabras/s; se pide "
                           f"de nuevo"})
            yield _evento("reintento", {
                "motivo": "ritmo_caido",
                "tokens_por_segundo": estado["ritmo_caido"]["tokens_por_segundo"],
                "minimo": estado["ritmo_caido"]["minimo"],
                "que_significa": "el proveedor respondia demasiado despacio para llegar a tiempo; "
                                 "se corta y se vuelve a pedir en vez de dejar la pantalla parada",
                # Si ya habia prosa, la interfaz la RETIRA antes de la segunda pasada: no se borra a
                # la callada, porque borrar sin decir nada le deja pensando que lo leyo mal.
                "ya_habia_prosa_en_pantalla": estado["emitido"],
            })

    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    uso, llamada = estado["uso"], estado["llamada"]

    # UNA PANTALLA EN BLANCO ES UNA ABSTENCION, Y ESTE CAMINO SE RE-CONDICIONA, NO SE RETIRA.
    #
    # HISTORIA, porque el disparador cambio de sitio dos veces y el motivo importa:
    #
    # 1. Hasta el 14/08/2026 el portero PODABA, y si podaba TODAS las frases la respuesta salia con
    #    `abstencion: False` y prosa vacia: pantalla en blanco sin explicacion, contada como
    #    entregada. Se arreglo disparando la abstencion cuando no se emitia ni un caracter.
    # 2. Desde que el portero MARCA, ese disparador ya no puede saltar por poda -no hay poda-, y la
    #    tentacion era retirar la rama entera. **No se retira: se re-condiciona.** Sigue existiendo
    #    el caso de PROSA VACIA -el modelo cumple el contrato y no escribe redaccion, o escribe solo
    #    espacios- y sin esta rama ese caso volveria exactamente a la pantalla en blanco sin
    #    declarar que costo medio dia encontrar. **Cambia el disparador, se conserva la salida.**
    #
    # Su motivo sigue siendo PROPIO y no se mezcla con los otros dos: no es "no hay material" ni "el
    # contrato se rompio". Aqui el contrato vino perfecto y las afirmaciones existen; lo que no hay
    # es nada que leer.
    portero = estado.get("portero")
    # SE MIRA `caracteres_emitidos` Y NO `emitidas`, y esa distincion escondio el fallo medio dia:
    # una frase de menos de tres palabras de contenido pasa POR DISEÑO -marcar "Vale." seria el falso
    # positivo por construccion-, asi que un punto suelto deja el contador de frases en 1 con la
    # pantalla vacia. El contador que responde a "¿se enseño algo?" es el de caracteres visibles.
    if validada is not None and portero is not None and portero.caracteres_emitidos == 0:
        validada, motivo = None, ("sin_prosa: el contrato vino bien y las afirmaciones existen, "
                                  "pero la redaccion no tiene ni un caracter que enseñar")
        estado["sin_prosa_respaldada"] = {"frases_marcadas": len(portero.huerfanas),
                                          "caracteres_emitidos": 0,
                                          "solape_minimo": portero.solape_minimo}

    afirmaciones = []
    if validada is not None:
        # UNA AFIRMACION NO PUEDE CITAR UN FRAGMENTO QUE NO SE LE DIO. Es comprobable sin modelo y
        # sin umbral -el servidor sabe exactamente que seis mando-, y si no se comprueba, el sistema
        # se estaria fabricando la procedencia: una `literal` que apunta a un id que no estuvo en el
        # contexto es una cita inventada con aspecto de verificable. Aqui solo se MARCA, porque la
        # decision de podar es del 4.5; marcarlo ya evita que llegue a la fase 4 disfrazado.
        en_contexto = {c.fragmento_id for c in elegidos}
        # LA REFERENCIA VUELVE A SER NUMERO AQUI, en la frontera y en un solo sitio: el modelo
        # escribe `F2936` porque un numero pelado es ingramatico para el (ver el contrato), y de
        # aqui hacia dentro todo -traza, interfaz, verificador- sigue trabajando con el id real.
        vistos = estado.get("veredictos") or {}
        afirmaciones = [{"tipo": a.tipo, "texto": a.texto,
                         "fragmento_id": numero_de_referencia(getattr(a, "fragmento_id", None)),
                         "veredicto": (vistos.get(a.id) or {}).get("veredicto") or SIN_VERIFICAR,
                         "detalle": {"cita": getattr(a, "cita", None),
                                     "apoyo": getattr(a, "apoyo", None),
                                     "expresion": getattr(a, "expresion", None),
                                     "andamiaje": getattr(a, "andamiaje", None),
                                     "id_en_contrato": a.id,
                                     "verificacion": vistos.get(a.id),
                                     "fragmento_en_contexto": (
                                         None if getattr(a, "fragmento_id", None) is None
                                         else numero_de_referencia(a.fragmento_id) in en_contexto)}}
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
                                "detalle": ("la redaccion vino vacia: no hay nada que enseñar"
                                            if estado.get("sin_prosa_respaldada")
                                            else "el contrato no llego bien formado")})
        yield _evento("abstencion", {
            "motivo": motivo,
            "que_significa": (
                f"la respuesta no llego dentro del plazo de {PRESUPUESTO_MS} ms; se corta y se dice, "
                f"en vez de dejar la pantalla congelada"
                if estado["plazo_agotado"] else
                "la respuesta venia bien formada y con sus afirmaciones, pero la redaccion no traia "
                "ni un caracter: no habia nada que enseñar y se dice, en vez de dejar una pantalla "
                "en blanco que parece un fallo"
                if estado.get("sin_prosa_respaldada") else
                "el proveedor no devolvio el contrato de la seccion 7; se abstiene en vez de "
                "ensenar algo sin forma conocida"),
            # RENOMBRADO EL 14/08 con el disparador: se llamaba `por_cobertura` cuando la causa era
            # que el portero habia podado toda la prosa. Ya no poda, asi que la causa que queda es
            # OTRA -la redaccion viene vacia- y el nombre viejo mandaria a buscar el fallo en el
            # umbral del 4.5, que no tiene nada que ver. `por_cobertura` se conserva un tiempo con
            # su valor por los consumidores viejos (scripts/medir_corregir.py, corridas guardadas).
            "por_prosa_vacia": bool(estado.get("sin_prosa_respaldada")),
            "por_cobertura": bool(estado.get("sin_prosa_respaldada")),
            "aviso_por_cobertura": ("nombre HEREDADO: hoy significa 'la redaccion vino vacia', no "
                                    "'el portero podo todo'. Usa por_prosa_vacia"),
            "por_plazo": bool(estado["plazo_agotado"]),
            # Las dos abstenciones NO se dibujan igual, y por eso viaja este campo. En falso, no ha
            # salido nada y la abstencion es limpia. En verdadero, el alumno YA tiene texto en
            # pantalla y hay que marcarlo como RETIRADO: no se borra a la callada, porque borrar sin
            # decir nada le deja pensando que lo leyo mal.
            "ya_habia_prosa_en_pantalla": estado["emitido"],
        })

    etapas = {
        "marcas": marcas,
        # LA FIRMA DEL QUE ELIGIO EL MODO, que `consultas.modo` no puede llevar sin migracion.
        "modo": eleccion,
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
            # Si el flujo se corto, el `usage` del proveedor no llego y el uso va ESTIMADO por
            # longitud. Se dice, porque un coste aproximado y uno medido no valen lo mismo.
            "uso_estimado": estado["uso_estimado"],
            "ritmo": estado["vigilante"].estado() if estado["vigilante"] else None,
            "plazo_agotado": estado["plazo_agotado"],
            "ritmo_caido": estado["ritmo_caido"],
            # EL DESGLOSE DE LA ESPERA, en tres tramos con palancas DISTINTAS:
            #   prefill    = 0 -> primer token del proveedor  (contexto de entrada + cola del
            #                proveedor). Palanca: bajar de 6 fragmentos a 4.
            #   afirmaciones = primer token -> primera prosa  (lo que el contrato manda escribir
            #                antes de la respuesta). Palanca: prompt, o el orden del contrato.
            #   prosa      = primera prosa -> fin.
            # Sin partirlo, "la culpa es de las afirmaciones" es una conjetura plausible y nada mas.
            "cobertura": estado["portero"].estado() if estado.get("portero") else None,
            "desglose": _desglose(estado, total_ms),
            "fin": estado["fin"],
            # EL CAMINO DE FALLO TAMBIEN DEJA RASTRO, y esto no es un extra de depuracion: es la
            # condicion para que los numeros de la fase 4 signifiquen algo.
            #
            # Hasta hoy, una respuesta que no validaba el contrato no metia NI UNA fila en
            # `afirmaciones` -no hay afirmaciones validadas que meter- y su `motivo` moria en el
            # evento SSE. O sea que la tabla contenia SOLO lo que salio bien. La tasa de poda, la de
            # abstencion y el reparto de veredictos que el 4.6 va a calcular encima habrian salido
            # todos sobre el subconjunto que funciono, que es el principio 11 cometido dentro de
            # nuestra propia base: una muestra elegida por el sintoma -aqui, por el EXITO-.
            #
            # Se guarda el motivo y el JSON tal como llego, acotado. Con eso, las afirmaciones que
            # el modelo INTENTO hacer son recuperables y el denominador vuelve a ser el bueno.
            "motivo_fallo": motivo if validada is None else None,
            "crudo_recibido": estado["crudo"][:LARGO_CRUDO_GUARDADO] if validada is None else None,
            "crudo_truncado": validada is None and len(estado["crudo"]) > LARGO_CRUDO_GUARDADO,
        },
        "recuperacion": {"construido": bool(elegidos), "pool": POOL,
                         "en_contexto": [c.fragmento_id for c in elegidos],
                         "confianza": confianza, "detalle_confianza": detalle_confianza},
        # QUE SE VERIFICO, CON QUE INSTRUMENTO Y CON QUE RESULTADO, que es la pregunta para la que
        # existe el 2.5. Y esto CORRIGE UN `false` PERSISTIDO: hasta el 14/08/2026 aqui iba
        # `construido: False, encargo: "fase 4"` en las 391 respuestas de la base, o sea que la
        # traza afirmaba en presente que no habia verificacion mientras el 4.2, el 4.3, el 4.4 y el
        # 4.5 corrian en cada consulta. Un `false` persistido se lee como una medida.
        "verificacion": {
            "construido": True, "encargos": ["4.2", "4.3", "4.4", "4.5"],
            "instrumentos": {"literal": INSTRUMENTO_LITERAL,
                             "parafrasis": INSTRUMENTO_NLI if nli is not None else None,
                             "calculo": INSTRUMENTO_CALCULO,
                             "cobertura": "4.5/portero_de_frases"},
            "nli_cargado": nli is not None,
            "umbral_nli": nli.umbral if nli is not None else None,
            "suelo_cobertura_nli": COBERTURA_MINIMA_NLI,
            # El interruptor SIGUE sin efecto, y se dice con esas palabras en vez de callarlo: lo
            # que hoy apaga la verificacion es NLI_ACTIVO=0 en el proceso, y la ablacion de verdad
            # -medir la misma configuracion con y sin capa- es el 7.3.
            "solicitada": peticion.verificacion,
            "solicitada_tiene_efecto": False,
            "como_se_apaga_hoy": "NLI_ACTIVO=0 en el proceso; la ablacion por peticion es el 7.3"},
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
        # LOS DOS PRESUPUESTOS, EN CADA RESPUESTA. El objetivo de producto son 5 s y el plazo
        # operativo 8; una respuesta de 6,2 s se ENTREGA y aun asi incumple el objetivo. Que las dos
        # cifras viajen juntas es lo que impide leer "0 % de cortes" como "cumplimos los 5 s".
        "objetivo_ms": OBJETIVO_MS, "presupuesto_ms": PRESUPUESTO_MS,
        "paso_del_objetivo": total_ms > OBJETIVO_MS,
        "ttft_proveedor_ms": round(llamada.ttft_proveedor_ms, 1) if llamada.ttft_proveedor_ms
        else None,
        "tokens_entrada": uso.tokens_entrada, "tokens_salida": uso.tokens_salida,
        "coste_eur": uso.coste_eur(), "version_prompt": version_prompt(eleccion["modo"]),
        "confianza_recuperacion": confianza, "detalle_confianza": detalle_confianza,
        "fragmentos_en_contexto": [c.fragmento_id for c in elegidos],
        # El gemelo del bloque de arriba, corregido el mismo dia y por el mismo motivo: decia
        # "no hay capa de verificacion que apagar hasta la fase 4" con las cuatro capas corriendo.
        "verificacion": {"solicitada": peticion.verificacion, "construido": True,
                         "solicitada_tiene_efecto": False,
                         "aviso": "la verificacion (4.2-4.5) corre en cada consulta; este "
                                  "interruptor todavia no la apaga (la ablacion es el 7.3)"},
        "traza": f"/trazas/{respuesta_id}",
    })


def _comprobar_la_puente(peticion: Consulta, catalogo) -> None:
    """LA ASIGNATURA TIENE QUE PERTENECER A LA TITULACIÓN, y esto se comprueba EN EL SERVIDOR.

    El navegador repuebla el desplegable al cambiar de titulación, pero eso es una promesa del
    cliente y **una promesa del cliente no es una garantía**: basta un fallo de red en esa petición,
    una carrera entre dos cambios seguidos, o un `curl` a mano, para que llegue un par cruzado. Y el
    daño no se ve: la consulta se responde igual, con material de una titulación que el alumno no
    cursa, y la traza lo registra como una consulta normal. **Contaminación entre titulaciones sin
    una sola línea roja** — que es justo lo que el filtro de asignatura de `recuperacion.py` existe
    para impedir un piso más abajo, y con el mismo argumento: la manera de que no pase por descuido
    no es acordarse, es que no se pueda.

    Las dos protecciones del navegador se quedan igualmente (el `catch` que vacía la lista y el
    contador que descarta respuestas tardías): esta es la que no depende de nadie.
    """
    if peticion.titulacion is None or peticion.asignatura_id is None or catalogo is None:
        return
    try:
        suyas = {a["id"] for a in catalogo.asignaturas(peticion.titulacion)}
    except Exception:                        # noqa: BLE001 - titulacion inventada o base caida
        return                               # no se inventa un rechazo por no poder comprobarlo
    if suyas and peticion.asignatura_id not in suyas:
        raise HTTPException(400, f"la asignatura {peticion.asignatura_id} no pertenece a "
                                 f"{peticion.titulacion}: no se responde con material de una "
                                 f"titulacion que no es la elegida")


@router.post("/consulta")
def consulta(peticion: Consulta, request: Request) -> StreamingResponse:
    traza = request.app.state.traza
    _comprobar_la_puente(peticion, getattr(request.app.state, "catalogo", None))
    cliente = request.app.state.cliente_inferencia
    if cliente is None:
        raise HTTPException(503, "sin proveedor de inferencia: "
                                 + getattr(request.app.state, "sin_proveedor", "no configurado"))
    # EL MODO, ANTES DE ABRIR LA TRAZA: `consultas.modo` y `consultas.version_prompt` tienen que
    # contar el modo con el que de verdad se va a generar, no el que venia en la peticion.
    eleccion = resolver_modo(peticion)
    consulta_id = traza.abrir_consulta(texto=peticion.texto, asignatura_id=peticion.asignatura_id,
                                       modo=eleccion["modo"], usuario_id=peticion.usuario_id,
                                       version_prompt=version_prompt(eleccion["modo"]))
    return StreamingResponse(_flujo(cliente, peticion, traza, consulta_id,
                                    getattr(request.app.state, "embebedor", None),
                                    request.app.state.url_base_datos,
                                    getattr(request.app.state, "reordenador", None),
                                    getattr(request.app.state, "nli", None),
                                    getattr(request.app.state, "catalogo", None),
                                    eleccion=eleccion),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
