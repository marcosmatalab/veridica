"""`GET /trazas/{id}` (encargo 2.5) y la FIRMA DEL INSTRUMENTO en cada veredicto.

**El criterio de cierre del 2.5 se lee literal: "para una consulta cualquiera, la traza responde a
'qué se recuperó, qué se afirmó, qué veredicto tuvo cada afirmación, cuánto costó cada etapa'".**
Así que aquí hay un test POR PREGUNTA, y cada uno comprueba que la respuesta contiene el dato, no
solo la clave: una traza con `que_se_recupero: {}` cumpliría un test de forma y no contestaría nada.

Lo que NO se prueba aquí y se dice: el SQL de `TrazaPostgres.leer_respuesta`. En CI no hay Postgres
(ADR 0001), así que la ruta HTTP se prueba contra `TrazaEnMemoria` y la lectura real se comprueba a
mano contra la base local, con su salida en la evidencia del 2.5. Es el mismo trato que el resto de
la casa: el hueco declarado, no tapado con un test que no prueba lo que su nombre dice.
"""
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.trazas import PREGUNTAS
from app.core.traza import TrazaEnMemoria
from app.core.verificador_calculo import INSTRUMENTO as INSTRUMENTO_CALCULO
from app.core.verificador_calculo import verificar as verificar_calculo
from app.core.verificador_literal import INSTRUMENTO as INSTRUMENTO_LITERAL
from app.core.verificador_literal import verificar as verificar_literal
from app.core.verificador_nli import INSTRUMENTO as INSTRUMENTO_NLI

ETAPAS = {
    "marcas": [{"nombre": "consulta_embebida", "ms": 41.0},
               {"nombre": "recuperacion", "ms": 78.2}],
    "generacion": {
        "ttft_proveedor_ms": 292.0, "ttft_prosa_ms": 1601.0, "total_ms": 2204.0,
        "intentos_http": 1, "codigos_transitorios": [], "uso_estimado": False,
        "ritmo": {"tokens": 430, "tokens_por_segundo": 133.0, "minimo_observado": 61.5,
                  "minimo": 35.0, "ventana_s": 2.0},
        "cobertura": {"frases_emitidas": 3, "frases_huerfanas": 1, "solape_minimo": 0.5,
                      "solapes": [{"solape": 0.8, "emitida": True, "corta": False},
                                  {"solape": 0.31, "emitida": False, "corta": False}]},
        "desglose": {"prefill_ms": 292.0, "afirmaciones_ms": 1309.0, "prosa_ms": 603.0},
        "motivo_fallo": None, "crudo_recibido": None, "crudo_truncado": False,
    },
    "recuperacion": {"construido": True, "pool": 40, "en_contexto": [2936, 4321],
                     "confianza": "alta", "detalle_confianza": {"margen": 0.12}},
    "verificacion": {"construido": True, "encargos": ["4.2", "4.3", "4.4", "4.5"],
                     "nli_cargado": True, "umbral_nli": 0.6, "solicitada_tiene_efecto": False},
}

AFIRMACIONES = [
    {"tipo": "literal", "texto": "La sesion se almacena en el servidor.", "fragmento_id": 2936,
     "veredicto": "verificada",
     "detalle": {"cita": "La sesion se almacena en el servidor", "id_en_contrato": 1,
                 "fragmento_en_contexto": True,
                 "verificacion": {"veredicto": "verificada", "nivel": "espacios",
                                  "instrumento": INSTRUMENTO_LITERAL, "motivo": None,
                                  "detalle": "subcadena exacta"}}},
    {"tipo": "parafrasis", "texto": "Los datos del usuario viven en el servidor.",
     "fragmento_id": 4321, "veredicto": "verificada",
     "detalle": {"apoyo": "los datos viven en el servidor", "id_en_contrato": 2,
                 "fragmento_en_contexto": True,
                 "verificacion": {"veredicto": "verificada", "nli": "entailment",
                                  "probabilidad": 0.97, "cobertura": 0.62,
                                  "seleccion": "ventana_por_apoyo",
                                  "instrumento": INSTRUMENTO_NLI, "motivo": None,
                                  "detalle": "el fragmento sostiene la afirmacion"}}},
    {"tipo": "calculo", "texto": "El PVP con IVA son 60,50 euros.", "fragmento_id": None,
     "veredicto": "podada",
     "detalle": {"expresion": "50 * 1,21", "id_en_contrato": 3,
                 "verificacion": {"veredicto": "podada", "recalculado": "60,50",
                                  "instrumento": INSTRUMENTO_CALCULO,
                                  "motivo": "resultado_no_coincide", "detalle": "no cuadra"}}},
]


@pytest.fixture
def cliente_http():
    traza = TrazaEnMemoria()
    traza.abrir_consulta(texto="que es una sesion", asignatura_id=29, modo="responder",
                         usuario_id=None, version_prompt="ventana-2026-08-14/responder")
    traza.cerrar_respuesta(consulta_id=1, afirmaciones=AFIRMACIONES, modelo="mistral-small",
                           ttft_ms=1601, total_ms=2204, tokens_entrada=2100, tokens_salida=331,
                           coste_eur=0.000149, etapas=ETAPAS, abstencion=False)
    app.state.traza = traza
    app.state.embebedor = None
    with TestClient(app) as c:
        yield c


def test_las_CUATRO_preguntas_del_enunciado_tienen_su_clave(cliente_http):
    """El criterio del 2.5, leído literal. Las claves llevan el nombre de la pregunta a propósito:
    si mañana alguien renombra una, esto se pone rojo en vez de cumplirse de memoria."""
    t = cliente_http.get("/trazas/1").json()
    for pregunta in PREGUNTAS:
        assert pregunta in t, f"la traza no contesta a '{pregunta}'"


def test_pregunta_1_que_se_recupero(cliente_http):
    """Y con el dato dentro, no la clave vacía: los ids que estuvieron en contexto, cuántos, la
    confianza medida por el servidor, y por dónde se abre cada fragmento."""
    r = cliente_http.get("/trazas/1").json()["que_se_recupero"]
    assert r["fragmentos_en_contexto"] == [2936, 4321] and r["cuantos"] == 2
    assert r["confianza"] == "alta" and r["hubo_recuperacion"] is True
    assert r["abrir_fragmento"][0] == "/respuestas/1/fragmentos/2936"


def test_pregunta_2_que_se_afirmo(cliente_http):
    a = cliente_http.get("/trazas/1").json()["que_se_afirmo"]
    assert a["cuantas"] == 3 and a["abstencion"] is False
    primera = a["afirmaciones"][0]
    assert primera["tipo"] == "literal" and primera["fragmento_id"] == 2936
    assert primera["cita"].startswith("La sesion")
    assert a["afirmaciones"][1]["apoyo"] == "los datos viven en el servidor", \
        "el apoyo de una parafrasis es parte de lo que se afirmo: sin el no se puede discutir"


def test_pregunta_3_que_veredicto_tuvo_cada_afirmacion_Y_CON_QUE_INSTRUMENTO(cliente_http):
    """LA PREGUNTA QUE EL 2.5 CONTESTA MEJOR QUE ANTES. Tres afirmaciones, tres verificadores
    distintos, y el reparto partido por firma: sin eso, `verificada` mezcla instrumentos y eso ya
    costó una calibración entera (12 positivos que el NLI se aprobó a sí mismo)."""
    v = cliente_http.get("/trazas/1").json()["que_veredicto_tuvo_cada_afirmacion"]
    assert v["reparto"] == {"verificada": 2, "podada": 1}
    assert v["por_instrumento"][INSTRUMENTO_LITERAL] == {"verificada": 1}
    assert v["por_instrumento"][INSTRUMENTO_NLI] == {"verificada": 1}
    assert v["por_instrumento"][INSTRUMENTO_CALCULO] == {"podada": 1}
    assert all(x["sin_firma_porque"] is None for x in v["veredictos"])
    assert v["veredictos"][1]["seleccion"] == "ventana_por_apoyo"


def test_una_afirmacion_QUE_NADIE_VERIFICA_no_se_confunde_con_una_fila_vieja(cliente_http):
    """EL FALLO QUE ENSEÑÓ LA PRIMERA CONSULTA REAL contra este endpoint, anclado.

    Una fila escrita hacía un minuto salía como *"anterior al 14/08"* porque sus afirmaciones eran
    `conocimiento`, que **no pasa por ningún verificador por diseño** (es la escotilla declarada).
    La etiqueta afirmaba una causa —la edad— que no había comprobado. Las dos razones de no llevar
    firma son distintas: una es correcta y permanente, la otra es una deuda que se agota sola.
    """
    app.state.traza.cerrar_respuesta(
        consulta_id=1, modelo="mistral-small", ttft_ms=900, total_ms=1500, tokens_entrada=10,
        tokens_salida=10, coste_eur=0.0, etapas=ETAPAS, abstencion=False,
        afirmaciones=[{"tipo": "conocimiento", "texto": "Esto lo se yo, no el temario.",
                       "fragmento_id": None, "veredicto": "sin_verificar",
                       "detalle": {"id_en_contrato": 1}},
                      {"tipo": "literal", "texto": "algo viejo", "fragmento_id": 1,
                       "veredicto": "verificada", "detalle": {"id_en_contrato": 2,
                                                              "verificacion": {"nivel": "espacios"}}}])
    v = cliente_http.get("/trazas/2").json()["que_veredicto_tuvo_cada_afirmacion"]
    assert "no verificable por diseño" in v["veredictos"][0]["sin_firma_porque"]
    assert "anterior al 14/08/2026" in v["veredictos"][1]["sin_firma_porque"], \
        "una verificada SIN firma si es una fila vieja: esa es la deuda de datos de verdad"
    assert set(v["por_instrumento"]) == {
        "sin verificador (tipo no verificable por diseño: conocimiento / andamiaje)",
        "sin_declarar (fila anterior al 14/08/2026)"}, \
        "los dos motivos en el mismo cajon volverian a mezclar dos preguntas en un contador"


def test_pregunta_4_cuanto_costo_cada_etapa(cliente_http):
    """Y las marcas son las MEDIDAS que se dibujaron: la condición del 2.4 era que cada etapa de la
    pantalla tuviera su entrada en la traza, y esto es el otro lado de esa comprobación."""
    e = cliente_http.get("/trazas/1").json()["cuanto_costo_cada_etapa"]
    assert [m["nombre"] for m in e["marcas"]] == ["consulta_embebida", "recuperacion"]
    assert e["ttft_prosa_ms"] == 1601 and e["total_ms"] == 2204
    assert e["coste_eur"] == pytest.approx(0.000149) and e["modelo"] == "mistral-small"
    assert e["ritmo"]["minimo_observado"] == 61.5, \
        "el peor momento es lo que el umbral de 35 tok/s juzga: sin el, la traza cuenta otra cosa"


def test_una_traza_que_no_existe_es_404_y_no_una_traza_vacia(cliente_http):
    """Un 200 con todo a nulo diría "esta consulta no recuperó nada y no afirmó nada", que es una
    respuesta falsa sobre algo que no ocurrió. Misma distinción que el 404 por procedencia."""
    r = cliente_http.get("/trazas/99")
    assert r.status_code == 404 and "no hay respuesta 99" in r.json()["detail"]


def test_la_traza_de_una_ABSTENCION_tambien_se_lee(cliente_http):
    """El camino de fallo también deja rastro desde el 14/08: si la traza solo supiera contar las
    respuestas que salieron bien, cualquier tasa calculada sobre ella estaría sesgada por el éxito
    — que es el principio 11 cometido dentro de nuestra propia base."""
    etapas = {**ETAPAS, "generacion": {**ETAPAS["generacion"],
                                       "motivo_fallo": "contrato_roto: falta 'modo'",
                                       "crudo_recibido": '{"afirmaciones": [', "crudo_truncado": True}}
    app.state.traza.cerrar_respuesta(consulta_id=1, afirmaciones=[], modelo="mistral-small",
                                     ttft_ms=None, total_ms=1200, tokens_entrada=2100,
                                     tokens_salida=40, coste_eur=0.00001, etapas=etapas,
                                     abstencion=True)
    a = cliente_http.get("/trazas/2").json()["que_se_afirmo"]
    assert a["abstencion"] is True and a["cuantas"] == 0
    assert "contrato_roto" in a["motivo_fallo"] and a["crudo_truncado"] is True


def test_las_columnas_QUE_NADIE_ESCRIBE_salen_con_su_aviso(cliente_http):
    """`cache_hit` y `escalado` valen siempre false porque nada las escribe. Un false suelto en una
    vitrina se lee como "la caché no acertó", que es una medida sobre algo que no existe."""
    c = cliente_http.get("/trazas/1").json()["campos_sin_escribir"]
    assert "NADA los escribe" in c["aviso"]


# --- la firma del instrumento, en los tres verificadores -------------------------------------------

def test_los_TRES_verificadores_firman_su_veredicto():
    """LA REGLA DEL 14/08 HECHA CÓDIGO: los tres escriben los mismos valores en `veredicto`, así que
    quien escribe firma. Se comprueba en los tres a la vez porque el fallo aparece justo cuando uno
    de ellos NO firma: el reparto por instrumento lo mete en "sin declarar" y vuelve la mezcla."""
    literal = verificar_literal({"cita": "una clave primaria", "fragmento_id": 1},
                                {1: "una clave primaria identifica cada fila"})
    calculo = verificar_calculo({"expresion": "50 * 1,21", "resultado_afirmado": "60,50"})
    assert literal["instrumento"] == INSTRUMENTO_LITERAL
    assert calculo["instrumento"] == INSTRUMENTO_CALCULO
    assert INSTRUMENTO_NLI.startswith("4.3/nli:"), "el NLI firma con su modelo, que es lo que juzga"
    assert len({INSTRUMENTO_LITERAL, INSTRUMENTO_NLI, INSTRUMENTO_CALCULO}) == 3, \
        "dos instrumentos con la misma firma no se pueden separar en una consulta"


def test_la_PUERTA_de_procedencia_firma_distinto_del_NLI():
    """Una poda por procedencia fabricada la decide la comparación de cadenas del 4.2, no el NLI.
    Si firmara como NLI, una consulta que contara podas del NLI incluiría podas que el NLI nunca
    vio — la misma mezcla, un piso más abajo."""
    v = verificar_literal({"cita": "lo que sea", "fragmento_id": 999}, {1: "otro texto"})
    assert v["veredicto"] == "podada" and v["motivo"] == "procedencia_fabricada"
    assert v["instrumento"] == INSTRUMENTO_LITERAL
