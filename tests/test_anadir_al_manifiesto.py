"""Tests de scripts/anadir_al_manifiesto.py (encargo 0.2).

Corren sobre un corpus de JUGUETE en un directorio temporal, nunca sobre el corpus real:
el corpus esta fuera de git, asi que el runner de CI no lo tiene y estos tests igual pasan alli.

Se invoca el script como proceso, no por import, para probar el contrato de verdad:
argumentos de linea de ordenes, manifiesto relativo al directorio de trabajo y codigo de salida.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "anadir_al_manifiesto.py"

ENTRADA_PREVIA = {
    "ruta": "corpus/viejo.txt", "fuente": "fuente previa", "licencia": "CC BY-SA 4.0",
    "version_corpus": "v3-2026-08-11", "hash_sha256": "0" * 64,
    "densidad": "parcial", "plantado": False,
}


def corpus_de_juguete(raiz: Path, entradas=(ENTRADA_PREVIA,)) -> Path:
    """Deja en `raiz` un corpus minimo: manifiesto con las entradas dadas y un fichero nuevo."""
    (raiz / "corpus").mkdir()
    manifiesto = raiz / "corpus" / "manifiesto.jsonl"
    with open(manifiesto, "w", encoding="utf-8", newline="\n") as f:
        for e in entradas:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    (raiz / "corpus" / "nuevo.txt").write_bytes(b"contenido de prueba\n")
    return manifiesto


def anadir(raiz: Path, version_corpus=None, ruta="corpus/nuevo.txt"):
    entorno = dict(os.environ)
    entorno.pop("VERSION_CORPUS", None)
    if version_corpus is not None:
        entorno["VERSION_CORPUS"] = version_corpus
    return subprocess.run(
        [sys.executable, str(SCRIPT), ruta, "fuente de prueba", "CC BY 4.0", "parcial", "false"],
        cwd=raiz, env=entorno, capture_output=True, text=True,
    )


def ultima_entrada(manifiesto: Path) -> dict:
    return json.loads(manifiesto.read_text(encoding="utf-8").strip().split("\n")[-1])


def test_hereda_la_version_de_la_ultima_entrada_del_manifiesto(tmp_path):
    """El caso que rompio en el 0.1: la version iba escrita a fuego y etiquetaba v1 en un corpus v3."""
    manifiesto = corpus_de_juguete(tmp_path)
    r = anadir(tmp_path)
    assert r.returncode == 0, r.stderr
    assert ultima_entrada(manifiesto)["version_corpus"] == "v3-2026-08-11"


def test_la_variable_de_entorno_manda_sobre_el_manifiesto(tmp_path):
    manifiesto = corpus_de_juguete(tmp_path)
    r = anadir(tmp_path, version_corpus="v4-2027-01-01")
    assert r.returncode == 0, r.stderr
    assert ultima_entrada(manifiesto)["version_corpus"] == "v4-2027-01-01"


def test_manifiesto_vacio_y_sin_variable_falla_sin_escribir_nada(tmp_path):
    """El caso donde DEBE fallar: sin version conocida no se inventa ninguna."""
    manifiesto = corpus_de_juguete(tmp_path, entradas=())
    r = anadir(tmp_path)
    assert r.returncode != 0
    assert manifiesto.read_bytes() == b""


def test_la_entrada_lleva_el_sha256_real_del_fichero(tmp_path):
    manifiesto = corpus_de_juguete(tmp_path)
    anadir(tmp_path)
    esperado = hashlib.sha256((tmp_path / "corpus" / "nuevo.txt").read_bytes()).hexdigest()
    e = ultima_entrada(manifiesto)
    assert e["hash_sha256"] == esperado
    assert e["ruta"] == "corpus/nuevo.txt"
    assert e["plantado"] is False


def test_escribe_con_fin_de_linea_lf_tambien_en_windows(tmp_path):
    """Anclado al fallo del 0.1: escribir en modo texto desde Windows metia CRLF en el manifiesto."""
    manifiesto = corpus_de_juguete(tmp_path)
    anadir(tmp_path)
    assert b"\r\n" not in manifiesto.read_bytes()
