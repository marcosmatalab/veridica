"""El verificador literal del 4.2: comparación de cadenas, sin modelo, con su puerta delante.

Corre entero en CI: no necesita base, ni corpus, ni GPU, ni proveedor. Eso no es casualidad —es la
propiedad que hace que este verificador valga (principio 6)—: una comparación de subcadena no
comparte supuesto con nadie, así que tampoco comparte dependencias.
"""
import pytest

from app.core.verificador_literal import (DEGRADADA, NIVEL_POR_DEFECTO, NIVELES, PODADA,
                                          VERIFICADA, verificar)

FRAGMENTO = (
    "La sesión se almacena en el servidor; la cookie solo contiene el identificador.\n"
    "  El bean BindingResult recoge los errores de validación y debe ir justo detrás "
    "del @ModelAttribute."
)
CONTEXTO = {7: FRAGMENTO}


def afirmacion(cita, fragmento_id=7):
    return {"tipo": "literal", "cita": cita, "fragmento_id": fragmento_id}


# --- la puerta, que va ANTES de comparar ---------------------------------------------------------

def test_un_fragmento_que_no_estuvo_en_el_contexto_se_PODA_sin_compararse():
    """EL ORDEN NO ES UNA PREFERENCIA. Si la comparación corriera primero y pasara, ya se habría
    emitido un veredicto FAVORABLE sobre una cita que el modelo no pudo haber leído."""
    v = verificar(afirmacion("La sesión se almacena en el servidor", fragmento_id=999), CONTEXTO)
    assert v["veredicto"] == PODADA
    assert v["motivo"] == "procedencia_fabricada"


def test_la_puerta_se_dispara_AUNQUE_la_cita_fuera_correcta():
    """El caso que hace que la puerta no sea decorativa: con 11.282 fragmentos que se solapan 64
    tokens, un id inventado del mismo tema PUEDE contener una frase que case. Si la comparación
    fuera primero, esa cita fabricada saldría verificada."""
    cita_perfecta = "La sesión se almacena en el servidor"
    assert cita_perfecta in FRAGMENTO
    v = verificar(afirmacion(cita_perfecta, fragmento_id=123), CONTEXTO)
    assert v["veredicto"] == PODADA, "comparó antes de comprobar la procedencia"


# --- el caso plantado del enunciado, y su simétrico ----------------------------------------------

def test_una_cita_con_UNA_palabra_cambiada_degrada_a_parafrasis():
    """El test anclado que pide el enunciado del 4.2."""
    v = verificar(afirmacion("La sesión se almacena en el navegador"), CONTEXTO)
    assert v["veredicto"] == DEGRADADA
    assert v["motivo"] == "no_es_subcadena"


def test_una_cita_CORRECTA_no_degrada():
    """El simétrico, que el enunciado NO pide y sin el cual el de arriba no probaría nada: un
    verificador que degradara SIEMPRE pasaría aquel test con nota."""
    v = verificar(afirmacion("la cookie solo contiene el identificador"), CONTEXTO)
    assert v["veredicto"] == VERIFICADA


def test_los_saltos_de_linea_y_la_sangria_del_troceado_no_cuentan():
    """El único paso de normalización que entró, y aquí está por qué: el salto de línea y la
    sangría son del troceado, no del texto."""
    v = verificar(afirmacion("de validación y debe ir justo detrás del @ModelAttribute"), CONTEXTO)
    assert v["veredicto"] == VERIFICADA


# --- lo que NO se normaliza, que es la decisión de fondo ------------------------------------------

def test_las_MAYUSCULAS_cuentan_y_por_eso_bindingresult_no_pasa():
    """LA RAZÓN CONCRETA POR LA QUE LA SECCIÓN 8 SE CORRIGIÓ. En un corpus medio código, ignorar
    mayúsculas aceptaría `bindingresult` como cita literal de `BindingResult`, y en un lenguaje
    sensible a mayúsculas eso no es la misma cadena ni significa lo mismo.

    Medido sobre 337 citas reales, el paso de minúsculas ganaba 2 —las dos por la letra inicial— y
    a cambio abría esta puerta. No entra."""
    v = verificar(afirmacion("el bean bindingresult recoge los errores"), CONTEXTO)
    assert v["veredicto"] == DEGRADADA, (
        "una cita con el identificador en minusculas paso como literal: en codigo eso es otra cosa")
    # Y la direccion sana: con la caja correcta, pasa.
    assert verificar(afirmacion("El bean BindingResult recoge los errores"),
                     CONTEXTO)["veredicto"] == VERIFICADA


def test_perder_una_TILDE_no_se_perdona_porque_es_la_señal():
    """Si el modelo pierde un acento es porque está REESCRIBIENDO, no copiando. Esa diferencia es
    la señal, y normalizarla la destruye. Se marca aparte para poder contarla."""
    v = verificar(afirmacion("La sesion se almacena en el servidor"), CONTEXTO)
    assert v["veredicto"] == DEGRADADA
    assert v["solo_tildes"] is True, "no se distingue reescritura de invencion"


# --- que no reviente, que un verificador que lanza convierte una poda en un 500 -------------------

@pytest.mark.parametrize("cita", ["", "   ", None])
def test_una_cita_vacia_degrada_en_vez_de_reventar(cita):
    v = verificar({"tipo": "literal", "cita": cita, "fragmento_id": 7}, CONTEXTO)
    assert v["veredicto"] == DEGRADADA and v["motivo"] == "sin_cita"


def test_el_nivel_por_defecto_es_el_que_el_barrido_dejo():
    """Ancla la DECISIÓN, no el valor: si alguien añade un paso de normalización, este test le
    recuerda que la carga de la prueba es suya y que hay una medida que consultar."""
    assert NIVEL_POR_DEFECTO == "espacios", (
        "cambio el nivel de normalizacion por defecto. Cada paso que se añade cambia un falso "
        "negativo por un falso positivo, y en un verificador el falso positivo es el caro: "
        "re-corre scripts/barrer_normalizacion.py y demuestra que el paso nuevo compra algo")
    assert NIVEL_POR_DEFECTO in NIVELES