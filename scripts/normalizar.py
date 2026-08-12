#!/usr/bin/env python3
"""Encargo 1.3: pasa el corpus a texto limpio en un arbol espejo.

Escribe corpus/derivado/<misma ruta>.md y registra cada derivado en el manifiesto con
derivado_de, herramienta y herramienta_version, heredando licencia, densidad y plantado del
original (ADR 0004).

REGLA DE UN DOCUMENTO, UNA FUENTE. El corpus trae el mismo documento en varios formatos por todas
partes (en Programacion, 53 de sus 63 PDF tienen gemelo .odt o .docx). Normalizar los dos metiria
el mismo contenido dos veces: infla el indice, reparte el peso de recuperacion entre dos copias y
llena de falsos positivos el detector de conflictos del encargo 1.8, que es justo la pieza que
tiene que estar limpia para la demo. Asi que cuando hay gemelos se normaliza UNO, por este orden:

  1. markdown o html, si existen: ya son texto limpio y convertir un PDF para obtener lo que ya
     esta en markdown solo puede empeorarlo.
  2. PDF: es lo que el profesor publico, conserva el orden de lectura y cubre TODOS los documentos,
     incluidos los dibujos .odg, cuyo unico texto usable es su PDF exportado.
  3. odt o docx, solo si no hay PDF.

Medido antes de elegir (ver COBERTURA.md): PDF y ofimatico dan practicamente el mismo texto
(ninguno aporta contenido que el otro pierda; las palabras "solo en el PDF" resultaron ser puntos
de indice). El PDF trae mas mobiliario de pagina, pero ese ruido es sistematico y se quita por
regla; el del odt es irregular.

Los dibujos (.odg, .svg, .dia) NO se convierten: no son documentos de texto. Se declaran fuera y,
si tienen PDF, ese PDF es la fuente.

Uso:
    python scripts/normalizar.py --raiz corpus/daw/curso1/programacion
    python scripts/normalizar.py                      # todo el corpus
    python scripts/normalizar.py --simulacro          # no escribe nada, solo dice que haria
"""
import argparse
import collections
import hashlib
import json
import os
import re
import sys
import unicodedata
import zipfile
from xml.etree import ElementTree

import mobiliario
import pypdf
from pypdf import PdfReader

DERIVADO = "corpus/derivado"
MANIFIESTO = "corpus/manifiesto.jsonl"
YA_TEXTO = (".md", ".markdown", ".html", ".htm", ".txt")
OFIMATICO = (".odt", ".docx")
DIBUJOS = (".odg", ".svg", ".dia", ".vsd")
CONVERTIBLES = (".pdf",) + OFIMATICO
MINIMO_CARACTERES = 200          # por documento; por debajo, es un hallazgo, no un fichero
MINIMO_POR_PAGINA = 40           # PDF con menos que esto por pagina huele a escaneo sin OCR

RE_PUNTOS_INDICE = re.compile(r"\.{4,}\s*\d*")
RE_ESPACIOS = re.compile(r"[ \t]+")


def clave_documento(nombre: str) -> str:
    """Nombre sin extension, sin tildes y sin separadores: asi 'UD1_Ejercicios.docx' y
    'UD1_Ejercicios.pdf' caen en el mismo grupo."""
    base = os.path.splitext(nombre)[0].lower()
    base = unicodedata.normalize("NFKD", base)
    base = "".join(c for c in base if not unicodedata.combining(c))
    return "".join(c for c in base if c.isalnum())


def sha256(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


# --- extraccion por formato ---------------------------------------------------------------

def mobiliario_de(paginas: list) -> set:
    """Lineas que se repiten en muchas paginas: cabeceras, pies y numeros de pagina.

    Se quitan porque, si no, cada trozo de 512 tokens se lleva pegado 'PROGRAMACION / CFGS DAW'.
    Medido en el corpus: un documento llegaba a 303 lineas repetidas mas de tres veces."""
    if len(paginas) < 3:
        return set()
    cuenta = collections.Counter()
    for pagina in paginas:
        for linea in {x.strip() for x in pagina.split("\n") if len(x.strip()) > 3}:
            cuenta[linea] += 1
    umbral = max(3, len(paginas) // 2)
    return {linea for linea, n in cuenta.items() if n >= umbral}


RE_CODIGO = re.compile(r"[{};=<>]|\)\s*$|^\s*(?:public|private|import|package|class|if|for|while|"
                       r"return|System\.|int |String |void )")


def parece_codigo(linea: str) -> bool:
    return bool(RE_CODIGO.search(linea))


def unir_lineas_partidas(texto: str) -> str:
    """El PDF parte las frases por ancho de pagina: medido, el 91% de las lineas de un documento
    de Programacion quedaban cortadas a media frase, y eso troceado da fragmentos ilegibles.

    Se une SOLO cuando esta claro que es continuacion de prosa: la linea no acaba en puntuacion de
    cierre, es larga, y ni ella ni la siguiente parecen codigo. Esta asignatura esta llena de
    listados en Java y unir codigo seria peor que el problema que arregla."""
    salida = []
    for linea in texto.split("\n"):
        actual = linea.rstrip()
        if (salida and actual and len(salida[-1]) > 30
                and salida[-1][-1] not in ".:;!?)»\"•-–"
                and not parece_codigo(salida[-1]) and not parece_codigo(actual)
                and not actual[0].isupper() and actual[0].isalpha()):
            salida[-1] = salida[-1] + " " + actual
        else:
            salida.append(actual)
    return "\n".join(salida)


def texto_de_pdf(ruta: str) -> tuple:
    paginas = [(p.extract_text() or "") for p in PdfReader(ruta).pages]
    fuera = mobiliario_de(paginas)
    limpias = []
    for pagina in paginas:
        lineas = []
        for linea in mobiliario.saltos_reales(pagina).split("\n"):
            desnuda = linea.strip()
            # es_mobiliario cubre el viejo isdigit() y ademas "- 8 -" y "Tema 3 - 13 -", que el
            # filtro por frecuencia NO puede ver: cada numero de pagina es una linea distinta y
            # ninguna se repite lo suficiente para cruzar su umbral (scripts/mobiliario.py).
            if not desnuda or desnuda in fuera or mobiliario.es_mobiliario(desnuda):
                continue
            lineas.append(RE_PUNTOS_INDICE.sub(" ", desnuda))
        limpias.append("\n".join(lineas))

    # Freno de mano: si quitar "mobiliario" se lleva mas de la mitad del documento, es que la
    # deteccion se ha equivocado (paginas muy repetitivas, un boletin de ejercicios con la misma
    # plantilla) y prefiere quedarse con el ruido antes que perder contenido. Un filtro de limpieza
    # que puede vaciar un documento en silencio es peor que el ruido que quita.
    podado = "\n\n".join(x for x in limpias if x.strip())
    if fuera:
        entero = "\n\n".join(p.strip() for p in paginas if p.strip())
        if len(podado) < len(entero) // 2:
            limpias = [p.strip() for p in paginas]
    # El tercer valor es el contenido UNICO (sin lo repetido en todas las paginas): es lo que
    # decide si el documento aporta texto o es un dibujo con cabecera. Si se midiera sobre el texto
    # restaurado por el freno de mano, tres mapas conceptuales del corpus entraban como documentos
    # cuando en realidad son un encabezado repetido y un titulo por pagina.
    # La limpieza de mobiliario va TAMBIEN despues del freno de mano: si el freno restaura las
    # paginas crudas, el documento vuelve con sus numeros de pagina dentro. Quitar formas no puede
    # vaciar un documento -solo se lleva lineas que son un numero-, asi que aqui no hace falta freno.
    entero = mobiliario.limpiar("\n\n".join(x for x in limpias if x.strip()))
    return unir_lineas_partidas(entero), len(paginas), len(podado)


def _texto_de_nodo(nodo) -> str:
    return "".join(nodo.itertext())


def texto_de_odt(ruta: str) -> tuple:
    """ODT es un zip con content.xml dentro: se lee con la libreria estandar, sin dependencias."""
    ns = {"text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
    with zipfile.ZipFile(ruta) as z:
        arbol = ElementTree.fromstring(z.read("content.xml"))
    lineas = []
    for nodo in arbol.iter():
        etiqueta = nodo.tag.split("}")[-1]
        if etiqueta == "h":
            nivel = int(nodo.get(f"{{{ns['text']}}}outline-level", "1") or 1)
            texto = _texto_de_nodo(nodo).strip()
            if texto:
                lineas.append("#" * min(nivel, 6) + " " + texto)
        elif etiqueta == "p":
            texto = _texto_de_nodo(nodo).strip()
            if texto:
                lineas.append(texto)
    unido = "\n\n".join(lineas)
    return unido, 0, len(unido)


def texto_de_docx(ruta: str) -> tuple:
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(ruta) as z:
        arbol = ElementTree.fromstring(z.read("word/document.xml"))
    lineas = []
    for parrafo in arbol.iter(f"{w}p"):
        texto = "".join(t.text or "" for t in parrafo.iter(f"{w}t")).strip()
        if not texto:
            continue
        estilo = parrafo.find(f"{w}pPr/{w}pStyle")
        nombre = (estilo.get(f"{w}val") if estilo is not None else "") or ""
        m = re.search(r"(?:Heading|Ttulo|Titulo)(\d)", nombre)
        lineas.append(("#" * min(int(m.group(1)), 6) + " " + texto) if m else texto)
    unido = "\n\n".join(lineas)
    return unido, 0, len(unido)


EXTRACTORES = {".pdf": texto_de_pdf, ".odt": texto_de_odt, ".docx": texto_de_docx}
HERRAMIENTAS = {".pdf": ("pypdf", pypdf.__version__),
                ".odt": ("xml.etree (stdlib)", f"python {sys.version_info.major}."
                                               f"{sys.version_info.minor}"),
                ".docx": ("xml.etree (stdlib)", f"python {sys.version_info.major}."
                                                f"{sys.version_info.minor}")}


# --- eleccion de fuente -------------------------------------------------------------------

def elegir_fuentes(raiz: str) -> tuple:
    """Devuelve (a_convertir, descartados, dibujos) aplicando la regla de un documento, una
    fuente."""
    grupos = collections.defaultdict(list)
    for base, _, ficheros in os.walk(raiz):
        base = base.replace(os.sep, "/")
        if base.startswith(DERIVADO):
            continue
        for nombre in ficheros:
            grupos[(base, clave_documento(nombre))].append(f"{base}/{nombre}")

    a_convertir, descartados, dibujos = [], [], []
    for (_, _), rutas in sorted(grupos.items()):
        por_ext = {os.path.splitext(r)[1].lower(): r for r in sorted(rutas)}
        dibujos += [r for e, r in por_ext.items() if e in DIBUJOS]
        texto = [r for e, r in por_ext.items() if e in YA_TEXTO]
        convertibles = {e: r for e, r in por_ext.items() if e in CONVERTIBLES}
        if not convertibles:
            continue
        if texto:
            descartados += [(r, f"ya hay texto limpio: {os.path.basename(texto[0])}")
                            for r in convertibles.values()]
            continue
        elegida = convertibles.get(".pdf") or next(iter(convertibles.values()))
        a_convertir.append(elegida)
        descartados += [(r, f"gemelo de {os.path.basename(elegida)}")
                        for r in convertibles.values() if r != elegida]
    return a_convertir, descartados, dibujos


# --- manifiesto ---------------------------------------------------------------------------

def cargar_manifiesto() -> list:
    with open(MANIFIESTO, encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


def guardar_manifiesto(entradas: list):
    with open(MANIFIESTO, "w", encoding="utf-8", newline="\n") as f:
        for e in entradas:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Normaliza el corpus a texto (encargo 1.3).")
    p.add_argument("--raiz", default="corpus", help="parte del corpus a normalizar")
    p.add_argument("--simulacro", action="store_true", help="no escribe nada")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    a_convertir, descartados, dibujos = elegir_fuentes(a.raiz)
    print(f"documentos a convertir: {len(a_convertir)} | descartados por gemelo: {len(descartados)}"
          f" | dibujos excluidos: {len(dibujos)}")
    if a.simulacro:
        for r in a_convertir:
            print("  CONVERTIRIA:", r)
        for r, motivo in sorted(descartados):
            print(f"  DESCARTADO:  {r}  ({motivo})")
        for r in sorted(dibujos):
            print("  DIBUJO:      ", r)
        return 0

    entradas = cargar_manifiesto()
    por_ruta = {e["ruta"]: e for e in entradas}
    hallazgos, escritos = [], 0
    for origen in a_convertir:
        ext = os.path.splitext(origen)[1].lower()
        destino = f"{DERIVADO}/{origen[len('corpus/'):]}.md"

        def descartar(motivo: str, origen=origen, destino=destino):
            """Un documento que hoy no da texto util no puede dejar en el arbol el derivado que
            genero una pasada antigua con otras reglas. Cuatro mapas conceptuales seguian ahi,
            aportando al indice paginas enteras de numeros sueltos."""
            hallazgos.append((origen, motivo))
            if os.path.exists(destino):
                os.remove(destino)
                print(f"  BORRADO EL DERIVADO VIEJO (hoy no da texto util): {destino}")

        try:
            texto, paginas, utiles = EXTRACTORES[ext](origen)
        except Exception as e:  # noqa: BLE001 - un documento roto no puede tumbar la pasada
            descartar(f"{type(e).__name__}: {e}")
            continue
        texto = RE_ESPACIOS.sub(" ", mobiliario.saltos_reales(texto)).strip()
        if len(texto) < MINIMO_CARACTERES:
            descartar(f"solo {len(texto)} caracteres")
            continue
        if paginas and utiles / paginas < MINIMO_POR_PAGINA:
            descartar(f"{utiles // paginas} caracteres unicos por pagina: dibujo o escaneo sin "
                      f"OCR, no documento")
            continue

        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto + "\n")
        escritos += 1

        original = por_ruta.get(origen, {})
        herramienta, version = HERRAMIENTAS[ext]
        nueva = {
            "ruta": destino, "fuente": f"normalizado de {origen}",
            "licencia": original.get("licencia", "sin licencia declarada"),
            "version_corpus": original.get("version_corpus", "v3-2026-08-11"),
            "hash_sha256": sha256(destino),
            "densidad": original.get("densidad", "parcial"),
            "plantado": original.get("plantado", False),
            "derivado_de": origen, "herramienta": herramienta, "herramienta_version": version,
        }
        if destino in por_ruta:
            por_ruta[destino].update(nueva)
        else:
            entradas.append(nueva)
            por_ruta[destino] = nueva

    # El arbol derivado es de este script, asi que tambien le toca dar de baja lo que ya no
    # produce: un documento que deja de dar texto util (o que se descarta por gemelo) dejaria su
    # entrada huerfana y el verificador del 1.0 en rojo por un cambio querido. Solo se tocan
    # entradas bajo corpus/derivado/ y solo si el fichero ya no esta: nunca el corpus original.
    huerfanas = [e["ruta"] for e in entradas
                 if e["ruta"].startswith(DERIVADO + "/") and not os.path.exists(e["ruta"])]
    if huerfanas:
        entradas = [e for e in entradas if e["ruta"] not in set(huerfanas)]
        for ruta in huerfanas:
            print(f"  DADO DE BAJA (ya no se genera): {ruta}")

    guardar_manifiesto(entradas)
    print(f"derivados escritos: {escritos} -> {DERIVADO}/")
    for ruta, motivo in hallazgos:
        print(f"  SIN TEXTO UTIL: {ruta} ({motivo})")
    print(f"hallazgos: {len(hallazgos)}")
    return 1 if hallazgos else 0


if __name__ == "__main__":
    sys.exit(main())
