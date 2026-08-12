#!/usr/bin/env python3
"""Puerta de admision: que entra al indice y que no (arreglo del 1.4 tras el muestreo de Marcos).

De 20 fragmentos revisados a mano salieron 6 que no eran material docente. El detector de firmas
que habia solo cazaba 2 de esos 6, asi que se ensancho con el criterio que de verdad los separa:
no es "contiene la palabra apt-get", es QUE NO SON PROSA DOCENTE.

Dos niveles, porque son dos problemas distintos:

  DOCUMENTO   hay ficheros enteros que no son temario: guias de como subir tareas a Moodle,
              trabajos de alumnos, indices sin contenido propio, diccionarios de palabras,
              volcados de configuracion. Se excluyen enteros y se declaran.
  FRAGMENTO   dentro de un documento legitimo puede haber trozos que no aportan: salidas de
              consola pegadas, cabeceras de correo, bloques de base64, tablas de identificadores.

El codigo NUNCA se juzga con las reglas de prosa: un .java no tiene puntos ni comas y seria
descartado por todas ellas. Los ficheros de codigo son material de primera en Programacion.
"""
import argparse
import collections
import json
import re
import sys

FRAGMENTOS = "corpus/fragmentos.jsonl"

# --- nivel documento -------------------------------------------------------------------------
# Cada patron con el porque al lado. Se aplica al NOMBRE y a la ruta, no al contenido: si un
# documento entero no es temario, no hay que leerlo para saberlo.
DOCUMENTOS_FUERA = [
    (re.compile(r"guia\s*de\s*estilo|guiadeestilo|normas?\s*de\s*entrega|como\s*entregar", re.I),
     "guia de formato o de entrega de tareas, no temario"),
    (re.compile(r"diccionario|listado?\s*de\s*palabras|wordlist|rockyou", re.I),
     "lista de palabras, no material docente"),
    (re.compile(r"\.(log|cfg|conf|ini|env|properties|lock|sum|mod)$", re.I),
     "fichero de configuracion o registro"),
]

# LISTA MANUAL, documento a documento y con su motivo escrito. Decision de Marcos y el porque es
# suyo: distinguir "trabajo de alumno" de temario POR LA FORMA DEL TEXTO es caro y arriesga falsos
# positivos sobre material bueno, porque los enunciados de ejercicio SI valen -son la fuente de las
# preguntas de los pares oro del 3.6-. Asi que aqui no hay regla automatica que aprenda a olfatear
# trabajos: hay una lista revisable, como las cuatro excepciones de DNI de detectar_sensibles.py.
# Si al revisar aparecen mas, se añaden aqui y punto.
#
# Una entrada que acaba en "/" excluye ese arbol entero, y entonces el motivo dice cuantos y de que.
EXCLUIDOS_A_MANO = {
    # Los dos primeros ya NO estan en el disco: se retiraron enteros por datos personales. Su
    # entrada se conserva porque esta lista es el registro de la decision, no solo un filtro; si
    # alguien vuelve a bajar el repositorio de origen, no hay que decidirlo otra vez.
    "corpus/asir/apuntes/lora-1asir/LM/PYTHON/Entrega 3/notas.txt":
        "datos personales: lista de alumnos con grupo y notas (borrado del disco)",
    "corpus/derivado/asir/apuntes/lora-1asir/FOL/Ejercicios/CV-Manuel-Lora-Román.odt.md":
        "CV real de una persona: nombre, telefono, correo, redes y centro de estudios. Datos "
        "personales de un tercero; ademas no es temario, es el ejercicio ya resuelto de FOL "
        "(borrado del disco, junto con su .odt original y sus dos entradas de manifiesto)",
    "corpus/derivado/asir/apuntes/lora-1asir/Redes/Ejercicios/polonia/Polonia.docx.md":
        "trabajo de alumno: memoria sobre operadoras de telecomunicaciones en Polonia, firmada por "
        "dos alumnos y fechada en 2018. No es temario de Redes",
    "corpus/derivado/asir/apuntes/lora-1asir/FOL/Ejercicios/mi_proyecto_personal.docx.md":
        "trabajo de alumno: reflexion autobiografica de FOL en primera persona",
    "corpus/asir/apuntes/lora-2asir/Proyecto.md":
        "trabajo de alumno: memoria del proyecto final de 2 ASIR ('mi proyecto'), no temario",
    "corpus/derivado/daw/curso1/programacion/lionel-ict/Trabajos/Trabajo 3_ Saber y Ganar/"
    "REVISIÓN_ ITEMS Y CRITERIOS EVAL_.docx.md":
        "plantilla interna de correccion del profesor (FEEDBACK PARA ALUMNO, X puntos), no temario",
    "corpus/derivado/daw/curso1/programacion/lionel-ict/Trabajos/Trabajo 4 Saber y Ganar 2.0/"
    "REVISIÓN_ ITEMS Y CRITERIOS EVAL_.docx.md":
        "plantilla interna de correccion del profesor, no temario",
    "corpus/derivado/daw/curso1/programacion/lionel-ict/Guia_del_alumno_PRG.pdf.md":
        "guia del alumno del modulo: bienvenida, tutorias y criterios de evaluacion, no contenidos",
    "corpus/daw/curso1/programacion/lionel-ict/Trabajos/Trabajo 3_ Saber y Ganar/ingles.txt":
        "banco de preguntas de trivial en ingles: es el DATO del juego del Trabajo 3, no temario",
    "corpus/daw/curso1/programacion/lionel-ict/Trabajos/Trabajo 2 Hundir la Flota/"
    "Lista_de_Funciones.html":
        "volcado HTML de un .java exportado por el IDE: marcado de coloreado, ni prosa ni codigo "
        "compilable (el .java bueno de ese trabajo ya entra por su cuenta)",
    "corpus/familia/indice-material-formativo/README.md":
        "indice del repositorio de material: enlaces a otros repos, ningun contenido propio",
    "corpus/dam/apuntes/temario-dam-comesana/SENDACYL/":
        "codigo de una aplicacion web entregada como proyecto: 50 de sus ficheros son el mismo "
        "index.html de '403 Forbidden' que protege cada carpeta. No es material docente",
}


def excluido_a_mano(ruta: str) -> str:
    """Motivo si la ruta esta en la lista manual (por fichero o por arbol), o None."""
    if ruta in EXCLUIDOS_A_MANO:
        return EXCLUIDOS_A_MANO[ruta]
    for clave, motivo in EXCLUIDOS_A_MANO.items():
        if clave.endswith("/") and ruta.startswith(clave):
            return motivo
    return None
# Umbrales de contenido a nivel documento, medidos sobre el corpus (ver COBERTURA.md).
MIN_PROSA_DOCUMENTO = 0.25      # proporcion minima de frases con puntuacion
MIN_PALABRAS_DOCUMENTO = 60

# --- nivel fragmento -------------------------------------------------------------------------
# LO QUE DICE LA MAQUINA, no lo que escribe la persona. La distincion no es un matiz: en ASIR los
# comandos SON la materia. La primera version de estas firmas buscaba "apt-get" y "dpkg " y se
# llevo por delante Teoria_03_LinuX_dpkg.md, un documento de teoria que explica que es dpkg, y la
# guia de instalacion de Ubuntu Server. Un detector de basura que borra el temario de sistemas es
# peor que no tenerlo, porque lo que quita no se ve: se ve lo que queda.
FIRMAS_DE_VOLCADO = {
    "salida de gestor de paquetes": re.compile(
        r"(Setting up |Unpacking |Get:\d|Reading package lists|Preparing to unpack|"
        r"\d+ upgraded, \d+ newly|Need to get \d|After this operation)"),
    "cabeceras de correo": re.compile(
        r"(DKIM-Signature:|Received: from|Content-Transfer-Encoding:|X-Spam|MIME-Version:|"
        r"^\s*b?h?=[A-Za-z0-9+/=]{40,})", re.M),
    "salida de consola o red": re.compile(
        r"(icmp_seq=|link/ether|64 bytes from|PING \S+ \(|inet6? \d|rtt min/avg/max)"),
}
# Estas no admiten matiz: el fichero entero es andamiaje, no documento. Son los 50 index.html que
# un framework PHP deja en cada carpeta para que el servidor no liste su contenido.
FIRMAS_ABSOLUTAS = {
    "pagina de directorio protegido": re.compile(
        r"(403 Forbidden|Directory access is forbidden|Index of /)", re.I),
}
# Cuanto del fragmento tiene que ser volcado para que el fragmento SEA un volcado. Con 0,4, dos
# lineas de salida pegadas dentro de una explicacion no tiran la explicacion.
PROPORCION_DE_VOLCADO = 0.4
RE_ENLACE_SOLO = re.compile(r"^\s*[-*]?\s*\[[^\]]+\]\([^)]+\)\s*$", re.M)
# El indice de un PDF derivado. La regla del indice de markdown no lo veia porque miraba la FORMA
# DEL ENLACE, y aqui no hay enlaces: hay "__call__ 105", "herencia multiple 46", "lambda 60". Lo
# que los separa es lo que tienen todas esas lineas y ninguna prosa: un termino corto, ningun
# verbo y un numero de pagina al final. Misma familia que el indice de enlaces, otra superficie.
RE_ENTRADA_DE_INDICE = re.compile(r"^\s*\S[^\n]{0,48}?\s+\d{1,4}(?:\s*,\s*\d{1,4})*\s*$", re.M)
# Una URL no es un volcado. La primera version media los tokens largos sobre el texto crudo y
# "ImplantacionSistemasOperativos", que es parte de la URL de las capturas de pantalla, contaba
# como base64: se llevo por delante la guia de instalacion de Ubuntu Server entera, que son 11
# fragmentos de material bueno ilustrado con imagenes. Asi que primero se quitan las direcciones,
# y ademas se exige que el token traiga algun digito, porque una palabra castellana larga y pegada
# no lo trae y un hash o una clave, si.
RE_URL = re.compile(r"(?:https?://|ftp://|www\.)\S+")
RE_TOKEN_LARGO = re.compile(r"\b(?=[A-Za-z0-9+/=]*\d)[A-Za-z0-9+/=]{24,}\b")
# Los dos puntos cuentan como fin de frase SOLO si va detras un espacio o el fin de linea. Sin esa
# condicion, un fichero de marcas horarias ("08:48:45 10:30:54 ...") salia con dos puntuaciones por
# palabra y se colaba como la prosa mas puntuada del corpus.
RE_FIN_DE_FRASE = re.compile(r"[.!?;]|:(?=\s|$)", re.M)


# Una frase: un tramo largo que acaba en punto. Contar frases es mejor que medir la puntuacion
# media, y la diferencia la enseño un documento real de teoria de normalizacion: sus fragmentos
# llevan una tabla de datos de ejemplo (que no puntua) Y la definicion de la 2FN (que si). La media
# los daba por volcado y se perdian las definiciones. Lo que hay que preguntar no es cuanto puntua,
# es si hay ALGUNA frase ahi dentro.
RE_FRASE = re.compile(r"[A-Za-zÁÉÍÓÚÑáéíóúñ][^.!?\n]{30,}[.!?]")
MINIMO_FRASES = 2


def frases_de(texto: str) -> int:
    return len(RE_FRASE.findall(texto))


def es_prosa(texto: str) -> tuple:
    """Proporcion de puntuacion por palabra y de caracteres dentro de tokens larguisimos.

    Un diccionario de palabras, una tabla de identificadores o un volcado de base64 comparten algo
    que ninguna prosa docente tiene: montones de palabras sin un solo punto."""
    palabras = texto.split()
    if not palabras:
        return 0.0, 1.0
    puntuacion = len(RE_FIN_DE_FRASE.findall(texto)) / len(palabras)
    sin_urls = RE_URL.sub(" ", texto)
    tokens = sum(len(t) for t in RE_TOKEN_LARGO.findall(sin_urls)) / max(len(sin_urls), 1)
    return puntuacion, tokens


def proporcion_de_lineas(patron, texto: str) -> float:
    lineas = [x for x in texto.split("\n") if x.strip()]
    if not lineas:
        return 0.0
    return sum(1 for x in lineas if patron.search(x)) / len(lineas)


def juzgar_fragmento(fr: dict) -> str:
    """Devuelve el motivo de rechazo, o None si entra."""
    if fr["tipo_contenido"] == "codigo":
        return None                      # el codigo no se juzga con reglas de prosa
    texto = fr["texto"]
    for nombre, patron in FIRMAS_ABSOLUTAS.items():
        if patron.search(texto):
            return nombre
    for nombre, patron in FIRMAS_DE_VOLCADO.items():
        if proporcion_de_lineas(patron, texto) >= PROPORCION_DE_VOLCADO:
            return nombre
    lineas = [x for x in texto.split("\n") if x.strip()]
    if len(lineas) > 5 and len(RE_ENLACE_SOLO.findall(texto)) / len(lineas) > 0.6:
        return "indice de enlaces sin contenido propio"
    if (len(lineas) > 8 and len(RE_ENTRADA_DE_INDICE.findall(texto)) / len(lineas) > 0.6
            and frases_de(texto) <= 1):
        return "indice alfabetico o de contenidos, no prosa"
    puntuacion, tokens_largos = es_prosa(texto)
    palabras = len(texto.split())
    # Las DOS condiciones a la vez, y esa conjuncion es el arreglo: casi no puntua Y no hay ni una
    # frase entera. Con solo la media caia un documento de teoria de normalizacion cuyos fragmentos
    # mezclan una tabla de datos de ejemplo con la definicion de la 2FN; con solo las frases caian
    # los enunciados de tarea, que van en vinetas cortas y son material bueno.
    if palabras >= 40 and puntuacion < 0.02 and frases_de(texto) == 0:
        return "ni puntuacion ni una frase entera: lista, tabla o volcado, no prosa"
    if tokens_largos > 0.25:
        return "volcado de cadenas largas (base64, hashes, claves)"
    return None


def juzgar_documento(ruta: str, fragmentos: list) -> str:
    a_mano = excluido_a_mano(ruta)
    if a_mano:
        return a_mano
    for patron, motivo in DOCUMENTOS_FUERA:
        if patron.search(ruta):
            return motivo
    codigo = sum(1 for f in fragmentos if f["tipo_contenido"] == "codigo")
    if codigo == len(fragmentos):
        return None
    rechazados = sum(1 for f in fragmentos if juzgar_fragmento(f))
    if rechazados == len(fragmentos):
        return "ninguno de sus fragmentos es material docente"
    texto = " ".join(f["texto"] for f in fragmentos if f["tipo_contenido"] != "codigo")
    palabras = len(texto.split())
    if palabras < MIN_PALABRAS_DOCUMENTO:
        return None                      # demasiado corto para juzgarlo por la forma: pasa
    puntuacion, _ = es_prosa(texto)
    if puntuacion < 0.02:
        return "el documento entero no es prosa (lista, volcado o tabla)"
    # La proporcion solo es evidencia si hay de que: en un documento de tres fragmentos, "el 66%"
    # son dos, y con dos tablas de datos de ejemplo se caia entero un documento de teoria de
    # normalizacion de bases de datos. Por debajo de cinco fragmentos manda el juicio por
    # fragmento, que ya se aplica despues.
    if len(fragmentos) >= 5 and rechazados / len(fragmentos) > 0.6:
        return f"el {100*rechazados//len(fragmentos)}% de sus fragmentos no es material docente"
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="Puerta de admision del indice (arreglo del 1.4).")
    p.add_argument("--fragmentos", default=FRAGMENTOS)
    p.add_argument("--detalle", action="store_true")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    fragmentos = [json.loads(x) for x in open(a.fragmentos, encoding="utf-8") if x.strip()]
    por_documento = collections.defaultdict(list)
    for f in fragmentos:
        por_documento[f["documento"]].append(f)

    fuera_doc, motivos_doc = {}, collections.Counter()
    for ruta, trozos in por_documento.items():
        motivo = juzgar_documento(ruta, trozos)
        if motivo:
            fuera_doc[ruta] = motivo
            motivos_doc[motivo.split(":")[0][:44]] += 1

    perdidos_por_doc = sum(len(por_documento[r]) for r in fuera_doc)
    fuera_frag = collections.Counter()
    for f in fragmentos:
        if f["documento"] in fuera_doc:
            continue
        motivo = juzgar_fragmento(f)
        if motivo:
            fuera_frag[motivo] += 1

    print(f"fragmentos: {len(fragmentos)} en {len(por_documento)} documentos\n")
    print(f"### documentos excluidos enteros: {len(fuera_doc)}  "
          f"({perdidos_por_doc} fragmentos, {100*perdidos_por_doc/len(fragmentos):.1f}%)")
    for motivo, n in motivos_doc.most_common():
        print(f"  {n:5}  {motivo}")
    if a.detalle:
        for ruta, motivo in sorted(fuera_doc.items()):
            print(f"     - {ruta[-70:]}  ({motivo})")
    print(f"\n### fragmentos sueltos rechazados (de documentos que SI entran): {sum(fuera_frag.values())}"
          f"  ({100*sum(fuera_frag.values())/len(fragmentos):.1f}%)")
    for motivo, n in fuera_frag.most_common():
        print(f"  {n:5}  {motivo}")
    total = perdidos_por_doc + sum(fuera_frag.values())
    print(f"\nTOTAL fuera del indice: {total} de {len(fragmentos)} ({100*total/len(fragmentos):.1f}%)")
    print(f"quedan {len(fragmentos)-total} fragmentos admitidos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
