"""Tests de la basura plantada (encargo 1.7).

El anclado es la puerta: el manifiesto tiene que listar EXACTAMENTE lo plantado. Si se planta algo
sin declarar, el detector del 1.8 encontraria un "hallazgo" que en realidad es basura nuestra sin
etiquetar, y su numero dejaria de significar nada.
"""
import importlib.util
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "scripts" / "plantar_basura.py"

# El corpus esta fuera de git (ADR 0001), asi que lo que necesite ficheros en disco solo corre en
# local. Lo que se puede comprobar contra el manifiesto -que si esta en git- corre tambien en CI.
sin_corpus = pytest.mark.skipif(not (RAIZ / "corpus" / "daw").exists(),
                                reason="necesita el corpus local (ADR 0001)")


def cargar():
    spec = importlib.util.spec_from_file_location("plantar_basura", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


pb = cargar()


def test_se_planta_uno_de_cada_tipo():
    motivos = sorted(p["motivo"] for p in pb.PLANTADOS)
    assert motivos.count("casi_duplicado") == 3      # (a) de la guia
    assert motivos.count("contradiccion") == 1       # (b) sintetica; la real es el par del corpus
    assert motivos.count("colado") == 1              # (c) para medir contaminacion cruzada


def test_el_colado_viene_de_otra_asignatura():
    colado = [p for p in pb.PLANTADOS if p["motivo"] == "colado"][0]
    assert "bases-de-datos" in colado["origen"]
    assert "programacion" in colado["destino"]


def test_el_casi_duplicado_se_parece_al_original_pero_no_es_igual():
    """Un casi duplicado que no se parece a nada no prueba nada: tiene que seguir siendo
    reconocible como copia."""
    original = ("Los bucles permiten repetir instrucciones. Es decir, el cuerpo se ejecuta "
                "varias veces.\n\n" + "\n\n".join(f"Parrafo {i} del temario original." for i in range(8)))
    copia = pb.casi_duplicar(original)
    assert "Los bucles permiten repetir instrucciones" in copia
    assert copia != original
    assert "O sea" in copia and "Es decir" not in copia


def test_plantar_dos_veces_da_el_mismo_fichero():
    """Sin azar: si el contenido cambiara en cada plantada, cambiaria su hash y el manifiesto
    entraria en rojo cada vez que alguien re-planta."""
    original = "Uno. Es decir, dos.\n\n" + "\n\n".join(f"P{i}" for i in range(9))
    assert pb.casi_duplicar(original) == pb.casi_duplicar(original)


def test_la_contradiccion_sintetica_choca_con_el_temario_en_algo_sustantivo():
    """No es 'el valor es 5' contra 'es 7': es la discusion real entre materiales docentes de Java
    sobre si los objetos se pasan por referencia."""
    texto = " ".join(pb.CONTRADICCION.lower().split())   # el texto va con saltos de linea reales
    assert "por valor" in texto and "por referencia" in texto
    assert "no existe el paso por referencia en java" in texto
    assert len(pb.CONTRADICCION) > 500, "una hoja de repaso de dos lineas no es material realista"


def test_lo_plantado_va_declarado_con_su_motivo_en_el_manifiesto():
    entradas = [json.loads(x) for x in
                (RAIZ / "corpus" / "manifiesto.jsonl").read_text(encoding="utf-8").split("\n")
                if x.strip()]
    por_ruta = {e["ruta"]: e for e in entradas}
    for p in pb.PLANTADOS:
        e = por_ruta.get(p["destino"])
        assert e, f"plantado sin entrada de manifiesto: {p['destino']}"
        assert e["plantado"] is True
        assert e["plantado_motivo"] == p["motivo"]


@sin_corpus
def test_la_puerta_cuadra_disco_contra_manifiesto():
    assert pb.comprobar() == 0
