"""Tests del troceador (encargo 1.4).

Los anclados son los tres que salieron de decisiones, no de gusto:
  - los 512 tokens se cuentan con el tokenizador REAL y INCLUYEN la linea de contexto;
  - el codigo no se parte por ventana ciega: un fichero es un fragmento si cabe, y si no, se corta
    por clase o por metodo;
  - los volcados de secretos no entran (en el corpus real hay una clave privada RSA en unos
    apuntes de ASIR).
"""
import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "scripts" / "trocear.py"


def cargar():
    spec = importlib.util.spec_from_file_location("trocear", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


tr = cargar()


@pytest.fixture(scope="module")
def tok():
    return tr.cargar_tokenizador()


# --- la unidad sale de la carpeta, no del BOE (ADR 0005) --------------------------------------

def test_la_unidad_sale_de_la_carpeta_del_material():
    partes = tr.ruta_a_partes(
        "corpus/derivado/daw/curso1/programacion/lionel-ict/Unidad 4 Introducción a Java/x.pdf.md")
    assert partes["titulacion"] == "daw"
    assert partes["curso"] == 1
    assert partes["asignatura"] == "programacion"
    assert partes["unidad"] == "Unidad 4 Introducción a Java"   # la del profesor, no la del BOE


def test_un_documento_sin_carpeta_de_unidad_no_se_inventa_una():
    partes = tr.ruta_a_partes("corpus/derivado/dam/apuntes/temario/tema.pdf.md")
    assert partes["unidad"] in (None, "temario")
    assert partes["titulacion"] == "dam"


# --- presupuesto de tokens ---------------------------------------------------------------------

def test_ningun_fragmento_de_prosa_pasa_de_512_contando_el_contexto(tok):
    texto = "\n\n".join(f"Parrafo numero {i} con contenido docente suficiente para llenar el "
                        f"presupuesto de tokens del fragmento y obligar a cortar." * 3
                        for i in range(40))
    contexto = "DAW · curso 1 · programacion · Unidad 4 · documento de prueba"
    presupuesto = tr.TOKENS - tr.contar(tok, contexto) - 2
    trozos, _ = tr.trocear_prosa(tok, texto, presupuesto)
    assert trozos
    for t in trozos:
        assert tr.contar(tok, contexto + "\n\n" + t) <= tr.TOKENS


def test_un_parrafo_sin_puntuacion_se_parte_igual(tok):
    """Las tablas de atajos de NetBeans del corpus son 1.011 tokens sin un solo punto."""
    texto = " ".join(f"atajo{i} combinacion{i}" for i in range(600))
    trozos, _ = tr.trocear_prosa(tok, texto, 200)
    assert len(trozos) > 1
    assert all(tr.contar(tok, t) <= 200 for t in trozos)


# --- codigo -------------------------------------------------------------------------------------

CLASE_JAVA = """package ejemplo;

public class Calculadora {
    public int sumar(int a, int b) {
        return a + b;
    }

    public int restar(int a, int b) {
        return a - b;
    }
}
"""


def test_un_fichero_de_codigo_que_cabe_es_UN_fragmento(tok):
    trozos, aviso = tr.trocear_codigo(tok, CLASE_JAVA, 480)
    assert trozos == [CLASE_JAVA] and aviso is None


def test_el_codigo_grande_se_corta_por_metodo_no_por_ventana(tok):
    cuerpo = "\n".join(f"        System.out.println(\"linea {i}\");" for i in range(60))
    fichero = ("public class Grande {\n"
               f"    public void primero() {{\n{cuerpo}\n    }}\n\n"
               f"    public void segundo() {{\n{cuerpo}\n    }}\n}}\n")
    trozos, _ = tr.trocear_codigo(tok, fichero, 480)
    assert len(trozos) > 1
    # cada trozo empieza donde empieza una clase o un metodo, no a media linea
    for t in trozos[1:]:
        assert t.lstrip().startswith(("public", "private", "protected", "class", "@")), t[:60]


def test_si_no_hay_donde_cortar_se_avisa_y_no_se_destroza(tok):
    """Mejor un fragmento grande que uno roto: uno roto no compila ni se entiende."""
    fichero = "\n".join(f"int variable{i} = {i};" for i in range(400))
    trozos, aviso = tr.trocear_codigo(tok, fichero, 200)
    assert trozos == [fichero]
    assert aviso and "clase" in aviso


# --- secretos -------------------------------------------------------------------------------

def test_una_clave_privada_no_entra_al_corpus(tok):
    """Encontrado en el corpus real: apuntes de ASIR con certificados de Kubernetes y una clave
    privada RSA volcados en base64. Un sistema que cita fragmentos al alumno no puede tener eso."""
    clave = "-----BEGIN RSA PRIVATE KEY-----\n" + "MIIEowIBAAKCAQEAwL3NvRaIPz2s" * 20
    texto = f"Contenido docente normal del tema.\n\n{clave}\n\nMas contenido docente."
    trozos, tirados = tr.trocear_prosa(tok, texto, 480)
    assert tirados == 1
    assert all("PRIVATE KEY" not in t for t in trozos)
    assert any("Contenido docente normal" in t for t in trozos)


def test_el_texto_normal_no_se_confunde_con_un_secreto():
    assert not tr.parece_secreto_o_volcado(
        "Una clave primaria identifica de forma unica cada fila de una tabla relacional. " * 5)


# --- tipo de contenido --------------------------------------------------------------------------

def test_el_tipo_de_contenido_sale_por_reglas():
    assert tr.tipo_de_contenido("class Foo {}", True) == "codigo"
    assert tr.tipo_de_contenido("Real Decreto 686/2010, anexo I", False) == "normativa"
    assert tr.tipo_de_contenido("Ejercicio 3: solucion del caso practico", False) == "ejemplo_resuelto"
    assert tr.tipo_de_contenido("Una clave ajena es una referencia a otra tabla", False) == "definicion"


def test_la_linea_de_contexto_lleva_el_camino_del_alumno():
    partes = {"titulacion": "daw", "curso": 1, "asignatura": "programacion",
              "unidad": "Unidad 4 Introducción a Java"}
    linea = tr.linea_de_contexto("x", partes, "ud4_Introduccion_a_Java")
    assert linea == ("DAW · curso 1 · programacion · Unidad 4 Introducción a Java · "
                     "ud4_Introduccion_a_Java")
