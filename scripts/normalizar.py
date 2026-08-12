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

RE_DIGITOS = re.compile(r"\d+")


def firma_de_linea(linea: str) -> str:
    """La linea con los numeros borrados. Dos cabeceras corridas que solo se diferencian en el
    numero de pagina son LA MISMA cabecera, y contarlas por separado era lo que las salvaba:
    'TEMA 6-1 Pagina 139 I.S.O.' aparece una vez, y su firma, cuarenta."""
    return RE_DIGITOS.sub("#", " ".join(linea.split()))


LARGO_DE_CABECERA = 90   # medido: la cabecera mas larga del corpus tiene 78 caracteres
# Pie con firma de autor: acaba en "Tema 6", "Pagina 12", "Unidad 3".
RE_PIE_DE_AUTOR = re.compile(r"(?:tema|unidad|cap[ií]tulo|p[aá]g(?:ina)?\.?)\s*#\s*$", re.I)


def lineas_del_borde(pagina: str) -> set:
    """Las dos primeras lineas de la pagina y las dos ultimas, si son cortas.

    Las dos condiciones son las que impiden que baste con repetirse, y las dos salieron de un
    fallo real. Sin la POSICION, bajar el umbral a un tercio se llevaba frases de contenido de un
    manual de Proxmox que repite "Introduzca el nombre (hostname del servidor)." en varias
    paginas. Sin el LARGO, un parrafo entero que solo cambia en un numero de una pagina a otra
    entraba como cabecera. Una cabecera de verdad es corta y vive en el borde.
    """
    lineas = [x.strip() for x in pagina.split("\n") if len(x.strip()) > 3]
    return {x for x in lineas[:2] + lineas[-2:] if len(x) <= LARGO_DE_CABECERA}


def mobiliario_de(paginas: list) -> set:
    """Lineas que se repiten en muchas paginas: cabeceras, pies y numeros de pagina.

    Se quitan porque, si no, cada trozo de 512 tokens se lleva pegado 'PROGRAMACION / CFGS DAW'.
    Medido en el corpus: un documento llegaba a 303 lineas repetidas mas de tres veces.

    Se cuenta por FIRMA y se devuelven las variantes crudas, que es lo que hay que borrar. El
    umbral baja a un tercio de las paginas porque una cabecera de seccion no sale en todo el
    documento: 'CFGS. DESARROLLO DE APLICACIONES WEB #.#' solo esta en su capitulo, y ahi estaba
    en el 20% de los fragmentos del muestreo."""
    if len(paginas) < 3:
        return set(), set()
    paginas_por_firma = collections.defaultdict(set)
    variantes = collections.defaultdict(set)
    for numero, pagina in enumerate(paginas):
        for linea in lineas_del_borde(pagina):
            firma = firma_de_linea(linea)
            paginas_por_firma[firma].add(numero)
            variantes[firma].add(linea)
    # Segunda pasada, en TODA la pagina y no solo en su borde, pero con el umbral en la mitad de
    # las paginas en vez de en un tercio. Es para la cabecera que el extractor no deja en el borde:
    # en DWEC06, "Jose Luis Comesaña Tema 6" cae en mitad de una tabla enorme y aun asi esta en
    # todas las paginas. Con la mitad de las paginas exigida, las frases repetidas de un manual
    # -tres de once en el de Proxmox- siguen a salvo.
    en_cualquier_sitio = collections.defaultdict(set)
    for numero, pagina in enumerate(paginas):
        for linea in {x.strip() for x in pagina.split("\n") if 3 < len(x.strip()) <= LARGO_DE_CABECERA}:
            en_cualquier_sitio[firma_de_linea(linea)].add(numero)
            variantes[firma_de_linea(linea)].add(linea)

    umbral = max(3, len(paginas) // 3)
    exactas, por_firma = set(), set()
    for firma, numeros in en_cualquier_sitio.items():
        if len(numeros) >= max(3, len(paginas) // 2):
            por_firma |= variantes[firma]
        # Y una regla estrecha para el pie con firma de autor: "... Jose Luis Comesaña Tema 6".
        # El extractor solo lo saca como linea propia en 7 de las 38 paginas de DWEC06, muy por
        # debajo de cualquier umbral razonable, asi que la frecuencia no basta. Se le pide en
        # cambio una forma muy concreta -acabar en "Tema N" o "Pagina N"- y repetirse identica al
        # menos tres veces. Una linea de contenido que acabe en "Tema 6" y salga tres veces
        # identica en el mismo documento no existe; una cabecera, si.
        elif len(numeros) >= 3 and RE_PIE_DE_AUTOR.search(firma):
            pie = {x for x in variantes[firma] if RE_PIE_DE_AUTOR.search(x)}
            # A los DOS conjuntos: `exactas` es lo que sobrevive al freno de mano, y `por_firma`
            # es lo que se poda en la pasada normal. Estando solo en el primero, esta regla no
            # borraba nada salvo que el freno llegara a saltar.
            exactas |= pie
            por_firma |= pie
    for firma, numeros in paginas_por_firma.items():
        if len(numeros) < umbral:
            continue
        por_firma |= variantes[firma]
        # La linea IDENTICA repetida en un tercio de las paginas es mobiliario sin discusion. La
        # que solo coincide en su firma es un candidato mas agresivo, y por eso van separadas: el
        # freno de mano deshace la agresiva y conserva la segura, en vez de deshacerlo todo.
        for variante in variantes[firma]:
            paginas_con_esa = sum(1 for p in paginas if variante in lineas_del_borde(p))
            if paginas_con_esa >= umbral:
                exactas.add(variante)
    return exactas, por_firma


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
    # Los saltos se normalizan UNA VEZ y aqui arriba, antes de contar nada. La primera version
    # contaba el mobiliario sobre las paginas crudas y luego filtraba sobre las paginas con los
    # \r ya convertidos: dos textos distintos, asi que "CFGS DAW" estaba en la lista de fuera y
    # aun asi no coincidia con ninguna linea. Es el mismo fallo de siempre -dos partes del codigo
    # con dos ideas de que es una linea- y por eso la normalizacion va antes que todo lo demas.
    paginas = [mobiliario.saltos_reales(p.extract_text() or "") for p in PdfReader(ruta).pages]
    exactas, por_firma = mobiliario_de(paginas)

    def podar(paginas: list, fuera: set, con_firma: bool) -> list:
        # Las variantes largas se borran ademas COMO SUBCADENA, porque el extractor no siempre las
        # deja en su linea: "Formacion y Orientacion Laboral Jose Luis Comesaña Tema 2" salia
        # pegado en mitad de un parrafo, y ahi el filtro por lineas no la ve. De largas para
        # cortas, y solo a partir de 12 caracteres: por debajo, borrar subcadenas come contenido.
        pegadas = sorted((x for x in fuera if len(x) >= 12), key=len, reverse=True)
        firmas = {firma_de_linea(x) for x in fuera} if con_firma else set()
        limpias = []
        for pagina in paginas:
            for cabecera in pegadas:
                pagina = pagina.replace(cabecera, " ")
            lineas, borde = [], lineas_del_borde(pagina)
            for linea in pagina.split("\n"):
                desnuda = linea.strip()
                # es_mobiliario cubre el viejo isdigit() y ademas "- 8 -" y "Tema 3 - 13 -", que
                # el filtro por frecuencia NO puede ver: cada numero de pagina es una linea
                # distinta y ninguna se repite lo bastante (scripts/mobiliario.py).
                if not desnuda or desnuda in fuera or mobiliario.es_mobiliario(desnuda):
                    continue
                # Por FIRMA solo se borra en el borde. Aplicarlo a toda la pagina era un agujero
                # serio: cualquier linea de contenido que solo se diferenciara de una cabecera en
                # un numero -"Parrafo 3-1...", "Ejercicio 4"- se borraba tambien, y en silencio.
                if desnuda in borde and firma_de_linea(desnuda) in firmas:
                    continue
                lineas.append(RE_PUNTOS_INDICE.sub(" ", desnuda))
            limpias.append("\n".join(lineas))
        return limpias

    # Freno de mano, en dos escalones. Si quitar mobiliario se lleva mas de la mitad del documento
    # es que la deteccion se equivoco, pero deshacerlo TODO tambien estaba mal: la regla por firma
    # es la agresiva y la de linea identica repetida es segura, asi que primero se deshace solo la
    # agresiva. Un filtro que puede vaciar un documento en silencio es peor que el ruido que quita;
    # uno que devuelve el ruido entero por culpa de su parte arriesgada, tambien.
    limpias_seguras = podar(paginas, exactas, con_firma=False)
    limpias = podar(paginas, por_firma, con_firma=True)
    entero = "\n\n".join(p.strip() for p in paginas if p.strip())
    podado = "\n\n".join(x for x in limpias if x.strip())
    # El contenido UNICO se mide sobre la poda SEGURA -la que quita solo lo que se repite identico-
    # y no sobre la agresiva ni sobre lo que devuelva el freno. Es lo que decide si el documento
    # aporta texto o es un dibujo con una cabecera repetida, y cada una de las otras dos opciones
    # se equivoca en un sentido distinto: midiendo sobre lo que devuelve el freno, siete mapas
    # conceptuales entraban como documentos; midiendo sobre la agresiva, un documento normal cuyos
    # parrafos comparten firma salia con cero caracteres utiles.
    unicos = len("\n\n".join(x for x in limpias_seguras if x.strip()))
    if por_firma and len(podado) < len(entero) // 2:
        limpias = limpias_seguras
        podado = "\n\n".join(x for x in limpias if x.strip())
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
    return unir_lineas_partidas(entero), len(paginas), unicos


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
