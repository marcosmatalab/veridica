"""`GET /trazas/{id}`: la traza completa de una respuesta (encargo 2.5).

**El enunciado hace CUATRO preguntas y esta respuesta tiene cuatro claves con esos nombres**, en vez
de un volcado del que haya que deducirlas: *qué se recuperó*, *qué se afirmó*, *qué veredicto tuvo
cada afirmación* y *cuánto costó cada etapa*. La forma no es cosmética — es lo que permite
comprobar el criterio de cierre cláusula a cláusula en vez de a ojo, y lo que hace que una pregunta
sin respuesta se vea como un hueco en lugar de esconderse entre cien campos.

## POR QUÉ ESTE ENDPOINT LLEGA DESPUÉS DE LA FASE 4, Y NO ES UNA EXCUSA RETROACTIVA

El 2.5 se movió detrás de la fase 4 el 13 de agosto de 2026 con el motivo escrito: de las cuatro
preguntas, la traza de entonces solo sabía contestar la última —no había recuperación (fase 3) ni
verificación (fase 4)—, así que habría sido la vitrina antes de tener qué poner dentro. Hoy las
cuatro tienen respuesta, y la tercera trae además **con qué instrumento**, que es la lección que
costó una calibración: dos verificadores escriben el mismo valor `verificada` y sin firma no hay
forma de saber cuál lo escribió.

## LEE Y NO DERIVA

Nada se recalcula aquí. Un veredicto recomputado hoy sobre una respuesta de la semana pasada usaría
los umbrales de hoy, o sea que sería una medida de otra configuración con aspecto de registro
histórico — el error viajando en el sumando, dentro de la propia vitrina. Lo que no esté persistido
se dice que no está; no se estima.
"""
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

#: Las cuatro preguntas del enunciado del 2.5, tal cual. Viven aquí porque el test del cierre las
#: recorre una a una: si mañana alguien renombra una clave, el criterio se pone rojo en vez de
#: cumplirse de memoria.
PREGUNTAS = ("que_se_recupero", "que_se_afirmo", "que_veredicto_tuvo_cada_afirmacion",
             "cuanto_costo_cada_etapa")


#: Los tipos que NINGÚN verificador juzga, y no por un hueco: `conocimiento` es la escotilla
#: declarada —lo que el modelo dice sin respaldo del temario— y `andamiaje` no afirma nada del
#: mundo. Su veredicto es `sin_verificar` y eso es la verdad, no un pendiente.
SIN_VERIFICADOR = ("conocimiento", "andamiaje")

#: Las dos razones por las que una afirmación puede no llevar firma, y **son distintas**: la
#: primera es correcta y permanente, la segunda es una deuda de datos que se agota sola.
NADIE_LA_VERIFICA = "sin verificador (tipo no verificable por diseño: conocimiento / andamiaje)"
FIRMA_SIN_DECLARAR = "sin_declarar (fila anterior al 14/08/2026)"


def _instrumento_de(detalle: dict) -> str | None:
    """Quién firmó este veredicto. `None` si no lo firmó nadie.

    **No se adivina por la forma del detalle**, que es lo que hubo que hacer para desatascar la
    calibración (`nivel` presente ⇒ lo escribió el 4.2). Aquello era un apaño sobre datos ya
    escritos; aquí, para filas nuevas, la firma es un campo.
    """
    v = (detalle or {}).get("verificacion") or {}
    return v.get("instrumento")


def _por_que_sin_firma(a: dict) -> str:
    """Por qué esta afirmación no lleva firma. **Las dos razones no se pueden confundir.**

    Lo enseñó la primera consulta real contra el endpoint: una fila escrita hacía un minuto salía
    etiquetada como *"anterior al 14/08"* porque sus cuatro afirmaciones eran `conocimiento`, que
    **no pasa por ningún verificador por diseño**. La etiqueta afirmaba una causa —la edad— que no
    había comprobado, que es exactamente lo que este repo persigue: una etiqueta describe cómo se
    clasificó algo, no lo que contiene. Se pregunta por el tipo antes de culpar a la fecha.
    """
    if a.get("tipo") in SIN_VERIFICADOR or a.get("veredicto") == "sin_verificar":
        return NADIE_LA_VERIFICA
    return FIRMA_SIN_DECLARAR


def _afirmacion_publica(a: dict) -> dict:
    d = a.get("detalle") or {}
    return {"id": a.get("id"), "id_en_contrato": d.get("id_en_contrato"), "tipo": a.get("tipo"),
            "texto": a.get("texto"), "fragmento_id": a.get("fragmento_id"),
            "cita": d.get("cita"), "apoyo": d.get("apoyo"), "expresion": d.get("expresion"),
            "andamiaje": d.get("andamiaje"),
            "fragmento_en_contexto": d.get("fragmento_en_contexto")}


def _veredicto_publico(a: dict) -> dict:
    d = a.get("detalle") or {}
    v = d.get("verificacion") or {}
    return {"id": a.get("id"), "id_en_contrato": d.get("id_en_contrato"), "tipo": a.get("tipo"),
            "veredicto": a.get("veredicto"),
            # LA FIRMA DEL INSTRUMENTO, y su ausencia dicha CON SU MOTIVO: que nadie la verifique
            # (correcto y permanente) no es lo mismo que que no se firmara (deuda de datos vieja).
            "instrumento": _instrumento_de(d),
            "sin_firma_porque": (None if _instrumento_de(d) else _por_que_sin_firma(a)),
            "motivo": v.get("motivo"), "detalle": v.get("detalle"),
            # Lo que cada verificador aporta para poder discutir su veredicto sin repetirlo.
            "nli": v.get("nli"), "probabilidad": v.get("probabilidad"),
            "cobertura": v.get("cobertura"), "seleccion": v.get("seleccion"),
            "umbral": v.get("umbral"), "suelo": v.get("suelo"),
            "nivel": v.get("nivel"), "solo_tildes": v.get("solo_tildes"),
            "recalculado": v.get("recalculado"), "comparacion": v.get("comparacion"),
            "calculo_no_declarado": v.get("calculo_no_declarado"),
            "operandos_sin_fuente": v.get("operandos_sin_fuente")}


@router.get("/trazas/{respuesta_id}")
def traza(respuesta_id: int, request: Request) -> dict:
    """La traza de una respuesta. 404 si no existe: no se inventa una vacía.

    Un 200 con todo a nulo diría *"esta consulta no recuperó nada y no afirmó nada"*, que es una
    respuesta falsa a una pregunta sobre algo que no ocurrió — la misma distinción que el 404 por
    procedencia del 2.4.
    """
    datos = request.app.state.traza.leer_respuesta(respuesta_id)
    if datos is None:
        raise HTTPException(404, f"no hay respuesta {respuesta_id}: la traza se pide por el id que "
                                 f"devuelve el evento 'fin' de /consulta")

    r, c = datos["respuesta"], datos["consulta"]
    etapas = r.get("etapas") or {}
    generacion = etapas.get("generacion") or {}
    recuperacion = etapas.get("recuperacion") or {}
    afirmaciones = datos["afirmaciones"]

    return {
        "respuesta_id": r.get("id"), "consulta_id": c.get("id"),
        "pregunta": {"texto": c.get("texto"), "modo": c.get("modo"),
                     "asignatura_id": c.get("asignatura_id"), "cuando": c.get("creada_en"),
                     "version_prompt": c.get("version_prompt"),
                     "version_corpus": c.get("version_corpus")},

        # (1) QUÉ SE RECUPERÓ. `construido: False` aquí es un hecho de ESA consulta —se respondió
        # sin fragmentos, y por qué—, no una capacidad que falte: la distinción importa porque el
        # mismo campo significaba lo segundo hasta la fase 3.
        "que_se_recupero": {
            "fragmentos_en_contexto": recuperacion.get("en_contexto") or [],
            "cuantos": len(recuperacion.get("en_contexto") or []),
            "pool": recuperacion.get("pool"),
            "confianza": recuperacion.get("confianza"),
            "detalle_confianza": recuperacion.get("detalle_confianza"),
            "hubo_recuperacion": bool(recuperacion.get("construido")),
            "abrir_fragmento": [f"/respuestas/{r.get('id')}/fragmentos/{i}"
                                for i in (recuperacion.get("en_contexto") or [])],
        },

        # (2) QUÉ SE AFIRMÓ. Incluye las de una respuesta que se abstuvo: desde el 14/08 el camino
        # de fallo también deja rastro (`motivo_fallo` y el crudo acotado), porque una tabla que
        # solo guarda lo que salió bien sesga toda métrica calculada encima.
        "que_se_afirmo": {
            "afirmaciones": [_afirmacion_publica(a) for a in afirmaciones],
            "cuantas": len(afirmaciones),
            "abstencion": r.get("abstencion"),
            "motivo_fallo": generacion.get("motivo_fallo"),
            "crudo_recibido": generacion.get("crudo_recibido"),
            "crudo_truncado": generacion.get("crudo_truncado"),
        },

        # (3) QUÉ VEREDICTO TUVO CADA AFIRMACIÓN, **Y CON QUÉ INSTRUMENTO**.
        "que_veredicto_tuvo_cada_afirmacion": {
            "veredictos": [_veredicto_publico(a) for a in afirmaciones],
            "reparto": _reparto(afirmaciones),
            "por_instrumento": _por_instrumento(afirmaciones),
            "verificacion": etapas.get("verificacion"),
            "cobertura_de_la_prosa": generacion.get("cobertura"),
            # LO QUE ESTA FILA NO PUEDE CONTAR, DICHO EN LA FILA. Las respuestas anteriores al
            # 14/08/2026 se guardaron con `verificacion.construido: false` y sin firma de
            # instrumento, mientras el 4.2, el 4.3 y el 4.4 corrían: el registro no se reescribe
            # —sería falsear la historia— pero tampoco se sirve a secas, porque leerlo tal cual
            # dice "aquí no se verificó nada" sobre una consulta que sí se verificó.
            "aviso_fila_vieja": (
                "esta respuesta es anterior al 14/08/2026: se persistió sin la firma del "
                "instrumento y con verificacion.construido=false aunque la verificación corría. "
                "El registro se sirve tal como se escribió; el aviso está para que no se lea como "
                "una medida" if not (etapas.get("verificacion") or {}).get("construido") else None),
        },

        # (4) CUÁNTO COSTÓ CADA ETAPA. Las marcas son las MEDIDAS que se dibujaron en pantalla: la
        # condición del 2.4 era que cada etapa dibujada tuviera su entrada aquí, y esto es el otro
        # lado de esa comprobación.
        "cuanto_costo_cada_etapa": {
            "marcas": etapas.get("marcas") or [],
            "ttft_prosa_ms": r.get("ttft_ms"), "total_ms": r.get("total_ms"),
            "ttft_proveedor_ms": generacion.get("ttft_proveedor_ms"),
            "desglose": generacion.get("desglose"),
            "ritmo": generacion.get("ritmo"),
            "plazo_agotado": generacion.get("plazo_agotado"),
            "ritmo_caido": generacion.get("ritmo_caido"),
            "intentos_http": generacion.get("intentos_http"),
            "codigos_transitorios": generacion.get("codigos_transitorios"),
            "tokens_entrada": r.get("tokens_entrada"), "tokens_salida": r.get("tokens_salida"),
            "uso_estimado": generacion.get("uso_estimado"),
            "coste_eur": r.get("coste_eur"), "modelo": r.get("modelo"),
        },

        # LOS DOS CAMPOS QUE NADIE ESCRIBE, con su aviso puesto AQUÍ y no en el lector: es una
        # propiedad del esquema y no de la fila, así que va donde no dependa de qué implementación
        # de `Traza` haya detrás. Un `false` suelto en una vitrina se lee como "la caché no acertó".
        "campos_sin_escribir": {
            "cache_hit": r.get("cache_hit"), "escalado": r.get("escalado"),
            "aviso": "cache_hit y escalado valen siempre false porque NADA los escribe: no hay "
                     "cache semantica ni escalonado construidos (corpus/COBERTURA.md)"},
    }


def _reparto(afirmaciones: list) -> dict:
    reparto: dict = {}
    for a in afirmaciones:
        clave = a.get("veredicto") or "sin_veredicto"
        reparto[clave] = reparto.get(clave, 0) + 1
    return reparto


def _por_instrumento(afirmaciones: list) -> dict:
    """El reparto que la regla del 14/08 hace posible: **el mismo `verificada` partido por quién lo
    firmó**. Sin esto, cualquier consulta sobre esta tabla mezcla los tres verificadores.

    Las que no llevan firma se agrupan por su MOTIVO y no en un cajón común: juntar *"esto no lo
    verifica nadie"* con *"esto se escribió antes de que existieran las firmas"* volvería a ser un
    contador contestando dos preguntas a la vez.
    """
    por: dict = {}
    for a in afirmaciones:
        firma = _instrumento_de(a.get("detalle") or {}) or _por_que_sin_firma(a)
        por.setdefault(firma, {})
        clave = a.get("veredicto") or "sin_veredicto"
        por[firma][clave] = por[firma].get(clave, 0) + 1
    return por
