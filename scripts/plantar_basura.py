#!/usr/bin/env python3
"""Encargo 1.7: planta basura controlada en el corpus, declarada en el manifiesto.

Tres tipos, que son los tres que el detector del 1.8 tiene que encontrar:

  casi_duplicado  tres copias de documentos reales con cambios menores (una cifra, un sinonimo,
                  una frase reordenada). No ruido aleatorio: un casi duplicado que no se parece a
                  nada no prueba nada.
  contradiccion   una hoja de repaso que contradice al temario en un detalle SUSTANTIVO.
  colado          un documento de otra asignatura dentro de la carpeta equivocada, que es lo que
                  permite medir contaminacion cruzada en el 3.5.

ESTA BASURA SE PLANTA ANTES DE ESCRIBIR EL 1.8, y a proposito. Si se escribiera pensando en como
la va a encontrar el detector, el detector no demostraria nada: seria el auditor compartiendo
supuesto con el parser (principio 6). La contradiccion sintetica esta redactada como la escribiria
un profesor que corrige una simplificacion de sus apuntes, no como un caso de prueba.

Y esta declarado que el caso sintetico es CONDICION NECESARIA -si el detector no lo encuentra, no
sirve-, mientras que la prueba honesta es el par REAL del corpus (el DWES de 2012 contra el de
2025, con sus dos definiciones incompatibles de la Vista de MVC, citadas en COBERTURA.md).

Uso:
    python scripts/plantar_basura.py --plantar
    python scripts/plantar_basura.py --retirar
    python scripts/plantar_basura.py            # solo comprueba disco contra manifiesto
"""
import argparse
import hashlib
import json
import os
import sys

MANIFIESTO = "corpus/manifiesto.jsonl"
PROG = "corpus/daw/curso1/programacion/lionel-ict"
DERIVADO = "corpus/derivado/daw/curso1/programacion/lionel-ict"

# --- (b) la contradiccion sintetica -----------------------------------------------------------
# El temario dice, en ud7_Funciones: "Parametros de tipo objeto (paso por referencias) [...] no se
# copia el objeto sino que se le pasa a la funcion una referencia al objeto original". Esta hoja
# dice lo contrario sobre el mismo concepto, y es una discusion REAL entre materiales docentes de
# Java, no un "el valor es 5" contra "el valor es 7".
CONTRADICCION = """# UD7 · Hoja de repaso: paso de parámetros en Java

Aclaración importante antes del examen, porque en los apuntes de la unidad se dice de otra manera
y conviene que lo tengáis claro.

**En Java TODOS los parámetros se pasan por valor, también los objetos.** No existe el paso por
referencia en Java. Lo que ocurre con un objeto es que lo que se copia es la **referencia**, no el
objeto: la función recibe una copia de la dirección, no la variable original.

La diferencia se ve cuando dentro de la función se hace `v = new int[3];`. Si el paso fuera por
referencia, la variable de fuera pasaría a apuntar al array nuevo. Como el paso es por valor, la
variable de fuera sigue apuntando al array de antes: solo cambió la copia local.

Decir "los objetos se pasan por referencia" es una simplificación que funciona para explicar por
qué se ven los cambios en los elementos de un array, pero es incorrecta y os va a fallar en cuanto
reasignéis el parámetro dentro de la función.

Un detalle relacionado: los objetos `String` son **inmutables**, así que ningún cambio hecho dentro
de una función puede modificar el String de fuera, ni siquiera al concatenar.
"""

PLANTADOS = [
    {"destino": f"{PROG}/Unidad 7 Funciones/ud7_repaso_paso_de_parametros.md",
     "motivo": "contradiccion", "contenido": CONTRADICCION,
     "porque": "contradice a ud7_Funciones sobre el paso de parametros de objetos en Java"},
    {"destino": f"{PROG}/Unidad 5 Bucles/ud5_Bucles_en_Java_v2.md",
     "motivo": "casi_duplicado", "origen": f"{DERIVADO}/Unidad 5 Bucles/ud5_Bucles_en_Java.pdf.md",
     "porque": "copia de los apuntes de bucles con cambios menores"},
    {"destino": f"{PROG}/Unidad 6 Arrays/ud6_Arrays_repaso.md",
     "motivo": "casi_duplicado", "origen": f"{DERIVADO}/Unidad 6 Arrays/ud6_Arrays.pdf.md",
     "porque": "copia de los apuntes de arrays con cambios menores"},
    {"destino": f"{PROG}/Unidad 8 POO (I)/ud8_POO_resumen.md",
     "motivo": "casi_duplicado", "origen": f"{DERIVADO}/Unidad 8 POO (I)/ud8_POO.pdf.md",
     "porque": "copia de los apuntes de POO con cambios menores"},
    {"destino": f"{PROG}/Unidad 13 Acceso a Bases de Datos/BD05_modelo_relacional.md",
     "motivo": "colado",
     "origen": "corpus/derivado/daw/curso1/bases-de-datos/comesana/BD05.pdf.md",
     "porque": "documento de Bases de datos (0484) metido en Programacion (0485)"},
]

# Cambios menores para los casi duplicados: sinonimos y cifras, aplicados en orden y sin azar, para
# que plantar dos veces de el mismo fichero y el mismo hash.
CAMBIOS = [("por lo tanto", "por tanto"), ("Es decir", "O sea"), ("por ejemplo", "por ejemplo,"),
           ("En este caso", "En tal caso"), ("se puede", "puede"), ("512", "1024"),
           ("Programación", "Programacion"), ("un array", "un vector")]


def casi_duplicar(texto: str) -> str:
    cabeza = ("# Repaso de la unidad (versión resumida para el examen)\n\n"
              "Este material repite el contenido de los apuntes de la unidad en una versión más\n"
              "breve para repasar.\n\n")
    cuerpo = texto
    for viejo, nuevo in CAMBIOS:
        cuerpo = cuerpo.replace(viejo, nuevo)
    parrafos = [p for p in cuerpo.split("\n\n") if p.strip()]
    if len(parrafos) > 6:                      # una frase reordenada, como en una copia real
        parrafos[3], parrafos[4] = parrafos[4], parrafos[3]
    return cabeza + "\n\n".join(parrafos[:120])


def sha256(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def cargar():
    with open(MANIFIESTO, encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


def guardar(entradas):
    with open(MANIFIESTO, "w", encoding="utf-8", newline="\n") as f:
        for e in entradas:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def plantar() -> int:
    entradas = cargar()
    por_ruta = {e["ruta"]: e for e in entradas}
    for p in PLANTADOS:
        if "contenido" in p:
            texto = p["contenido"]
        else:
            if not os.path.exists(p["origen"]):
                sys.exit(f"falta el original del que copiar: {p['origen']}")
            original = open(p["origen"], encoding="utf-8").read()
            texto = casi_duplicar(original) if p["motivo"] == "casi_duplicado" else original
        os.makedirs(os.path.dirname(p["destino"]), exist_ok=True)
        with open(p["destino"], "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        entrada = {
            "ruta": p["destino"], "fuente": f"plantado por scripts/plantar_basura.py: {p['porque']}",
            "licencia": "propia (material plantado, no redistribuible)",
            "version_corpus": "v3-2026-08-11", "hash_sha256": sha256(p["destino"]),
            "densidad": "n/a", "plantado": True, "plantado_motivo": p["motivo"],
        }
        if "origen" in p:
            entrada["plantado_origen"] = p["origen"]
        if p["destino"] in por_ruta:
            por_ruta[p["destino"]].update(entrada)
        else:
            entradas.append(entrada)
            por_ruta[p["destino"]] = entrada
        print(f"  plantado ({p['motivo']}): {p['destino']}")
    guardar(entradas)
    return 0


def retirar() -> int:
    entradas = cargar()
    rutas = {p["destino"] for p in PLANTADOS}
    for ruta in sorted(rutas):
        if os.path.exists(ruta):
            os.remove(ruta)
            print("  retirado:", ruta)
    guardar([e for e in entradas if e["ruta"] not in rutas])
    return 0


def comprobar() -> int:
    """El manifiesto tiene que listar EXACTAMENTE lo plantado por este script: ni uno mas (basura
    sin declarar) ni uno menos (declarada y no plantada)."""
    declarados = {e["ruta"]: e for e in cargar()
                  if e.get("plantado_motivo") in ("casi_duplicado", "contradiccion", "colado")}
    esperados = {p["destino"]: p["motivo"] for p in PLANTADOS}
    en_disco = {r for r in esperados if os.path.exists(r)}

    sin_declarar = sorted(en_disco - set(declarados))
    sin_fichero = sorted(set(declarados) - en_disco)
    mal_motivo = sorted(r for r in set(declarados) & en_disco
                        if declarados[r]["plantado_motivo"] != esperados.get(r))
    for r in sin_declarar:
        print("PLANTADO SIN DECLARAR:", r)
    for r in sin_fichero:
        print("DECLARADO Y NO PLANTADO:", r)
    for r in mal_motivo:
        print("MOTIVO QUE NO CUADRA:", r)

    por_motivo = {}
    for e in declarados.values():
        por_motivo[e["plantado_motivo"]] = por_motivo.get(e["plantado_motivo"], 0) + 1
    print(f"plantados declarados: {len(declarados)} {por_motivo}")
    print("ademas, el par contradictorio REAL: 16 ficheros del DWES antiguo con plantado=true "
          "(ver COBERTURA.md)")
    return 1 if (sin_declarar or sin_fichero or mal_motivo) else 0


def main() -> int:
    p = argparse.ArgumentParser(description="Planta basura controlada (encargo 1.7).")
    p.add_argument("--plantar", action="store_true")
    p.add_argument("--retirar", action="store_true")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.plantar and a.retirar:
        sys.exit("--plantar y --retirar son incompatibles")
    if a.plantar:
        plantar()
    elif a.retirar:
        retirar()
    return comprobar()


if __name__ == "__main__":
    sys.exit(main())
