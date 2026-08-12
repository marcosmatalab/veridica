#!/usr/bin/env python3
"""Puerta de material sensible en el corpus (encargo 1.4, ampliado tras dos hallazgos de rebote).

Motivo: en el 1.4 aparecio una clave privada RSA y en el 1.5 un CSV con nombres y notas de alumnos.
Los dos se cazaron POR CASUALIDAD, mirando otra cosa. Un corpus recolectado de repos publicos
contiene datos personales y secretos aunque nadie los haya puesto a proposito, asi que buscarlos
tiene que ser una pasada sistematica y no un golpe de suerte.

Dos niveles, y la diferencia importa:

  BLOQUEANTE (salida 1): claves privadas, certificados, tokens, DNI o NIE con letra correcta,
  IBAN, y listados de nombre con notas. Nada de esto es temario y todo tiene consecuencias.

  AVISO (no bloquea): correos y telefonos. En material docente estan por todas partes y son del
  propio profesor que lo publico -su correo aparece en la portada de sus apuntes-, asi que
  bloquear por eso dejaria la puerta en rojo permanente, y una puerta siempre roja acaba relajada
  (la leccion del ADR 0001). Se cuentan y se enseñan, y una persona decide.

Y un tercer nivel, que salio de un hueco real: un CV con nombre, telefono, correo, codigo postal y
redes de una persona paso por esta puerta como cinco avisos sueltos, porque cada señal por separado
es de las que no bloquean. Lo cazo la puerta de admision del indice, no esta.

  CONCENTRACION (salida 1): un documento donde las señales de datos personales son DENSAS respecto
  a su longitud y ademas de VARIAS CLASES. Un documento que contiene un correo no es lo mismo que
  un documento que ES datos personales.

La variedad no es un adorno del criterio, es lo que lo hace funcionar, y se decidio midiendo: por
densidad sola, el CV (13,8 señales por mil palabras) queda por DEBAJO de un ejercicio de Postgres
con diez correos de ejemplo (23,3) y de unos apuntes de Docker (15,9). Contando clases distintas, el
CV salta a 48,3 con cuatro clases y el siguiente documento del corpus con dos clases se queda en
11,5: margen de cuatro veces, no de un pelo.

Uso:
    python scripts/detectar_sensibles.py                 # todo el corpus
    python scripts/detectar_sensibles.py --raiz corpus/daw --detalle
"""
import argparse
import collections
import os
import re
import sys

EXTENSIONES = {".md", ".txt", ".html", ".htm", ".java", ".cs", ".sql", ".xml", ".json", ".yml",
               ".yaml", ".properties", ".csv", ".py", ".js", ".ts", ".kt", ".gradle", ".jsonl",
               ".sh", ".bat", ".ps1", ".env", ".cfg", ".ini", ".conf"}

BLOQUEANTES = {
    "clave_privada": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "certificado": re.compile(r"-----BEGIN CERTIFICATE-----"),
    "token_conocido": re.compile(r"\b(?:ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{32,}|"
                                 r"AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b"),
    "iban": re.compile(r"\bES\d{2}[ ]?\d{4}[ ]?\d{4}[ ]?\d{2}[ ]?\d{10}\b"),
    "lista_de_notas": re.compile(
        r"[A-ZÁÉÍÓÚÑ]{3,}\s+[A-ZÁÉÍÓÚÑ]{3,},\s*[A-ZÁÉÍÓÚÑ ]{3,},\s*\d[A-Za-z],(?:\s*\d+,){3}"),
}
AVISOS = {
    "correo": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"),
    "telefono": re.compile(r"(?<!\d)(?:\+34[ -]?)?[6789]\d{2}[ -]?\d{3}[ -]?\d{3}(?!\d)"),
}

# --- concentracion: el documento como un todo, no la linea -----------------------------------
# Las clases que identifican a UNA persona. Se cuentan valores DISTINTOS, no ocurrencias: el correo
# del profesor repetido en el pie de sus sesenta paginas es un dato, no sesenta.
CLASES_PERSONALES = {
    "correo": AVISOS["correo"],
    "telefono": AVISOS["telefono"],
    "direccion_postal": re.compile(
        r"\b\d{5}\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-Za-záéíóúñ]+){0,3},?\s*"
        r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+"),
    # Con los dos puntos detras: asi caza "LinkedIn: Fulano" de una portada de CV y no la frase
    # "puedes compartirlo en LinkedIn" de unos apuntes de marketing.
    "perfil_social": re.compile(r"\b(?:twitter|linkedin|facebook|instagram|medium)\s*:", re.I),
}
# Los tres numeros del criterio, medidos sobre el corpus y no elegidos a ojo (ver COBERTURA.md).
CLASES_MINIMAS = 2
SEÑALES_MINIMAS = 3          # con dos, un documento "contiene un correo"; no "es datos personales"
DENSIDAD_MINIMA = 10.0       # señales distintas por cada mil palabras
# Excepciones DECLARADAS una a una, con su motivo. No se silencia una categoria entera: si mañana
# aparece un DNI en material nuevo, la puerta se pone roja. Lo que se declara es este fichero, este
# tipo y este porque, revisado a mano.
DECLARADOS = {
    ("corpus/daw/curso1/programacion/lionel-ict/Unidad 8 POO (I)/Solución Ejercicios/E2/"
     "UD8_E2_ProgramaPersona.java", "dni"): "ejercicio de validacion de DNI: el numero es el enunciado",
    ("corpus/derivado/daw/curso1/bases-de-datos/comesana/BD07.pdf.md", "dni"):
        "INSERT de ejemplo con personas inventadas en un ejercicio de SQL",
    ("corpus/derivado/daw/curso1/bases-de-datos/comesana/tareas/BD_Tarea5.pdf.md", "dni"):
        "enunciado de tarea con DNI y nombres inventados",
    ("corpus/derivado/daw/curso1/programacion/lionel-ict/Unidad 8 POO (I)/"
     "ud8_CasoPractico_DawBank.pdf.md", "iban"):
        "explicacion del formato IBAN con un ejemplo, no una cuenta real",
    ("corpus/derivado/asir/apuntes/lora-1asir/BBDD/Ejercicios/"
     "Primera_base_de_datos_de_alumnos.pdf.md", "concentracion_datos_personales"):
        "enunciado del IES Gonzalo Nazareno: la tabla de 'alumnos' que manda teclear son personas "
        "inventadas (los DNI no llevan letra, las fechas van de 1956 a 1977 y las direcciones no "
        "existen). Revisado a mano linea por linea antes de declararlo",
}

# El agregado no se revisa: su contenido es la union de ficheros que ya se revisan de uno en uno, y
# revisarlo dos veces solo duplica ocurrencias y obliga a declarar excepciones dos veces.
AGREGADOS = {"corpus/fragmentos.jsonl"}

RE_DNI = re.compile(r"\b(\d{8})[ -]?([A-HJ-NP-TV-Z])\b", re.I)
LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"


def dni_valido(numero: str, letra: str) -> bool:
    """Con la letra comprobada, no solo con la forma: sin esto, cualquier numero de ocho cifras
    seguido de una letra (una referencia, un codigo de pieza) seria un falso positivo."""
    return LETRAS_DNI[int(numero) % 23] == letra.upper()


def enmascarar(texto: str) -> str:
    """Lo que se imprime no puede ser el propio dato: un informe de datos personales que los
    reproduce es el mismo problema en otro fichero."""
    limpio = " ".join(texto.split())[:80]
    return re.sub(r"[A-Za-z0-9ÁÉÍÓÚÑáéíóúñ]", "·", limpio[:20]) + limpio[20:40] + "…"


def concentracion(texto: str) -> dict:
    """Cuenta, por clase, cuantos valores DISTINTOS de datos personales trae el documento."""
    presentes = {}
    for clase, patron in CLASES_PERSONALES.items():
        valores = {re.sub(r"[ \-]", "", m.group(0)).lower() for m in patron.finditer(texto)}
        if valores:
            presentes[clase] = len(valores)
    palabras = max(len(texto.split()), 1)
    señales = sum(presentes.values())
    return {"clases": presentes, "señales": señales, "palabras": palabras,
            "densidad": 1000 * señales / palabras}


def es_concentracion(medida: dict) -> bool:
    return (len(medida["clases"]) >= CLASES_MINIMAS
            and medida["señales"] >= SEÑALES_MINIMAS
            and medida["densidad"] >= DENSIDAD_MINIMA)


def revisar(ruta: str) -> list:
    try:
        texto = open(ruta, encoding="utf-8", errors="replace").read()
    except OSError:
        return []
    hallazgos = []
    medida = concentracion(texto)
    if es_concentracion(medida):
        hallazgos.append(("concentracion_datos_personales", "bloqueante", 0,
                          f"{medida['señales']} señales distintas de "
                          f"{len(medida['clases'])} clases {sorted(medida['clases'])} en "
                          f"{medida['palabras']} palabras: {medida['densidad']:.1f} por mil"))
    for numero, linea in enumerate(texto.split("\n"), 1):
        for tipo, patron in BLOQUEANTES.items():
            if patron.search(linea):
                hallazgos.append((tipo, "bloqueante", numero, enmascarar(linea)))
        for m in RE_DNI.finditer(linea):
            if dni_valido(m.group(1), m.group(2)):
                hallazgos.append(("dni", "bloqueante", numero, enmascarar(linea)))
        for tipo, patron in AVISOS.items():
            if patron.search(linea):
                hallazgos.append((tipo, "aviso", numero, enmascarar(linea)))
    return hallazgos


def main() -> int:
    p = argparse.ArgumentParser(description="Busca secretos y datos personales en el corpus.")
    p.add_argument("--raiz", default="corpus")
    p.add_argument("--detalle", action="store_true", help="lista fichero a fichero")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    por_tipo = collections.Counter()
    bloqueantes, ficheros_con_aviso = [], set()
    revisados = declarados = 0
    for base, _, ficheros in os.walk(a.raiz):
        base = base.replace(os.sep, "/")
        for nombre in ficheros:
            if os.path.splitext(nombre)[1].lower() not in EXTENSIONES:
                continue
            ruta = f"{base}/{nombre}"
            if ruta in AGREGADOS:
                continue
            revisados += 1
            for tipo, nivel, linea, muestra in revisar(ruta):
                if (ruta, tipo) in DECLARADOS:
                    declarados += 1
                    continue
                por_tipo[(nivel, tipo)] += 1
                if nivel == "bloqueante":
                    bloqueantes.append((ruta, tipo, linea, muestra))
                else:
                    ficheros_con_aviso.add((ruta, tipo))

    print(f"revisados {revisados} ficheros de texto bajo {a.raiz} "
          f"({declarados} ocurrencias en excepciones ya declaradas)")
    for (nivel, tipo), n in sorted(por_tipo.items()):
        print(f"  {nivel:11} {tipo:16} {n:5} ocurrencias")
    print(f"ficheros distintos con aviso: {len({r for r, _ in ficheros_con_aviso})}")

    if bloqueantes:
        print(f"\nBLOQUEANTES: {len(bloqueantes)} ocurrencias en "
              f"{len({r for r, _, _, _ in bloqueantes})} ficheros")
        for ruta, tipo, linea, muestra in (bloqueantes if a.detalle else bloqueantes[:20]):
            print(f"  {tipo:16} {ruta}:{linea}  {muestra}")
    else:
        print("\nsin hallazgos bloqueantes")

    # Ocurrencias y hallazgos por separado, como manda el repo.
    print(f"\nresumen: {len(bloqueantes)} ocurrencias bloqueantes en "
          f"{len({r for r, _, _, _ in bloqueantes})} ficheros | "
          f"{sum(n for (nivel, _), n in por_tipo.items() if nivel == 'aviso')} avisos en "
          f"{len({r for r, _ in ficheros_con_aviso})} ficheros")
    return 1 if bloqueantes else 0


if __name__ == "__main__":
    sys.exit(main())
