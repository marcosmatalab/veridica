"""Tests del embebedor (encargo 1.5).

No cargan el modelo: eso son 2,3 GB y 2,6 s, y lo que hay que probar aqui es la fontaneria de la
reanudacion, que es donde se pierde una tanda. La tanda de verdad ya se corrio y se midio.

El anclado es el orden de escritura del checkpoint: primero los vectores, despues sus ids. Si se
escribiera al reves y el proceso muriera en medio, al reanudar habria ids sin vectores y la matriz
quedaria descuadrada respecto al fichero de ids, en silencio.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "scripts" / "embeber.py"


def cargar():
    spec = importlib.util.spec_from_file_location("embeber", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


em = cargar()


def claves(n, desde=0):
    return [{"documento": f"doc{i}.md", "orden": 1, "asignatura": "programacion"}
            for i in range(desde, desde + n)]


def test_sin_checkpoints_no_hay_nada_hecho(tmp_path):
    vectores, hechas = em.hechos_hasta_ahora(str(tmp_path / "no_existe"))
    assert vectores == [] and hechas == []


def test_la_reanudacion_cuenta_lo_ya_embebido(tmp_path):
    em.guardar_checkpoint(str(tmp_path), 0, np.zeros((3, em.DIMENSION), dtype=np.float32), claves(3))
    em.guardar_checkpoint(str(tmp_path), 1, np.zeros((2, em.DIMENSION), dtype=np.float32),
                          claves(2, 3))
    vectores, hechas = em.hechos_hasta_ahora(str(tmp_path))
    assert len(hechas) == 5
    assert sum(len(v) for v in vectores) == 5


def test_un_checkpoint_a_medias_se_ignora_entero(tmp_path):
    """EL caso anclado: si el proceso muere entre el .npy y su .ids.jsonl, ese lote no cuenta.
    Darlo por bueno dejaria vectores sin dueno y la matriz descuadrada, en silencio."""
    em.guardar_checkpoint(str(tmp_path), 0, np.zeros((4, em.DIMENSION), dtype=np.float32), claves(4))
    np.save(tmp_path / "lote_00001.npy", np.zeros((7, em.DIMENSION), dtype=np.float32))  # sin ids
    vectores, hechas = em.hechos_hasta_ahora(str(tmp_path))
    assert len(hechas) == 4, "el lote sin ids no puede contarse"
    assert sum(len(v) for v in vectores) == 4


def test_los_ids_guardan_de_que_fragmento_es_cada_fila(tmp_path):
    em.guardar_checkpoint(str(tmp_path), 0, np.zeros((2, em.DIMENSION), dtype=np.float32),
                          [{"documento": "a.md", "orden": 3, "asignatura": "programacion"},
                           {"documento": "b.md", "orden": 1, "asignatura": "bases-de-datos"}])
    lineas = (tmp_path / "lote_00000.ids.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert [json.loads(x)["documento"] for x in lineas] == ["a.md", "b.md"]


def test_se_embebe_el_fragmento_entero_con_su_contexto():
    """Decision del 1.4: lo que se embebe incluye la linea de contexto, y por eso los 512 la
    cuentan dentro."""
    fr = {"contexto": "DAW · curso 1 · programacion · Unidad 5", "texto": "El bucle for se usa..."}
    completo = em.texto_a_embeber(fr)
    assert completo.startswith("DAW · curso 1")
    assert "El bucle for" in completo


def test_la_revision_del_modelo_esta_anclada():
    """Sin revision fijada, una revision nueva del modelo daria vectores no comparables con los
    viejos y no habria forma de saberlo mirando el fichero."""
    assert len(em.REVISION) == 40 and all(c in "0123456789abcdef" for c in em.REVISION)
    assert em.MODELO == "BAAI/bge-m3"
