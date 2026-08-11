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

RE_MODULO = re.compile(
    r"M[oó]dulo\s+[Pp]rofesional:\s*(?P<nombre>[^\n]{3,90}?)\s*\.?\s*\n"
    r"(?:[^\n]*\n){0,2}?\s*C[oó]digo:\s*(?P<codigo>\d{4})", re.M)
RE_RA = re.compile(r"^\s*(\d{1,2})\.\s+(.{15,400}?)\s*Criterios de evaluaci[oó]n:", re.M | re.S)
RE_BLOQUE_RD = re.compile(r"^[ \t]*([A-ZÁÉÍÓÚÑ][^\n:]{4,90}):[ \t]*\n[ \t]*[−–-]", re.M)
RE_BLOQUE_ORDEN = re.compile(r"^[ \t]*[a-z]\)\s*([^\n:]{4,95}):", re.M)


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
RE_INICIO_CONTENIDOS = re.compile(r"^[ \t]*Contenidos(?:\s+b[aá]sicos)?\s*[:.]", re.I | re.M)
# A PROPOSITO mas laxo que el anterior, y usado SOLO para auditar: si el detector de "este modulo
# declara contenidos" comparte el patron con el que trocea, un encabezado que el patron no
# reconozca deja el modulo mudo Y sin denunciar, que es como se colo el fallo de ASIR 0378.
# El auditor no puede compartir la suposicion del parser.
# Laxo con la puntuacion (da igual ':' que '.' que nada) pero exigente en que el encabezado sea la
# linea ENTERA: sin el final de linea se tragaba frases partidas que empiezan por "contenidos".
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


def modulos_mudos(modulos_por_titulacion: dict) -> list:
    """Modulos que declaran contenidos y aun asi no han dado ni una unidad: eso es el extractor
    comiendoselos, no la norma callandose. Nacio de una revision a mano que encontro tres."""
    return [(clave, codigo) for clave, modulos in modulos_por_titulacion.items()
            for codigo, datos in sorted(modulos.items())
            if datos["declara_contenidos"] and not datos["unidades"]]


def comprobar(nodos: list) -> int:
    """Cruza los codigos extraidos contra los que la norma declara en su articulado."""
    problemas = 0
    for clave, cfg in NORMATIVA.items():
        extraidos = {n["codigo"] for n in nodos
                     if n["nivel"] == "asignatura" and n["titulacion"] == clave}
        texto, _ = texto_con_paginas(paginas_de(cfg["titulo"][1]))
        declarados = codigos_del_articulado(texto)
        if not declarados:
            print(f"  {clave:5} CRUCE IMPOSIBLE: no se localizo la lista del articulado")
            problemas += 1
            continue
        faltan, sobran = declarados - extraidos, extraidos - declarados
        estado = "ok" if not (faltan or sobran) else "DESCUADRE"
        print(f"  {clave:5} articulado={len(declarados):3} extraidos={len(extraidos):3} {estado}"
              + (f" faltan={sorted(faltan)} sobran={sorted(sobran)}" if faltan or sobran else ""))
        problemas += bool(faltan or sobran)
    return problemas


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


def escribir_muestreo(nodos: list, camino: str, cuantos: int = 10, forzar: bool = False):
    """Deja los nodos a comprobar A MANO contra el BOE. No los comprueba este script: comprobarse
    a si mismo contra el PDF del que acaba de extraer no seria verificacion de nada."""
    if os.path.exists(camino) and not forzar:
        print(f"muestreo intacto (ya existe y puede llevar anotaciones a mano): {camino}")
        print("  para rehacerlo: --forzar-muestreo")
        return
    candidatos = [n for n in nodos if n["nivel"] in ("asignatura", "unidad")]
    paso = max(1, len(candidatos) // cuantos)
    muestra = candidatos[::paso][:cuantos]
    lineas = [
        "# Muestreo del arbol oficial (encargo 1.1)",
        "",
        "Diez nodos elegidos a intervalo regular sobre el arbol extraido. **Los comprueba una",
        "persona contra el PDF del BOE**, no el propio extractor. Escribe al lado si el nodo dice",
        "lo que dice la norma en esa pagina, y el numero de acuerdo se anota tal cual: es un",
        "muestreo de 10, no una prueba de que los cientos restantes esten bien.",
        "",
        "| # | Titulación | Nodo | Dice | Norma | Documento (pág. del PDF) | ¿De acuerdo? |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, n in enumerate(muestra, 1):
        que = n["codigo"] if n["nivel"] == "asignatura" else f"{n['orden']} de {n['asignatura']}"
        dice = n["nombre"] + (f" · curso {n['curso']}" if n.get("curso") else "")
        f = n["fuente"]
        lineas.append(f"| {i} | {n['titulacion'].upper()} | {n['nivel']} {que} | {dice} | "
                      f"{f['norma']} | `{f['documento'].split('/')[-1]}` p. {f['pagina']} | |")
    lineas += ["", "Número de acuerdo: __ de 10 (lo rellena quien comprueba)."]
    with open(camino, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lineas) + "\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Extrae el arbol oficial del BOE (encargo 1.1).")
    p.add_argument("--salida", default="corpus/arbol_oficial.jsonl")
    p.add_argument("--muestreo", default="docs/muestreo-arbol-oficial.md")
    p.add_argument("--forzar-muestreo", action="store_true",
                   help="rehace el muestreo aunque ya exista (pierde lo anotado a mano)")
    a = p.parse_args()

    nodos, por_titulacion = [], {}
    for clave in NORMATIVA:
        de_esta, por_titulacion[clave] = nodos_de_titulacion(clave)
        nodos.extend(de_esta)

    with open(a.salida, "w", encoding="utf-8", newline="\n") as fh:
        for n in nodos:
            fh.write(json.dumps(n, ensure_ascii=False) + "\n")
    escribir_muestreo(nodos, a.muestreo, forzar=a.forzar_muestreo)

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{len(nodos)} nodos -> {a.salida}")
    print(resumen(nodos))
    print("cruce contra la lista de modulos del articulado de cada norma:")
    problemas = comprobar(nodos)
    mudos = modulos_mudos(por_titulacion)
    for clave, codigo in mudos:
        print(f"  MODULO MUDO: {clave} {codigo} declara contenidos y no ha dado ninguna unidad")
    problemas += len(mudos)
    print(f"muestreo para comprobar a mano -> {a.muestreo}")
    return 1 if problemas else 0


if __name__ == "__main__":
    unicodedata.normalize("NFC", "")  # el texto del BOE viene con tildes descompuestas a ratos
    sys.exit(main())
