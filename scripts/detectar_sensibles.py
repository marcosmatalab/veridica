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


def revisar(ruta: str) -> list:
    try:
        texto = open(ruta, encoding="utf-8", errors="replace").read()
    except OSError:
        return []
    hallazgos = []
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
