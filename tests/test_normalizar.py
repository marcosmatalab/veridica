"""Tests del normalizador (encargo 1.3).

Los dos anclados son los que costaron medidas de verdad:
  - la regla de un documento, una fuente: con gemelos, se convierte UNO. Sin ella, Programacion
    entraba dos veces (53 de sus 63 PDF tienen gemelo .odt o .docx) y el detector de conflictos
    del 1.8 se llenaba de falsos positivos.
  - unir prosa partida SIN unir codigo: la asignatura curada esta llena de listados en Java.
"""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from fpdf import FPDF

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "scripts" / "normalizar.py"


def cargar():
    import importlib.util
    spec = importlib.util.spec_from_file_location("normalizar", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


nz = cargar()


def crear(raiz: Path, *nombres):
    for n in nombres:
        destino = raiz / n
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text("x", encoding="utf-8")


# --- regla de un documento, una fuente ------------------------------------------------------

def test_con_gemelos_gana_el_pdf(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    crear(tmp_path, "corpus/u1/UD1_Ejercicios.pdf", "corpus/u1/UD1_Ejercicios.docx",
          "corpus/u1/ud4_Java.pdf", "corpus/u1/ud4_Java.odt")
    convertir, descartados, _ = nz.elegir_fuentes("corpus")
    assert sorted(convertir) == ["corpus/u1/UD1_Ejercicios.pdf", "corpus/u1/ud4_Java.pdf"]
    assert {r for r, _ in descartados} == {"corpus/u1/UD1_Ejercicios.docx", "corpus/u1/ud4_Java.odt"}


def test_si_ya_hay_markdown_no_se_convierte_nada(tmp_path, monkeypatch):
    """Convertir un PDF para obtener lo que ya esta en markdown solo puede empeorarlo."""
    monkeypatch.chdir(tmp_path)
    crear(tmp_path, "corpus/u1/tema.md", "corpus/u1/tema.pdf")
    convertir, descartados, _ = nz.elegir_fuentes("corpus")
    assert convertir == []
    assert descartados and "ya hay texto limpio" in descartados[0][1]


def test_los_dibujos_ni_se_convierten_ni_se_pierden(tmp_path, monkeypatch):
    """Un .odg es un dibujo de LibreOffice, no un documento: se declara fuera y manda su PDF."""
    monkeypatch.chdir(tmp_path)
    crear(tmp_path, "corpus/u1/esquema.odg", "corpus/u1/esquema.pdf", "corpus/u1/suelto.odg")
    convertir, _, dibujos = nz.elegir_fuentes("corpus")
    assert convertir == ["corpus/u1/esquema.pdf"]
    assert sorted(dibujos) == ["corpus/u1/esquema.odg", "corpus/u1/suelto.odg"]


def test_el_gemelo_se_reconoce_aunque_cambien_tildes_y_mayusculas(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    crear(tmp_path, "corpus/u1/Programación_del_módulo.pdf", "corpus/u1/programacion_del_modulo.odt")
    convertir, descartados, _ = nz.elegir_fuentes("corpus")
    assert len(convertir) == 1 and len(descartados) == 1


# --- limpieza del texto ---------------------------------------------------------------------

def test_el_mobiliario_repetido_en_muchas_paginas_se_quita():
    paginas = ["PROGRAMACION\nCFGS DAW\ntexto propio de la pagina uno" for _ in range(9)]
    fuera = nz.mobiliario_de(paginas)
    assert "PROGRAMACION" in fuera and "CFGS DAW" in fuera


def test_una_linea_que_sale_una_vez_no_es_mobiliario():
    paginas = ["cabecera\nesto solo sale aqui"] + ["cabecera\notra cosa"] * 8
    assert "esto solo sale aqui" not in nz.mobiliario_de(paginas)


def test_el_filtro_de_mobiliario_no_puede_vaciar_un_documento(tmp_path):
    """Con paginas casi identicas (un boletin con la misma plantilla), TODAS las lineas parecen
    mobiliario. Antes del freno de mano, ese documento salia con cero caracteres en silencio."""
    pdf = FPDF()
    pdf.set_font("helvetica", size=11)
    for _ in range(5):
        pdf.add_page()
        for i in range(8):
            pdf.cell(0, 5, f"Enunciado repetido numero {i} en todas las paginas.",
                     new_x="LMARGIN", new_y="NEXT")
    destino = tmp_path / "repetido.pdf"
    pdf.output(str(destino))
    texto, _, _ = nz.texto_de_pdf(str(destino))
    assert len(texto) > 200, "el documento se ha quedado sin contenido"


def test_une_la_prosa_que_el_pdf_partio():
    texto = ("El sistema de ficheros organiza la informacion en directorios y\n"
             "subdirectorios que cuelgan de una raiz comun.")
    assert nz.unir_lineas_partidas(texto).count("\n") == 0


def test_no_une_lineas_de_codigo(tmp_path):
    """EL caso anclado: unir listados de Java destrozaria la asignatura curada."""
    codigo = ("public static void main(String[] args) {\n"
              "int valor = lector.nextInt();\n"
              "writer.write(8);\n"
              "}")
    assert nz.unir_lineas_partidas(codigo) == codigo


# --- lectura de ofimatica sin dependencias nuevas --------------------------------------------

def escribir_odt(destino: Path) -> str:
    contenido = ("<?xml version='1.0'?><office:document-content "
                 "xmlns:office='urn:oasis:names:tc:opendocument:xmlns:office:1.0' "
                 "xmlns:text='urn:oasis:names:tc:opendocument:xmlns:text:1.0'><office:body>"
                 "<text:h text:outline-level='1'>Titulo de la unidad</text:h>"
                 "<text:p>Un parrafo con contenido suficiente.</text:p>"
                 "</office:body></office:document-content>")
    with zipfile.ZipFile(destino, "w") as z:
        z.writestr("content.xml", contenido)
    return str(destino)


def test_el_odt_se_lee_con_la_libreria_estandar(tmp_path):
    texto, _, _ = nz.texto_de_odt(escribir_odt(tmp_path / "t.odt"))
    assert texto.startswith("# Titulo de la unidad")
    assert "Un parrafo con contenido suficiente." in texto


# --- de punta a punta -------------------------------------------------------------------------

@pytest.fixture
def corpus_de_juguete(tmp_path):
    (tmp_path / "corpus" / "u1").mkdir(parents=True)
    pdf = FPDF()
    pdf.set_font("helvetica", size=11)
    for pagina in range(4):
        pdf.add_page()
        pdf.cell(0, 5, "CFGS DAW", new_x="LMARGIN", new_y="NEXT")          # mobiliario
        for i in range(12):
            pdf.cell(0, 5, f"Parrafo {pagina}-{i} con contenido docente distinto en cada pagina.",
                     new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(tmp_path / "corpus/u1/tema.pdf"))
    original = {"ruta": "corpus/u1/tema.pdf", "fuente": "apuntes", "licencia": "CC BY-NC-SA 4.0",
                "version_corpus": "v3-2026-08-11", "hash_sha256": "0" * 64,
                "densidad": "completa", "plantado": True}
    with open(tmp_path / "corpus/manifiesto.jsonl", "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(original, ensure_ascii=False) + "\n")
    return tmp_path


def test_el_derivado_se_registra_con_su_procedencia_y_hereda_licencia(corpus_de_juguete):
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=corpus_de_juguete,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    derivado = corpus_de_juguete / "corpus/derivado/u1/tema.pdf.md"
    assert derivado.exists()
    assert "CFGS DAW" not in derivado.read_text(encoding="utf-8"), "el mobiliario debia irse"

    entradas = [json.loads(x) for x in
                (corpus_de_juguete / "corpus/manifiesto.jsonl").read_text(encoding="utf-8").split("\n")
                if x.strip()]
    nueva = [e for e in entradas if e["ruta"].startswith("corpus/derivado")][0]
    assert nueva["derivado_de"] == "corpus/u1/tema.pdf"      # ADR 0004
    assert nueva["herramienta"] == "pypdf" and nueva["herramienta_version"]
    assert nueva["licencia"] == "CC BY-NC-SA 4.0"            # hereda la del original
    assert nueva["plantado"] is True                          # y su marca de plantado


def test_un_pdf_sin_texto_util_es_un_hallazgo_no_un_fichero(corpus_de_juguete):
    """Los mapas conceptuales del corpus real son dibujos: 37 caracteres por pagina."""
    vacio = FPDF()
    vacio.set_font("helvetica", size=11)
    for _ in range(4):
        vacio.add_page()
        vacio.cell(0, 5, "fig.", new_x="LMARGIN", new_y="NEXT")
    vacio.output(str(corpus_de_juguete / "corpus/u1/mapas.pdf"))
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=corpus_de_juguete,
                       capture_output=True, text=True)
    assert r.returncode == 1
    assert "SIN TEXTO UTIL" in r.stdout and "mapas.pdf" in r.stdout
    assert not (corpus_de_juguete / "corpus/derivado/u1/mapas.pdf.md").exists()
