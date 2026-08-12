#!/usr/bin/env python3
"""Encargo 1.4: trocea el corpus normalizado en fragmentos de 512 tokens con su contexto.

Escribe corpus/fragmentos.jsonl, uno por linea, listo para embeber en el encargo 1.5.

TRES DECISIONES QUE VIENEN DE LA GUIA, y que se notan en todo el fichero:

1. Los 512 tokens se cuentan con el TOKENIZADOR REAL de BGE-M3, no estimando. Medido: la prosa
   castellana cunde 4,6 caracteres por token y el codigo 2,3, asi que estimar por palabras se
   equivoca al doble justo en el material de Programacion.
2. Los 512 INCLUYEN la linea de contexto (26 a 32 tokens, media 29). Lo que se embebe es el
   fragmento entero, contexto incluido: si el presupuesto fuera solo del cuerpo, el vector real
   llevaria 540 tokens y el "512" del README seria un numero que no existe.
3. La UNIDAD sale de la carpeta del material, no del arbol del BOE (ADR 0005): son taxonomias
   distintas ("Unidad 4 Introduccion a Java" frente a "Utilizacion de objetos") y no hay mapeo
   fiable. La particion y el filtro van por asignatura, que si casa en las dos.

El codigo tiene regla propia: un fichero es UN fragmento si cabe, y si no cabe se parte por clase o
por metodo, jamas por ventana ciega. Trocear codigo cada 512 tokens produce fragmentos que no
compilan ni se entienden.

Uso:
    python scripts/trocear.py                      # todo el corpus normalizado
    python scripts/trocear.py --raiz corpus/derivado/daw/curso1/programacion
    python scripts/trocear.py --muestreo docs/muestreo-fragmentos.md
"""
import argparse
import collections
import json
import os
import re
import sys

import admitir
from transformers import AutoTokenizer

MODELO = "BAAI/bge-m3"
TOKENS = 512
SOLAPE = 64
SALIDA = "corpus/fragmentos.jsonl"
DERIVADO = "corpus/derivado"

EXT_CODIGO = {".java": "java", ".cs": "csharp", ".sql": "sql", ".kt": "kotlin",
              ".py": "python", ".js": "javascript", ".ts": "typescript"}
EXT_TEXTO = {".md", ".markdown", ".txt", ".html", ".htm"}

RE_TITULO = re.compile(r"^#{1,3}\s+(.+)$", re.M)

# --- señales de tipo_contenido ----------------------------------------------------------------
# Una definicion de verdad tiene FORMA de definicion: un termino, la copula y su genero proximo.
# "es un" suelto en mitad de un parrafo no lo es, y esa era la regla vieja.
RE_DEFINICION_FUERTE = re.compile(
    r"(?:^|[.:;)\n]\s+)(?:la|el|los|las|un|una|unos|unas)\s+"
    r"[\wáéíóúñü]{3,}(?:\s+[\wáéíóúñü]{2,}){0,4}\s+"
    r"(?:es|son)\s+(?:un|una|unos|unas|el|la|los|las|aquell?[oa]s?|cualquier)\b"
    r"|\bse\s+(?:define|definen|denomina|denominan|conoce|conocen)\s+como\b"
    r"|\bse\s+entiende\s+por\b"
    r"|(?:^|[.:;)\n]\s+)(?:la|el|los|las|un|una)\s+[\wáéíóúñü]{3,}"
    r"(?:\s+[\wáéíóúñü]{2,}){0,4}\s+consiste\s+en\b", re.I)
RE_PREGUNTA = re.compile(r"\?")
# Genero proximo que no define nada: "es una de las tareas tipicas", "es el que se encarga". La
# forma es de definicion pero la frase no lo es, y son la mitad de los falsos positivos medidos.
RE_GENERO_DEBIL = re.compile(
    r"\b(?:es|son)\s+(?:uno|una|unos|unas)\s+de\b"
    r"|\b(?:es|son)\s+(?:el|la|los|las|lo)\s+que\b"
    r"|\b(?:es|son)\s+(?:el|la|los|las)\s+"
    r"(?:siguientes?|mismos?|misma|habituales?|anteriores?|de siempre)\b"
    r"|\bconsiste\s+en\s+que\b"
    r"|^\s*(?:el|la|los|las|lo)\s+que\b", re.I)
# Una frase que arrastra una valla de codigo o una lista de vinetas no es una frase: es el corte
# de frases tropezando con la maquetacion.
RE_NO_ES_FRASE = re.compile(r"```|\n\s*[*\-•]\s")

RE_VALLA = re.compile(r"```")
RE_LINEA_CODIGO = re.compile(
    r"[{};]\s*$|^\s*[}\]);]|=>|\w+\.\w+\([^)]*\)\s*;|"
    r"^\s*(?:public|private|protected|static|final|abstract|import|package|class|interface|def|"
    r"function|var|let|const|return|else|using|namespace|#include|@\w+|<\?php)\b|"
    r"^\s*(?:if|for|foreach|while|switch|catch)\s*\(", re.M)

# El numero de paso vale al principio de linea Y detras de un punto: el texto sacado de un PDF
# llega con los pasos seguidos en el mismo parrafo, y pedirlos en su linea era pedirle al detector
# que compartiera el supuesto del extractor.
RE_PASO = re.compile(r"(?:^|(?<=[.;:])\s)\s*(?:\d{1,2}\s*[.)-]\s+\S|paso\s+\d|primero[,:]|"
                     r"a continuaci[oó]n[,:]|por [uú]ltimo[,:]|luego[,:]|despu[eé]s[,:])",
                     re.I | re.M)
RE_IMPERATIVO = re.compile(
    r"\b(instal[ae]|ejecut[ae]|abr[ea]|escrib[ea]|pulsa|haz clic|crea|configur[ae]|edita|copia|"
    r"descarga|selecciona|introduce|guarda|reinicia|comprueba|añade|modifica|arranca|accede)\b",
    re.I)
RE_ORDEN_CONSOLA = re.compile(
    r"^\s*(?:[$#>]\s*)?(?:sudo|apt(?:-get)?|yum|dnf|systemctl|service|docker|docker-compose|git|"
    r"mvn|npm|pip|cd|mkdir|chmod|chown|nano|vim?|useradd|usermod|mysql|psql|tar|wget|curl|"
    r"ssh|scp|ip|ifconfig|iptables)\s+\S", re.M)

RE_EJEMPLO_EXPLICITO = re.compile(
    r"^#{1,6}[^\n]*\b(ejemplo|ejercicio|caso pr[aá]ctico|soluci[oó]n)\b"
    r"|^\s*(?:ejemplo|ejercicio)s?\s*\d*\s*[:.)-]", re.I | re.M)
RE_NORMATIVA = re.compile(r"\b(real decreto|orden edu|bolet[ií]n oficial|anexo|"
                          r"resultados de aprendizaje)\b", re.I)

RE_METODO = re.compile(
    r"^[ \t]*(?:@\w+[^\n]*\n[ \t]*)*"
    r"(?:public|private|protected|static|final|abstract|synchronized|internal|override|\s)*"
    r"[\w<>\[\],.\s]+\s+\w+\s*\([^;{]*\)\s*(?:throws [\w,\s.]+)?\s*\{", re.M)
RE_CLASE = re.compile(r"^[ \t]*(?:public|private|protected|static|final|abstract|sealed|\s)*"
                      r"(?:class|interface|enum|record|struct)\s+\w+", re.M)


def cargar_tokenizador():
    return AutoTokenizer.from_pretrained(MODELO)


def contar(tok, texto: str) -> int:
    return len(tok.encode(texto, add_special_tokens=False))


# --- contexto y metadatos -------------------------------------------------------------------

# El corpus no tiene UNA forma de arbol, porque cada repositorio lo organizo quien lo escribio:
#
#   daw/curso{1,2}/<asignatura>/<repo>/<carpetas...>   la asignatura esta en la ruta
#   asir|dam/apuntes/<repo>/<sigla>/<carpetas...>      la asignatura es la sigla de quien lo escribio
#   asir/apuntes/aberlanas-iso/<carpetas...>           el repositorio ENTERO es una asignatura
#
# Leyendo la ruta a ciegas (el nivel siguiente a la titulacion es la asignatura) salian 3.495
# fragmentos -el 27% del indice- con asignatura "apuntes". Y la asignatura no es un adorno: es la
# particion del filtro de recuperacion y la del detector de colados del 1.8, asi que con ASIR y DAM
# enteros metidos en un cajon llamado "apuntes" un colado dentro de ASIR era invisible POR
# CONSTRUCCION, igual que los pares consecutivos del solape.
#
# La equivalencia sigla -> modulo va DECLARADA aqui, una a una y con su norma al lado, no deducida:
# es interpretacion del nombre que puso una persona. Donde no hay equivalencia segura no se inventa
# -misma regla que el `curso` de DAM y ASIR, que va a null porque no hay orden de curriculo-: se
# deja la sigla tal cual y se declara de donde sale en `asignatura_origen`.
REPOS_DE_UNA_ASIGNATURA = {
    # ISO, modulo de 1 ASIR (RD 1629/2009, anexo I). El repositorio entero es de ese modulo y sus
    # carpetas UD01..UD12 son sus unidades.
    "asir/apuntes/aberlanas-iso": "implantacion-de-sistemas-operativos",
}
ASIGNATURA_POR_SIGLA = {
    "asir/apuntes/lora-1asir": {
        "BBDD": "gestion-de-bases-de-datos",
        "FOL": "formacion-y-orientacion-laboral",
        "HW": "fundamentos-de-hardware",
        "LM": "lenguajes-de-marcas-y-sistemas-de-gestion-de-informacion",
        "Redes": "planificacion-y-administracion-de-redes",
        "SO": "implantacion-de-sistemas-operativos",
    },
    "asir/apuntes/lora-2asir": {
        "ASO": "administracion-de-sistemas-operativos",
        "BBDD": "administracion-de-sistemas-gestores-de-bases-de-datos",
        "Empresa e iniciativa emprendedora": "empresa-e-iniciativa-emprendedora",
        "IAW": "implantacion-de-aplicaciones-web",
        "SAD": "seguridad-y-alta-disponibilidad",
        "SRI": "servicios-de-red-e-internet",
        # HLC y Talleres no son modulos del RD 1629/2009. No se traducen: se quedan con su sigla.
    },
    "dam/apuntes/temario-dam-comesana": {
        "AD": "acceso-a-datos",
        "DI": "desarrollo-de-interfaces",
        "PSP": "programacion-de-servicios-y-procesos",
        "SGE": "sistemas-de-gestion-empresarial",
    },
}

RE_UNIDAD = re.compile(r"^(unidad|tema|ud|ut|bloque|m[oó]dulo|cap[ií]tulo)[ _.-]*\d", re.I)
# Carpetas que solo dicen como esta guardado el material, no de que trata. Ponerlas de unidad es
# meter ruido en la linea de contexto, y esa linea SE EMBEBE: entra en el vector.
CARPETAS_SIN_SIGNIFICADO = {
    "apuntes", "material", "materiales", "documentos", "documentacion", "docs", "doc", "teoria",
    "practicas", "practica", "ejercicios", "ejercicio", "src", "img", "imagenes", "images",
    "manuales", "manual", "guias", "guia", "recursos", "varios", "otros", "temario", "pdf", "pdfs",
    "java", "python", "php", "sql", "csharp", "netcore", "springboot", "models", "views",
    "controllers", "test", "tests", "examen", "examenes", "tareas", "trabajos", "resumen", "code",
    "assets", "css", "js", "data", "files", "notas", "anexos", "presentaciones", "videos",
}


def _sin_tildes(texto: str) -> str:
    tabla = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
    return texto.translate(tabla)


def carpeta_significativa(nombre: str) -> bool:
    """Dice de que trata el material, no donde esta guardado."""
    if RE_UNIDAD.match(nombre):
        return True
    palabras = [p for p in re.split(r"[ _\-.]+", _sin_tildes(nombre).lower()) if len(p) > 2]
    if not palabras or all(p in CARPETAS_SIN_SIGNIFICADO for p in palabras):
        return False
    return len(palabras) >= 2


def unidad_de(carpetas: list) -> str:
    """El PRIMER directorio con significado bajo la asignatura, y vacio si no hay ninguno.

    Antes era el mas profundo, y de ahi salian unidades como "comesana" (3.370 fragmentos),
    "Manuales", "java" o "D4": el nombre de quien escribio los apuntes o el formato del fichero.
    Vacio es mejor que ruido, porque esto no es un adorno del JSON: viaja en la linea de contexto
    y por tanto entra en el vector.
    """
    for carpeta in carpetas:
        if RE_UNIDAD.match(carpeta):
            return carpeta
    for carpeta in carpetas:
        if carpeta_significativa(carpeta):
            return carpeta
    return None


def ruta_a_partes(ruta: str) -> dict:
    """De la ruta salen titulacion, curso, asignatura y unidad. La unidad es la CARPETA del
    material, no el arbol del BOE (ADR 0005)."""
    partes = ruta.split("/")
    if partes[:2] == ["corpus", "derivado"]:
        partes = partes[2:]
    elif partes[:1] == ["corpus"]:
        partes = partes[1:]
    datos = {"titulacion": partes[0] if partes else "", "curso": None,
             "asignatura": "", "asignatura_origen": None, "unidad": None}
    resto = partes[1:]
    if resto and re.fullmatch(r"curso(\d)", resto[0]):
        datos["curso"] = int(resto[0][-1])
        resto = resto[1:]
        if resto:
            datos["asignatura"] = resto[0]
            datos["asignatura_origen"] = "carpeta del ciclo"
            # El primer nivel bajo la asignatura es el repositorio de origen (lionel-ict,
            # joseluisgs-01, comesana): de donde viene el material, no de que trata.
            resto = resto[1:]
        carpetas = resto[1:-1] if len(resto) > 1 else []
    else:
        repo = "/".join([datos["titulacion"]] + resto[:2])
        if repo in REPOS_DE_UNA_ASIGNATURA:
            datos["asignatura"] = REPOS_DE_UNA_ASIGNATURA[repo]
            datos["asignatura_origen"] = "repositorio de una sola asignatura, tabla declarada"
            carpetas = resto[2:-1]
        elif repo in ASIGNATURA_POR_SIGLA and len(resto) > 3:
            sigla = resto[2]
            declarada = ASIGNATURA_POR_SIGLA[repo].get(sigla)
            datos["asignatura"] = declarada or _sin_tildes(sigla).lower().replace(" ", "-")
            datos["asignatura_origen"] = ("sigla del material, tabla declarada" if declarada
                                          else "sigla del material SIN equivalencia declarada")
            carpetas = resto[3:-1]
        elif repo in ASIGNATURA_POR_SIGLA:
            # Ficheros sueltos en la raiz del repositorio, sin carpeta de asignatura. No se deduce
            # de que modulo son por lo que hablan: se declara que no consta, como el `curso`.
            datos["asignatura_origen"] = "no declarada: ficheros sueltos en la raiz del repositorio"
            carpetas = resto[2:-1]
        else:
            datos["asignatura"] = resto[0] if resto else ""
            datos["asignatura_origen"] = "carpeta del ciclo"
            carpetas = resto[1:-1]
    datos["unidad"] = unidad_de([c for c in carpetas if c])
    return datos


def titulo_de(ruta: str, texto: str) -> str:
    """El titulo del documento: el primer encabezado que PAREZCA un titulo, y si no, el nombre.

    En un .md derivado de PDF no hay encabezados, pero si hay lineas que empiezan por almohadilla:
    los comentarios de shell y los ficheros de configuracion que el profesor pego dentro. Sin este
    filtro, 329 fragmentos se embebian con un contexto que terminaba en "/etc/init.d/nscd restart"
    o en "apt-get install eclipse". Y la linea de contexto no es decorado del JSON: va dentro del
    vector, asi que un titulo falso desplaza al fragmento entero en la recuperacion.
    """
    for m in RE_TITULO.finditer(texto):
        candidato = m.group(1).strip().rstrip("#").strip()
        if not 3 <= len(candidato) <= 80:
            continue
        if RE_ORDEN_CONSOLA.search(candidato) or "/" in candidato.split()[0]:
            continue
        return candidato
    return os.path.basename(ruta).replace(".pdf.md", "").replace(".md", "")


def linea_de_contexto(ruta: str, partes: dict, titulo: str) -> str:
    trozos = [partes["titulacion"].upper()]
    if partes["curso"]:
        trozos.append(f"curso {partes['curso']}")
    trozos.append(partes["asignatura"])
    if partes["unidad"]:
        trozos.append(partes["unidad"])
    trozos.append(titulo)
    return " · ".join(t for t in trozos if t)


def proporcion_de_codigo(texto: str) -> float:
    """Cuanto del fragmento es codigo, contando las vallas ``` y, si no las hay, las lineas que lo
    parecen. Un .md de Programacion puede ser tres cuartas partes de Java."""
    vallas = [m.start() for m in RE_VALLA.finditer(texto)]
    if len(vallas) >= 2:
        dentro = sum(vallas[i + 1] - vallas[i] for i in range(0, len(vallas) - 1, 2))
        return dentro / max(len(texto), 1)
    lineas = [x for x in texto.split("\n") if x.strip()]
    if not lineas:
        return 0.0
    return sum(1 for x in lineas if RE_LINEA_CODIGO.search(x)) / len(lineas)


def frase_definitoria(texto: str) -> str:
    """LA FRASE que define, no el fragmento que la contiene. Devuelve None si no hay ninguna.

    Este cambio de unidad sale de medir, y es el hallazgo que desbloquea el 1.6. Marcar el
    fragmento entero como "definicion" no puede ser preciso por construccion: un fragmento son 512
    tokens de prosa docente y casi cualquier trozo de 512 tokens contiene EN ALGUN SITIO una frase
    con "es un". Medido a mano sobre 20 fragmentos marcados asi, definiciones de verdad habia 3.
    El problema no era el patron, era la unidad.

    Lo que el 1.6 necesita no es "este fragmento habla de definiciones": es la frase exacta, porque
    de ella sale la entrada del glosario y contra ella se valida despues. Y ademas encaja con el
    principio 6: si la definicion es literal, comprobar que esta en su fragmento es una comparacion
    de cadenas, sin modelo, independiente del que la extrajo.
    """
    for frase in re.split(r"(?<=[.!?])\s+", texto):
        frase = frase.strip()
        if len(frase.split()) < 6 or "?" in frase:
            continue
        if RE_GENERO_DEBIL.search(frase) or RE_NO_ES_FRASE.search(frase):
            continue
        if RE_DEFINICION_FUERTE.search(frase):
            return frase
    return None


def es_definicion(texto: str, codigo: float) -> bool:
    if codigo >= 0.2:
        return False
    if len(texto.split()) < 30:
        return False
    if len(RE_PREGUNTA.findall(texto)) >= 2:        # cuestionario, no temario expositivo
        return False
    return frase_definitoria(texto) is not None


def tipo_de_contenido(texto: str, es_codigo: bool) -> str:
    """El orden importa y es este por un motivo: lo que se reconoce por la FORMA (codigo, pasos)
    manda sobre lo que se reconoce por una palabra suelta ("ejemplo", "es un")."""
    if es_codigo:
        return "codigo"
    codigo = proporcion_de_codigo(texto)
    if codigo >= 0.5:
        return "codigo"
    pasos, ordenes = len(RE_PASO.findall(texto)), len(RE_ORDEN_CONSOLA.findall(texto))
    # Tres puntos numerados no bastan: una lista de tres ventajas tambien los tiene. Lo que
    # distingue un procedimiento es que MANDA hacer algo, asi que se pide ademas verbo en
    # imperativo o una orden de consola. Al reves, tres ordenes seguidas ya son procedimiento
    # aunque nadie las haya numerado.
    if (pasos >= 3 and (RE_IMPERATIVO.search(texto) or ordenes)) or ordenes >= 3:
        return "procedimiento"
    if RE_EJEMPLO_EXPLICITO.search(texto):
        return "ejemplo_resuelto"
    if es_definicion(texto, codigo):
        return "definicion"
    if len(RE_NORMATIVA.findall(texto)) >= 2:
        return "normativa"
    return "explicacion"


# --- troceado de prosa ----------------------------------------------------------------------

def partir_en_piezas(texto: str) -> list:
    """Jerarquia de separadores: primero por encabezados, luego por parrafos, luego por frases.
    Nunca se corta a mitad de palabra."""
    piezas = []
    for bloque in re.split(r"\n(?=#{1,6}\s)", texto):
        for parrafo in re.split(r"\n\s*\n", bloque):
            parrafo = parrafo.strip()
            if parrafo:
                piezas.append(parrafo)
    return piezas


# La lista de ficheros que no entran por lo que contienen (y no por su formato) vive ahora en
# scripts/admitir.py junto al resto de la puerta de admision, para que haya UNA sola lista y no dos
# que se contradigan. Lo que se excluye no se borra del disco: el corpus es material de terceros y
# no se reescribe, pero esto no llega a fragmento y por tanto no llega a embedding ni a respuesta.

# Pista, no puerta: filas tipo "APELLIDO APELLIDO, NOMBRE,1B,8,7,9" delatan listas de clase. Lo que
# encuentre se ENSEÑA para que lo decida una persona, no se excluye solo; un detector de datos
# personales de verdad no cabe en una regex, y creerse que si seria peor que no tenerlo.
RE_LISTA_DE_CLASE = re.compile(
    r"[A-ZÁÉÍÓÚÑ]{3,}\s+[A-ZÁÉÍÓÚÑ]{3,},\s*[A-ZÁÉÍÓÚÑ ]{3,},\s*\d[A-Za-z],(?:\s*\d+,){3}")

RE_BASE64 = re.compile(r"^[A-Za-z0-9+/=\s]{200,}$")
RE_PEM = re.compile(r"-----BEGIN [A-Z ]*(?:KEY|CERTIFICATE)-----")


def parece_secreto_o_volcado(texto: str) -> bool:
    """Bloques PEM y chorros de base64: claves, certificados y binario en base64.

    Encontrado en el corpus real: los apuntes de un alumno de ASIR traen certificados de Kubernetes
    y una CLAVE PRIVADA RSA volcados en base64. Eso no es temario: no se trocea mejor, no entra.
    Un sistema que cita fragmentos del corpus a un alumno no puede tener eso dentro."""
    if RE_PEM.search(texto):
        return True
    plano = texto.strip()
    if len(plano) < 200 or " " in plano[:200]:
        return False
    if not RE_BASE64.match(plano):
        return False
    try:
        import base64
        cabeza = base64.b64decode(plano[:400] + "==", validate=False)[:40]
        return b"BEGIN" in cabeza or not cabeza.isascii()
    except Exception:  # noqa: BLE001
        return True


def atomos(tok, texto: str, presupuesto: int) -> list:
    """Trocea hasta que ninguna pieza pase del presupuesto, bajando por la jerarquia:
    encabezado, parrafo, frase y, como ultimo recurso, ventana de palabras.

    La ventana solo se usa cuando ya no queda ningun corte natural: por ejemplo las tablas de
    atajos de NetBeans del corpus, que son 1.011 tokens sin un solo punto. Se corta entre palabras,
    nunca dentro de una."""
    pendientes, salida, tirados = partir_en_piezas(texto), [], 0
    for pieza in pendientes:
        if parece_secreto_o_volcado(pieza):
            tirados += 1
            continue
        if contar(tok, pieza) <= presupuesto:
            salida.append(pieza)
            continue
        for frase in re.split(r"(?<=[.!?:;])\s+", pieza):
            if contar(tok, frase) <= presupuesto:
                if frase.strip():
                    salida.append(frase)
                continue
            palabras, bloque, tb = frase.split(), [], 0
            for palabra in palabras:
                np = contar(tok, palabra + " ")
                if np > presupuesto:      # una sola "palabra" mas grande que el fragmento entero
                    tirados += 1          # no es una palabra: es un volcado. Fuera y declarado.
                    continue
                if tb + np > presupuesto and bloque:
                    salida.append(" ".join(bloque))
                    bloque, tb = [], 0
                bloque.append(palabra)
                tb += np
            if bloque:
                salida.append(" ".join(bloque))
    return [x for x in salida if x.strip()], tirados


def cola_de(tok, texto: str, tokens: int) -> str:
    """Las ultimas ~N palabras completas del trozo, para el solape."""
    palabras, cola, total = texto.split(), [], 0
    for palabra in reversed(palabras):
        n = contar(tok, palabra + " ")
        if total + n > tokens:
            break
        cola.insert(0, palabra)
        total += n
    return " ".join(cola)


def trocear_prosa(tok, texto: str, presupuesto: int) -> list:
    """Empaqueta atomos hasta llenar el presupuesto, arrastrando SOLAPE tokens del trozo anterior.

    El solape se cuenta DENTRO del presupuesto: si se sumara aparte, el fragmento embebido pasaria
    de 512 y el numero del README dejaria de ser cierto."""
    trozos, actual, tokens_actual = [], [], 0
    piezas, tirados = atomos(tok, texto, presupuesto)
    for pieza in piezas:
        n = contar(tok, pieza)
        if actual and tokens_actual + n > presupuesto:
            hecho = "\n\n".join(actual)
            trozos.append(hecho)
            cola = cola_de(tok, hecho, SOLAPE)
            actual = [cola] if cola else []
            tokens_actual = contar(tok, cola) if cola else 0
            if tokens_actual + n > presupuesto:      # el solape no puede impedir que quepa la pieza
                actual, tokens_actual = [], 0
        actual.append(pieza)
        tokens_actual += n
    if actual:
        trozos.append("\n\n".join(actual))
    return [t for t in trozos if t.strip()], tirados


# --- troceado de codigo ---------------------------------------------------------------------

def cortes_de_codigo(texto: str) -> list:
    """Posiciones donde empieza una clase o un metodo. Es un contador de llaves, no un parser:
    si no encuentra cortes, se devuelve el fichero entero y se declara como hallazgo antes que
    partirlo mal. Un fragmento grande es peor que uno roto solo en coste; uno roto es basura."""
    posiciones = sorted({m.start() for m in RE_CLASE.finditer(texto)}
                        | {m.start() for m in RE_METODO.finditer(texto)})
    return posiciones


def trocear_codigo(tok, texto: str, presupuesto: int) -> tuple:
    """Devuelve (trozos, aviso). Sin solape: repetir codigo entre fragmentos no ayuda a nada."""
    if contar(tok, texto) <= presupuesto:
        return [texto], None
    posiciones = cortes_de_codigo(texto)
    if not posiciones:
        return [texto], "no se encontro ni una clase ni un metodo donde cortar"
    trozos, inicio = [], 0
    for pos in posiciones[1:]:
        trozo = texto[inicio:pos]
        if contar(tok, trozo) >= presupuesto // 2:
            trozos.append(trozo)
            inicio = pos
    trozos.append(texto[inicio:])
    grandes = [t for t in trozos if contar(tok, t) > presupuesto]
    aviso = (f"{len(grandes)} trozo(s) siguen pasandose de {presupuesto} tokens tras cortar por "
             f"clase o metodo") if grandes else None
    return [t for t in trozos if t.strip()], aviso


# --- pasada principal -----------------------------------------------------------------------

def ficheros_a_trocear(raiz: str) -> list:
    encontrados = []
    for base, _, ficheros in os.walk(raiz):
        base = base.replace(os.sep, "/")
        # La normativa (BOE) no es temario y su arbol ya se extrajo en el 1.1. Estaba fuera del
        # recorrido del corpus original pero se colaba por el espejo corpus/derivado/, y son 430
        # fragmentos de articulado con asignatura "normativa" compitiendo en la recuperacion con
        # los apuntes. Fuera en los dos sitios, que para eso se mira aqui.
        if "/normativa" in base:
            continue
        for nombre in ficheros:
            ext = os.path.splitext(nombre)[1].lower()
            if ext in EXT_TEXTO or ext in EXT_CODIGO:
                encontrados.append(f"{base}/{nombre}")
    return sorted(encontrados)


def escribir_muestreo(fragmentos: list, camino: str, cuantos: int = 20, desfase: int = 0):
    """20 fragmentos a intervalo regular, con su contexto y su origen, para leerlos A OJO.

    El `desfase` mueve el punto de arranque: el segundo muestreo tiene que caer sobre fragmentos
    DISTINTOS del primero. Si midiera sobre los mismos veinte que ya se corrigieron, el numero que
    saliera no diria si el arreglo funciona, diria que se arreglaron esos veinte.

    No se sobrescribe si ya existe: puede llevar anotaciones a mano, que es lo unico de este
    fichero que no se puede regenerar."""
    if os.path.exists(camino):
        print(f"muestreo intacto (puede llevar anotaciones): {camino}")
        return
    paso = max(1, len(fragmentos) // cuantos)
    muestra = fragmentos[desfase::paso][:cuantos]
    lineas = ["# Muestreo de fragmentos (encargo 1.4)", "",
              f"Veinte fragmentos a intervalo regular ({paso}) sobre los {len(fragmentos)} del "
              f"índice, empezando en el {desfase}. **Los lee una persona**, con su línea de",
              "contexto delante, y anota si el fragmento se entiende solo y si su "
              "`tipo_contenido` es el que le pega.",
              "",
              "La `unidad` es el primer directorio con significado bajo la asignatura, y va vacía "
              "cuando no hay ninguno (ADR 0005: sale de la carpeta del material, no del BOE).", ""]
    for i, fr in enumerate(muestra, 1):
        cuerpo = fr["texto"].strip().replace("\n", " ")
        lineas += [f"## {i}. `{fr['tipo_contenido']}` · {fr['tokens']} tokens", "",
                   f"- **Contexto:** {fr['contexto']}",
                   f"- **Origen:** `{fr['documento']}` (trozo {fr['orden']})",
                   f"- **Asignatura:** {fr['asignatura'] or '(no declarada)'} "
                   f"— *{fr.get('asignatura_origen')}*",
                   f"- **Unidad:** {fr['unidad'] or '(ninguna carpeta con significado)'}"]
        if fr.get("frase_definitoria"):
            frase = " ".join(fr["frase_definitoria"].split())
            lineas.append(f"- **Frase candidata a definición:** {frase[:300]}")
        lineas += ["", "> " + (cuerpo[:600] + ("…" if len(cuerpo) > 600 else "")), "",
                   "¿Se entiende solo? ___  ¿El tipo es correcto? ___", ""]
    with open(camino, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lineas) + "\n")
    print(f"muestreo para leer a ojo -> {camino}")


def escribir_descartes(por_documento: list, por_fragmento: list, admitidos: int, camino: str):
    """La lista de descartes, entera y con su motivo, en un fichero de git.

    Se regenera en cada pasada A PROPOSITO: asi un cambio en la puerta se ve en el diff como lo que
    es -que documento entra y cual sale-, y no como un numero que sube o baja en un resumen.
    """
    total = sum(n for _, _, n in por_documento) + len(por_fragmento)
    lineas = [
        "# Descartes de la puerta de admision (arreglo del 1.4)", "",
        "Generado por `scripts/trocear.py`. **No se edita a mano**: los criterios están en",
        "`scripts/admitir.py` y la lista manual de documentos, también.", "",
        f"- Fragmentos admitidos: **{admitidos}**",
        f"- Fuera por documento excluido entero: **{sum(n for _, _, n in por_documento)}** "
        f"en {len(por_documento)} documentos",
        f"- Fuera sueltos, dentro de documentos que sí entran: **{len(por_fragmento)}**",
        f"- Total fuera: **{total}** de {total + admitidos} "
        f"({100 * total / max(total + admitidos, 1):.1f} %)", "",
        "## Por qué salen los documentos", "",
    ]
    motivos = collections.Counter(m for _, m, _ in por_documento)
    for motivo, n in motivos.most_common():
        lineas.append(f"- {n} documento(s): {motivo}")
    lineas += ["", "## Documentos excluidos, uno a uno", "",
               "| fragmentos | documento | motivo |", "| ---: | --- | --- |"]
    for ruta, motivo, n in sorted(por_documento, key=lambda x: -x[2]):
        lineas.append(f"| {n} | `{ruta}` | {motivo} |")
    lineas += ["", "## Fragmentos sueltos, por motivo", "",
               "| fragmentos | motivo |", "| ---: | --- |"]
    for motivo, n in collections.Counter(m for _, _, m in por_fragmento).most_common():
        lineas.append(f"| {n} | {motivo} |")
    with open(camino, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lineas) + "\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Trocea el corpus normalizado (encargo 1.4).")
    p.add_argument("--raiz", default=None, help="por defecto, corpus/derivado y los .md nativos")
    p.add_argument("--salida", default=SALIDA)
    p.add_argument("--muestreo", default="docs/muestreo-fragmentos.md")
    p.add_argument("--descartes", default="docs/descartes-admision.md")
    p.add_argument("--desfase", type=int, default=0,
                   help="desde que fragmento arranca el muestreo (para muestrear otros distintos)")
    p.add_argument("--solo-muestreo", action="store_true",
                   help="no trocea: lee el indice ya escrito y saca otro muestreo")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if a.solo_muestreo:
        with open(a.salida, encoding="utf-8") as f:
            escribir_muestreo([json.loads(x) for x in f if x.strip()], a.muestreo,
                              desfase=a.desfase)
        return 0

    tok = cargar_tokenizador()
    if a.raiz:
        rutas = ficheros_a_trocear(a.raiz)
    else:
        rutas = ficheros_a_trocear(DERIVADO)
        for base, _, ficheros in os.walk("corpus"):
            base = base.replace(os.sep, "/")
            # Fuera la normativa (su arbol ya se extrajo en el 1.1) y fuera la raiz de corpus/,
            # donde viven los metadatos del propio corpus: COBERTURA.md no es temario, y se estaba
            # troceando como si lo fuera (14 fragmentos con titulacion "COBERTURA.md").
            if base.startswith(DERIVADO) or "/normativa" in base or base == "corpus":
                continue
            for nombre in ficheros:
                ext = os.path.splitext(nombre)[1].lower()
                if ext in EXT_TEXTO or ext in EXT_CODIGO:
                    rutas.append(f"{base}/{nombre}")
        rutas = sorted(set(rutas))

    fragmentos, avisos, secretos, excluidos, sospechas = [], [], [], [], []
    fuera_de_documento, fuera_de_fragmento = [], []
    saltados = 0
    for ruta in rutas:
        ext = os.path.splitext(ruta)[1].lower()
        es_codigo = ext in EXT_CODIGO
        try:
            texto = open(ruta, encoding="utf-8", errors="replace").read().strip()
        except OSError as e:
            avisos.append((ruta, f"no se pudo leer: {e}"))
            continue
        if not texto:
            saltados += 1
            continue
        if RE_LISTA_DE_CLASE.search(texto):
            sospechas.append(ruta)

        partes = ruta_a_partes(ruta)
        titulo = titulo_de(ruta, texto)
        contexto = linea_de_contexto(ruta, partes, titulo)
        presupuesto = TOKENS - contar(tok, contexto) - 2   # 2 por los especiales del modelo
        if presupuesto < 100:
            avisos.append((ruta, f"la linea de contexto se come el fragmento ({contexto[:60]}...)"))
            continue

        if es_codigo:
            trozos, aviso = trocear_codigo(tok, texto, presupuesto)
            if aviso:
                avisos.append((ruta, aviso))
        else:
            trozos, tirados = trocear_prosa(tok, texto, presupuesto)
            if tirados:
                secretos.append((ruta, tirados))

        del_fichero = []
        for orden, trozo in enumerate(trozos, 1):
            completo = contexto + "\n\n" + trozo
            del_fichero.append({
                "documento": ruta,
                "orden": orden,
                "titulacion": partes["titulacion"],
                "curso": partes["curso"],
                "asignatura": partes["asignatura"],
                "asignatura_origen": partes["asignatura_origen"],
                "unidad": partes["unidad"],
                "unidad_origen": "carpeta del material (ADR 0005)" if partes["unidad"] else None,
                "tipo_contenido": tipo_de_contenido(trozo, es_codigo),
                # La frase candidata a definicion viaja con el fragmento: es la unidad que el 1.6
                # necesita, y guardarla aqui deja el glosario verificable por comparacion literal.
                "frase_definitoria": None if es_codigo else frase_definitoria(trozo),
                "lenguaje": EXT_CODIGO.get(ext),
                "contexto": contexto,
                "texto": trozo,
                "tokens": contar(tok, completo),
                "tokens_cuerpo": contar(tok, trozo),
            })

        # LA PUERTA DE ADMISION (scripts/admitir.py), en sus dos niveles y en este orden: primero
        # el documento entero, que es donde esta el volumen, y solo dentro de los que entran se
        # juzga fragmento a fragmento. Al reves, un diccionario de palabras aportaria 654 motivos
        # de fragmento y ninguna decision sobre el fichero.
        motivo = admitir.juzgar_documento(ruta, del_fichero)
        if motivo:
            fuera_de_documento.append((ruta, motivo, len(del_fichero)))
            continue
        for fr in del_fichero:
            motivo = admitir.juzgar_fragmento(fr)
            if motivo:
                fuera_de_fragmento.append((ruta, fr["orden"], motivo))
            else:
                fragmentos.append(fr)

    # `orden` NO se renumera tras la puerta, y esto no es pereza. El detector del 1.8 excluye por
    # diseño los pares consecutivos del mismo documento, porque comparten los 64 tokens de solape y
    # son artefacto suyo. Si al caer el fragmento 5 se renumerara el 6 como 5, el 4 y el 6 -que
    # nunca solaparon entre si- pasarian a parecer vecinos y el detector se comeria un par bueno.
    # El hueco en la numeracion dice la verdad: ahi habia un fragmento y la puerta se lo llevo.
    with open(a.salida, "w", encoding="utf-8", newline="\n") as f:
        for fr in fragmentos:
            f.write(json.dumps(fr, ensure_ascii=False) + "\n")

    escribir_muestreo(fragmentos, a.muestreo)
    escribir_descartes(fuera_de_documento, fuera_de_fragmento, len(fragmentos), a.descartes)

    # La puerta distingue lo que es defecto de lo que es la regla funcionando:
    #   - prosa por encima de 512  -> DEFECTO: el troceador no ha hecho su trabajo.
    #   - codigo por encima de 512 -> DECLARADO: la regla dice que una clase o un metodo no se
    #     parten por ventana ciega, asi que un metodo grande da un fragmento grande. Se cuenta y
    #     se enseña, no se esconde, pero no es un fallo.
    #   - cualquiera por encima del maximo del modelo -> DEFECTO: eso ni se puede embeber.
    prosa_grande = [fr for fr in fragmentos if fr["tokens"] > TOKENS
                    and fr["tipo_contenido"] != "codigo"]
    codigo_grande = [fr for fr in fragmentos if fr["tokens"] > TOKENS
                     and fr["tipo_contenido"] == "codigo"]
    inembebibles = [fr for fr in fragmentos if fr["tokens"] > 8192]
    vacios = [fr for fr in fragmentos if not fr["texto"].strip()]

    perdidos = sum(n for _, _, n in fuera_de_documento)
    print(f"{len(fragmentos)} fragmentos de {len(rutas)} ficheros -> {a.salida}"
          f" ({saltados} ficheros vacios saltados)")
    print(f"  puerta de admision: {perdidos} fragmentos fuera por documento excluido "
          f"({len(fuera_de_documento)} documentos) + {len(fuera_de_fragmento)} sueltos"
          f" = {perdidos + len(fuera_de_fragmento)} de "
          f"{perdidos + len(fuera_de_fragmento) + len(fragmentos)}"
          f" -> {a.descartes}")
    for ruta, motivo in excluidos:
        print(f"  EXCLUIDO A PROPOSITO: {ruta} ({motivo})")
    for ruta in sospechas:
        print(f"  POSIBLES DATOS PERSONALES (decide una persona): {ruta}")
    for ruta, cuantos in secretos:
        print(f"  FUERA POR SECRETO O VOLCADO: {ruta} ({cuantos} bloque(s) descartados)")
    for ruta, motivo in avisos:
        print(f"  AVISO: {ruta} ({motivo})")
    for fr in prosa_grande[:10]:
        print(f"  PROSA QUE SE PASA: {fr['documento']} #{fr['orden']} ({fr['tokens']} tokens)")
    if codigo_grande:
        mayor = max(fr["tokens"] for fr in codigo_grande)
        print(f"  codigo por encima de {TOKENS} (declarado, no es fallo): {len(codigo_grande)} "
              f"fragmentos, el mayor de {mayor} tokens")
    print(f"hallazgos: {len(prosa_grande)} de prosa pasados, {len(inembebibles)} inembebibles, "
          f"{len(vacios)} vacios | declarados: {len(codigo_grande)} de codigo, "
          f"{sum(c for _, c in secretos)} bloques fuera por secreto")
    return 1 if (prosa_grande or vacios or inembebibles) else 0


if __name__ == "__main__":
    sys.exit(main())
