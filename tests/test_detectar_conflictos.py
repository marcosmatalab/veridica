"""Tests del detector de conflictos (encargo 1.8), anclados en el corpus real.

Las dos direcciones, que es lo que exige el principio 6:
  - encuentra lo plantado (condicion necesaria),
  - y NO marca los controles negativos, que son documentos legitimos que se le parecen mucho.

El control negativo del colado lo eligio Marcos y es el bueno: la Unidad 13 de Programacion es
"Acceso a Bases de Datos", asi que su vecindario semantico cae de lleno en otra asignatura y aun
asi NO es un colado. Un detector que no distinga eso no sirve.
"""
import importlib.util
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "scripts" / "detectar_conflictos.py"
CONFLICTOS = RAIZ / "corpus" / "conflictos.jsonl"


def cargar():
    spec = importlib.util.spec_from_file_location("detectar_conflictos", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


dc = cargar()
hay_corpus = CONFLICTOS.exists()
sin_corpus = pytest.mark.skipif(not hay_corpus, reason="necesita el corpus local (ADR 0001)")


@pytest.fixture(scope="module")
def hallazgos():
    return [json.loads(x) for x in CONFLICTOS.read_text(encoding="utf-8").split("\n") if x.strip()]


# --- unidades puras, sin corpus: corren siempre en CI --------------------------------------

def test_la_version_antigua_de_un_modulo_es_el_mismo_modulo():
    """Sin esto el par contradictorio real era invisible: vive en la carpeta '-antiguo' y el
    detector solo compara dentro de la misma asignatura."""
    assert dc.asignatura_real("desarrollo-web-entorno-servidor-antiguo") == \
        "desarrollo-web-entorno-servidor"
    assert dc.asignatura_real("programacion") == "programacion"


def test_el_mejor_par_de_frases_elige_las_que_hablan_de_lo_mismo():
    a = "Los bucles repiten instrucciones. En Java los objetos se pasan por referencia siempre."
    b = "El array se recorre con for. En Java todos los parametros se pasan por valor, tambien los objetos."
    par, solape = dc.mejor_par_de_frases(a, b)
    assert par and "objetos" in par[0] and "objetos" in par[1]
    assert solape > 0


def test_el_codigo_no_entra_al_nli():
    """Dos lineas de codigo casi iguales daban 'contradiccion' a puñados."""
    assert dc.RE_CODIGO.search("private final Logger logger = LoggerFactory.getLogger(X.class);")
    assert not dc.RE_CODIGO.search("Una clave primaria identifica de forma unica cada fila.")


def test_un_parentesis_no_convierte_una_frase_en_codigo():
    """Fallo real de la primera version: '(un puntero)' hacia que se descartara la frase que
    contenia LA contradiccion plantada."""
    assert not dc.RE_CODIGO.search(
        "no se copia el objeto sino que se le pasa una referencia al objeto original (un puntero)")


# --- anclados al corpus real ------------------------------------------------------------------

@sin_corpus
def test_encuentra_la_contradiccion_plantada(hallazgos):
    p = [x for x in hallazgos if x["tipo"] == "contradiccion"
         and "ud7_repaso_paso_de_parametros" in x["a"]["documento"] + x["b"]["documento"]]
    assert p, "la contradiccion plantada en el 1.7 tiene que aparecer"
    assert p[0]["probabilidad_nli"] >= 0.90
    assert "referencia" in (p[0]["frase_a"] + p[0]["frase_b"]).lower()


@sin_corpus
def test_encuentra_los_casi_duplicados_plantados_que_pasan_el_umbral(hallazgos):
    """Dos de los tres. El tercero (ud5) se queda en 0,946 y NO se detecta a 0,95: queda anclado
    aqui para que, si alguien mueve el umbral o el troceado, se entere."""
    nombres = {"ud6_Arrays_repaso.md", "ud8_POO_resumen.md"}
    encontrados = {n for n in nombres for x in hallazgos if x["tipo"] == "casi_duplicado"
                   and n in x["a"]["documento"] + x["b"]["documento"]}
    assert encontrados == nombres
    escapado = [x for x in hallazgos if x["tipo"] == "casi_duplicado"
                and "ud5_Bucles_en_Java_v2" in x["a"]["documento"] + x["b"]["documento"]]
    assert not escapado, "si ud5 empieza a detectarse, alguien cambio el umbral: revisar la decision"


@sin_corpus
def test_encuentra_el_colado(hallazgos):
    colados = [x for x in hallazgos if x["tipo"] == "colado"]
    rutas = " ".join(x["documento"] for x in colados)
    assert "BD05_modelo_relacional.md" in rutas
    assert all(x["proporcion_casi_duplicada_fuera"] >= dc.UMBRAL_COLADO for x in colados)


@sin_corpus
def test_no_marca_como_colado_un_documento_legitimo_de_frontera(hallazgos):
    """EL control negativo: ud13 y Consultas-SQL son Programacion legitima que habla de bases de
    datos (11 de sus 15 vecinos caen en Bases de datos) y NO pueden salir como colados."""
    colados = " ".join(x["documento"] for x in hallazgos if x["tipo"] == "colado")
    for legitimo in ("ud13_AccesoBBDD", "Consultas-SQL", "ingles.txt", "LMSGI_01"):
        assert legitimo not in colados, f"falso positivo de colado: {legitimo}"


@sin_corpus
def test_ningun_hallazgo_es_un_solape_consecutivo(hallazgos):
    """El artefacto del troceado: 5.143 pares de la banda son consecutivos del mismo documento.
    Si alguno se cuela como hallazgo, el detector esta midiendo su propia sombra."""
    for x in hallazgos:
        if x["tipo"] in ("casi_duplicado", "contradiccion"):
            if x["a"]["documento"] == x["b"]["documento"]:
                assert abs(x["a"]["orden"] - x["b"]["orden"]) > 1


@sin_corpus
def test_cada_conflicto_trae_lo_que_la_fase_4_necesita_para_responder(hallazgos):
    """No basta con la marca: sin las dos fechas, el 4.5 no puede ordenar por vigencia."""
    for x in hallazgos:
        if x["tipo"] in ("casi_duplicado", "contradiccion"):
            assert x["a"]["texto"] and x["b"]["texto"]
            assert "fecha_fuente" in x["a"] and "fecha_fuente" in x["b"]
            assert x["similitud"] is not None
