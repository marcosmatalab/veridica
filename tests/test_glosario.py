"""La validación del glosario (encargo 2.6), que es la pieza de la que depende que sea citable.

Aquí no hay ningún modelo, y esa es la propiedad que se prueba: quien valida es una comparación de
cadenas, así que no comparte supuesto con el modelo que extrajo (principio 6). Si algún día alguien
mete un modelo en este lazo, estos tests son los que tienen que empezar a hablar de otra cosa.
"""
import pytest

from app.modelos.glosario import (ContratoDeGlosarioRoto, esquema_de_extraccion, leer_entrada,
                                  normalizar, validar_literal)

FRAGMENTO = ("## 4.2 Cookies\n\nUna cookie es un fichero de texto que un sitio web guarda en el "
             "entorno   del usuario del navegador.\nSe usan para mantener la sesión.")


def test_una_definicion_copiada_letra_a_letra_pasa():
    pasa, evidencia = validar_literal(
        "Una cookie es un fichero de texto que un sitio web guarda en el entorno del usuario del "
        "navegador.", FRAGMENTO)
    assert pasa and "posicion" in evidencia


def test_una_definicion_reescrita_no_pasa():
    """LA DIRECCIÓN QUE IMPORTA. El modelo tiende a "mejorar" lo que copia, y una definición
    mejorada ya no es lo que dice el temario: es lo que el modelo cree que dice."""
    pasa, motivo = validar_literal(
        "Una cookie es un archivo de texto que una web guarda en el navegador del usuario.",
        FRAGMENTO)
    assert not pasa and motivo == "no aparece en el fragmento"


def test_una_palabra_cambiada_tampoco_pasa():
    """Sin umbral y sin porcentaje de parecido: o está o no está. Es la misma regla que la sección 8
    le exige a una afirmación `literal`, y por el mismo motivo."""
    pasa, _ = validar_literal(
        "Una cookie es un fichero de texto que un sitio web guarda en el ordenador del usuario del "
        "navegador.", FRAGMENTO)
    assert not pasa


def test_los_espacios_de_mas_no_rompen_la_comparacion():
    """El corpus viene de conversiones de PDF: un doble espacio no es una diferencia de contenido."""
    pasa, _ = validar_literal("guarda en el entorno del usuario", FRAGMENTO)
    assert pasa


def test_las_tildes_se_conservan_y_distinguen():
    """"cómo" y "como" no son la misma palabra. Un validador que las iguale acepta citas que no lo
    son, y este validador es lo único que separa el glosario de la invención."""
    assert normalizar("Sesión") == "sesión"
    assert normalizar("Sesión") != normalizar("Sesion")
    pasa, _ = validar_literal("Se usan para mantener la sesion.", FRAGMENTO)
    assert not pasa, "sin tilde no es la misma cadena: no puede pasar"


def test_la_e_acentuada_compuesta_y_la_precompuesta_se_tratan_igual():
    """Las dos se ven idénticas en pantalla y son cadenas distintas. Sin normalizar la forma
    Unicode, el validador rechazaría citas correctas y nadie entendería por qué."""
    combinante = "Se usan para mantener la sesión."
    assert validar_literal(combinante, FRAGMENTO)[0]


def test_una_definicion_vacia_no_cuela():
    pasa, motivo = validar_literal("   ", FRAGMENTO)
    assert not pasa and motivo == "definicion vacia"


def test_el_contrato_de_extraccion_es_estricto():
    esquema = esquema_de_extraccion()["json_schema"]["schema"]
    assert esquema["additionalProperties"] is False
    assert set(esquema["required"]) == set(esquema["properties"])
    assert set(esquema["properties"]) == {"termino", "definicion", "hay_definicion"}


def test_el_modelo_puede_decir_que_ahi_no_hay_definicion():
    """Sin esta salida, el modelo se inventa una definición para cualquier trozo de prosa: es el
    mismo problema que tenía marcar el fragmento entero como definición (3 aciertos de 20)."""
    entrada = leer_entrada({"termino": "-", "definicion": "-", "hay_definicion": "no"})
    assert entrada.hay_definicion == "no"


def test_el_guion_de_esa_salida_no_puede_contarse_como_contrato_roto():
    """SALIÓ ESCRIBIENDO ESTE TEST, y es de las que no se ven al leer el código: el contrato tenía
    `min_length` en los dos campos, así que la respuesta correcta "aquí no se define nada" —con un
    guion en ambos— habría reventado la validación y se habría contado como CONTRATO ROTO. Dos
    cubos de descarte distintos intercambiándose casos en silencio, y esos cubos son los que
    deciden si este encargo va con la versión A o la B de la demo."""
    entrada = leer_entrada({"termino": "-", "definicion": "-", "hay_definicion": "no"})
    assert entrada.termino == "-" and entrada.definicion == "-"


def test_una_respuesta_sin_los_campos_del_contrato_se_rechaza():
    with pytest.raises(ContratoDeGlosarioRoto):
        leer_entrada({"termino": "cookie"})
