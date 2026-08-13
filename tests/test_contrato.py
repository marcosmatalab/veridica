"""El contrato de la seccion 7: que valida y, sobre todo, que NO valida (encargo 2.2).

Estos tests comprueban FORMA. Ninguno comprueba que lo que dice la respuesta sea verdad, porque
este encargo no verifica nada: eso es la fase 4. Si algun dia alguien anade aqui un test que
compruebe que una cita esta en su fragmento, se ha equivocado de fichero y de fase.
"""
import json

import pytest

from app.modelos.contrato import (SIN_VERIFICAR, ContratoRoto, esquema_json, response_format,
                                  validar_forma)


def respuesta(afirmaciones) -> dict:
    return {
        "modo": "responder",
        "afirmaciones": afirmaciones,
        "respuesta_redactada": "Una clave primaria identifica cada fila.",
        "siguiente_paso": {"tipo": "pregunta_al_alumno", "texto": "Y una ajena?"},
    }


CONOCIMIENTO = {"id": 1, "tipo": "conocimiento", "texto": "Identifica cada fila.",
                "fragmento_id": None}
LITERAL = {"id": 2, "tipo": "literal", "texto": "Es unica.", "fragmento_id": "F7",
           "cita": "la clave primaria es unica"}


def test_una_respuesta_bien_formada_pasa():
    v = validar_forma(respuesta([CONOCIMIENTO, LITERAL]))
    assert [a.tipo for a in v.afirmaciones] == ["conocimiento", "literal"]
    assert v.afirmaciones[1].cita == "la clave primaria es unica"


def test_la_cita_en_un_conocimiento_se_rechaza():
    """EL FALLO REAL QUE ENSENO LA PRIMERA LLAMADA DE VERDAD, y por eso esta anclado aqui.

    Con el esquema plano -un solo modelo con `cita` opcional-, el modelo relleno `cita` en las
    afirmaciones de tipo `conocimiento` en las TRES repeticiones, copiando su propio texto. Una
    cita promete verificacion literal contra un fragmento; ponerla donde no hay fragmento es
    prometer algo que la fase 4 no podra comprobar. El esquema se partio en cinco variantes para
    que el decodificador no pueda emitirla, y el validador la sigue rechazando: el que comprueba
    no se fia del que produce, aunque el esquema lo escriba el mismo cliente.
    """
    malo = dict(CONOCIMIENTO, cita="Identifica cada fila.")
    with pytest.raises(ContratoRoto):
        validar_forma(respuesta([malo]))


def test_una_literal_sin_cita_se_rechaza():
    sin_cita = {"id": 1, "tipo": "literal", "texto": "x", "fragmento_id": "F3"}
    with pytest.raises(ContratoRoto):
        validar_forma(respuesta([sin_cita]))


def test_una_literal_con_cita_vacia_se_rechaza():
    """Una cita en blanco pasa cualquier comprobacion de presencia y no se puede verificar contra
    nada: es el hueco por el que se cuela una afirmacion sin fuente con aspecto de tenerla."""
    with pytest.raises(ContratoRoto):
        validar_forma(respuesta([dict(LITERAL, cita="   ")]))


def test_un_andamiaje_sin_clase_se_rechaza():
    with pytest.raises(ContratoRoto):
        validar_forma(respuesta([{"id": 1, "tipo": "andamiaje", "texto": "Vamos por partes."}]))


def test_un_tipo_inventado_se_rechaza():
    with pytest.raises(ContratoRoto):
        validar_forma(respuesta([{"id": 1, "tipo": "opinion", "texto": "creo que si"}]))


def test_los_ids_repetidos_se_rechazan():
    """La traza referencia afirmaciones por id: dos con el mismo id hacen imposible saber cual
    verifico la fase 4."""
    with pytest.raises(ContratoRoto):
        validar_forma(respuesta([CONOCIMIENTO, dict(LITERAL, id=1)]))


def test_el_esquema_que_se_envia_es_estricto_en_todos_los_objetos():
    """Lo que pide la documentacion del proveedor: `additionalProperties` en falso y TODO en
    `required`. Se comprueba recorriendo el esquema entero, no solo la raiz, porque el que se
    escapaba era siempre un objeto anidado."""
    def recorrer(nodo, camino="raiz"):
        if isinstance(nodo, dict):
            if nodo.get("type") == "object" and "properties" in nodo:
                assert nodo.get("additionalProperties") is False, camino
                assert set(nodo["required"]) == set(nodo["properties"]), camino
            for k, v in nodo.items():
                recorrer(v, f"{camino}.{k}")
        elif isinstance(nodo, list):
            for i, v in enumerate(nodo):
                recorrer(v, f"{camino}[{i}]")

    recorrer(esquema_json())


def test_el_esquema_no_lleva_palabras_que_el_proveedor_no_necesita():
    crudo = json.dumps(esquema_json())
    assert "discriminator" not in crudo
    assert '"default"' not in crudo


def test_el_response_format_va_en_modo_esquema_y_no_en_json_object():
    """`json_object` es el modo heredado y sin esquema: la propia documentacion de Scaleway avisa
    de que da peor calidad. Sin esquema, el contrato deja de ser un contrato."""
    f = response_format()
    assert f["type"] == "json_schema"
    assert f["json_schema"]["name"] == "RespuestaTipada"
    assert "schema" in f["json_schema"]


def test_la_cita_solo_existe_en_la_variante_literal_del_esquema():
    """Lo que hace imposible el fallo de la primera llamada: si `cita` no esta en la gramatica de
    `conocimiento`, el decodificador restringido no la puede emitir."""
    defs = esquema_json()["$defs"]
    assert "cita" in defs["AfirmacionLiteral"]["properties"]
    for variante in ("AfirmacionConocimiento", "AfirmacionParafrasis", "AfirmacionAndamiaje",
                     "AfirmacionCalculo"):
        assert "cita" not in defs[variante]["properties"], variante


def test_el_veredicto_por_defecto_dice_lo_que_es():
    assert SIN_VERIFICAR == "sin_verificar"
