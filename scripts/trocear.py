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
import json
import os
import re
import sys

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
RE_DEFINICION = re.compile(r"\b(se define como|es un|es una|se denomina|se conoce como|"
                           r"consiste en|definici[oó]n)\b", re.I)
RE_PROCEDIMIENTO = re.compile(r"^\s*(?:\d+[.)]|paso \d|primero|a continuaci[oó]n|"
                              r"por [uú]ltimo)\b", re.I | re.M)
RE_EJEMPLO = re.compile(r"\b(ejemplo|ejercicio|soluci[oó]n|resuelto|caso pr[aá]ctico)\b", re.I)
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

def ruta_a_partes(ruta: str) -> dict:
    """De 'corpus/derivado/daw/curso1/programacion/lionel-ict/Unidad 4 .../x.pdf.md' saca
    titulacion, curso, asignatura y unidad. La unidad es la CARPETA (ADR 0005)."""
    partes = ruta.split("/")
    if partes[:2] == ["corpus", "derivado"]:
        partes = partes[2:]
    elif partes[:1] == ["corpus"]:
        partes = partes[1:]
    datos = {"titulacion": partes[0] if partes else "", "curso": None,
             "asignatura": "", "unidad": None}
    resto = partes[1:]
    if resto and re.fullmatch(r"curso(\d)", resto[0]):
        datos["curso"] = int(resto[0][-1])
        resto = resto[1:]
    if resto:
        datos["asignatura"] = resto[0]
        resto = resto[1:]
    carpetas = resto[:-1]
    if carpetas:
        datos["unidad"] = carpetas[-1]
    return datos


def linea_de_contexto(ruta: str, partes: dict, titulo: str) -> str:
    trozos = [partes["titulacion"].upper()]
    if partes["curso"]:
        trozos.append(f"curso {partes['curso']}")
    trozos.append(partes["asignatura"])
    if partes["unidad"]:
        trozos.append(partes["unidad"])
    trozos.append(titulo)
    return " · ".join(t for t in trozos if t)


def tipo_de_contenido(texto: str, es_codigo: bool) -> str:
    if es_codigo:
        return "codigo"
    if RE_NORMATIVA.search(texto):
        return "normativa"
    if RE_EJEMPLO.search(texto):
        return "ejemplo_resuelto"
    if len(RE_PROCEDIMIENTO.findall(texto)) >= 2:
        return "procedimiento"
    if RE_DEFINICION.search(texto):
        return "definicion"
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


# Ficheros que NO entran al corpus por lo que contienen, no por su formato. Se apuntan aqui con su
# motivo en vez de borrarlos del disco: el corpus es material de terceros y no se reescribe, pero
# esto no llega a fragmento y por tanto no llega a embedding ni a una respuesta.
EXCLUIDOS = {
    "corpus/asir/apuntes/lora-1asir/LM/PYTHON/Entrega 3/notas.txt":
        "datos personales: lista de alumnos con grupo y notas",
}

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
        for nombre in ficheros:
            ext = os.path.splitext(nombre)[1].lower()
            if ext in EXT_TEXTO or ext in EXT_CODIGO:
                encontrados.append(f"{base}/{nombre}")
    return sorted(encontrados)


def escribir_muestreo(fragmentos: list, camino: str, cuantos: int = 20):
    """20 fragmentos a intervalo regular, con su contexto y su origen, para leerlos A OJO.

    No se sobrescribe si ya existe: puede llevar anotaciones a mano, que es lo unico de este
    fichero que no se puede regenerar."""
    if os.path.exists(camino):
        print(f"muestreo intacto (puede llevar anotaciones): {camino}")
        return
    paso = max(1, len(fragmentos) // cuantos)
    muestra = fragmentos[::paso][:cuantos]
    lineas = ["# Muestreo de fragmentos (encargo 1.4)", "",
              "Veinte fragmentos a intervalo regular sobre los " + str(len(fragmentos)) +
              " del corpus. **Los lee una persona**, con su línea de contexto delante, y anota si",
              "el fragmento se entiende solo y si su `tipo_contenido` es el que le pega.",
              "",
              "La `unidad` sale de la CARPETA del material, no del árbol del BOE (ADR 0005).", ""]
    for i, fr in enumerate(muestra, 1):
        cuerpo = fr["texto"].strip().replace("\n", " ")
        lineas += [f"## {i}. `{fr['tipo_contenido']}` · {fr['tokens']} tokens", "",
                   f"- **Contexto:** {fr['contexto']}",
                   f"- **Origen:** `{fr['documento']}` (trozo {fr['orden']})",
                   f"- **Unidad:** {fr['unidad'] or '(el documento no cuelga de ninguna carpeta)'}",
                   "", "> " + (cuerpo[:600] + ("…" if len(cuerpo) > 600 else "")), "",
                   "¿Se entiende solo? ___  ¿El tipo es correcto? ___", ""]
    with open(camino, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lineas) + "\n")
    print(f"muestreo para leer a ojo -> {camino}")


def main() -> int:
    p = argparse.ArgumentParser(description="Trocea el corpus normalizado (encargo 1.4).")
    p.add_argument("--raiz", default=None, help="por defecto, corpus/derivado y los .md nativos")
    p.add_argument("--salida", default=SALIDA)
    p.add_argument("--muestreo", default="docs/muestreo-fragmentos.md")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

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
    saltados = 0
    for ruta in rutas:
        if ruta in EXCLUIDOS:
            excluidos.append((ruta, EXCLUIDOS[ruta]))
            continue
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
        titulo_md = RE_TITULO.search(texto)
        titulo = (titulo_md.group(1).strip() if titulo_md
                  else os.path.basename(ruta).replace(".pdf.md", "").replace(".md", ""))
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

        for orden, trozo in enumerate(trozos, 1):
            completo = contexto + "\n\n" + trozo
            fragmentos.append({
                "documento": ruta,
                "orden": orden,
                "titulacion": partes["titulacion"],
                "curso": partes["curso"],
                "asignatura": partes["asignatura"],
                "unidad": partes["unidad"],
                "unidad_origen": "carpeta del material (ADR 0005)" if partes["unidad"] else None,
                "tipo_contenido": tipo_de_contenido(trozo, es_codigo),
                "lenguaje": EXT_CODIGO.get(ext),
                "contexto": contexto,
                "texto": trozo,
                "tokens": contar(tok, completo),
                "tokens_cuerpo": contar(tok, trozo),
            })

    with open(a.salida, "w", encoding="utf-8", newline="\n") as f:
        for fr in fragmentos:
            f.write(json.dumps(fr, ensure_ascii=False) + "\n")

    escribir_muestreo(fragmentos, a.muestreo)

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

    print(f"{len(fragmentos)} fragmentos de {len(rutas)} ficheros -> {a.salida}"
          f" ({saltados} ficheros vacios saltados)")
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
