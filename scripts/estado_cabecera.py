#!/usr/bin/env python3
"""La cabecera de `docs/ESTADO.md`, DERIVADA en vez de escrita a mano.

POR QUÉ EXISTE, con el caso que lo pagó: el fichero cuyo trabajo es no estar desfasado se quedó
diciendo **`rama: prueba-de-jueces`** cuando esa rama ya no existía, y **`¿en main? NO`** cuando el
trabajo llevaba horas fusionado. No fue un descuido: la cabecera se escribía a mano y **dependía de
quién la regenerara**. Es el ADR 0013 otra vez —*lo estático manda revalidar en vez de avisarlo por
escrito*— y el mismo patrón que el hash del manifiesto tras un merge: **lo que pasa el 100 % de las
veces deja de ser una nota que alguien tiene que acordarse de leer y pasa a ser un paso del
procedimiento.**

Y LAS PUERTAS SE CORREN, NO SE TRANSCRIBEN. La línea *"la última vez que se corrieron enteras:
`ruff` 0 · `pytest` 0…"* es una afirmación sobre algo que ocurrió, así que este script **las
ejecuta** y escribe lo que vio, incluido un rojo. No hay bandera para saltarse `pytest`: una cabecera
que puede decir "pytest 0" sin haber corrido pytest es exactamente la clase de verde que este repo
persigue.

LO QUE ESTE SCRIPT NO DECIDE: el resto de `ESTADO.md`. Solo reescribe el bloque entre las dos marcas,
y la prosa que va debajo —lo que sirve el lunes, y lo que no se deriva de nada— se queda donde está.

    python scripts/estado_cabecera.py            # corre las cuatro puertas y reescribe el bloque
    python scripts/estado_cabecera.py --ver      # lo enseña sin tocar el fichero

Códigos de salida: `0` escrito (aunque alguna puerta saliera roja: lo rojo se escribe, no se
esconde), `2` si no se puede leer git o el fichero no trae las dos marcas — que no es lo mismo, y por
eso no comparte código con lo anterior.
"""
import argparse
import pathlib
import re
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ESTADO = RAIZ / "docs" / "ESTADO.md"

ABRE = "<!-- cabecera-derivada: la escribe scripts/estado_cabecera.py, NO se teclea -->"
CIERRA = "<!-- /cabecera-derivada -->"


def git(*args: str) -> str:
    """`git` con la salida limpia. Devuelve "" si el comando falla, para que quien llama decida."""
    try:
        hecho = subprocess.run(("git", *args), cwd=RAIZ, capture_output=True, text=True)
    except OSError:
        return ""
    return hecho.stdout.strip() if hecho.returncode == 0 else ""


def esta_en_main(sha: str) -> bool | None:
    """¿Está ese commit dentro de `main`? `None` si no hay con qué contestar.

    Se prueban las dos formas de nombrar main —la local y la del remoto— porque en un CI con
    `HEAD` desprendido la rama local no existe, y contestar "no está en main" cuando lo que pasa es
    que no hay ninguna referencia con la que mirar sería inventarse el dato.
    """
    for nombre in ("main", "origin/main", "refs/remotes/origin/main"):
        if not git("rev-parse", "--verify", "--quiet", nombre):
            continue
        hecho = subprocess.run(("git", "merge-base", "--is-ancestor", sha, nombre),
                               cwd=RAIZ, capture_output=True, text=True)
        if hecho.returncode == 0:
            return True
        if hecho.returncode == 1:
            return False
    return None


def puerta(nombre: str, orden: list[str]) -> tuple[str, int]:
    """Corre una puerta y devuelve su nombre con el código que DIO, no con el que debería dar."""
    try:
        hecho = subprocess.run(orden, cwd=RAIZ, capture_output=True, text=True)
        return nombre, hecho.returncode
    except OSError as e:
        print(f"  ! {nombre} no se ha podido correr: {e}", file=sys.stderr)
        return nombre, -1


def cuenta_de_tests() -> tuple[int, int]:
    """Tests y ficheros, contados con `pytest --collect-only`, que es quien sabe cuántos hay.

    `pytest` y no `python -m pytest`: el segundo mete el directorio actual en `sys.path` y el CI no
    lo hace, así que contaríamos sobre un árbol de importación distinto del que corre la puerta.
    """
    hecho = subprocess.run(("pytest", "--collect-only", "-q"),
                           cwd=RAIZ, capture_output=True, text=True)
    filas = re.findall(r"^tests/\S+: (\d+)$", hecho.stdout, re.M)
    return sum(int(n) for n in filas), len(filas)


def lineas(f: pathlib.Path) -> int:
    with f.open(encoding="utf-8") as fh:
        return sum(1 for _ in fh)


def bloque() -> str:
    sha = git("rev-parse", "--short", "HEAD")
    if not sha:
        print("no se puede leer git: la cabecera no se toca", file=sys.stderr)
        raise SystemExit(2)
    rama = git("rev-parse", "--abbrev-ref", "HEAD") or "(HEAD desprendido)"
    dentro = esta_en_main(sha)

    print("corriendo las cuatro puertas (pytest tarda; es el precio de no transcribirlo)…")
    resultados = [
        puerta("ruff", ["ruff", "check", "."]),
        puerta("pytest", ["pytest", "-q"]),
        puerta("verificar_manifiesto", [sys.executable, "scripts/verificar_manifiesto.py"]),
        puerta("verificar_oro", [sys.executable, "scripts/verificar_oro.py"]),
    ]
    codigos = dict(resultados)
    tests, ficheros = cuenta_de_tests()
    manifiesto = lineas(RAIZ / "corpus" / "manifiesto.jsonl")
    oro = lineas(RAIZ / "evals" / "casos" / "oro_recuperacion.jsonl")

    if dentro is True:
        en_main = "**SÍ** — quien clone el repo hoy lo ve"
    elif dentro is False:
        pendientes = git("rev-list", "--count", "main..HEAD") or "?"
        en_main = f"**NO** — {pendientes} commits por delante; quien clone el repo hoy NO ve esto"
    else:
        en_main = "**no se ha podido comprobar**: no hay ninguna referencia `main` con la que mirar"

    return "\n".join([
        ABRE,
        f"- **HEAD:** `{sha}` · **rama:** `{rama}` · **¿en `main`?** {en_main}.",
        "  *(Esta línea nombra el commit ANTERIOR al que la trae: una cabecera no puede contener su",
        "  propio hash, porque escribirlo lo cambia. La puerta lo sabe y exige ascendencia, no",
        "  igualdad.)*",
        # EL `.replace(",", ".")` ESTABA PUESTO PARA EL SEPARADOR DE MILLARES Y SE COMIA LA PROSA.
        # Se aplicaba a la cadena ENTERA, asi que la cabecera publicada decia "**Puertas. corridas
        # por este script**" -- un reemplazo cuyo ALCANCE es mayor que su intencion, que es la
        # familia del patron que casa donde no se le llamaba. Ahora el formato va donde va el
        # numero: `f"{n:,}".replace(...)` sobre el numero SOLO, no sobre la frase que lo rodea.
        f"- **Puertas, corridas por este script y no transcritas:** "
        f"`ruff` {codigos['ruff']} · `pytest` {codigos['pytest']} "
        f"(**{tests}** tests en {ficheros} ficheros) · "
        f"`verificar_manifiesto` {codigos['verificar_manifiesto']} "
        f"({f'{manifiesto:,}'.replace(',', '.')} entradas) · "
        f"`verificar_oro` {codigos['verificar_oro']} ({oro} pares).",
        CIERRA,
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ver", action="store_true", help="enseñarlo sin escribir")
    args = ap.parse_args()

    nuevo = bloque()
    if args.ver:
        print(nuevo)
        return 0

    texto = ESTADO.read_text(encoding="utf-8")
    if texto.count(ABRE) != 1 or texto.count(CIERRA) != 1:
        print(f"{ESTADO} no trae exactamente una pareja de marcas: no se toca nada", file=sys.stderr)
        return 2
    inicio, fin = texto.index(ABRE), texto.index(CIERRA) + len(CIERRA)
    ESTADO.write_text(texto[:inicio] + nuevo + texto[fin:], encoding="utf-8")
    print(nuevo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
