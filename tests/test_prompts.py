"""Los prompts por modo del 4.1, y lo que NO puede desaparecer de ellos sin que nadie se entere.

Un prompt no tiene test de comportamiento —lo que el modelo haga con él es del modelo—, así que lo
que se puede anclar es **lo que el prompt DICE**. Y merece anclarse porque las cláusulas duras del
modo `acompanar` son **la pedagogía del proyecto escrita en código** (sección 3): si alguien
"simplifica" el prompt y se lleva por delante *"nunca des el resultado"*, el sistema seguirá
respondiendo, seguirá validando el contrato y seguirá pasando toda la suite — resolviéndole el
ejercicio al alumno, que es exactamente lo que el modo existe para no hacer.
"""
import pytest

from app.core.prompts import COMUN, MODOS_CONSTRUIDOS, POR_MODO, VERSION, sistema, version


def test_los_tres_modos_construidos_y_examinar_NO():
    """`examinar` está DISEÑADO Y NO CONSTRUIDO en la sección 3, con su nota del AI Act. Darle un
    prompt sería construirlo por la puerta de atrás, y el primer sitio donde este proyecto no puede
    afirmar en presente lo no construido es su propio código."""
    assert set(MODOS_CONSTRUIDOS) == {"responder", "acompanar", "corregir"}
    assert "examinar" not in POR_MODO


@pytest.mark.parametrize("modo", MODOS_CONSTRUIDOS)
def test_todos_los_modos_llevan_las_clausulas_comunes(modo):
    """Las obligatorias de la guía: solo desde los fragmentos, cada tipo con su forma, y la prosa
    sin decir nada que no esté en las afirmaciones."""
    s = sistema(modo)
    assert "Responde SOLO desde ellos" in s
    assert "'literal'" in s and "'parafrasis'" in s and "'conocimiento'" in s
    assert "no puede decir nada que no esté en las afirmaciones" in s


def test_las_REGLAS_DURAS_de_acompanar_estan_en_el_prompt():
    """LA PEDAGOGÍA ESCRITA EN CÓDIGO. Sin estas líneas el modo `acompanar` es `responder` con otro
    nombre, y ningún otro test del repo se pondría rojo por ello.

    **HUECO DECLARADO, y no se cubre pretendiendo lo contrario: esto ancla que la CLÁUSULA está, no
    que el COMPORTAMIENTO se cumpla.** Un prompt que conserve la frase y aun así suelte la solución
    pasaría aquí en verde. La otra mitad es el conjunto `fuga_de_solucion` del 1.10, que mide el
    efecto sobre casos reales y lo debe el propietario. Hasta entonces el modo está cubierto en su
    declaración y NO en su comportamiento."""
    s = sistema("acompanar")
    assert "NUNCA des el resultado final" in s
    assert "MÁXIMO UNA PISTA por turno" in s
    assert "tres veces" in s, "falta la salida del bucle: ofrecer cambiar a modo responder"
    assert "andamiaje" in s


def test_corregir_lleva_el_resultado_como_ORACULO_y_su_salida_honesta():
    """Sección 3: con solo el resultado, el resultado manda; y si no hay camino desde el temario
    hasta ese número, se DICE en vez de forzar la derivación para que cuadre."""
    s = sistema("corregir")
    assert "oráculo" in s
    assert "quizá el resultado está mal" in s
    assert "No fuerces la derivación" in s


def test_un_modo_desconocido_cae_a_responder_en_vez_de_quedarse_sin_prompt():
    """Un prompt vacío por un modo mal escrito daría una respuesta sin ninguna cláusula: el sistema
    seguiría contestando y habría perdido TODAS las reglas a la vez, en silencio."""
    s = sistema("modo-que-no-existe")
    assert "MODO RESPONDER" in s
    assert version("modo-que-no-existe").endswith("/responder")


def test_la_confianza_se_le_DICE_pero_no_se_le_deja_escribir():
    """ADR 0014: el campo salió del esquema porque es un hecho de la recuperación que el modelo no
    puede conocer. Aquí se le dice para que ajuste su comportamiento, y se le recuerda que no es
    suyo — que es la mitad que evita que lo cuele en la prosa como si lo hubiera medido él."""
    s = sistema("responder", contexto=True, confianza="baja")
    assert "confianza 'baja'" in s and "NO va en el JSON" in s
    assert "confianza" not in sistema("responder", contexto=False)


def test_la_version_distingue_los_MODOS_y_no_solo_la_fecha():
    """Dos modos son dos prompts. Guardar solo `4.1` en la traza haría imposible saber con cuál
    salió una respuesta, que es justo para lo que sirve el campo."""
    assert version("acompanar") != version("responder")
    assert version("acompanar").startswith(VERSION)


def test_el_prompt_NO_pide_lo_que_la_GRAMATICA_ya_impone():
    """Principio 7 aplicado al propio prompt: pedir por prompt algo que el esquema puede prohibir es
    pedir un favor. El tope de la cita lo pone `maxLength` y la referencia con F la pone `pattern`;
    el prompt los EXPLICA para que el modelo colabore, pero no son su responsabilidad.

    Lo que sí se comprueba es que no haya crecido con reglas de forma que el esquema ya cubre: cada
    línea de más aquí se paga en prefill EN CADA CONSULTA."""
    assert len(COMUN) <= 12, (
        "el prompt comun ha crecido: comprueba si lo nuevo lo puede imponer el json_schema, que es "
        "gratis en tokens y ademas no se puede desobedecer")