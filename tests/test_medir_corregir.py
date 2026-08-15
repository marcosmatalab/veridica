"""La sonda de `duda` del 5.3, su SUELO declarado, y la corrida que sostiene el número publicado.

**POR QUÉ ESTE FICHERO EXISTE**, y sale de una noche entera: el número publicado del 5.3 —*"de las 6
entregadas con el resultado mal, **5 corrigen**"*— lo puso **un ojo humano**, y el detector
automático que el mismo script imprime con las mismas palabras daba **2**. Las dos cifras son
correctas y miden cosas distintas; lo que faltaba era **decir cuál es cuál**. Un veredicto lleva la
firma de su instrumento, o toda lectura posterior mezcla instrumentos.
"""
import json
import pathlib
import re
import sys

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

from medir_corregir import FRASES_NO, FRASES_SI, RE_DUDA, sonda  # noqa: E402

#: La corrida ANCLADA (inmutable) que sostiene la tabla del §6 de la evidencia del 5.3. No es
#: `ultima_corrida_corregir.json`, que no se versiona porque su nombre caduca solo.
CORRIDA = RAIZ / "evals" / "corridas" / "2026-08-14-corregir-tras-arreglos.json"

#: **LEÍDAS A OJO, UNA A UNA, Y ESTA ES LA LECTURA QUE SE PUBLICA.** Va aquí escrita para que se
#: pueda discutir el juicio en vez de heredarlo: `corr-002` contesta *"El PVP del pijama es
#: 12,1 €."* a quien traía 12,4 — dice el valor bueno sin contrastar nada, y se cuenta como
#: corrección porque el alumno lee el número correcto. Es la más floja de las cinco.
A_OJO = {"corr-002": True, "corr-008": False, "corr-010": True,
         "corr-014": True, "corr-018": True, "corr-020": True}


def _corrida():
    return json.loads(CORRIDA.read_text(encoding="utf-8"))


def _entregadas():
    return [r for r in _corrida() if r["prosa"].strip()]


def test_la_sonda_pasa_en_las_DOS_direcciones():
    """Sin las dos, el verde de un detector no significa nada. Y las frases de las dos listas
    incluyen **salida real** además de las mías: la primera versión daba 6/6 sobre frases que
    escribí yo y fallaba 3 de 6 sobre lo que el sistema escribe de verdad."""
    assert sonda() == 0


def test_las_dos_listas_llevan_SALIDA_REAL_y_no_solo_frases_mias():
    """Ancla la corrección, no el resultado: si alguien recorta las listas a lo que escribió a
    mano, la sonda vuelve a medir su propia idea de cómo se expresa una duda (principio 11 dentro
    del instrumento)."""
    prosas = {r["prosa"].strip() for r in _entregadas()}

    def sale_de_corrida(frase):
        return any(frase.rstrip(".") in p for p in prosas)

    assert sum(sale_de_corrida(f) for f in FRASES_SI) >= 2, \
        "FRASES_SI ya no lleva salida real: la sonda ha vuelto a validarse contra sí misma"
    assert sum(sale_de_corrida(f) for f in FRASES_NO) >= 3, \
        "FRASES_NO ya no lleva salida real"


@pytest.mark.parametrize("caso,texto", [
    # LOS DOS QUE EL DETECTOR VIEJO PERDIA, y el motivo de cada uno.
    ("corr-020", "es de 300 MB/s, no de 150 MB/s."),      # "no DE 150": preposicion en medio
    ("corr-010", "es de 30 minutos, por lo que 15 minutos no es suficiente."),   # sin contraste
])
def test_las_dos_formas_que_el_patron_viejo_perdia_ahora_se_cazan(caso, texto):
    """**Un filtro escrito sobre el ejemplo que miraste caza el ejemplo, no la clase.** El patrón
    viejo se escribió sobre *"es 12,1 €, no 12,4 €"* y por eso exigía que el `no` fuera pegado a
    una cifra; la clase es *"contrasta el valor bueno con el del alumno"*, y ese contraste admite
    preposición y artículo."""
    assert RE_DUDA.search(texto), f"{caso}: el detector vuelve a perder su propia clase"


def test_el_SUELO_del_detector_esta_declarado_y_anclado():
    """**Una medida cuyo resultado no puede moverse no informa, pero un límite sin ancla se olvida.**
    `corr-002` NO lo caza ningún detector de frases: dice el valor correcto y no contrasta. Si
    alguien lo hiciera pasar, habría cambiado el mecanismo (extracción, ADR 0016) y tiene que
    re-derivar los números publicados — este rojo es el aviso, no una regresión."""
    dos = next(r for r in _entregadas() if r["id"] == "corr-002")
    assert not RE_DUDA.search(dos["prosa"]), \
        ("corr-002 ahora se caza: el detector ha dejado de ser de frases. Re-deriva el 4/5 y el "
         "5/6 publicados antes de poner esto en verde.")


def test_los_dos_numeros_del_5_3_y_su_FIRMA_de_instrumento():
    """EL TEST QUE IMPIDE VOLVER A PUBLICAR UNO SOLO. El ojo ve 5 de 6; el detector automático ve
    4 de 6 y su suelo declarado explica el hueco entero (`corr-002`). Los dos son ciertos, miden
    cosas distintas, y lo que no vale es enseñar uno con el nombre del otro."""
    mal = [r for r in _entregadas() if not r["resultado_es_correcto"]]
    assert len(mal) == 6, "la corrida anclada ha cambiado de forma"
    a_ojo = sum(A_OJO[r["id"]] for r in mal)
    detector = sum(bool(RE_DUDA.search(r["prosa"])) for r in mal)
    assert a_ojo == 5, "la lectura a ojo publicada era 5 de 6"
    assert detector == 4, "el detector automatico daba 4 de 6 sobre esta misma prosa"
    assert a_ojo - detector == 1, "el hueco entre los dos instrumentos es exactamente corr-002"


def test_la_otra_direccion_sobre_SALIDA_REAL_cero_falsos_positivos():
    """Un detector más ancho es peor si se come los aciertos. Las 8 respuestas a casos con el
    resultado BIEN son negativos reales, e incluyen la trampa buena: `corr-005` dice *"no cumple
    con el máximo semanal de 40 horas"* — un `no` con una cifra al lado que **no** es dudar del
    resultado."""
    bien = [r for r in _entregadas() if r["resultado_es_correcto"]]
    assert len(bien) == 8
    falsos = [r["id"] for r in bien if RE_DUDA.search(r["prosa"])]
    assert falsos == [], f"el detector se ha vuelto tan ancho que se come los aciertos: {falsos}"


def test_el_EMBUDO_publicado_se_reproduce_desde_la_corrida_anclada():
    """La tabla del §6 —14/20 entregadas, 3 en blanco por cobertura, 0 sin declarar— sale de este
    fichero y de ningún otro. Si el fichero no la reproduce, el número no tiene evidencia."""
    d = _corrida()
    vacias = [r for r in d if not r["prosa"].strip()]
    por_cobertura = [r for r in vacias if (r.get("abstencion") or {}).get("por_cobertura")]
    por_plazo = [r for r in vacias if (r.get("abstencion") or {}).get("por_plazo")]
    assert len(d) == 20 and len(d) - len(vacias) == 14
    assert len(por_cobertura) == 3 and len(por_plazo) == 3
    assert len(vacias) - len(por_cobertura) - len(por_plazo) == 0, \
        "reaparecen vacias SIN declarar como abstencion: era el arreglo 1 del 5.3"


def test_ningun_fuente_python_lleva_caracteres_de_control_invisibles():
    """**EL CANAL QUE TRANSPORTA EL PARCHE TAMBIÉN ES UN PATRÓN QUE PUEDE NO CASAR**, y esta es su
    puerta. `RE_DUDA` llevaba un **retroceso de verdad** (`0x08`) donde se quiso escribir `\\b`:
    dentro de una cadena cruda eso exige un carácter de retroceso literal antes del `no`, o sea que
    esa alternativa **no podía casar nunca**. Código muerto que ningún editor enseña, que ningún
    test veía —porque la alternativa de al lado tapaba el hueco en los dos casos que sí salían— y
    que se coló porque el canal se comió el escape, la misma avería que los acentos por *heredoc*.

    Se generaliza a propósito en vez de anclar el caso: la clase es *"byte de control C0 en un
    fuente"*, y nombrarla cuesta lo mismo que nombrar el ejemplo.
    """
    control = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
    sucios = []
    for ruta in sorted(RAIZ.glob("**/*.py")):
        if any(p in ruta.parts for p in ("__pycache__", ".venv", "venv")):
            continue
        texto = ruta.read_text(encoding="utf-8")
        for n, linea in enumerate(texto.splitlines(), 1):
            if control.search(linea):
                sucios.append(f"{ruta.relative_to(RAIZ)}:{n}")
    assert sucios == [], f"caracteres de control invisibles en: {sucios}"
