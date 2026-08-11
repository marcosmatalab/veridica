"""Tests anclados de scripts/verificar_manifiesto.py (encargo 1.0).

El caso que da sentido al encargo es el tercero: se cambia UN BYTE de un fichero sin tocar su
tamano y el verificador tiene que ponerse rojo. Antes del 1.0 ese caso salia en verde.

Todo corre sobre un corpus de JUGUETE en directorio temporal, asi que estos tests entran en CI
aunque el runner no tenga el corpus real (ADR 0001).
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verificar_manifiesto.py"

FICHEROS = {
    "corpus/daw/apuntes/uno.md": b"# Unidad 1\nUna clave primaria identifica una fila.\n",
    "corpus/daw/apuntes/dos.md": b"# Unidad 2\nUna clave ajena referencia a otra tabla.\n",
    "corpus/COBERTURA.md": b"# Cobertura de juguete\n",
}


def entrada(ruta: str, contenido: bytes, **extra) -> dict:
    e = {
        "ruta": ruta, "fuente": "fuente de prueba", "licencia": "CC BY 4.0",
        "version_corpus": "v3-2026-08-11", "hash_sha256": hashlib.sha256(contenido).hexdigest(),
        "densidad": "parcial", "plantado": False,
    }
    e.update(extra)
    return e


def corpus_de_juguete(raiz: Path, entradas=None) -> Path:
    """Escribe los ficheros y un manifiesto que los declara con su hash real."""
    for ruta, contenido in FICHEROS.items():
        destino = raiz / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
    if entradas is None:
        entradas = [entrada(r, c) for r, c in FICHEROS.items()]
    manifiesto = raiz / "corpus" / "manifiesto.jsonl"
    with open(manifiesto, "w", encoding="utf-8", newline="\n") as f:
        for e in entradas:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return manifiesto


def verificar(raiz: Path):
    return subprocess.run([sys.executable, str(SCRIPT)], cwd=raiz, capture_output=True, text=True)


def test_corpus_integro_sale_en_verde(tmp_path):
    corpus_de_juguete(tmp_path)
    r = verificar(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ocurrencias=0" in r.stdout


def test_un_byte_cambiado_sin_variar_el_tamano_pone_el_verificador_en_rojo(tmp_path):
    """EL caso anclado del encargo 1.0: mismo nombre, mismo tamano, contenido distinto."""
    corpus_de_juguete(tmp_path)
    victima = tmp_path / "corpus/daw/apuntes/uno.md"
    antes = victima.read_bytes()
    victima.write_bytes(antes.replace(b"primaria", b"primarla"))  # un byte, mismo tamano
    assert len(victima.read_bytes()) == len(antes), "la mutacion no debe cambiar el tamano"

    r = verificar(tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "HASH DISTINTO" in r.stdout
    assert "corpus/daw/apuntes/uno.md" in r.stdout
    assert "hash_distinto=1" in r.stdout


def test_fichero_borrado_sale_como_sin_fichero(tmp_path):
    corpus_de_juguete(tmp_path)
    (tmp_path / "corpus/daw/apuntes/dos.md").unlink()
    r = verificar(tmp_path)
    assert r.returncode == 1
    assert "SIN FICHERO: corpus/daw/apuntes/dos.md" in r.stdout
    assert "sin_fichero=1" in r.stdout


def test_fichero_no_declarado_sale_como_sin_manifiesto(tmp_path):
    corpus_de_juguete(tmp_path)
    (tmp_path / "corpus/daw/apuntes/colado.md").write_bytes(b"esto no lo declaro nadie\n")
    r = verificar(tmp_path)
    assert r.returncode == 1
    assert "SIN MANIFIESTO: corpus/daw/apuntes/colado.md" in r.stdout
    assert "sin_manifiesto=1" in r.stdout


def test_ruta_duplicada_en_el_manifiesto_se_denuncia(tmp_path):
    """Antes del 1.0 la segunda entrada pisaba a la primera y los conteos seguian cuadrando."""
    entradas = [entrada(r, c) for r, c in FICHEROS.items()]
    entradas.append(entrada("corpus/daw/apuntes/uno.md", FICHEROS["corpus/daw/apuntes/uno.md"]))
    corpus_de_juguete(tmp_path, entradas)
    r = verificar(tmp_path)
    assert r.returncode == 1
    assert "RUTA DUPLICADA: corpus/daw/apuntes/uno.md" in r.stdout
    assert "ruta_duplicada=1" in r.stdout


def test_campos_nuevos_en_una_entrada_no_rompen_nada(tmp_path):
    """El manifiesto va a crecer (encargo 1.3: ficheros normalizados). No se asume inmutable."""
    entradas = [entrada(r, c) for r, c in FICHEROS.items()]
    entradas[0].update(origen="ocr", derivado_de="corpus/daw/apuntes/original.pdf", nota="lo que sea")
    corpus_de_juguete(tmp_path, entradas)
    r = verificar(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_manifiesto_mal_formado_sale_con_2_y_no_finge_verde(tmp_path):
    corpus_de_juguete(tmp_path)
    manifiesto = tmp_path / "corpus" / "manifiesto.jsonl"
    manifiesto.write_text(manifiesto.read_text(encoding="utf-8") + "{esto no es json}\n",
                          encoding="utf-8", newline="\n")
    r = verificar(tmp_path)
    assert r.returncode == 2
    assert "MAL FORMADO" in r.stderr
