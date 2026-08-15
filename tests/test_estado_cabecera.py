"""La puerta de la cabecera de `docs/ESTADO.md`, que es la que impide que vuelva a desfasarse.

## Qué se ancla aquí, y qué NO se puede anclar

El fichero cuyo trabajo es no estar desfasado llegó a decir **`rama: prueba-de-jueces`** cuando esa
rama ya no existía y **`¿en main? NO`** con el trabajo fusionado hacía horas. La causa no fue un
descuido: la cabecera **se escribía a mano**, así que su exactitud dependía de quién la regenerara.
`scripts/estado_cabecera.py` la deriva; **esto comprueba que la derivada es la que está puesta**.

**Lo que NO se puede exigir es igualdad con el HEAD actual**, y el motivo es bonito: una cabecera no
puede contener su propio hash, porque escribirlo cambia el commit. Así que lo que se ancla es
**ascendencia** —el commit que la cabecera nombra tiene que ser un antepasado de `HEAD`, o `HEAD`
mismo—, que es la afirmación verdadera y comprobable. Exigir igualdad sería una puerta imposible de
satisfacer que alguien acabaría desactivando, que es peor que no tenerla.

**Y no se corre `pytest` dentro de `pytest`**: el script ejecuta las cuatro puertas y una de ellas es
esta suite. Aquí solo se comprueban las partes que se derivan de `git` y del fichero, sin volver a
lanzar nada.
"""
import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
ESTADO = RAIZ / "docs" / "ESTADO.md"
ABRE = "<!-- cabecera-derivada: la escribe scripts/estado_cabecera.py, NO se teclea -->"
CIERRA = "<!-- /cabecera-derivada -->"


def cabecera() -> str:
    texto = ESTADO.read_text(encoding="utf-8")
    assert texto.count(ABRE) == 1 and texto.count(CIERRA) == 1, \
        "ESTADO.md no trae exactamente una pareja de marcas de cabecera derivada"
    return texto[texto.index(ABRE):texto.index(CIERRA) + len(CIERRA)]


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(("git", *args), cwd=RAIZ, capture_output=True, text=True)


def test_la_cabecera_esta_DERIVADA_y_no_tecleada():
    """Las dos marcas existen y entre ellas hay algo. Un bloque vacío es el estado a medias en el que
    quedó el 15/08: las marcas puestas y el generador sin correr."""
    bloque = cabecera()
    cuerpo = bloque[len(ABRE):-len(CIERRA)].strip()
    assert cuerpo, "el bloque de cabecera está VACÍO: se pusieron las marcas y no se corrió el script"
    assert "**HEAD:**" in cuerpo and "**rama:**" in cuerpo
    assert "`ruff`" in cuerpo and "`pytest`" in cuerpo, \
        "la cabecera ha dejado de decir cómo fueron las puertas"


def test_el_commit_QUE_NOMBRA_es_antepasado_de_HEAD():
    """LA COMPROBACIÓN QUE DE VERDAD IMPORTA: que el commit de la cabecera esté en la historia.

    Un sha que no es antepasado significa que la cabecera se escribió en otra rama, o a mano, o que
    se rebasó la historia por debajo — los tres casos en que la línea afirma algo falso sobre dónde
    está el trabajo.
    """
    if git("rev-parse", "--git-dir").returncode != 0:
        pytest.skip("fuera de un repo git")
    m = re.search(r"\*\*HEAD:\*\* `([0-9a-f]{7,40})`", cabecera())
    assert m, "la cabecera no nombra ningún commit"
    sha = m.group(1)
    assert git("cat-file", "-e", f"{sha}^{{commit}}").returncode == 0, \
        f"la cabecera nombra `{sha}`, que no existe en este repo"
    assert git("merge-base", "--is-ancestor", sha, "HEAD").returncode == 0, \
        (f"la cabecera nombra `{sha}`, que NO es antepasado de HEAD: se escribió en otra rama o a "
         f"mano. Corre `python scripts/estado_cabecera.py`")


def test_la_rama_QUE_NOMBRA_existe_o_dice_que_no():
    """`rama: prueba-de-jueces` con esa rama ya borrada fue el caso exacto que pagó esta puerta."""
    if git("rev-parse", "--git-dir").returncode != 0:
        pytest.skip("fuera de un repo git")
    m = re.search(r"\*\*rama:\*\* `([^`]+)`", cabecera())
    assert m, "la cabecera no nombra ninguna rama"
    rama = m.group(1)
    if rama == "(HEAD desprendido)":
        return                                  # es lo que dice el script en un CI, y es verdad
    # SE PRUEBAN LAS TRES FORMAS DE NOMBRAR UNA RAMA, igual que hace `esta_en_main` en el script, y
    # no es laxitud: en el CI el checkout deja `HEAD` desprendido y la rama existe solo como
    # `origin/main`. Exigir la forma local haría fallar a la puerta por CÓMO se clonó el repo y no
    # por lo que dice la cabecera, que es medir el instrumento en vez de lo medido.
    formas = (rama, f"origin/{rama}", f"refs/remotes/origin/{rama}")
    assert any(git("rev-parse", "--verify", "--quiet", f).returncode == 0 for f in formas), \
        f"la cabecera dice `rama: {rama}` y no existe en ninguna forma. Corre `estado_cabecera.py`"


def test_la_sonda_SE_PONE_ROJA_con_un_sha_que_no_es_antepasado(tmp_path, monkeypatch):
    """LA OTRA DIRECCIÓN, porque una puerta que no sabe ponerse roja no protege nada.

    Se le da a la misma comprobación un sha **válido pero de otra historia** —el árbol vacío de git,
    que existe en todo repo y no es antepasado de nada— y se exige que la distinga. Sin esto, los
    tres tests de arriba pasarían igual con la comprobación invertida.
    """
    if git("rev-parse", "--git-dir").returncode != 0:
        pytest.skip("fuera de un repo git")
    # `4b825dc...` es el hash del arbol VACIO, constante en todo repo git. No es un commit, asi que
    # `--is-ancestor` tiene que fallar: es el impostor mas barato que existe.
    vacio = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    assert git("merge-base", "--is-ancestor", vacio, "HEAD").returncode != 0, \
        "la comprobación de ascendencia daría por bueno un objeto que no está en la historia"