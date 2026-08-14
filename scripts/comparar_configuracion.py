#!/usr/bin/env python3
"""Lo que el CÓDIGO cree que vale cada variable contra lo que vale DE VERDAD (encargo 4.4).

    python scripts/comparar_configuracion.py            # compose.yml contra los valores del código
    python scripts/comparar_configuracion.py --vivo     # y además lo que corre DENTRO del contenedor

**POR QUÉ EXISTE ESTO, con el caso que lo pagó.** `timeout_lectura` valía `5.0` en su dataclass y el
contenedor corría con **60**: `desde_entorno` leía `TIMEOUT_ETAPA_MS`, que `compose.yml` trae en 60000
desde el encargo 0.3 —cuando no existían ni el plazo ni el vigilante—. El código parecía correcto al
leerlo. Una consulta se quedó **62 segundos** congelada delante de la medida.

La regla que sale de ahí: **un valor por defecto que el entorno puede pisar no es un valor por
defecto, es una sugerencia — y el que corre es el del entorno.** Así que esto compara las tres capas
y marca cada diferencia:

1. el valor por defecto escrito en el **código** (`os.environ.get("X") or <valor>`),
2. el que **compose** fija (`${X:-<valor>}`),
3. y con `--vivo`, el que hay **dentro del contenedor**, que es el único que de verdad corre.

Una diferencia no es un fallo por sí sola —fijar un valor en compose es legítimo—, pero **toda
diferencia tiene que ser una decisión**, y las de este repo se tomaron antes de que existiera casi
todo lo que hoy depende de ellas.

Códigos de salida: `0` sin diferencias, `1` con diferencias, `2` no se pudo leer algo.
"""
import pathlib
import re
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]

#: `os.environ.get("X") or 5000` y `os.environ.get("X", "1")`, que son las dos formas del repo.
RE_POR_DEFECTO = re.compile(
    r'os\.environ\.get\(\s*"(?P<var>[A-Z_0-9]+)"\s*(?:,\s*(?P<dos>[^)]+?))?\s*\)'
    r'(?:\s*or\s*(?P<or>[^\n,)]+))?')
#: `X: ${X:-60000}` de compose.
RE_COMPOSE = re.compile(r'^\s*([A-Z_0-9]+):\s*\$\{[A-Z_0-9]+:-([^}]*)\}', re.M)


#: LO QUE NO SE IMPRIME NUNCA, y esto es un arreglo de la primera version de este script: al correrlo
#: escupio `INFERENCIA_API_KEY` entera por pantalla. La regla del repo dice que la clave jamas sale, y
#: una herramienta de auditoria que la enseña es peor que no tenerla, porque se corre a menudo y su
#: salida se pega en informes. Se compara igual -se dice SI difiere- pero el valor va tapado.
SECRETOS = ("KEY", "PASSWORD", "SECRET", "TOKEN", "CLAVE")


def tapado(var: str, valor: str) -> str:
    """El valor, o `(oculto)` si el nombre huele a secreto. La comparacion se hace con el de verdad;
    lo que se tapa es lo que se imprime."""
    return "(oculto)" if any(s in var.upper() for s in SECRETOS) else valor


def limpio(v) -> str:
    return (v or "").strip().strip('"').strip("'").strip() or "(sin defecto)"


def del_codigo() -> dict:
    valores = {}
    for py in sorted((RAIZ / "app").rglob("*.py")):
        texto = py.read_text(encoding="utf-8")
        for m in RE_POR_DEFECTO.finditer(texto):
            var = m.group("var")
            defecto = m.group("or") or m.group("dos")
            valores.setdefault(var, (limpio(defecto), py.relative_to(RAIZ).as_posix()))
    return valores


def del_compose() -> dict:
    texto = (RAIZ / "compose.yml").read_text(encoding="utf-8")
    return {m.group(1): limpio(m.group(2)) for m in RE_COMPOSE.finditer(texto)}


def del_contenedor() -> dict:
    """Lo que de verdad corre. **Esta es la capa que importa** y la única que no se puede deducir."""
    try:
        salida = subprocess.run(["docker", "compose", "exec", "-T", "api", "env"],
                                cwd=RAIZ, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"no se pudo leer el contenedor: {type(e).__name__}: {e}")
        return {}
    if salida.returncode != 0:
        print(f"no se pudo leer el contenedor (codigo {salida.returncode}); ¿esta levantado?")
        return {}
    vivos = {}
    for linea in salida.stdout.splitlines():
        if "=" in linea:
            k, v = linea.split("=", 1)
            vivos[k.strip()] = v.strip() or "(vacio)"
    return vivos


def main() -> int:
    vivo = "--vivo" in sys.argv
    codigo, compose = del_codigo(), del_compose()
    contenedor = del_contenedor() if vivo else {}
    if vivo and not contenedor:
        return 2

    variables = sorted(set(codigo) | set(compose))
    print(f"{'variable':30} {'codigo':>16}  {'compose':>16}" + ("  {:>16}".format("contenedor") if vivo else ""))
    print("-" * (66 + (18 if vivo else 0)))
    diferencias = 0
    for var in variables:
        c = codigo.get(var, ("(no lo lee)", ""))[0]
        y = compose.get(var, "(no lo fija)")
        fila = f"{var:30} {tapado(var, c):>16}  {tapado(var, y):>16}"
        marca = ""
        if var in codigo and var in compose and c != y and c != "(sin defecto)":
            marca = "  <-- DIFIEREN"
            diferencias += 1
        if vivo:
            v = contenedor.get(var, "(no esta)")
            fila += f"  {tapado(var, v):>16}"
            if var in codigo and v not in ("(no esta)", "(vacio)") and v != c:
                marca = marca or "  <-- el que CORRE no es el del codigo"
                diferencias += 1 if not marca.startswith("  <-- DIFIEREN") else 0
        print(fila + marca)

    print(f"\ndiferencias: {diferencias}")
    print("Una diferencia no es un fallo: es una DECISION que tiene que estar tomada. Lo que no vale\n"
          "es que el codigo diga una cosa, el despliegue haga otra y nadie lo sepa.")
    return 1 if diferencias else 0


if __name__ == "__main__":
    raise SystemExit(main())
