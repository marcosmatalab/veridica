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
# La version del prompt sale del modulo que lo escribe, no de una constante suelta que nadie
# toca al cambiar el texto: eso es lo que la convertia en un campo con nombre de
# trazabilidad y contenido de adorno.
from app.core.prompts import sistema as prompt_sistema
from app.core.prompts import version as version_prompt
from app.core.prosa_parcial import ProsaEnCurso
from app.core.recuperacion import buscar_vectorial, confianza_de, recuperar
from app.core.ritmo import RitmoCaido, VigilanteDeRitmo
from app.core.verificador_calculo import verificar as verificar_calculo
from app.core.verificador_literal import verificar
from app.modelos.contrato import (SIN_VERIFICAR, ContratoRoto, numero_de_referencia,
                                  response_format, validar_forma)

router = APIRouter()

#: Los que entran en el contexto. El reordenador del 3.4 escogera estos 6 de entre los
#: 30 del pool; hasta que exista, se toman los 6 primeros de la fusion tal cual.
FRAGMENTOS_EN_CONTEXTO = 6
POOL = 30

#: REQUISITO DE PRODUCTO (seccion 11), no un umbral de ajuste: la consulta no pasa de 5 s. Se lee
#: del entorno para que sea una sola verdad, y se HACE CUMPLIR mas abajo cortando: un tope que nadie
#: comprueba es una aspiracion, y la avería medida el 13 de agosto -63 s de p95- es exactamente lo
#: que una aspiracion no evita.
PRESUPUESTO_MS = int(os.environ.get("PRESUPUESTO_CONSULTA_MS") or 5000)


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


def _veredictos_en_curso(estado: dict, textos_en_contexto: dict):
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
    for a in array:
        if not isinstance(a, dict) or a.get("tipo") not in ("literal", "calculo"):
            continue
        if a.get("tipo") == "calculo":
            v = verificar_calculo(a)
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
                textos_en_contexto: dict | None = None, modo: str = "responder"):
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
                for evento in _veredictos_en_curso(estado, textos_en_contexto or {}):
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
            portero = estado.get("portero")
            nueva = portero.alimentar(nueva) if portero else nueva
            if not nueva:
                continue
            estado["emitido"] = True
            yield _evento("token", {"t": nueva})
    except RitmoCaido as e:
        # No es un fallo del proveedor: responde, solo que a un ritmo que no llega. Se corta aqui y
        # el que decide si se reintenta es `_flujo`, que es quien sabe si ya habia prosa en pantalla.
        estado["ritmo_caido"] = {"tokens_por_segundo": round(e.ritmo, 1), "minimo": e.minimo}
        estado["error"] = f"RitmoCaido: {e}"
        _estimar_uso(estado)
    except PlazoAgotado as e:
        estado["plazo_agotado"] = {"ms": e.ms, "presupuesto_ms": e.presupuesto_ms}
        estado["error"] = f"PlazoAgotado: {e}"
        _estimar_uso(estado)
    except (ErrorTransitorio, ErrorDefinitivo) as e:
        estado["error"] = f"{type(e).__name__}: {e}"
    # LA ULTIMA FRASE, que casi nunca trae punto final. Se juzga igual que las demas: una frase sin
    # cerrar no es una excepcion a la regla de cobertura, solo es una que el modelo no termino.
    if estado.get("portero"):
        resto = estado["portero"].cerrar()
        if resto:
            estado["emitido"] = True
            yield _evento("token", {"t": resto})
        if estado["portero"].huerfanas:
            # SE DICE, y ademas se dice CUANTAS: una respuesta con frases podadas es una respuesta
            # con agujeros, y el alumno tiene derecho a saber que falta algo en vez de leer un
            # parrafo que salta. La retirada del 2.4 sigue siendo para otra cosa.
            yield _evento("cobertura", {
                "frases_podadas": len(estado["portero"].huerfanas),
                "frases_emitidas": estado["portero"].emitidas,
                "que_significa": "hubo frases de la redaccion que no estaban respaldadas por "
                                 "ninguna afirmacion declarada, asi que no se han enseñado",
                "ejemplos": estado["portero"].huerfanas[:3],
            })
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
        estado = yield from _generacion(cliente, peticion.texto, t0, contexto, confianza,
                                        {c.fragmento_id: c.texto for c in elegidos},
                                        peticion.modo)
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
                                "detalle": "el contrato no llego bien formado"})
        yield _evento("abstencion", {
            "motivo": motivo,
            "que_significa": (
                f"la respuesta no llego dentro del plazo de {PRESUPUESTO_MS} ms; se corta y se dice, "
                f"en vez de dejar la pantalla congelada"
                if estado["plazo_agotado"] else
                "el proveedor no devolvio el contrato de la seccion 7; se abstiene en vez de "
                "ensenar algo sin forma conocida"),
            "por_plazo": bool(estado["plazo_agotado"]),
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
        "coste_eur": uso.coste_eur(), "version_prompt": version_prompt(peticion.modo),
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
                                       modo=peticion.modo, usuario_id=peticion.usuario_id,
                                       version_prompt=version_prompt(peticion.modo))
    return StreamingResponse(_flujo(cliente, peticion, traza, consulta_id,
                                    getattr(request.app.state, "embebedor", None),
                                    request.app.state.url_base_datos,
                                    getattr(request.app.state, "reordenador", None)),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
