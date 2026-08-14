"""El contrato de la seccion 7: que valida y, sobre todo, que NO valida (encargo 2.2).

Estos tests comprueban FORMA. Ninguno comprueba que lo que dice la respuesta sea verdad, porque
este encargo no verifica nada: eso es la fase 4. Si algun dia alguien anade aqui un test que
compruebe que una cita esta en su fragmento, se ha equivocado de fichero y de fase.
"""
import json

import pytest

from app.modelos.contrato import (LARGO_MINIMO_TEXTO, SIN_VERIFICAR, TIPOS, ContratoRoto,
                                  esquema_json, response_format, validar_forma)


def respuesta(afirmaciones) -> dict:
    return {
        "modo": "responder",
        "afirmaciones": afirmaciones,
        "respuesta_redactada": "Una clave primaria identifica cada fila.",
        "siguiente_paso": {"tipo": "pregunta_al_alumno", "texto": "Y una ajena?"},
    }


CONOCIMIENTO = {"id": 1, "tipo": "conocimiento", "texto": "Identifica cada fila.",
                "fragmento_id": None}
# El texto sube de "Es unica." (9) a una frase de verdad: desde el suelo de 13 caracteres, un
# `texto` mas corto que el nombre de tipo mas largo es INGRAMATICAL, y un doble de test que no
# cumple el contrato prueba un mundo que el sistema ya no admite.
LITERAL = {"id": 2, "tipo": "literal", "texto": "La clave primaria es unica.", "fragmento_id": "F7",
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
    sin_cita = {"id": 1, "tipo": "literal", "texto": "Una frase con cuerpo.", "fragmento_id": "F3"}
    with pytest.raises(ContratoRoto):
        validar_forma(respuesta([sin_cita]))


# --- el suelo de longitud del texto y su red (14 de agosto de 2026) --------------------------------

def test_el_NOMBRE_DE_UN_TIPO_como_texto_es_INGRAMATICAL():
    """LAS 152 FILAS REALES, cerradas en la gramática y no en una corrección posterior.

    El 15,6 % de `afirmaciones` lleva como `texto` el nombre de su propio tipo —147 `'literal'` y 5
    `'parafrasis'`—: el modelo emitiendo la ETIQUETA en vez del contenido. `texto: str` sin suelo lo
    hacía gramatical, así que la decodificación restringida podía escribirlo y ninguna capa
    posterior lo miraba. Con `min_length=13` la clase entera queda fuera de la gramática: el nombre
    más largo, `conocimiento`, mide 12.
    """
    for nombre in ("literal", "parafrasis", "calculo", "conocimiento", "andamiaje"):
        with pytest.raises(ContratoRoto):
            validar_forma(respuesta([{"id": 1, "tipo": "conocimiento", "texto": nombre,
                                      "fragmento_id": None}]))


def test_el_suelo_sale_del_NOMBRE_MAS_LARGO_y_no_de_una_intuicion():
    """El número se ancla con su derivación, porque es lo único que lo justifica: 13 es el primer
    valor que deja fuera a `conocimiento` (12). Un suelo mayor no compra nada aquí y sí cuesta
    afirmaciones legítimas —con 20, `@RestController` (15) y `{% include ... %}` (17) dejarían de
    poder afirmarse, y en este corpus son literales normales—."""
    assert LARGO_MINIMO_TEXTO == max(len(t) for t in TIPOS) + 1


def test_la_RED_caza_lo_que_el_suelo_no_puede_ver():
    """El suelo mira la LONGITUD y la avería es otra cosa: el texto es la etiqueta. Un `'literal'`
    con relleno de espacios o repetido mide bastante y sigue sin ser una afirmación."""
    for disfraz in ("literal literal", "  parafrasis   ", "calculo calculo calculo"):
        with pytest.raises(ContratoRoto):
            validar_forma(respuesta([{"id": 1, "tipo": "conocimiento", "texto": disfraz,
                                      "fragmento_id": None}]))


def test_la_red_NO_muerde_una_frase_que_MENCIONA_un_tipo():
    """La otra dirección, que es la que evita el falso positivo por construcción: *"El cálculo de
    subredes"* contiene la palabra `calculo` y es una afirmación perfectamente legítima. La red
    exige que TODAS las palabras sean nombres de tipo, no que aparezca una."""
    v = validar_forma(respuesta([{"id": 1, "tipo": "conocimiento",
                                  "texto": "El calculo de subredes usa la mascara.",
                                  "fragmento_id": None}]))
    assert v.afirmaciones[0].texto.startswith("El calculo")


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
