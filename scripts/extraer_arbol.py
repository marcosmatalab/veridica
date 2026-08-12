#!/usr/bin/env python3
"""Encargo 1.1: extrae el arbol oficial de las tres titulaciones desde los PDF del BOE.

Escribe corpus/arbol_oficial.jsonl, UNA LINEA POR NODO (titulacion, asignatura, unidad,
resultado_aprendizaje), cada uno con la referencia legal de donde sale: norma, documento y pagina
del PDF. Asi el arbol se revisa con diff, no depende de que Postgres este levantado y sobrevive a
un 'down -v'. La carga a base de datos es del encargo 2.1, no de aqui.

Fuentes, que NO son las mismas para las tres:
  DAW  RD 686/2010, ACTUALIZADO por el RD 405/2023 (articulo tercero), mas la Orden EDU/2887/2010
       (curriculo), que amplia contenidos modulo a modulo y trae la secuenciacion por curso.
  DAM  RD 450/2010, ACTUALIZADO por el RD 405/2023 (articulo segundo). Sin orden de curriculo.
  ASIR RD 1629/2009. El RD 405/2023 no lo toca. Sin orden de curriculo.

Consecuencia declarada, no disimulada: las unidades de DAW salen mas finas que las de sus hermanas
porque tienen una fuente mas. No es un fallo del extractor, es la fuente.

El campo 'curso' SOLO se rellena donde una norma lo dice. La orden de curriculo de DAW fija el
reparto en su Anexo II (tabla de secuenciacion, leida por coordenadas para no confundir columnas).
Para DAM y ASIR no hay fuente estatal del curso: el campo va a null con su motivo. Jamas se deduce
de lo que "suele ser": un fichero que presume de referencia legal por nodo no puede llevar campos
a ojo.

Uso:
    python scripts/extraer_arbol.py                 # escribe corpus/arbol_oficial.jsonl
    python scripts/extraer_arbol.py --salida x.jsonl --muestreo docs/muestreo.md
"""
import argparse
import datetime
import json
import os
import re
import sys
import unicodedata

import pdfplumber
from pypdf import PdfReader

NORMATIVA = {
    "daw": {
        "nombre": "Técnico Superior en Desarrollo de Aplicaciones Web",
        "titulo": ("RD 686/2010", "corpus/daw/normativa/RD-686-2010-titulo-DAW.pdf"),
        "actualiza": ("RD 405/2023", "corpus/daw/normativa/RD-405-2023-actualizacion-DAW-DAM.pdf",
                      "tercero"),
        "curriculo": ("Orden EDU/2887/2010",
                      "corpus/daw/normativa/Orden-EDU-2887-2010-curriculo-DAW.pdf"),
    },
    "dam": {
        "nombre": "Técnico Superior en Desarrollo de Aplicaciones Multiplataforma",
        "titulo": ("RD 450/2010", "corpus/dam/normativa/RD-450-2010-titulo-DAM.pdf"),
        "actualiza": ("RD 405/2023", "corpus/daw/normativa/RD-405-2023-actualizacion-DAW-DAM.pdf",
                      "segundo"),
        "curriculo": None,
    },
    "asir": {
        "nombre": "Técnico Superior en Administración de Sistemas Informáticos en Red",
        "titulo": ("RD 1629/2009", "corpus/asir/normativa/RD-1629-2009-titulo-ASIR.pdf"),
        "actualiza": None,
        "curriculo": None,
    },
}

SIN_FUENTE_DE_CURSO = ("sin fuente estatal: no hay orden de curriculo de esta titulacion en el "
                       "corpus, y el reparto por curso no lo fija el real decreto del titulo")

# Ultimo caracter con contenido de una linea que CONTINUA en la siguiente. El texto envuelto se
# parte a media frase, asi que nunca termina en punto: "...y proteccion \nambiental:". Ese punto es
# lo unico que separa un nombre partido de un elemento de lista seguido de un encabezado entero
# ("- VLAN. Etiquetado de tramas. IEEE802.1Q.\nConfiguracion y administracion de protocolos..."),
# que sin este guardian se fusionaban en un nodo inventado. Lo cazo el diff, no los tests.
CORTE_DE_LINEA = r"[^\n:.\s]"

# El nombre del modulo PUEDE partirse en dos lineas: el BOE lo hace en 3 de las 74 cabeceras de los
# cinco documentos (DAW 0373, DAM 0373 y ASIR 0379). Con [^\n] el nombre salia cortado por el salto
# y NADIE se enteraba, porque el modulo se extraia igual y con su codigo correcto: solo le faltaba
# la ultima palabra ("...sistemas de gestion de" en vez de "...de informacion").
# La continuacion se corta ante una etiqueta de campo y ante cualquier linea que lleve ':', que es
# justo lo que separa "de \ninformacion." de "Equivalencia en creditos ECTS: 7".
RE_MODULO = re.compile(
    r"M[oó]dulo\s+[Pp]rofesional:[ \t]*"
    r"(?P<nombre>"
    r"[^\n:]{2,89}" + CORTE_DE_LINEA + r"[ \t]*\n[ \t]*"
    r"(?!(?:Equivalencia|C[oó]digo|Duraci[oó]n|Resultados|Contenidos|M[oó]dulo)\b)[^\n:]{1,60}"
    r"|[^\n]{3,90})"
    r"[ \t]*\n"
    r"(?:[^\n]*\n){0,2}?\s*C[oó]digo:\s*(?P<codigo>\d{4})", re.M)
RE_RA = re.compile(r"^\s*(\d{1,2})\.\s+(.{15,400}?)\s*Criterios de evaluaci[oó]n:", re.M | re.S)

# Los encabezados de unidad fallaban por DOS sitios, y los dos en silencio:
#   1. dos puntos DENTRO del nombre. Con [^\n:] el corte caia en el primer ':', no en el que cierra
#      el encabezado. Si los dos puntos internos van a mitad de linea el encabezado no casaba y la
#      unidad desaparecia entera (ASIR 0371 y 0377); si van al final, salia truncada (DAW 0612).
#   2. encabezado partido en dos lineas, que no casaba y borraba la unidad (ASIR 0371 y 0375,
#      DAM 0487 y DAW 0616).
# El cierre real es el ':' que termina la linea, no el primero que aparece: por eso el nombre va
# greedy y el ancla la pone lo que viene DESPUES (salto y vineta). La rama de dos lineas exige que
# la primera NO lleve ':' (si lo llevara, ya seria un encabezado completo) y que la segunda no
# empiece por vineta (seria un elemento de la lista, no la cola del nombre).
RE_BLOQUE_RD = re.compile(
    r"^[ \t]*([A-ZÁÉÍÓÚÑ](?:"
    r"[^\n:]{3,89}" + CORTE_DE_LINEA + r"[ \t]*\n[ \t]*(?![−–\-•])[^\n:]{1,70}"
    r"|[^\n]{4,90}))"
    r":[ \t]*\n[ \t]*[−–-]", re.M)
RE_BLOQUE_ORDEN = re.compile(
    r"^[ \t]*[a-z]\)[ \t]*((?:"
    r"[^\n:]{4,94}" + CORTE_DE_LINEA + r"[ \t]*\n[ \t]*(?![−–\-•])[^\n:]{1,70}"
    r"|[^\n]{4,95}))"
    r":[ \t]*$", re.M)


# Mobiliario de pagina del BOE. Se quita ANTES de parsear porque cae en mitad de las frases
# cuando un modulo cruza de pagina: por eso el 0483 de DAM se leia del RD de 2010 en vez de su
# actualizacion, y por eso algun resultado de aprendizaje se llevaba pegada media cabecera.
RE_MOBILIARIO = re.compile(
    r"^(?:BOLET[IÍ]N OFICIAL DEL ESTADO"
    r"|N[uú]m\.\s*\d+\s+.{0,40}\s+Sec\..{0,30}P[aá]g\.\s*[\d.]+"
    r"|cve:\s*BOE-[\w-]+"
    r"|Verificable en\s+https?://\S+"
    r"|ISSN:\s*[\d-]+"
    r"|D\.\s*L\.:.*"
    r"|https?://\S+)\s*$", re.M | re.I)


def limpiar(texto: str) -> str:
    return " ".join(texto.replace("\xa0", " ").replace(" ", " ").split()).strip(" .")


def paginas_de(pdf: str) -> list:
    return [RE_MOBILIARIO.sub("", p.extract_text() or "") for p in PdfReader(pdf).pages]


def texto_con_paginas(paginas: list) -> tuple:
    """Devuelve el texto entero y una lista de (posicion_inicial, numero_de_pagina)."""
    trozos, indice, pos = [], [], 0
    for numero, texto in enumerate(paginas, 1):
        indice.append((pos, numero))
        trozos.append(texto + "\n")
        pos += len(texto) + 1
    return "".join(trozos), indice


def pagina_de(indice: list, posicion: int) -> int:
    numero = 1
    for inicio, n in indice:
        if inicio > posicion:
            break
        numero = n
    return numero


# El BOE no es coherente consigo mismo: en los cinco documentos conviven "Contenidos basicos:",
# "Contenidos basicos.", "Contenidos:" y "Contenidos.". Exigir los dos puntos dejaba sin unidades
# a modulos enteros (ASIR 0378, DAM 0489 y 0490) en silencio. Anclado a principio de linea para no
# tragarse la palabra "contenidos" en mitad de una frase.
# SIN re.I, y esto no es cosmetica: los criterios de evaluacion hablan de "la sindicacion de
# contenidos", y cuando esa frase envuelve, la palabra "contenidos." queda sola a principio de
# linea y casaba como si fuera el encabezado. La seccion de 0373 (DAW y DAM) empezaba entonces a
# mitad de los criterios, decenas de lineas antes de donde debe. Lo destapo la sonda de
# encabezados sueltos, que denunciaba "Criterios de evaluacion" dentro de la seccion de
# contenidos: si la sonda ve eso, es que la seccion esta mal acotada. Comprobado en los cinco
# documentos: los 67 encabezados de verdad van todos con mayuscula, y lo unico que se pierde al
# quitar re.I son los 7 "contenidos." en minuscula.
RE_INICIO_CONTENIDOS = re.compile(r"^[ \t]*Contenidos(?:\s+b[aá]sicos)?\s*[:.]", re.M)
# A PROPOSITO mas laxo que el anterior, y usado SOLO para auditar: si el detector de "este modulo
# declara contenidos" comparte el patron con el que trocea, un encabezado que el patron no
# reconozca deja el modulo mudo Y sin denunciar, que es como se colo el fallo de ASIR 0378.
# El auditor no puede compartir la suposicion del parser.
# Laxo con la puntuacion (da igual ':' que '.' que nada) pero exigente en que el encabezado sea la
# linea ENTERA: sin el final de linea se tragaba frases partidas que empiezan por "contenidos".
# CONSERVA re.I aunque el parser lo haya perdido, y a proposito: el auditor se equivoca hacia el
# ruido (puede gritar "modulo mudo" de mas por un "contenidos." envuelto) y nunca hacia el
# silencio. Si aqui se copiara la mayuscula del parser, los dos compartirian el mismo supuesto y
# un encabezado en minuscula dejaria el modulo mudo Y sin denunciar.
RE_CONTENIDOS_LAXO = re.compile(r"^[ \t]*Contenidos(?:\s+b[aá]sicos)?[ \t]*[:.]?[ \t]*$", re.I | re.M)
RE_FIN_CONTENIDOS = re.compile(r"Orientaciones\s+pedag[oó]gicas|Este m[oó]dulo profesional contiene",
                               re.I)


def seccion_de_contenidos(cuerpo: str) -> tuple:
    """Acota la busqueda de unidades a la seccion de contenidos del modulo.

    Sin esto se colaban como 'unidad' frases del apartado de orientaciones pedagogicas que
    terminan en dos puntos y llevan una lista debajo (por ejemplo 'La funcion de programacion de
    bases de datos incluye aspectos como:'). Lo cazo el muestreo a mano, no los tests."""
    inicio = RE_INICIO_CONTENIDOS.search(cuerpo)
    if not inicio:
        return 0, 0
    fin = RE_FIN_CONTENIDOS.search(cuerpo, inicio.end())
    return inicio.end(), fin.start() if fin else len(cuerpo)


def modulos_de(texto: str, indice: list, patron_bloques) -> dict:
    """Corta el texto por modulos y saca de cada uno sus RA y sus bloques de contenido."""
    encontrados = list(RE_MODULO.finditer(texto))
    modulos = {}
    for n, m in enumerate(encontrados):
        fin = encontrados[n + 1].start() if n + 1 < len(encontrados) else len(texto)
        cuerpo = texto[m.end():fin]
        desde, hasta = seccion_de_contenidos(cuerpo)
        codigo = m.group("codigo")
        modulos[codigo] = {
            "codigo": codigo,
            "nombre": limpiar(m.group("nombre")),
            "pagina": pagina_de(indice, m.start()),
            # Si el modulo declara contenidos, tiene que salir con unidades: la diferencia entre
            # "esta norma no da contenidos para este modulo" (proyecto, FCT) y "el extractor se
            # los ha comido" no se puede dejar al ojo de nadie.
            "declara_contenidos": bool(RE_CONTENIDOS_LAXO.search(cuerpo)),
            "resultados": [limpiar(ra) for _, ra in RE_RA.findall(cuerpo)],
            "unidades": [(limpiar(b.group(1)), pagina_de(indice, m.end() + desde + b.start()))
                         for b in patron_bloques.finditer(cuerpo[desde:hasta])],
        }
        modulos[codigo]["encabezados_sueltos"] = encabezados_sin_unidad(
            cuerpo[desde:hasta], [n for n, _ in modulos[codigo]["unidades"]])
    return modulos


def rango_del_articulo(texto: str, ordinal: str) -> tuple:
    """El RD 405/2023 actualiza DAM en su articulo segundo y DAW en el tercero: hay que cortar."""
    orden = ["primero", "segundo", "tercero", "cuarto"]
    inicio = re.search(rf"Art[ií]culo\s+{ordinal}\.", texto)
    if not inicio:
        return None
    siguiente = orden[orden.index(ordinal) + 1] if ordinal in orden[:-1] else None
    fin = re.search(rf"Art[ií]culo\s+{siguiente}\.", texto) if siguiente else None
    return (inicio.start(), fin.start() if fin else len(texto))


def secuenciacion_daw(pdf: str) -> dict:
    """Lee el Anexo II (curso y horas por modulo) POR COORDENADAS.

    En texto plano las columnas se pisan y no se sabe si un 5 es de primero o de segundo. Aqui se
    mira la x de cada numero contra la x de su cabecera, que es leer la tabla, no adivinarla.
    """
    with pdfplumber.open(pdf) as doc:
        for numero, pagina in enumerate(doc.pages, 1):
            palabras = pagina.extract_words()
            texto = " ".join(w["text"] for w in palabras)
            if "Secuenciación y distribución horaria" not in texto:
                continue
            columnas = {}
            for w in palabras:
                if w["text"] == "Primer":
                    columnas["primero"] = w["x0"]
                elif w["text"] == "Segundo":
                    columnas["segundo"] = w["x0"]
            if "primero" not in columnas or "segundo" not in columnas:
                return {}
            frontera = (columnas["primero"] + columnas["segundo"]) / 2
            filas = {}
            for w in palabras:
                filas.setdefault(round(w["top"]), []).append(w)
            secuencia = {}
            for _, ws in sorted(filas.items()):
                ws = sorted(ws, key=lambda w: w["x0"])
                linea = " ".join(w["text"] for w in ws)
                m = re.match(r"^(\d{4})\.", linea)
                if not m:
                    continue
                numeros = [w for w in ws if re.fullmatch(r"\d+", w["text"]) and w["x0"] > 315]
                if not numeros:
                    continue
                horas = int(numeros[0]["text"])
                curso = 1 if all(w["x0"] < frontera for w in numeros[1:]) else 2
                if len(numeros) == 1:
                    curso = None
                secuencia[m.group(1)] = {"curso": curso, "horas": horas, "pagina": numero}
            return secuencia
    return {}


def nodos_de_titulacion(clave: str) -> tuple:
    cfg = NORMATIVA[clave]
    norma_titulo, pdf_titulo = cfg["titulo"]
    texto, indice = texto_con_paginas(paginas_de(pdf_titulo))
    modulos = modulos_de(texto, indice, RE_BLOQUE_RD)
    for datos in modulos.values():
        datos["fuente"] = {"norma": norma_titulo, "documento": pdf_titulo, "pagina": datos["pagina"]}
        datos["fuente_unidades"] = datos["fuente"]

    # El RD 405/2023 manda sobre el de 2010 en los modulos que reescribe.
    if cfg["actualiza"]:
        norma_act, pdf_act, articulo = cfg["actualiza"]
        texto_act, indice_act = texto_con_paginas(paginas_de(pdf_act))
        rango = rango_del_articulo(texto_act, articulo)
        if rango:
            desde, hasta = rango
            recorte = texto_act[desde:hasta]
            indice_recorte = [(p - desde, n) for p, n in indice_act if desde <= p < hasta]
            for codigo, datos in modulos_de(recorte, indice_recorte, RE_BLOQUE_RD).items():
                fuente = {"norma": norma_act, "documento": pdf_act, "pagina": datos["pagina"],
                          "nota": f"actualiza {norma_titulo} (articulo {articulo})"}
                datos["fuente"] = datos["fuente_unidades"] = fuente
                modulos[codigo] = datos

    # La Orden de curriculo (solo DAW) da unidades mas finas y la secuenciacion por curso.
    secuencia = {}
    if cfg["curriculo"]:
        norma_cur, pdf_cur = cfg["curriculo"]
        texto_cur, indice_cur = texto_con_paginas(paginas_de(pdf_cur))
        for codigo, datos in modulos_de(texto_cur, indice_cur, RE_BLOQUE_ORDEN).items():
            if codigo in modulos and datos["unidades"]:
                modulos[codigo]["unidades"] = datos["unidades"]
                modulos[codigo]["fuente_unidades"] = {"norma": norma_cur, "documento": pdf_cur,
                                                      "pagina": datos["pagina"]}
        secuencia = secuenciacion_daw(pdf_cur)

    nodos = [{
        "nivel": "titulacion", "titulacion": clave, "nombre": cfg["nombre"],
        "fuente": {"norma": norma_titulo, "documento": pdf_titulo, "pagina": 1},
    }]
    for codigo in sorted(modulos):
        datos = modulos[codigo]
        seq = secuencia.get(codigo, {})
        curso = seq.get("curso")
        nodo = {
            "nivel": "asignatura", "titulacion": clave, "codigo": codigo, "nombre": datos["nombre"],
            "curso": curso, "horas": seq.get("horas"), "fuente": datos["fuente"],
        }
        if curso is None:
            nodo["curso_nota"] = SIN_FUENTE_DE_CURSO if not secuencia else \
                "la tabla de secuenciacion no da un curso unico para este modulo"
        else:
            nodo["curso_fuente"] = {"norma": cfg["curriculo"][0], "documento": cfg["curriculo"][1],
                                    "anexo": "II", "pagina": seq["pagina"]}
        nodos.append(nodo)
        for orden, texto_ra in enumerate(datos["resultados"], 1):
            nodos.append({"nivel": "resultado_aprendizaje", "titulacion": clave,
                          "asignatura": codigo, "orden": orden, "texto": texto_ra,
                          "fuente": datos["fuente"]})
        for orden, (nombre, pagina) in enumerate(datos["unidades"], 1):
            fuente = dict(datos["fuente_unidades"], pagina=pagina)
            nodos.append({"nivel": "unidad", "titulacion": clave, "asignatura": codigo,
                          "orden": orden, "nombre": nombre, "fuente": fuente})
    return nodos, modulos


# DAW escribe "0483. Sistemas informaticos"; DAM y ASIR, "0483 Sistemas informaticos" (sin punto).
RE_CODIGO_EN_LISTA = re.compile(r"^\s*(0\d{3})\.?\s+[A-ZÁÉÍÓÚa-z]", re.M)


def codigos_del_articulado(texto: str) -> set:
    """La lista de modulos que la norma da en su ARTICULADO, que es otro sitio del documento
    distinto del Anexo I del que se extrae el arbol: si los dos no dicen los mismos modulos, el
    extractor se ha dejado uno o se ha inventado otro.

    Se acota por region (todo lo anterior al ANEXO I) en vez de buscar corridas de lineas
    seguidas: la lista cruza paginas y algunos nombres van a dos lineas, asi que fiarse de que
    las lineas sean consecutivas daba cruces falsos (ASIR salia descuadrado por eso)."""
    fin = re.search(r"^\s*ANEXO\s+I\b", texto, re.M)
    region = texto[:fin.start()] if fin else texto
    return set(RE_CODIGO_EN_LISTA.findall(region))


# La lista del articulado da tambien el NOMBRE de cada modulo, no solo su codigo, y lo da en otro
# sitio del documento y con otra tipografia. Por eso sirve de contraste: este patron no comparte
# nada con RE_MODULO, asi que un fallo del parser (un corte, una fusion, una linea perdida) sale a
# la luz en vez de confirmarse a si mismo. El nombre puede continuar en la linea siguiente, que es
# como la lista escribe los mas largos.
RE_NOMBRE_EN_LISTA = re.compile(
    r"^[ \t]*(0\d{3})\.?[ \t]+([A-ZÁÉÍÓÚa-z][^\n]{3,120}?)\.?[ \t]*$"
    r"(?:\n[ \t]*([a-záéíóúñ][^\n]{0,80}?)\.?[ \t]*$)?", re.M)


def comparable(nombre: str) -> str:
    """Normaliza para comparar: sin tildes, sin mayusculas y sin puntuacion de adorno. El BOE
    alterna 'Lenguajes de Marcas' y 'Lenguajes de marcas' para el mismo modulo, y eso NO es un
    hallazgo: lo que se persigue son palabras que faltan o sobran, no el estilo de la caja."""
    plano = unicodedata.normalize("NFD", nombre.lower())
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    return " ".join(plano.replace(".", " ").replace(",", " ").split())


def nombres_del_articulado(texto: str) -> dict:
    fin = re.search(r"^\s*ANEXO\s+I\b", texto, re.M)
    region = texto[:fin.start()] if fin else texto
    nombres = {}
    for codigo, primera, continuacion in (m.groups() for m in RE_NOMBRE_EN_LISTA.finditer(region)):
        nombres.setdefault(codigo, comparable(primera + (" " + continuacion if continuacion else "")))
    return nombres


# El BOE se contradice consigo mismo, y eso NO se corrige: se declara. El Anexo I de ASIR titula el
# modulo "Gestion de Base de Datos" y su propio articulado lo llama "Gestion de bases de datos".
# El arbol se queda con lo que dice el Anexo I, que es de donde sale el nodo, y la discrepancia se
# publica en vez de taparse. Cada excepcion lleva su motivo: sin motivo no entra aqui, porque esta
# tabla es exactamente el sitio por donde se le puede colar un fallo de verdad a la puerta.
DISCREPANCIAS_DE_LA_NORMA = {
    ("asir", "0372"): "el Anexo I titula 'Gestion de Base de Datos' y el articulado de la MISMA "
                      "norma dice 'Gestion de bases de datos'; se conserva el Anexo I, que es la "
                      "fuente del nodo",
}


def discrepancias_de_nombre(nodos: list, textos: dict) -> tuple:
    """Cruza el nombre de cada modulo contra el que la norma da en su articulado.

    Devuelve (nuevas, conocidas). Las conocidas son contradicciones de la propia norma, ya
    declaradas con su motivo; las nuevas son fallos del extractor hasta que se demuestre lo
    contrario, y hacen fallar la corrida."""
    nuevas, conocidas = [], []
    for clave, cfg in NORMATIVA.items():
        declarados = nombres_del_articulado(textos[clave])
        for n in nodos:
            if n["nivel"] != "asignatura" or n["titulacion"] != clave:
                continue
            esperado = declarados.get(n["codigo"])
            if esperado is None or esperado == comparable(n["nombre"]):
                continue
            caso = (clave, n["codigo"], esperado, n["nombre"])
            (conocidas if (clave, n["codigo"]) in DISCREPANCIAS_DE_LA_NORMA else nuevas).append(caso)
    return nuevas, conocidas


# Auditor de unidades, deliberadamente ajeno a como el parser reconoce un encabezado: solo mira
# lineas que TERMINAN en dos puntos y no empiezan por vineta. Si una de esas no ha salido como
# unidad, o el parser se la ha comido o es prosa; en los dos casos hay que mirarlo, porque el
# modo de fallo real no fue una unidad mal puesta, fue una unidad que no estaba y no se echaba
# de menos. Los modulos_mudos solo veian el modulo con CERO unidades: el que perdia dos de cinco
# pasaba en verde.
RE_CIERRA_ENCABEZADO = re.compile(
    r"^[ \t]*(?![−–\-•])(?:[a-z]\)[ \t]*)?(?P<t>[^\n]{4,140}):[ \t]*$", re.M)


def encabezados_sin_unidad(seccion: str, capturadas: list) -> list:
    sueltos = []
    for m in RE_CIERRA_ENCABEZADO.finditer(seccion):
        t = limpiar(m.group("t"))
        if any(t == c or c.endswith(t) or t.endswith(c) for c in capturadas):
            continue
        sueltos.append(t)
    return sueltos


def modulos_mudos(modulos_por_titulacion: dict) -> list:
    """Modulos que declaran contenidos y aun asi no han dado ni una unidad: eso es el extractor
    comiendoselos, no la norma callandose. Nacio de una revision a mano que encontro tres."""
    return [(clave, codigo) for clave, modulos in modulos_por_titulacion.items()
            for codigo, datos in sorted(modulos.items())
            if datos["declara_contenidos"] and not datos["unidades"]]


def comprobar(nodos: list) -> int:
    """Cruza CODIGOS y NOMBRES extraidos contra los que la norma declara en su articulado.

    El cruce de codigos ya estaba y caza el modulo perdido o inventado. El de nombres es la puerta
    que falto: un modulo puede salir con su codigo correcto y el nombre cortado, y eso el cruce de
    codigos lo da por bueno. Asi salio a la luz que tres nombres venian truncados por el salto de
    linea, despues de que un muestreo a mano encontrara uno."""
    problemas = 0
    textos = {}
    for clave, cfg in NORMATIVA.items():
        extraidos = {n["codigo"] for n in nodos
                     if n["nivel"] == "asignatura" and n["titulacion"] == clave}
        textos[clave], _ = texto_con_paginas(paginas_de(cfg["titulo"][1]))
        declarados = codigos_del_articulado(textos[clave])
        if not declarados:
            print(f"  {clave:5} CRUCE IMPOSIBLE: no se localizo la lista del articulado")
            problemas += 1
            continue
        faltan, sobran = declarados - extraidos, extraidos - declarados
        estado = "ok" if not (faltan or sobran) else "DESCUADRE"
        print(f"  {clave:5} articulado={len(declarados):3} extraidos={len(extraidos):3} {estado}"
              + (f" faltan={sorted(faltan)} sobran={sorted(sobran)}" if faltan or sobran else ""))
        problemas += bool(faltan or sobran)

    nuevas, conocidas = discrepancias_de_nombre(nodos, textos)
    print(f"cruce de NOMBRES contra el articulado: {len(nuevas)} sin explicar, "
          f"{len(conocidas)} declaradas como contradiccion de la propia norma")
    for clave, codigo, esperado, extraido in nuevas:
        print(f"  NOMBRE DESCUADRADO {clave} {codigo}: articulado dice {esperado!r}, "
              f"el arbol dice {extraido!r}")
    for clave, codigo, _, extraido in conocidas:
        print(f"  (declarada) {clave} {codigo} {extraido!r}: "
              f"{DISCREPANCIAS_DE_LA_NORMA[(clave, codigo)]}")
    return problemas + len(nuevas)


def resumen(nodos: list) -> str:
    filas = []
    for clave in NORMATIVA:
        de_esta = [n for n in nodos if n["titulacion"] == clave]
        asigs = [n for n in de_esta if n["nivel"] == "asignatura"]
        con_curso = sum(1 for n in asigs if n.get("curso"))
        filas.append(f"  {clave:5} asignaturas={len(asigs):3} con curso={con_curso:3} "
                     f"unidades={sum(1 for n in de_esta if n['nivel'] == 'unidad'):4} "
                     f"RA={sum(1 for n in de_esta if n['nivel'] == 'resultado_aprendizaje'):4}")
    return "\n".join(filas)


# Modulos tocados por la reparacion de nombres cortados y unidades perdidas. NINGUNO entra en el
# muestreo nuevo: revisar a mano justo lo que se acaba de arreglar es verificacion circular. Lo que
# se quiere saber es si el arreglo aguanta donde nadie ha mirado.
MODULOS_REPARADOS = {("daw", "0373"), ("dam", "0373"), ("asir", "0379"), ("daw", "0612"),
                     ("daw", "0616"), ("dam", "0487"), ("asir", "0371"), ("asir", "0375"),
                     ("asir", "0377")}

# Los diez del primer muestreo (11 de agosto de 2026). Tampoco se repiten: ya se comprobaron, y
# gastar el muestreo nuevo en ellos no anade informacion.
YA_MUESTREADOS = {("daw", "asignatura", "0373"), ("daw", "unidad", "0485"),
                  ("daw", "unidad", "0613"), ("daw", "asignatura", "0618"),
                  ("dam", "unidad", "0483"), ("dam", "unidad", "0487"),
                  ("dam", "asignatura", "0491"), ("asir", "unidad", "0369"),
                  ("asir", "unidad", "0373"), ("asir", "unidad", "0376")}


def afirmaciones_de(n: dict) -> list:
    """Cada cosa que el nodo AFIRMA, con la norma que lo dice. Un nodo puede tener dos procedencias
    distintas: el nombre del modulo sale del real decreto y su curso sale de la Orden de curriculo
    (Anexo II), que es otra norma. La tabla anterior tenia una sola columna de norma para las dos,
    asi que atribuia al RD un reparto por cursos que el RD no fija: el dato estaba bien en el JSONL
    (campos 'fuente' y 'curso_fuente' separados) y era el documento el que mentia."""
    afirmaciones = [("nombre", n["nombre"], n["fuente"])]
    if n.get("curso") and n.get("curso_fuente"):
        f = n["curso_fuente"]
        afirmaciones.append((f"curso {n['curso']}", f"curso {n['curso']}",
                             dict(f, norma=f"{f['norma']} (anexo {f['anexo']})")))
    return afirmaciones


def escribir_muestreo(nodos: list, camino: str, cuantos: int = 10, forzar: bool = False,
                      fecha: str = "") -> None:
    """Deja los nodos a comprobar A MANO contra el BOE. No los comprueba este script: comprobarse
    a si mismo contra el PDF del que acaba de extraer no seria verificacion de nada."""
    if os.path.exists(camino) and not forzar:
        print(f"muestreo intacto (ya existe y puede llevar anotaciones a mano): {camino}")
        print("  para rehacerlo: --forzar-muestreo")
        return
    anterior = ""
    if os.path.exists(camino):
        with open(camino, encoding="utf-8") as fh:
            anterior = fh.read().strip()

    def clave(n: dict) -> tuple:
        return (n["titulacion"], n["nivel"], n.get("codigo") or n["asignatura"])

    candidatos = [n for n in nodos if n["nivel"] in ("asignatura", "unidad")
                  and clave(n) not in YA_MUESTREADOS
                  and (n["titulacion"], n.get("codigo") or n["asignatura"]) not in MODULOS_REPARADOS]
    paso = max(1, len(candidatos) // cuantos)
    muestra = candidatos[::paso][:cuantos]
    lineas = [
        "# Muestreo del arbol oficial (encargo 1.1)",
        "",
        f"Muestreo vigente, rehecho el {fecha} tras reparar los nombres cortados y las unidades",
        "perdidas. **Los comprueba una persona contra el PDF del BOE**, no el propio extractor.",
        "",
        "Dos reglas de como se eligen los diez, y las dos importan:",
        "",
        "1. **No sale ningún módulo de los que se acaban de arreglar.** Revisar a mano justo lo",
        "   reparado es verificación circular: confirma el parche, no el extractor. Lo que se",
        "   quiere saber es si el arreglo aguanta donde nadie ha mirado.",
        "2. **No se repite ninguno de los diez del muestreo anterior.** Ya se comprobaron.",
        "",
        "Una fila por **afirmación**, no por nodo: un módulo afirma su nombre (lo dice el real",
        "decreto) y su curso (lo dice la Orden de currículo en su Anexo II). Son dos normas",
        "distintas y por eso van en filas distintas, cada una con la suya.",
        "",
        "| # | Titulación | Nodo | Campo | Dice | Norma que lo dice | Documento (pág. del PDF) | ¿De acuerdo? |",
        "|---|---|---|---|---|---|---|---|",
    ]
    i = 0
    for n in muestra:
        que = n["codigo"] if n["nivel"] == "asignatura" else f"{n['orden']} de {n['asignatura']}"
        for campo, dice, f in afirmaciones_de(n):
            i += 1
            campo_visible = "curso" if campo.startswith("curso") else "nombre"
            lineas.append(
                f"| {i} | {n['titulacion'].upper()} | {n['nivel']} {que} | {campo_visible} | "
                f"{dice} | {f['norma']} | `{f['documento'].split('/')[-1]}` p. {f['pagina']} | |")
    lineas += ["", f"Número de acuerdo: __ de {i} (lo rellena quien comprueba).", ""]
    if anterior:
        lineas += [
            "---",
            "",
            f"## Muestreo anterior, conservado entero ({fecha} lo sustituye)",
            "",
            "**Esto no es una copia de seguridad: es la prueba.** El muestreo humano de abajo",
            "encontró un defecto real que las puertas automáticas daban por bueno —el nombre del",
            "módulo 0373 salía cortado, «...sistemas de gestión de» en vez de «...de información»—",
            "y de tirar de ese hilo salieron cuatro nombres truncados, ocho unidades que faltaban",
            "enteras y una contradicción del propio BOE. Diez nodos mirados a ojo valieron más que",
            "los cientos que el verde declaraba correctos. Se conserva con sus anotaciones para que",
            "esa evidencia no se pierda al regenerar la tabla.",
            "",
            anterior,
        ]
    with open(camino, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lineas) + "\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Extrae el arbol oficial del BOE (encargo 1.1).")
    p.add_argument("--salida", default="corpus/arbol_oficial.jsonl")
    p.add_argument("--muestreo", default="docs/muestreo-arbol-oficial.md")
    p.add_argument("--forzar-muestreo", action="store_true",
                   help="rehace la tabla del muestreo CONSERVANDO la anterior dentro del fichero")
    p.add_argument("--fecha", default=datetime.date.today().isoformat(),
                   help="fecha que se estampa en el muestreo rehecho")
    a = p.parse_args()

    nodos, por_titulacion = [], {}
    for clave in NORMATIVA:
        de_esta, por_titulacion[clave] = nodos_de_titulacion(clave)
        nodos.extend(de_esta)

    with open(a.salida, "w", encoding="utf-8", newline="\n") as fh:
        for n in nodos:
            fh.write(json.dumps(n, ensure_ascii=False) + "\n")
    escribir_muestreo(nodos, a.muestreo, forzar=a.forzar_muestreo, fecha=a.fecha)

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{len(nodos)} nodos -> {a.salida}")
    print(resumen(nodos))
    print("cruce contra la lista de modulos del articulado de cada norma:")
    problemas = comprobar(nodos)
    mudos = modulos_mudos(por_titulacion)
    for clave, codigo in mudos:
        print(f"  MODULO MUDO: {clave} {codigo} declara contenidos y no ha dado ninguna unidad")
    problemas += len(mudos)

    sueltos = [(clave, codigo, t) for clave, modulos in por_titulacion.items()
               for codigo, datos in sorted(modulos.items())
               for t in datos.get("encabezados_sueltos", [])]
    print(f"encabezados con dos puntos que NO han salido como unidad: {len(sueltos)} "
          f"(sonda informativa: hay prosa que tambien termina en dos puntos)")
    for clave, codigo, t in sueltos:
        print(f"  SIN UNIDAD: {clave} {codigo} {t[:90]!r}")
    print(f"muestreo para comprobar a mano -> {a.muestreo}")
    return 1 if problemas else 0


if __name__ == "__main__":
    unicodedata.normalize("NFC", "")  # el texto del BOE viene con tildes descompuestas a ratos
    sys.exit(main())
