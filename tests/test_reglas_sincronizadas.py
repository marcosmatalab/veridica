"""CLAUDE.md y el Apendice A de la guia tienen que decir LO MISMO (encargo 1.1, puerta anadida).

Las reglas de trabajo viven en dos sitios a proposito: la guia es la fuente de verdad y CLAUDE.md
es lo que Claude Code lee al arrancar. Pero dos documentos que dicen lo mismo se separan solos: ya
paso con LEEME.md, que acabo describiendo un corpus que no existia. Hasta ahora esto se comprobaba
a mano, o sea que no se comprobaba: comprobacion manual que puede hacerse automatica, se hace
automatica.

El bloque del Apendice A debe ser PREFIJO EXACTO de CLAUDE.md. CLAUDE.md puede anadir secciones
propias despues (las puertas, el entorno local), pero no puede tocar ni una coma de las reglas.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CLAUDE = RAIZ / "CLAUDE.md"
GUIA = RAIZ / "guia-definitiva.md"


def bloque_del_apendice() -> str:
    texto = GUIA.read_text(encoding="utf-8")
    assert "# APÉNDICE A" in texto, "la guia ya no tiene Apendice A: alguien lo movio o lo borro"
    tras_apendice = texto.split("# APÉNDICE A", 1)[1]
    assert "```markdown" in tras_apendice, "el Apendice A ya no trae su bloque markdown"
    return tras_apendice.split("```markdown", 1)[1].split("```", 1)[0].strip()


def test_el_apendice_a_de_la_guia_y_claude_md_no_han_divergido():
    apendice = bloque_del_apendice()
    claude = CLAUDE.read_text(encoding="utf-8").strip()
    assert claude.startswith(apendice), (
        "CLAUDE.md y el Apendice A de la guia dicen cosas distintas. Se editan LOS DOS o ninguno:\n"
        + primera_diferencia(apendice, claude)
    )


def test_las_reglas_no_se_han_quedado_en_nada():
    """Un bloque vacio haria pasar el test de arriba sin comprobar nada: eso tambien es un verde
    mentiroso. Si las reglas bajan de diez, es que alguien se ha llevado media lista por delante."""
    reglas = [x for x in bloque_del_apendice().split("\n") if x.startswith("- ")]
    assert len(reglas) >= 10, f"solo quedan {len(reglas)} reglas en el Apendice A"


def primera_diferencia(esperado: str, obtenido: str) -> str:
    a, b = esperado.split("\n"), obtenido.split("\n")
    for i, (x, y) in enumerate(zip(a, b), 1):
        if x != y:
            return f"  primera linea distinta ({i}):\n    guia   : {x}\n    CLAUDE : {y}"
    return f"  CLAUDE.md se queda corto: la guia tiene {len(a)} lineas y alli hay {len(b)}"
