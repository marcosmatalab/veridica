"""Tests de la puerta de material sensible.

Validada en las DOS direcciones, que es lo que exige el principio 6: que encuentre lo que tiene que
encontrar, y que NO se dispare con lo que parece pero no es. Un detector que marca todo es tan
inutil como uno que no marca nada, y encima acaba relajado.

Los casos vienen de hallazgos reales del corpus: una clave privada en unos apuntes de Kubernetes,
un CSV con nombres y notas de alumnos, y -del otro lado- DNI e IBAN que son enunciados de ejercicio.
"""
import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "scripts" / "detectar_sensibles.py"
# El corpus esta fuera de git (ADR 0001): lo anclado a ficheros reales solo corre en local.
sin_corpus = pytest.mark.skipif(not (RAIZ / "corpus" / "derivado").exists(),
                                reason="necesita el corpus local (ADR 0001)")


def cargar():
    spec = importlib.util.spec_from_file_location("detectar_sensibles", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


ds = cargar()


def revisar_texto(tmp_path, texto: str, nombre="x.md"):
    ruta = tmp_path / nombre
    ruta.write_text(texto, encoding="utf-8")
    return ds.revisar(str(ruta))


def tipos(hallazgos, nivel=None):
    return {t for t, n, _, _ in hallazgos if nivel is None or n == nivel}


# --- direccion 1: tiene que encontrarlo ------------------------------------------------------

def test_encuentra_una_clave_privada(tmp_path):
    h = revisar_texto(tmp_path, "texto normal\n-----BEGIN RSA PRIVATE KEY-----\nMIIEow...")
    assert "clave_privada" in tipos(h, "bloqueante")


def test_encuentra_un_certificado(tmp_path):
    h = revisar_texto(tmp_path, "-----BEGIN CERTIFICATE-----\nMIIC5zCCAc+g...")
    assert "certificado" in tipos(h, "bloqueante")


def test_encuentra_una_lista_de_alumnos_con_notas(tmp_path):
    h = revisar_texto(tmp_path, "Nombre,Apellidos,Curso\nGARCIA LOPEZ, MARIA,1B,8,7,9,10")
    assert "lista_de_notas" in tipos(h, "bloqueante")


def test_encuentra_un_dni_con_letra_correcta(tmp_path):
    h = revisar_texto(tmp_path, "El titular es 12345678Z segun el registro")
    assert "dni" in tipos(h, "bloqueante")


def test_encuentra_un_token_de_api(tmp_path):
    h = revisar_texto(tmp_path, "export TOKEN=ghp_" + "a" * 36)
    assert "token_conocido" in tipos(h, "bloqueante")


def test_el_correo_avisa_pero_no_bloquea(tmp_path):
    """Los apuntes llevan el correo del profesor en la portada: bloquear por eso dejaria la puerta
    en rojo permanente, y una puerta siempre roja acaba relajada (ADR 0001)."""
    h = revisar_texto(tmp_path, "Autor: Lionel Tarazon - lionel.tarazon@ceedcv.es")
    assert "correo" in tipos(h, "aviso")
    assert not tipos(h, "bloqueante")


# --- direccion 2: NO puede dispararse con lo que no es ---------------------------------------

def test_un_numero_de_ocho_cifras_con_letra_no_es_un_dni(tmp_path):
    """12345678A no es un DNI: la letra no cuadra. Sin comprobar el digito de control, cualquier
    referencia o codigo de pieza saldria como dato personal."""
    assert not ds.dni_valido("12345678", "A")
    h = revisar_texto(tmp_path, "La referencia del articulo es 12345678A en el catalogo")
    assert "dni" not in tipos(h)


def test_el_temario_normal_no_dispara_nada(tmp_path):
    h = revisar_texto(tmp_path, "Una clave primaria identifica de forma unica cada fila.\n"
                                "El bucle for recorre el array de 0 a n-1.\n"
                                "public class Ejemplo { int x = 42; }")
    assert h == []


def test_un_hash_o_un_uuid_no_son_secretos(tmp_path):
    h = revisar_texto(tmp_path, "hash: 5617a9f61b028005a4858fdac845db406aefb181\n"
                                "id: 550e8400-e29b-41d4-a716-446655440000")
    assert not tipos(h, "bloqueante")


def test_las_excepciones_se_declaran_una_a_una_con_su_motivo():
    """No se silencia una categoria entera: si mañana aparece un DNI en material nuevo, salta."""
    assert ds.DECLARADOS, "deberia haber excepciones declaradas del corpus real"
    for (ruta, tipo), motivo in ds.DECLARADOS.items():
        assert ruta and tipo and len(motivo) > 20, f"excepcion sin motivo escrito: {ruta}"


# --- concentracion: un documento que ES datos personales -------------------------------------
# El hueco que enseño el CV: nombre, telefono, correo, codigo postal y redes de una persona pasaban
# como cinco avisos sueltos, porque cada señal por separado es de las que no bloquean. El fichero
# real ya NO esta en el corpus (se borro del disco, como el CSV de notas), asi que el positivo de
# este test es sintetico y con datos inventados: meter el CV de alguien en la suite de tests para
# probar que detectamos CV seria repetir el problema dentro del repo.

CV_SINTETICO = """Nombre Apellido Apellido
41000 Localidad, Provincia
600111222
nombre.apellido@ejemplo.com
Twitter: @nombreapellido
LinkedIn: Nombre Apellido

FORMACION ACADEMICA
Graduado en Bachillerato, 2012-2014
Cursando Grado Superior de Administracion de Sistemas Informaticos en Red
"""


def test_un_documento_que_es_datos_personales_bloquea(tmp_path):
    h = revisar_texto(tmp_path, CV_SINTETICO)
    assert "concentracion_datos_personales" in tipos(h, "bloqueante")


def test_hacen_falta_varias_clases_y_no_solo_densidad(tmp_path):
    """La mutacion del criterio. Con el telefono, el codigo postal y las redes fuera queda un
    documento corto con un correo: denso, pero de una sola clase. Y por densidad sola el CV real
    (13,8 por mil) quedaba POR DEBAJO de un ejercicio de Postgres con diez correos de ejemplo
    (23,3): sin la variedad, este criterio marca lo que no es y se salta lo que si."""
    solo_correos = "\n".join(f"alumno{i}@ejemplo.com" for i in range(8))
    h = revisar_texto(tmp_path, solo_correos)
    assert "concentracion_datos_personales" not in tipos(h, "bloqueante")
    assert "correo" in tipos(h, "aviso")


def test_dos_señales_no_son_concentracion(tmp_path):
    """Un documento que CONTIENE un correo y un telefono -una portada, un pie de pagina- no es un
    documento que ES datos personales."""
    h = revisar_texto(tmp_path, "Tutor del modulo: profe@centro.es, telefono 954112233.")
    assert not tipos(h, "bloqueante")


@sin_corpus
def test_los_apuntes_con_el_correo_del_profesor_en_portada_no_bloquean():
    """EL control negativo, y son del corpus real, elegidos por estar CERCA del umbral:
      - las recomendaciones de la Unidad 6 llevan dos correos de profesor en 211 palabras (9,5 por
        mil, mas densas que el CV en señales brutas);
      - la actividad de Postgres lleva diez correos de ejemplo en 429 palabras (23,3 por mil).
    Las dos son material docente legitimo y las dos tienen UNA sola clase de señal."""
    for relativa in ("daw/curso1/programacion/lionel-ict/Unidad 6 Arrays/"
                     "ud6_recomendaciones_estudio.pdf.md",
                     "dam/apuntes/temario-dam-comesana/SGE/Unidad 1 SGE/Act2Postgre.pdf.md"):
        ruta = RAIZ / "corpus" / "derivado" / relativa
        assert ruta.exists(), ruta
        medida = ds.concentracion(ruta.read_text(encoding="utf-8"))
        assert not ds.es_concentracion(medida), f"{relativa}: {medida['clases']}"
