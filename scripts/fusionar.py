#!/usr/bin/env python3
"""Fusionar es un COMANDO, y el comando recalcula el manifiesto (14 de agosto de 2026).

    python scripts/fusionar.py <rama> --mensaje <fichero> [--destino main]

VAN DOS DE DOS: en los dos merges hechos hasta hoy (fase 2 y fase 3) las dos ramas habían editado
`corpus/COBERTURA.md`, así que el contenido fusionado era un TERCERO que no había hasheado ninguna
y `verificar_manifiesto` salía en rojo DESPUÉS del merge. **Si algo pasa el 100 % de las veces que
se hace una operación, no es una nota que recordar: es un paso del procedimiento** (ADR 0013
aplicado a nosotros: los avisos son prosa que alguien tiene que acordarse de leer; un paso es una
vez y para siempre). Y como la puerta es local por diseño (ADR 0001: el runner no tiene corpus), el
paso no puede vivir en el CI, ni en un gancho —que no se versiona—: vive aquí, versionado, y
fusionar ES correr esto.

Cierra además dos trampas ya pagadas el mismo día en que se escribió:

- **`git merge -F -` NO lee de stdin**: falla con "could not read file '-'", el merge no ocurre, y
  el que fusiona se queda corriendo las puertas en verde sobre la rama SIN fusionar (séptima de la
  familia "el instrumento miente"). Aquí el mensaje es un fichero de verdad, comprobado antes de
  tocar git.
- **El código de salida se lee SIN tubería**, paso a paso, y el final recuerda el push: el valor de
  una puerta es función de su frecuencia, y un CI que no ve los commits no protege nada.

Qué hace, en orden y parándose en el primer rojo: (1) exige árbol limpio y se pone en la rama de
destino; (2) `git merge --no-ff` con el mensaje del fichero; (3) `verificar_manifiesto`, y si sale
1 con SOLO hallazgos `HASH DISTINTO` recalcula esas entradas, re-verifica y commitea el ajuste —un
`SIN FICHERO` o un 2 NO se autorreparan: eso no es un hash desactualizado, es otra avería—;
(4) ruff, pytest y `verificar_oro`; (5) imprime el recordatorio de empujar y mirar el CI.

Qué NO hace: empujar (es una decisión), resolver conflictos (es trabajo de persona), ni tocar nada
si el merge no se completa.
"""
import argparse
import pathlib
import re
import subprocess
import sys

RE_HASH_DISTINTO = re.compile(r"^HASH DISTINTO: (.+)$", re.MULTILINE)
RE_HALLAZGO = re.compile(r"^(SIN MANIFIESTO|SIN FICHERO|RUTA DUPLICADA):", re.MULTILINE)


def ficheros_con_hash_distinto(salida: str) -> list:
    """Las rutas recalculables de la salida de `verificar_manifiesto`, y SOLO esas.

    Un `HASH DISTINTO` tras un merge limpio es el contenido fusionado que nadie hasheó: se
    recalcula. Cualquier otra clase de hallazgo NO se autorrepara —un fichero que falta no es un
    hash viejo—, y por eso `hay_hallazgos_no_reparables` existe aparte: un reparador que repara de
    más es la puerta poniéndose verde sola.
    """
    return RE_HASH_DISTINTO.findall(salida)


def hay_hallazgos_no_reparables(salida: str) -> bool:
    return bool(RE_HALLAZGO.search(salida))


def _correr(descripcion: str, orden: list) -> subprocess.CompletedProcess:
    print(f"--- {descripcion}: {' '.join(orden)}")
    r = subprocess.run(orden, capture_output=True, text=True)
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.stderr.strip():
        print(r.stderr.strip(), file=sys.stderr)
    return r


def _herramienta(nombre: str) -> str:
    """ruff/pytest del MISMO entorno que este intérprete, que es la regla del repo: la puerta y la
    máquina de quien la corre tienen que ejecutar lo mismo (nada de coger el primero del PATH)."""
    carpeta = pathlib.Path(sys.executable).parent
    for candidata in (carpeta / "Scripts" / f"{nombre}.exe", carpeta / f"{nombre}.exe",
                      carpeta / "Scripts" / nombre, carpeta / nombre):
        if candidata.exists():
            return str(candidata)
    return nombre    # último recurso: el PATH, y que el error sea visible si tampoco está


def main() -> int:
    p = argparse.ArgumentParser(description="Fusiona una rama con el procedimiento entero.")
    p.add_argument("rama")
    p.add_argument("--mensaje", required=True,
                   help="fichero con el mensaje del merge (un FICHERO: -F - no lee stdin)")
    p.add_argument("--destino", default="main")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    mensaje = pathlib.Path(a.mensaje)
    if not mensaje.is_file() or not mensaje.read_text(encoding="utf-8").strip():
        print(f"el mensaje del merge tiene que ser un fichero no vacío: {a.mensaje}",
              file=sys.stderr)
        return 2

    if subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                      capture_output=True, text=True).stdout.strip():
        print("árbol sucio: se fusiona desde un árbol limpio, siempre", file=sys.stderr)
        return 2
    if _correr("rama de destino", ["git", "checkout", a.destino]).returncode != 0:
        return 2
    if _correr("merge --no-ff", ["git", "merge", "--no-ff", a.rama, "-F", str(mensaje)]
               ).returncode != 0:
        print("EL MERGE NO SE HA COMPLETADO: nada de lo de abajo se ha corrido. Resuélvelo y "
              "vuelve a lanzar este comando.", file=sys.stderr)
        return 1

    # El paso que motivó el script: la puerta local, DESPUÉS del merge, con recálculo.
    interprete = sys.executable
    r = _correr("verificar_manifiesto (post-merge)", [interprete, "scripts/verificar_manifiesto.py"])
    if r.returncode == 2:
        print("manifiesto ilegible: eso no se autorrepara", file=sys.stderr)
        return 1
    if r.returncode == 1:
        if hay_hallazgos_no_reparables(r.stdout):
            print("hay hallazgos que NO son un hash desactualizado: se miran a mano", file=sys.stderr)
            return 1
        rutas = ficheros_con_hash_distinto(r.stdout)
        for ruta in rutas:
            if _correr("recalcular hash", [interprete, "scripts/actualizar_hash_manifiesto.py",
                                           ruta]).returncode != 0:
                return 1
        if _correr("re-verificar", [interprete, "scripts/verificar_manifiesto.py"]).returncode != 0:
            return 1
        cuerpo = ("El hash del manifiesto tras el merge: paso del procedimiento, ya no nota\n\n"
                  "Las dos ramas editaron " + ", ".join(rutas) + " y el contenido fusionado es un\n"
                  "tercero que no hasheo ninguna. Recalculado por scripts/fusionar.py, que existe\n"
                  "porque esto paso en el 100 % de los merges (fase 2 y fase 3).\n")
        if _correr("commit del ajuste", ["git", "add", "--"] + ["corpus/manifiesto.jsonl"]
                   ).returncode != 0:
            return 1
        if subprocess.run(["git", "commit", "-m", cuerpo]).returncode != 0:
            return 1

    for nombre, orden in (("ruff", [_herramienta("ruff"), "check", "."]),
                          ("pytest", [_herramienta("pytest"), "-p", "no:warnings", "-q"]),
                          ("verificar_oro", [interprete, "scripts/verificar_oro.py"])):
        if _correr(nombre, orden).returncode != 0:
            print(f"ROJO en {nombre}: el merge está hecho pero NO está en condiciones de "
                  f"empujarse. Se arregla aquí, no se empuja el rojo.", file=sys.stderr)
            return 1

    print("\nTODO EN VERDE. Falta lo que este script no decide por ti:")
    print(f"  git push origin {a.destino}   # y mirar el CI: una puerta que no ve los commits no protege")
    return 0


if __name__ == "__main__":
    sys.exit(main())
