"""Tests del mapa de asignaturas (encargo 2.1).

El mapa traduce la asignatura del FRAGMENTO -un slug de carpeta o una sigla del profesor- a la
asignatura del ARBOL OFICIAL -titulacion y codigo del BOE-. Son dos nociones distintas de la misma
palabra y sin esta tabla la carga tendria que adivinar.

La red que sostiene todo lo demas: **declarado o excluido, sin tercera opcion**. Si aparece un slug
nuevo en el indice y nadie lo declara, la carga se para en vez de inventarse una asignatura.
"""
import importlib.util
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MAPA = RAIZ / "corpus" / "mapa_asignaturas.jsonl"
ARBOL = RAIZ / "corpus" / "arbol_oficial.jsonl"
FRAGMENTOS = RAIZ / "corpus" / "fragmentos.jsonl"
sin_corpus = pytest.mark.skipif(not FRAGMENTOS.exists(),
                                reason="necesita el corpus local (ADR 0001)")


def leer(ruta):
    return [json.loads(x) for x in ruta.read_text(encoding="utf-8").split("\n") if x.strip()]


def cargar_script():
    spec = importlib.util.spec_from_file_location("cargar_base", RAIZ / "scripts" / "cargar_base.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


MAPEO = leer(MAPA)
ASIGNATURAS_ARBOL = [n for n in leer(ARBOL) if n.get("nivel") == "asignatura"]


def test_cada_entrada_o_traduce_o_excluye_con_motivo():
    for e in MAPEO:
        if e.get("excluido"):
            assert len(e.get("motivo", "")) > 30, f"exclusion sin motivo escrito: {e['clave']}"
        else:
            assert e["titulacion_duena"] and e["codigo"], e["clave"]
            assert len(e.get("evidencia", "")) > 20, f"traduccion sin evidencia: {e['clave']}"


def test_todo_codigo_declarado_existe_en_el_arbol_del_boe():
    """El mapa no puede inventarse un modulo: su codigo tiene que estar en el arbol, y bajo la
    titulacion que se declara como dueña."""
    del_arbol = {(n["titulacion"], n["codigo"]) for n in ASIGNATURAS_ARBOL}
    for e in MAPEO:
        if not e.get("excluido"):
            par = (e["titulacion_duena"], e["codigo"])
            assert par in del_arbol, f"{e['clave']} apunta a {par}, que no esta en el arbol"


def test_la_clave_lleva_la_titulacion_de_la_carpeta_y_no_solo_el_slug():
    """La colision real que lo obliga: 'empresa-e-iniciativa-emprendedora' existe en DAW (0618) y
    en ASIR (0381). Con el slug solo como clave, una de las dos se cargaria en la asignatura
    equivocada y nadie se enteraria."""
    eie = {e["clave"]: e for e in MAPEO if e["slug"] == "empresa-e-iniciativa-emprendedora"}
    assert set(eie) == {"daw/empresa-e-iniciativa-emprendedora",
                        "asir/empresa-e-iniciativa-emprendedora"}
    assert eie["daw/empresa-e-iniciativa-emprendedora"]["codigo"] == "0618"
    assert eie["asir/empresa-e-iniciativa-emprendedora"]["codigo"] == "0381"


def test_una_carpeta_de_asir_puede_mapear_a_un_codigo_cuya_dueña_es_daw():
    """El caso transversal: el 0373 esta en los tres titulos, se carga UNA vez bajo DAW y la puente
    lo alcanza desde ASIR. El material de lora-1asir/LM va a esa particion, no a una de ASIR."""
    e = next(x for x in MAPEO if x["clave"].startswith("asir/lenguajes-de-marcas"))
    assert e["titulacion_carpeta"] == "asir"
    assert e["titulacion_duena"] == "daw"
    assert e["codigo"] == "0373" and e["transversal"] is True


def test_los_dos_slugs_de_dwes_caen_en_la_misma_asignatura():
    """Si el DWES viejo cayera en otra particion, el detector de conflictos no compararia nunca el
    par contradictorio real, que es de lo que vive el momento 3 de la demo."""
    codigos = {e["codigo"] for e in MAPEO
               if e["slug"].startswith("desarrollo-web-entorno-servidor")}
    assert codigos == {"0613"}


def test_el_transversal_se_carga_una_sola_vez_bajo_su_dueña():
    cb = cargar_script()
    filas, puente = cb.asignaturas_a_cargar(leer(ARBOL))
    codigos = [n["codigo"] for n in filas]
    assert len(codigos) == len(set(codigos)), "un codigo se carga dos veces: rompe la puente"
    assert len(puente) == len(ASIGNATURAS_ARBOL), "la puente pierde mapeos"
    # 0373 esta en las tres titulaciones del arbol y solo puede cargarse una vez.
    assert sum(1 for n in filas if n["codigo"] == "0373") == 1
    assert sum(1 for n in puente if n["codigo"] == "0373") == 3
    # Y cada fila de la puente lleva el nombre de SU norma, no el de la dueña: el 0373 se escribe
    # distinto en el RD de DAW y en el de ASIR (migracion 0003).
    nombres = {n["titulacion"]: n["nombre"] for n in puente if n["codigo"] == "0373"}
    assert nombres["daw"] != nombres["asir"], "los dos nombres del 0373 no pueden ser el mismo"


@sin_corpus
def test_ningun_slug_del_indice_se_queda_sin_declarar():
    """La red: declarado o excluido, sin tercera opcion."""
    declarados = {e["clave"] for e in MAPEO}
    del_indice = {f"{f['titulacion']}/{f['asignatura']}"
                  for f in leer(FRAGMENTOS)}
    huerfanos = del_indice - declarados
    assert not huerfanos, f"slugs del indice sin entrada en el mapa: {sorted(huerfanos)}"


@sin_corpus
def test_lo_excluido_suma_exactamente_lo_que_dice_el_adr_0007():
    """201 fragmentos, no 'unos doscientos': el ADR y el comprobador de la carga usan ese numero."""
    excluidas = {e["clave"] for e in MAPEO if e.get("excluido")}
    fuera = sum(1 for f in leer(FRAGMENTOS)
                if f"{f['titulacion']}/{f['asignatura']}" in excluidas)
    assert fuera == 201, f"el ADR 0007 dice 201 y el indice tiene {fuera}"
