"""Tests del mobiliario de pagina (arreglo del 1.3 tras el muestreo a mano).

Las dos direcciones, que es lo que pide el principio 6:
  - se lleva los numeros de pagina y las viñetas mal convertidas (lo que se le escapaba al filtro
    por frecuencia, que no puede verlos porque cada numero de pagina es una linea distinta);
  - y NO se lleva una lista numerada de verdad, ni un titulo que acaba en numero.

Importa mas de lo que parece: una cita literal con "- 8 -" dentro se ve en pantalla el dia de la
demo, y la fidelidad de la cita es justo lo que enseñamos.
"""
from pathlib import Path

import mobiliario as mb
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sin_corpus = pytest.mark.skipif(not (RAIZ / "corpus" / "daw").exists(),
                                reason="necesita el corpus local (ADR 0001)")


def test_se_va_el_numero_de_pagina_en_sus_varias_formas():
    for linea in ("- 8 -", "8", "  – 12 – ", "8 / 24", "Pág. 8", "Tema 3 - 13 -"):
        assert mb.es_mobiliario(linea), linea


def test_no_se_va_lo_que_dice_algo():
    """El control negativo. "Windows 10 - 2" es un titulo, no un pie: por eso el pie exige el
    guion de cierre."""
    for linea in ("Windows 10 - 2", "1. Introduccion a Java", "- 8 - bits por caracter",
                  "El resultado es 8", "Unidad 3", "9. concat() devuelve dos cadenas"):
        assert not mb.es_mobiliario(linea), linea


def test_el_corte_de_pagina_pegado_a_la_frase_tambien_se_va():
    texto = "las operaciones de los demas usuarios. - 4 - 2.- Edicion de la informacion"
    assert mb.quitar_pagina_pegada(texto) == \
        "las operaciones de los demas usuarios. 2.- Edicion de la informacion"


def test_el_glifo_de_vineta_se_sustituye_solo_si_se_repite():
    """El "9" de la viñeta Wingdings que el extractor convierte en digito. La condicion de que sea
    EL MISMO digito al menos tres veces es lo que salva a una lista numerada: esa gasta cada
    numero una vez y ademas escribe "9." o "9)"."""
    vineta = "\n".join(f"9 funcion{i}(), devuelve algo" for i in range(4))
    assert "- funcion0()" in mb.glifo_de_vineta(vineta)
    assert "9 funcion" not in mb.glifo_de_vineta(vineta)


def test_una_lista_numerada_de_verdad_sobrevive():
    lista = "1 Introduccion\n2 Desarrollo\n3 Conclusiones\n9 Bibliografia"
    assert mb.glifo_de_vineta(lista) == lista
    con_puntos = "9. concat()\n9. sum()\n9. string-length()"
    assert mb.glifo_de_vineta(con_puntos) == con_puntos


def test_dos_apariciones_no_bastan():
    """La mutacion del umbral: con dos, el texto tiene que quedarse igual."""
    dos = "9 concat(), devuelve dos cadenas\n9 sum(), devuelve la suma"
    assert mb.glifo_de_vineta(dos) == dos


def test_un_retorno_de_carro_suelto_es_una_linea_para_todo_el_mundo():
    r"""El falso verde que descubrio el propio arreglo: con "\r" dentro, el limpiador veia una
    linea larga y el troceador -que lee en modo texto- veia dos, con el numero de pagina en medio.
    """
    texto = "Fin de la explicacion.\r 8 \rSigue el contenido del tema."
    limpio = mb.limpiar(texto)
    assert "8" not in limpio.replace("Fin", "")
    assert limpio.split("\n") == ["Fin de la explicacion.", "Sigue el contenido del tema."]


def test_limpiar_es_idempotente():
    texto = "Contenido del tema.\n- 8 -\nSigue el contenido. - 9 - y mas texto.\n"
    una = mb.limpiar(texto)
    assert mb.limpiar(una) == una
    assert "- 8 -" not in una and "Contenido del tema." in una


@sin_corpus
def test_el_corpus_derivado_de_pdf_ya_no_trae_mobiliario():
    """Anclado al corpus real: 3.329 ocurrencias en 2.448 fragmentos antes del arreglo.

    Solo los derivados de PDF, que es de donde sale el mobiliario de pagina. Queda declarado el
    unico resto: mi_proyecto_personal.docx.md tiene 102 lineas que son un numero suelto, pero son
    los puntos de una lista de Word, no numeros de pagina, y ese documento ademas esta en la lista
    manual de exclusion (trabajo de alumno), asi que no entra al indice.
    """
    quedan = []
    for ruta in (RAIZ / "corpus" / "derivado").rglob("*.pdf.md"):
        for linea in ruta.read_text(encoding="utf-8").split("\n"):
            if mb.es_mobiliario(linea):
                quedan.append((ruta.name, linea))
    assert not quedan[:5], f"{len(quedan)} lineas de mobiliario siguen en el derivado de PDF"
