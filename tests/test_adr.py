"""La puerta del espacio de nombres de los ADR (añadida tras el duplicado del 12 de agosto de 2026).

Dos sesiones que trabajan en paralelo cogieron cada una "el siguiente número libre" sin verse, y
salieron **dos ADR 0011**: el de la paráfrasis y el del `UNIQUE` del glosario. Cada sesión comprobó
la interacción donde esperaba tenerla —los ficheros de `web/`, los tests— y ninguna miró el sitio
donde el choque era invisible: el nombre del fichero.

Es la familia del "3.6" y del "6.3" que ya mordió antes, ahora en forma de duplicado en vez de
hueco. Un número de ADR se cita desde la guía, desde el código y desde los mensajes de commit, así
que dos ADR con el mismo número convierten cada una de esas citas en una ambigüedad permanente.

Cuatro líneas de puerta cierran la familia entera.
"""
import collections
import re
from pathlib import Path

ADR = Path(__file__).resolve().parents[1] / "docs" / "adr"
RE_PREFIJO = re.compile(r"^(\d{4})-")


def ficheros() -> list:
    return sorted(p for p in ADR.glob("*.md"))


def test_no_hay_dos_adr_con_el_mismo_numero():
    por_numero = collections.defaultdict(list)
    for p in ficheros():
        casa = RE_PREFIJO.match(p.name)
        assert casa, f"{p.name} no empieza por cuatro digitos y un guion"
        por_numero[casa.group(1)].append(p.name)
    repetidos = {n: v for n, v in por_numero.items() if len(v) > 1}
    assert not repetidos, f"numeros de ADR repetidos: {repetidos}"


def test_la_numeracion_no_tiene_huecos():
    """Un hueco no es tan grave como un duplicado, pero ya ha fabricado dos referencias fantasma en
    este proyecto: si falta un número, o se explica o se rellena."""
    numeros = sorted(int(RE_PREFIJO.match(p.name).group(1)) for p in ficheros())
    assert numeros == list(range(1, len(numeros) + 1)), f"la serie tiene huecos: {numeros}"


def test_cada_adr_dice_su_numero_en_el_titulo():
    """El nombre del fichero y el titulo se separan solos en cuanto alguien renumera a mano: es
    exactamente lo que habia que arreglar el dia que se escribio este test."""
    for p in ficheros():
        numero = RE_PREFIJO.match(p.name).group(1)
        primera = p.read_text(encoding="utf-8").splitlines()[0]
        assert primera.startswith(f"# ADR {numero}"), \
            f"{p.name} se titula '{primera[:40]}...' y deberia empezar por '# ADR {numero}'"


def test_todos_traen_su_cabecera_de_fecha_encargo_y_estado():
    for p in ficheros():
        cabeza = p.read_text(encoding="utf-8")[:600]
        for campo in ("**Fecha:**", "**Encargo:**", "**Estado:**"):
            assert campo in cabeza, f"{p.name} no lleva {campo}"
