"""Las cifras del índice, cruzadas entre los documentos y los DOS ficheros que escribe la máquina.

**EL FALLO QUE ESTA PUERTA EXISTE PARA CAZAR**, encontrado el 15 de agosto de 2026: `COBERTURA.md`
decía **11.574** fragmentos y vectores en dos cabeceras y **11.483** en otras dos y en el README.
Uno era falso. Y no fue un descuido aislado: el commit `6e70f9c` re-troceó el corpus, regeneró los
dos ficheros que escribe la máquina —`corpus/medidas-ingesta.json` y `docs/descartes-admision.md`—
y **solo actualizó parte de la prosa**. Con la sección de embeddings entera se fueron también el
ritmo (194,9 frag/s), el total (59,4 s) y las seis cifras de la extrapolación a un tera.

**POR QUÉ SE CRUZA CONTRA LOS FICHEROS GENERADOS Y NO CONTRA UNA CONSTANTE DE ESTE TEST.** Una
constante aquí sería una tercera copia del mismo número, o sea el mismo problema con un sitio más
donde desincronizarse. `medidas-ingesta.json` lo escribe `embeber.py` y `descartes-admision.md` lo
escribe `trocear.py`: son la salida de quien hizo el trabajo, y los dos están en git. Cuando la
clase ya existe enumerada en algún sitio, se importa en vez de repetirla.

**Y por eso el test cruza TRES cosas y no dos**: los dos generados entre sí (¿cuenta lo mismo quien
trocea y quien embebe?) y los documentos contra ellos (¿dice la prosa lo que midió la máquina?).
"""
import json
import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
MEDIDAS = RAIZ / "corpus" / "medidas-ingesta.json"
DESCARTES = RAIZ / "docs" / "descartes-admision.md"
DOCUMENTOS = ("README.md", "corpus/COBERTURA.md")

#: Cifras de índice que aparecen en la prosa y **no** son el tamaño actual, cada una con qué es.
#: No es una lista de excepciones cómodas: es la única forma de distinguir "número histórico
#: declarado" de "número que se quedó sin actualizar", y crece solo con un motivo escrito al lado.
#: (a) VIGENTES: cifras a escala de indice que son ciertas HOY y pueden decirse en cualquier sitio.
VIGENTES = {
    12494: "troceados en bruto, antes de la puerta de admision",
    11282: "cargados en base = admitidos - 201 sin asignatura declarada (ADR 0007)",
    13096: "el indice CON la basura plantada del 1.7, que es otro indice a proposito",
}
#: (b) HISTORICAS: cifras que fueron ciertas y ya NO lo son. Se pueden citar, pero **solo donde el
#: propio texto declare que son pasado**, y esa es toda la diferencia.
#:
#: **LA PRIMERA VERSION DE ESTE TEST METIA LAS DOS FAMILIAS EN LA MISMA LISTA, y por eso pasaba la
#: mutacion**: al declarar `11574` para que el aviso de correccion pudiera citarlo, el test dejo de
#: poder distinguir el aviso de una cabecera que vuelve a afirmarlo en presente -- o sea que la
#: excusa escrita para una linea honesta amnistiaba justo el defecto que la puerta persigue. Se vio
#: mutando: devolver "## Troceado: 11.574 fragmentos" dejaba el test EN VERDE.
#:
#: Un permiso por VALOR no sirve cuando lo que separa lo correcto de lo falso es el CONTEXTO.
HISTORICAS = {
    13030: "la version anterior del troceado",
    11574: "el troceado de a0637e2, antes del segundo muestreo a mano",
}
#: Lo que hace historica a una linea, y se comprueba estructuralmente: o es una cita en bloque
#: -donde viven los avisos de correccion de este repo- o dice en palabras que habla del pasado.
RE_ES_PASADO = re.compile(r"^\s*>|\banterior(?:es)?\b|\bantes\b|\bdec[íi]a\b|\bera[n]?\b|"
                          r"\bhasta el\b|\bya no\b|\bhoy\b", re.I)


def medidas() -> dict:
    return json.loads(MEDIDAS.read_text(encoding="utf-8"))


def descartes() -> dict:
    texto = DESCARTES.read_text(encoding="utf-8")

    def numero(patron):
        m = re.search(patron, texto)
        assert m, f"docs/descartes-admision.md ya no trae {patron!r}: lo genera trocear.py"
        return int(m.group(1))

    return {"admitidos": numero(r"Fragmentos admitidos: \*\*(\d+)\*\*"),
            "por_documento": numero(r"documento excluido entero: \*\*(\d+)\*\*"),
            "sueltos": numero(r"Fuera sueltos[^:]*: \*\*(\d+)\*\*"),
            "fuera": numero(r"Total fuera: \*\*(\d+)\*\*"),
            "troceados": numero(r"Total fuera: \*\*\d+\*\* de (\d+)")}


def test_los_dos_ficheros_generados_cuentan_LO_MISMO():
    """Quien trocea y quien embebe tienen que haber visto el mismo corpus. Si no, uno de los dos
    corrió sobre otra cosa y cualquier cifra publicada encima hereda la diferencia sin declararla."""
    m, d = medidas(), descartes()
    assert m["fragmentos"] == d["admitidos"], \
        f"embeber dice {m['fragmentos']} y trocear dice {d['admitidos']}"
    assert m["embebidos_en_esta_tanda"] == m["fragmentos"], \
        "la tanda no cubrio el indice entero: el .npy no corresponde a fragmentos.jsonl"
    assert d["admitidos"] + d["fuera"] == d["troceados"], \
        f"la aritmetica de la puerta no cierra: {d['admitidos']} + {d['fuera']} != {d['troceados']}"
    assert d["por_documento"] + d["sueltos"] == d["fuera"], \
        "los dos niveles de la puerta no suman su total"


@pytest.mark.parametrize("documento", DOCUMENTOS)
def test_ninguna_cifra_de_indice_de_la_prosa_diverge_de_lo_medido(documento):
    """**LA PUERTA QUE FALTABA.** Toda cifra **a escala de índice** escrita delante de "fragmentos"
    o "vectores" en estos dos documentos tiene que ser el tamaño actual, o estar declarada arriba
    con lo que es. Un número nuevo sin declarar pone esto en rojo, que es lo que se quiere: no se
    prohíbe citar un histórico, se prohíbe citarlo **sin decir que lo es**.

    **"A escala de índice" se deriva del dato y no se escribe a mano**: la mitad del índice actual.
    Los documentos están llenos de subconteos legítimos —3.370 fragmentos de una unidad, 2.321 con
    unidad de verdad, 3.892 en una partición— que no afirman nada sobre el tamaño del corpus, y un
    tope fijo los habría metido dentro o habría dejado fuera la mitad de los históricos. La clase es
    *"esta cifra pretende ser el índice"*, y con este corpus eso empieza cerca de 5.700.
    """
    actual = medidas()["fragmentos"]
    d = descartes()
    vigentes = {actual, d["fuera"], d["por_documento"], d["sueltos"]} | set(VIGENTES)
    escala_de_indice = actual // 2
    texto = (RAIZ / documento).read_text(encoding="utf-8")
    malas = []
    for n, linea in enumerate(texto.splitlines(), 1):
        for m in re.finditer(r"(\d{1,3}(?:\.\d{3})+)\s*(?:×\s*1024\s*)?\b(fragmentos|vectores)\b",
                             linea):
            valor = int(m.group(1).replace(".", ""))
            if valor < escala_de_indice or valor in vigentes:
                continue
            donde = f"{documento}:{n}: {m.group(1)} {m.group(2)} -> {linea.strip()[:85]}"
            if valor not in HISTORICAS:
                malas.append(f"{donde}   [cifra de indice DESCONOCIDA]")
            elif not RE_ES_PASADO.search(linea):
                malas.append(f"{donde}   [historica AFIRMADA EN PRESENTE: {HISTORICAS[valor]}]")
    assert malas == [], (
        f"cifras a escala de indice mal puestas (el indice son {actual} fragmentos):\n"
        + "\n".join(malas))


@pytest.mark.parametrize("documento", DOCUMENTOS)
def test_el_tamano_del_indice_SE_AFIRMA_al_menos_una_vez(documento):
    """La otra dirección, sin la cual lo de arriba pasaría con un documento que no dice ninguna
    cifra: un test que solo prohíbe se satisface borrando. Los dos documentos tienen que seguir
    afirmando el tamaño real."""
    actual = f"{medidas()['fragmentos']:,}".replace(",", ".")
    texto = (RAIZ / documento).read_text(encoding="utf-8")
    assert re.search(rf"{re.escape(actual)}\s*(?:×\s*1024\s*)?\b(fragmentos|vectores)\b", texto), \
        f"{documento} ha dejado de decir el tamano del indice ({actual})"


#: LAS SEIS CIFRAS DE LA EXTRAPOLACIÓN, con el patrón que las encuentra en la prosa y la clave del
#: JSON de la que salen. Cada entrada es (clave, patrón, factor). El `factor` lleva la unidad de la
#: prosa a la del fichero: "28,8 millones" son 28,8 × 1e6 fragmentos.
#:
#: **POR QUÉ ESTA LISTA EXISTE, y es el agujero que esta puerta tenía**: el docstring de arriba
#: nombra "las seis cifras de la extrapolación a un tera" entre lo que se quedó atrás en `6e70f9c`,
#: y después esta puerta cubría el ritmo y el total **y no las seis**. Estaban bien hoy porque
#: alguien las arregló a mano, que es exactamente de lo que una puerta existe para no depender.
EXTRAPOLACION = (
    ("ratio_binario_a_texto", r"ratio binario→texto\s*\*\*([\d,]+):1\*\*", 1),
    ("fragmentos_por_mb_de_texto", r"([\d.,]+)\s*fragmentos por MB de texto", 1),
    ("fragmentos_por_tera", r"([\d,]+)\s*millones de fragmentos por TB", 1_000_000),
    ("horas_de_embebido_por_tera", r"\*\*([\d,]+) horas\*\* de embebido", 1),
    ("gb_de_vectores_por_tera_float32",
     r"\*\*([\d,]+) GB\*\* de vectores en float32", 1),
    ("gb_de_vectores_por_tera_float16",
     r"\*\*[\d,]+ GB\*\* de vectores en float32 \(([\d,]+) en float16\)", 1),
)


def _numero(texto: str) -> float:
    """`1.075,7` -> 1075.7. Punto de millar y coma decimal, que es como escribe este repo."""
    return float(texto.replace(".", "").replace(",", "."))


@pytest.mark.parametrize("documento", DOCUMENTOS)
def test_la_extrapolacion_a_un_tera_es_la_MEDIDA(documento):
    """Las seis cifras del «¿y si el corpus fuera mucho mayor?», cruzadas contra el JSON generado.

    **SE COMPRUEBA EL RECUENTO DE LO QUE CASÓ Y NO SOLO LO QUE CASÓ**, que es la mitad que importa:
    un patrón que no encuentra nada devuelve cero coincidencias **sin error**, o sea que un test
    escrito solo con `if m:` se pondría verde sobre un documento que hubiera borrado las seis
    cifras — el mismo verde que sobre uno correcto. Por eso falta y valor son dos fallos distintos
    y los dos son rojos.
    """
    m = medidas()["extrapolacion_a_un_tera"]
    # Los dos documentos van envueltos a 100 columnas, asi que "de embebido" puede llegar partido
    # por un salto de linea. Se normaliza el espacio ANTES de buscar: si no, el patron deja de casar
    # por como quedo el parrafo y el fallo se lee como "la cifra no esta".
    texto = re.sub(r"\s+", " ", (RAIZ / documento).read_text(encoding="utf-8"))
    faltan, malas = [], []
    for clave, patron, factor in EXTRAPOLACION:
        hallado = re.search(patron, texto)
        if not hallado:
            faltan.append(f"{clave}: el patron {patron!r} no casa en {documento}")
            continue
        escrito, medido = _numero(hallado.group(1)) * factor, m[clave]
        # Tolerancia de media unidad del ultimo decimal escrito, porque la prosa redondea.
        if abs(escrito - medido) > (factor / 2 if factor > 1 else 0.05):
            malas.append(f"{clave}: {documento} dice {escrito:g} y la ingesta midio {medido:g}")
    assert not faltan, "cifras de la extrapolacion AUSENTES (un patron que no casa es un verde " \
                       "que no ha comprobado nada):\n" + "\n".join(faltan)
    assert not malas, "cifras de la extrapolacion DIVERGENTES:\n" + "\n".join(malas)


def test_el_ritmo_y_el_total_de_la_ingesta_son_los_MEDIDOS():
    """La fila que se quedó atrás con las cabeceras: 194,9 frag/s y 59,4 s son 11.574/59,4, o sea
    la pasada anterior. Se cruza con una cifra decimal de tolerancia porque COBERTURA redondea."""
    m = medidas()
    texto = (RAIZ / "corpus" / "COBERTURA.md").read_text(encoding="utf-8")
    fila = re.search(r"\|\s*\*\*Ritmo\*\*\s*\|\s*\*\*([\d,]+) fragmentos/s\*\*\s*·\s*([\d,]+) s",
                     texto)
    assert fila, "COBERTURA ya no trae su fila de Ritmo con el formato esperado"
    ritmo, segundos = (float(x.replace(",", ".")) for x in fila.groups())
    assert abs(ritmo - m["fragmentos_por_segundo"]) < 0.1, \
        f"COBERTURA dice {ritmo} frag/s y la ingesta midio {m['fragmentos_por_segundo']}"
    assert abs(segundos - m["segundos_embebido"]) < 0.1, \
        f"COBERTURA dice {segundos} s y la ingesta midio {m['segundos_embebido']}"
    assert abs(m["fragmentos"] / m["segundos_embebido"] - m["fragmentos_por_segundo"]) < 1.0, \
        "el propio fichero de medidas no es coherente consigo mismo"
