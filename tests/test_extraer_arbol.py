"""Tests anclados del extractor del arbol oficial (encargo 1.1).

Se fabrica un PDF de JUGUETE con la forma del BOE (fpdf2) y se pasa por la tuberia real, pypdf
incluido. Asi los tests entran en CI sin necesidad de los PDF del BOE ni del corpus.

El caso anclado es el primero: cuando un salto de pagina mete la cabecera del BOE entre el nombre
del modulo y su codigo, el modulo tiene que extraerse igual. Ese fallo era real y silencioso: por
el, el modulo 0483 de DAM se leia del RD de 2010 en vez de su actualizacion de 2023, y nadie se
habria enterado mirando el fichero de salida.
"""
import importlib.util
from pathlib import Path

import pytest
from fpdf import FPDF

RAIZ = Path(__file__).resolve().parents[1]


def cargar_extractor():
    ruta = RAIZ / "scripts" / "extraer_arbol.py"
    spec = importlib.util.spec_from_file_location("extraer_arbol", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


ex = cargar_extractor()

CABECERA_BOE = ["BOLETIN OFICIAL DEL ESTADO",
                "Num. 132 Sabado 3 de junio de 2023 Sec. I.   Pag. 79006",
                "cve: BOE-A-2023-13221"]

ARTICULADO = ["Articulo 11. Modulos profesionales.",
              "Son los que a continuacion se relacionan:",
              "0483 Sistemas informaticos.",
              "0484 Bases de datos."]

MODULO_PARTIDO = ["Modulo Profesional: Sistemas informaticos.",
                  "Equivalencia en creditos ECTS: 10."]

RESTO_DEL_MODULO = [
    "Codigo: 0483.",
    "Resultados de aprendizaje y criterios de evaluacion.",
    "1. Evalua sistemas informaticos identificando sus componentes.",
    "Criterios de evaluacion:",
    "a) Se han reconocido los componentes.",
    "Contenidos basicos:",
    "Explotacion de sistemas microinformaticos:",
    "- Hardware de un sistema.",
    "- Arquitecturas.",
    "Instalacion de software libre y propietario:",
    "- Tipos de licencia.",
]

MODULO_ENTERO = [
    "ANEXO I",
    "Modulo Profesional: Bases de datos.",
    "Codigo: 0484.",
    "Resultados de aprendizaje y criterios de evaluacion.",
    "1. Reconoce los elementos de las bases de datos analizando sus funciones.",
    "Criterios de evaluacion:",
    "a) Se han analizado los sistemas logicos.",
    "Contenidos basicos:",
    "Almacenamiento de la informacion:",
    "- Ficheros planos e indexados.",
]


def escribir_pdf(destino: Path, paginas: list) -> str:
    pdf = FPDF()
    pdf.set_font("helvetica", size=9)
    for lineas in paginas:
        pdf.add_page()
        for linea in lineas:
            pdf.cell(0, 5, linea, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(destino))
    return str(destino)


@pytest.fixture
def pdf_de_juguete(tmp_path):
    """Dos paginas: el primer modulo queda PARTIDO por la cabecera del BOE, como en el real."""
    return escribir_pdf(tmp_path / "boe.pdf", [
        ARTICULADO + MODULO_ENTERO,
        MODULO_PARTIDO + CABECERA_BOE,
        RESTO_DEL_MODULO,
    ])


def modulos_del(pdf: str) -> dict:
    texto, indice = ex.texto_con_paginas(ex.paginas_de(pdf))
    return ex.modulos_de(texto, indice, ex.RE_BLOQUE_RD), texto


def test_extrae_el_modulo_aunque_la_cabecera_del_boe_parta_el_bloque(pdf_de_juguete):
    """EL caso anclado: nombre en una pagina, codigo en la siguiente, cabecera del BOE en medio."""
    modulos, _ = modulos_del(pdf_de_juguete)
    assert set(modulos) == {"0483", "0484"}
    assert modulos["0483"]["nombre"] == "Sistemas informaticos"


def test_las_unidades_salen_de_los_bloques_de_contenido(pdf_de_juguete):
    modulos, _ = modulos_del(pdf_de_juguete)
    nombres = [n for n, _ in modulos["0483"]["unidades"]]
    assert nombres == ["Explotacion de sistemas microinformaticos",
                       "Instalacion de software libre y propietario"]


def test_los_resultados_de_aprendizaje_salen_limpios(pdf_de_juguete):
    modulos, _ = modulos_del(pdf_de_juguete)
    assert modulos["0484"]["resultados"] == [
        "Reconoce los elementos de las bases de datos analizando sus funciones"]


def test_cada_nodo_sabe_de_que_pagina_sale(pdf_de_juguete):
    modulos, _ = modulos_del(pdf_de_juguete)
    assert modulos["0484"]["pagina"] == 1
    assert modulos["0483"]["pagina"] == 2


def test_el_cruce_con_el_articulado_detecta_un_modulo_que_falta(pdf_de_juguete):
    """La lista del articulado es otra parte del documento: si no cuadra con lo extraido, el
    extractor se ha dejado algo. Sin este cruce, un modulo perdido pasaria en silencio."""
    _, texto = modulos_del(pdf_de_juguete)
    declarados = ex.codigos_del_articulado(texto)
    assert declarados == {"0483", "0484"}
    assert declarados - {"0484"} == {"0483"}, "el cruce debe delatar el modulo que falta"


MODULO_CON_PUNTO = [
    "ANEXO I",
    "Modulo profesional: Seguridad y alta disponibilidad.",
    "Codigo: 0378.",
    "Contenidos basicos.",                      # con PUNTO, no con dos puntos: asi lo escribe el BOE
    "Adopcion de pautas de seguridad informatica:",
    "- Fiabilidad, confidencialidad, integridad.",
    "Implantacion de mecanismos de seguridad activa:",
    "- Ataques y contramedidas.",
    "Orientaciones pedagogicas.",
    "La funcion de seguridad incluye aspectos como:",   # esto NO es una unidad
    "- No debe salir en el arbol.",
]


def test_un_encabezado_de_contenidos_con_punto_no_deja_el_modulo_mudo(tmp_path):
    """El BOE escribe 'Contenidos basicos:' y tambien 'Contenidos basicos.'. Exigir los dos puntos
    dejaba sin unidades a modulos enteros (ASIR 0378, DAM 0489 y 0490) sin que nada avisara."""
    pdf = escribir_pdf(tmp_path / "punto.pdf", [MODULO_CON_PUNTO])
    modulos, _ = modulos_del(pdf)
    nombres = [n for n, _ in modulos["0378"]["unidades"]]
    assert nombres == ["Adopcion de pautas de seguridad informatica",
                       "Implantacion de mecanismos de seguridad activa"]
    assert modulos["0378"]["declara_contenidos"] is True


def test_las_orientaciones_pedagogicas_no_cuelan_frases_como_unidades(tmp_path):
    pdf = escribir_pdf(tmp_path / "punto.pdf", [MODULO_CON_PUNTO])
    modulos, _ = modulos_del(pdf)
    assert all("incluye aspectos" not in n for n, _ in modulos["0378"]["unidades"])


def test_un_modulo_que_declara_contenidos_y_no_da_unidades_se_denuncia():
    """La comprobacion que hasta ahora hacia una persona mirando la tabla a ojo."""
    ex_modulos = {
        "asir": {
            "0378": {"declara_contenidos": True, "unidades": []},          # el extractor fallo
            "0379": {"declara_contenidos": False, "unidades": []},         # la norma no da nada
            "0369": {"declara_contenidos": True, "unidades": [("x", 1)]},  # bien
        }
    }
    assert ex.modulos_mudos(ex_modulos) == [("asir", "0378")]


def test_el_mobiliario_del_boe_no_acaba_dentro_de_los_textos(pdf_de_juguete):
    _, texto = modulos_del(pdf_de_juguete)
    assert "BOLETIN OFICIAL" not in texto
    assert "cve: BOE" not in texto
