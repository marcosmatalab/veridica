"""Tests de la puerta de material sensible.

Validada en las DOS direcciones, que es lo que exige el principio 6: que encuentre lo que tiene que
encontrar, y que NO se dispare con lo que parece pero no es. Un detector que marca todo es tan
inutil como uno que no marca nada, y encima acaba relajado.

Los casos vienen de hallazgos reales del corpus: una clave privada en unos apuntes de Kubernetes,
un CSV con nombres y notas de alumnos, y -del otro lado- DNI e IBAN que son enunciados de ejercicio.
"""
import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "scripts" / "detectar_sensibles.py"


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
