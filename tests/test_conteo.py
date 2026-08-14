"""El conteo que declara su unidad. Nació el 14/08/2026 de un fallo con nombre y tamaño.

Todos los titulares de ese día se calcularon contando FILAS del arnés de evaluación creyendo contar
CASOS: 158 "positivos" eran 74 pares distintos y uno solo salía 20 veces. La regla —ocurrencias y
hallazgos se cuentan por separado— llevaba meses escrita; lo que faltó fue preguntar qué era una
fila. Estos tests anclan que la confusión sea **imposible** y no solo improbable.
"""
import pytest

from app.core.conteo import Conteo, contar, porcentaje

FILAS = [
    {"frag": "A", "texto": "la sesion vive en el servidor"},
    {"frag": "A", "texto": "la sesion vive en el servidor"},   # la misma pregunta, otra vez
    {"frag": "A", "texto": "la sesion vive en el servidor"},
    {"frag": "B", "texto": "la cookie lleva el identificador"},
]


def test_devuelve_LAS_DOS_cifras_siempre():
    """Lo que hace imposible el fallo: no se puede obtener una sin la otra."""
    c = contar(FILAS, lambda x: (x["frag"], x["texto"]), "fragmento + texto de la afirmacion")
    assert c.ocurrencias == 4 and c.casos == 2
    assert c.factor == 2.0
    assert "casos distintos" in str(c) and "ocurrencias" in str(c)
    assert set(c.a_dict()) == {"ocurrencias", "casos", "factor", "clave"}


def test_la_CLAVE_es_obligatoria_porque_el_numero_depende_de_la_pregunta():
    """*"La misma cita"*, *"la misma afirmación"* y *"la misma frase"* son preguntas distintas y dan
    números distintos. Un conteo sin clave declarada no se puede auditar."""
    with pytest.raises(ValueError, match="clave"):
        contar(FILAS, lambda x: x["texto"], "")


def test_la_clave_CAMBIA_el_numero_y_por_eso_viaja_con_el():
    por_texto = contar(FILAS, lambda x: x["texto"], "solo el texto")
    por_par = contar(FILAS, lambda x: (x["frag"], x["texto"]), "fragmento + texto")
    assert por_texto.casos == 2 and por_par.casos == 2
    por_frag = contar(FILAS, lambda x: x["frag"], "solo el fragmento")
    assert por_frag.casos == 2
    assert por_texto.clave != por_par.clave != por_frag.clave


def test_el_porcentaje_sale_en_LAS_DOS_unidades():
    """Publicar solo el porcentaje que gusta es el fallo original con otra cara: aquí salen los dos
    o no sale ninguno."""
    total = contar(FILAS, lambda x: (x["frag"], x["texto"]), "par")
    parte = contar(FILAS[:3], lambda x: (x["frag"], x["texto"]), "par")
    texto = porcentaje(parte, total)
    assert "en casos" in texto and "en filas" in texto
    assert "50.0 %" in texto and "75.0 %" in texto, \
        "las dos unidades dan 50 % y 75 % sobre estos datos: esa brecha es justo lo que hay que ver"


def test_el_orden_es_DETERMINISTA_y_se_queda_el_primero():
    c = contar(FILAS, lambda x: x["frag"], "fragmento")
    assert [x["frag"] for x in c.elementos] == ["A", "B"]


def test_sin_repeticiones_el_factor_es_uno():
    """La otra dirección: si no hay repetición, el conteo no inventa ninguna."""
    c = contar(FILAS[2:], lambda x: (x["frag"], x["texto"]), "par")
    assert c.ocurrencias == c.casos == 2 and c.factor == 1.0


def test_un_conteo_vacio_no_revienta_ni_divide_por_cero():
    c = Conteo(ocurrencias=0, casos=0, clave="lo que sea")
    assert c.factor == 0.0 and "n/a" in porcentaje(c, c)
