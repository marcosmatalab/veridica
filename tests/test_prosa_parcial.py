"""El extractor incremental de prosa (encargo 2.2).

De este modulo depende que el TTFT del alumno sea distinto del total, o sea que el streaming compre
algo. Se prueba con el flujo TROCEADO A UN CARACTER, que es el peor caso real: el proveedor parte
donde quiere, incluido en mitad de un escape.
"""
import json

import pytest

from app.core.prosa_parcial import ProsaEnCurso

PROSA = 'Hola "mundo"\nsegunda línea, con acentos y un emoji \U0001f600 al final.'

OBJETO = {
    "modo": "responder",
    "afirmaciones": [{"id": 1, "tipo": "literal", "texto": "t", "fragmento_id": 3,
                      "cita": 'el campo "respuesta_redactada": "TRAMPA" del contrato'}],
    "respuesta_redactada": PROSA,
    "siguiente_paso": {"tipo": "pregunta_al_alumno", "ref": None,
                       "texto": 'y aqui otra "respuesta_redactada": "TRAMPA"'},
}


def alimentar(crudo: str, tam: int) -> tuple:
    p = ProsaEnCurso()
    salida = "".join(p.alimentar(crudo[i:i + tam]) for i in range(0, len(crudo), tam))
    return salida, p


@pytest.mark.parametrize("ensure_ascii", [True, False])
@pytest.mark.parametrize("tam", [1, 2, 3, 7, 64, 100000])
def test_saca_la_prosa_entera_partan_el_flujo_donde_lo_partan(tam, ensure_ascii):
    salida, p = alimentar(json.dumps(OBJETO, ensure_ascii=ensure_ascii), tam)
    assert salida == PROSA
    assert p.terminada


def test_no_pica_con_la_clave_dentro_de_otro_valor():
    """LA RAZON DE QUE ESTO NO SEA UNA EXPRESION REGULAR. `"respuesta_redactada"` aparece dentro de
    una `cita` y dentro del `siguiente_paso`. Un buscador de subcadenas emitiria 'TRAMPA' como si
    fuera la respuesta al alumno; el automata sabe que esta dentro de una cadena y no de una clave.
    """
    salida, _ = alimentar(json.dumps(OBJETO), 1)
    assert "TRAMPA" not in salida


def test_la_clave_a_profundidad_dos_no_cuenta():
    """La prosa del alumno es la del objeto raiz. Una clave con el mismo nombre dentro de un objeto
    anidado no es esa, y emitirla seria mezclar dos cosas distintas."""
    anidado = {"afirmaciones": [{"respuesta_redactada": "NO ES ESTA"}],
               "respuesta_redactada": "esta si"}
    salida, _ = alimentar(json.dumps(anidado), 1)
    assert salida == "esta si"


def test_los_escapes_partidos_entre_dos_trozos_no_salen_a_pantalla_a_medias():
    """Un `\\u00e9` cortado por la mitad no puede emitirse como `\\u00`: el alumno veria basura."""
    crudo = '{"respuesta_redactada": "caf\\u00e9 y ni\\u00f1o"}'
    p = ProsaEnCurso()
    trozos = [p.alimentar(crudo[i:i + 1]) for i in range(len(crudo))]
    assert "".join(trozos) == "café y niño"
    assert all(t == "" or t.isprintable() for t in trozos)


def test_un_par_suplente_partido_sale_como_un_solo_caracter():
    crudo = '{"respuesta_redactada": "fin \\ud83d\\ude00"}'
    salida, _ = alimentar(crudo, 1)
    assert salida == "fin \U0001f600"


def test_mientras_no_llega_la_prosa_no_emite_nada():
    """Si emitiera antes, el alumno veria llaves y comillas, que es la otra salida deshonesta."""
    p = ProsaEnCurso()
    cabeza = '{"modo": "responder", "afirmaciones": [{"id": 1, "tipo": "conocimiento",'
    assert p.alimentar(cabeza) == ""
    assert not p.empezada


def test_un_json_cortado_a_media_prosa_no_se_da_por_terminado():
    """El caso del tope de max_tokens: hay prosa emitida pero el objeto nunca cierra. El extractor
    NO puede decir que termino, porque quien lo llama decide abstenerse justo por eso."""
    salida, p = alimentar('{"respuesta_redactada": "empieza y se corta', 1)
    assert salida == "empieza y se corta"
    assert p.empezada and not p.terminada
