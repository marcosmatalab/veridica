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


# ---------------------------------------------------------------------------------------------
# Nombres cortados y unidades perdidas.
#
# Los encontro un muestreo A MANO de diez nodos: el 0373 decia "...sistemas de gestion de" y la
# norma dice "...de informacion". El cruce de codigos que ya existia daba ese modulo por bueno,
# porque el codigo era correcto y solo faltaba una palabra del nombre. De tirar del hilo salieron
# cuatro nombres truncados y ocho unidades que no estaban, por dos mecanismos distintos:
# el salto de linea y los dos puntos internos.
# ---------------------------------------------------------------------------------------------

MODULO_CON_NOMBRE_PARTIDO = [
    "ANEXO I",
    "Modulo Profesional: Lenguajes de marcas y sistemas de gestion de ",
    "informacion.",
    "Equivalencia en creditos ECTS: 7.",
    "Codigo: 0373.",
    "Contenidos basicos:",
    "Reconocimiento de las caracteristicas de lenguajes de marcas:",
    "- Clasificacion.",
]


def test_un_nombre_de_modulo_partido_en_dos_lineas_sale_entero(tmp_path):
    """El fallo real: el BOE parte el nombre a mitad y [^\\n] no cruza el salto. El modulo se
    extraia igual, con su codigo bien, y solo le faltaba la ultima palabra: por eso nadie lo vio."""
    pdf = escribir_pdf(tmp_path / "partido.pdf", [MODULO_CON_NOMBRE_PARTIDO])
    modulos, _ = modulos_del(pdf)
    assert modulos["0373"]["nombre"] == "Lenguajes de marcas y sistemas de gestion de informacion"


def test_un_nombre_de_modulo_de_una_linea_no_se_traga_la_linea_siguiente(pdf_de_juguete):
    """La otra direccion, que es donde un arreglo perezoso rompe todo lo demas: si el nombre ya
    esta completo, la continuacion NO debe activarse y comerse 'Equivalencia en creditos ECTS'."""
    modulos, _ = modulos_del(pdf_de_juguete)
    assert modulos["0483"]["nombre"] == "Sistemas informaticos"
    assert modulos["0484"]["nombre"] == "Bases de datos"


MODULO_CON_UNIDADES_DIFICILES = [
    "ANEXO I",
    "Modulo profesional: Administracion de sistemas.",
    "Codigo: 0377.",
    "Contenidos basicos:",
    # dos puntos DENTRO del encabezado, y a mitad de linea: la unidad desaparecia entera
    "Automatizacion de tareas: construccion de guiones de administracion:",
    "- Herramientas para creacion de guiones.",
    # encabezado partido en dos lineas: la unidad desaparecia entera
    "Cumplimiento de las normas de prevencion de riesgos laborales y proteccion ",
    "ambiental:",
    "- Identificacion de riesgos.",
    # elemento de lista acabado en punto, y debajo un encabezado ENTERO: no se fusionan
    "- VLAN. Etiquetado de tramas.",
    "IEEE802.1Q.",
    "Configuracion y administracion de protocolos dinamicos:",
    "- Protocolos de encaminamiento.",
]


def test_una_unidad_con_dos_puntos_dentro_del_nombre_no_se_pierde(tmp_path):
    """Con [^\\n:] el corte caia en el PRIMER ':', no en el que cierra el encabezado. Si los dos
    puntos internos van a mitad de linea, el encabezado no casaba y la unidad no existia."""
    pdf = escribir_pdf(tmp_path / "dificiles.pdf", [MODULO_CON_UNIDADES_DIFICILES])
    modulos, _ = modulos_del(pdf)
    nombres = [n for n, _ in modulos["0377"]["unidades"]]
    assert "Automatizacion de tareas: construccion de guiones de administracion" in nombres


def test_una_unidad_con_el_encabezado_partido_en_dos_lineas_no_se_pierde(tmp_path):
    pdf = escribir_pdf(tmp_path / "dificiles.pdf", [MODULO_CON_UNIDADES_DIFICILES])
    modulos, _ = modulos_del(pdf)
    nombres = [n for n, _ in modulos["0377"]["unidades"]]
    assert ("Cumplimiento de las normas de prevencion de riesgos laborales y proteccion ambiental"
            in nombres)


def test_un_elemento_de_lista_acabado_en_punto_no_se_fusiona_con_el_encabezado(tmp_path):
    """El guardian del arreglo, y el unico caso que el propio arreglo rompio al escribirlo: el
    texto envuelto se parte a media frase y NUNCA termina en punto. Sin esa condicion, ASIR 0370
    salia como 'IEEE802.1Q. Configuracion y administracion de protocolos dinamicos', un nodo
    inventado que ninguna norma dice. Lo caza el diff de la re-extraccion, no el verde."""
    pdf = escribir_pdf(tmp_path / "dificiles.pdf", [MODULO_CON_UNIDADES_DIFICILES])
    modulos, _ = modulos_del(pdf)
    nombres = [n for n, _ in modulos["0377"]["unidades"]]
    assert "Configuracion y administracion de protocolos dinamicos" in nombres
    assert all("IEEE802.1Q" not in n for n in nombres)


# La Orden de curriculo numera sus bloques con "a)", "b)"..., asi que lleva OTRO patron. Se prueba
# aparte a proposito: al mutar el patron de la Orden al viejo, la suite seguia en verde con los
# tests de arriba, porque ninguno lo tocaba. Y de la Orden salen justo el nombre truncado de
# DAW 0612 y las dos unidades perdidas de DAW 0616.
MODULO_DE_LA_ORDEN = [
    "10. Modulo Profesional: Desarrollo web en entorno cliente",
    "Codigo: 0612",
    "Contenidos:",
    # dos puntos DENTRO del nombre, y el que cierra al final de la linea: salia truncado
    "e) Interaccion con el usuario: eventos y formularios:",
    "Modelo de eventos.",
    # encabezado partido en dos lineas: la unidad no existia
    "f) Identificacion de necesidades del sector productivo y de la ",
    "organizacion de la empresa:",
    "Identificacion de las funciones de los puestos de trabajo.",
]


def unidades_de_la_orden(pdf: str) -> list:
    texto, indice = ex.texto_con_paginas(ex.paginas_de(pdf))
    modulos = ex.modulos_de(texto, indice, ex.RE_BLOQUE_ORDEN)
    return [n for n, _ in modulos["0612"]["unidades"]]


def test_en_la_orden_un_nombre_con_dos_puntos_dentro_no_sale_truncado(tmp_path):
    """DAW 0612 decia 'Interaccion con el usuario' y la Orden dice '...: eventos y formularios'.
    Termina en sustantivo, asi que buscar nombres acabados en preposicion no lo encontraba."""
    pdf = escribir_pdf(tmp_path / "orden.pdf", [MODULO_DE_LA_ORDEN])
    assert "Interaccion con el usuario: eventos y formularios" in unidades_de_la_orden(pdf)


def test_en_la_orden_un_encabezado_partido_en_dos_lineas_no_se_pierde(tmp_path):
    pdf = escribir_pdf(tmp_path / "orden.pdf", [MODULO_DE_LA_ORDEN])
    assert ("Identificacion de necesidades del sector productivo y de la organizacion de la empresa"
            in unidades_de_la_orden(pdf))


# ---------------------------------------------------------------------------------------------
# La puerta permanente: el nombre extraido contra el nombre que la norma da en su ARTICULADO.
# Es lo unico que NO comparte patron con el parser (principio 6), asi que es lo que puede cazar
# el siguiente fallo de esta familia.
# ---------------------------------------------------------------------------------------------

def test_el_cruce_de_nombres_delata_un_nombre_cortado():
    """Sano y mutado: el mismo cruce tiene que callar con el nombre entero y gritar con el
    cortado. Un detector que solo se prueba en verde no ha demostrado que detecte nada."""
    articulado = "0373 Lenguajes de marcas y sistemas de gestion de informacion.\nANEXO I\n"
    textos = {"daw": articulado, "dam": articulado, "asir": articulado}
    entero = [{"nivel": "asignatura", "titulacion": "daw", "codigo": "0373",
               "nombre": "Lenguajes de marcas y sistemas de gestion de informacion"}]
    cortado = [dict(entero[0], nombre="Lenguajes de marcas y sistemas de gestion de")]

    assert ex.discrepancias_de_nombre(entero, textos) == ([], [])
    nuevas, conocidas = ex.discrepancias_de_nombre(cortado, textos)
    assert conocidas == []
    assert [(c, cod) for c, cod, _, _ in nuevas] == [("daw", "0373")]


def test_el_cruce_de_nombres_no_confunde_mayusculas_con_un_hallazgo():
    """El BOE alterna 'Lenguajes de Marcas' y 'Lenguajes de marcas' para el mismo modulo. Si eso
    saliera como hallazgo, la puerta se volveria ruido y se acabaria ignorando."""
    textos = {c: "0373 Lenguajes de marcas y sistemas de gestion de informacion.\nANEXO I\n"
              for c in ("daw", "dam", "asir")}
    nodos = [{"nivel": "asignatura", "titulacion": "asir", "codigo": "0373",
              "nombre": "Lenguajes de Marcas y Sistemas de Gestion de Informacion"}]
    assert ex.discrepancias_de_nombre(nodos, textos) == ([], [])


def test_una_contradiccion_declarada_de_la_norma_no_cuenta_como_fallo_del_extractor():
    """ASIR 0372: el Anexo I dice 'Gestion de Base de Datos' y el articulado de la MISMA norma
    dice 'Gestion de bases de datos'. El BOE se contradice consigo mismo. Eso se anota, no se
    corrige, y no puede teñir de rojo una corrida sana... pero tampoco desaparecer del informe."""
    textos = {c: "0372 Gestion de bases de datos.\nANEXO I\n" for c in ("daw", "dam", "asir")}
    nodos = [{"nivel": "asignatura", "titulacion": "asir", "codigo": "0372",
              "nombre": "Gestion de Base de Datos"}]
    nuevas, conocidas = ex.discrepancias_de_nombre(nodos, textos)
    assert nuevas == []
    assert [(c, cod) for c, cod, _, _ in conocidas] == [("asir", "0372")]


MODULO_CON_CONTENIDOS_ENVUELTO = [
    "ANEXO I",
    "Modulo profesional: Lenguajes de marcas.",
    "Codigo: 0373.",
    "Resultados de aprendizaje y criterios de evaluacion.",
    "1. Reconoce las caracteristicas de lenguajes de marcas.",
    "Criterios de evaluacion:",
    "i) Se han identificado las tecnologias en que se basa la sindicacion de ",
    "contenidos.",                       # NO es el encabezado: es una frase que ha envuelto
    # el falso encabezado va en el PRIMER resultado de aprendizaje, como en el PDF real, para que
    # abrir la seccion ahi se lleve por delante los criterios de los que vienen detras
    "2. Utiliza lenguajes de marcas en entornos web.",
    "Criterios de evaluacion:",
    "a) Se han identificado los estandares.",
    "Contenidos basicos:",               # este si
    "Almacenamiento de informacion:",
    "- Ficheros planos.",
]


def test_la_palabra_contenidos_envuelta_no_abre_la_seccion_antes_de_tiempo(tmp_path):
    """'...la sindicacion de \\ncontenidos.' dejaba la palabra sola a principio de linea y abria la
    seccion decenas de lineas antes, dentro de los criterios de evaluacion. La misma familia que
    los nombres cortados: el salto de linea inventando un encabezado donde solo hay una frase."""
    pdf = escribir_pdf(tmp_path / "envuelto.pdf", [MODULO_CON_CONTENIDOS_ENVUELTO])
    texto, _ = ex.texto_con_paginas(ex.paginas_de(pdf))
    cuerpo = texto[texto.index("Codigo: 0373"):]
    desde, _ = ex.seccion_de_contenidos(cuerpo)
    assert "Criterios de evaluacion" not in cuerpo[desde:], "la seccion empieza demasiado pronto"
    modulos, _ = modulos_del(pdf)
    assert [n for n, _ in modulos["0373"]["unidades"]] == ["Almacenamiento de informacion"]


def test_la_sonda_denuncia_un_encabezado_que_no_ha_salido_como_unidad():
    """modulos_mudos solo veia el modulo con CERO unidades: el que perdia dos de cinco pasaba en
    verde. Esta sonda mira lineas que terminan en dos puntos sin importarle como el parser
    reconoce un encabezado, que es justo el supuesto que fallaba."""
    seccion = ("Explotacion de sistemas microinformaticos:\n- Hardware.\n"
               "Automatizacion de tareas: construccion de guiones:\n- Herramientas.\n")
    assert ex.encabezados_sin_unidad(seccion, ["Explotacion de sistemas microinformaticos",
                                               "Automatizacion de tareas: construccion de guiones"]) == []
    perdidos = ex.encabezados_sin_unidad(seccion, ["Explotacion de sistemas microinformaticos"])
    assert perdidos == ["Automatizacion de tareas: construccion de guiones"]


# ---------------------------------------------------------------------------------------------
# El muestreo: procedencia POR CAMPO, y sin verificacion circular.
# ---------------------------------------------------------------------------------------------

NODO_CON_DOS_PROCEDENCIAS = {
    "nivel": "asignatura", "titulacion": "daw", "codigo": "0618",
    "nombre": "Empresa e iniciativa emprendedora", "curso": 2, "horas": 60,
    "fuente": {"norma": "RD 686/2010", "documento": "x/RD-686-2010-titulo-DAW.pdf", "pagina": 56},
    "curso_fuente": {"norma": "Orden EDU/2887/2010", "documento": "x/Orden-EDU-2887-2010.pdf",
                     "anexo": "II", "pagina": 29},
}


def test_el_curso_cita_la_orden_y_no_el_real_decreto():
    """El reparto por cursos NO lo fija el real decreto: lo fija la Orden en su Anexo II. El JSONL
    ya lo tenia bien en campos separados; era la tabla del muestreo, con una sola columna de
    norma para las dos afirmaciones, la que se lo atribuia al RD."""
    campos = {campo: f["norma"] for campo, _, f in ex.afirmaciones_de(NODO_CON_DOS_PROCEDENCIAS)}
    assert campos["nombre"] == "RD 686/2010"
    assert campos["curso 2"] == "Orden EDU/2887/2010 (anexo II)"


def test_un_nodo_sin_curso_solo_afirma_su_nombre():
    sin_curso = {k: v for k, v in NODO_CON_DOS_PROCEDENCIAS.items()
                 if k not in ("curso", "curso_fuente")}
    assert [campo for campo, _, _ in ex.afirmaciones_de(sin_curso)] == ["nombre"]


def test_el_muestreo_no_repite_lo_que_se_acaba_de_reparar_ni_lo_ya_comprobado(tmp_path):
    """Revisar a mano justo lo reparado confirma el parche, no el extractor."""
    nodos = [NODO_CON_DOS_PROCEDENCIAS]  # 0618: ya muestreado en la tanda anterior
    nodos += [{"nivel": "unidad", "titulacion": "daw", "asignatura": "0612", "orden": i,
               "nombre": f"reparada {i}", "fuente": NODO_CON_DOS_PROCEDENCIAS["fuente"]}
              for i in range(1, 4)]  # 0612: modulo reparado
    nodos += [{"nivel": "unidad", "titulacion": "dam", "asignatura": "0490", "orden": i,
               "nombre": f"intacta {i}", "fuente": NODO_CON_DOS_PROCEDENCIAS["fuente"]}
              for i in range(1, 4)]
    destino = tmp_path / "muestreo.md"
    ex.escribir_muestreo(nodos, str(destino), forzar=True, fecha="hoy")
    escrito = destino.read_text(encoding="utf-8")
    assert "intacta" in escrito
    assert "reparada" not in escrito
    assert "0618" not in escrito


def test_el_muestreo_rehecho_conserva_entera_la_tabla_anterior(tmp_path):
    """La tabla vieja es la PRUEBA de que el muestreo humano encontro un defecto que el verde
    daba por bueno. Vale mas que la tabla en si, asi que no se sustituye: se conserva dentro."""
    destino = tmp_path / "muestreo.md"
    destino.write_text("# Viejo\n\n| 1 | DAW | asignatura 0373 |\n\nNumero de acuerdo: 3 de 10.\n",
                       encoding="utf-8")
    nodos = [{"nivel": "unidad", "titulacion": "dam", "asignatura": "0490", "orden": 1,
              "nombre": "intacta", "fuente": NODO_CON_DOS_PROCEDENCIAS["fuente"]}]
    ex.escribir_muestreo(nodos, str(destino), forzar=True, fecha="hoy")
    escrito = destino.read_text(encoding="utf-8")
    assert "Numero de acuerdo: 3 de 10." in escrito, "las anotaciones a mano no se pierden"
    assert "Muestreo anterior, conservado entero" in escrito


def test_sin_forzar_el_muestreo_no_se_toca(tmp_path):
    destino = tmp_path / "muestreo.md"
    destino.write_text("intacto\n", encoding="utf-8")
    ex.escribir_muestreo([], str(destino))
    assert destino.read_text(encoding="utf-8") == "intacto\n"
