"""La recuperación léxica del 3.1, probada contra la base cargada.

**Estos tests necesitan Postgres con el corpus dentro, así que no corren en CI**: mismo criterio que
la puerta del manifiesto (ADR 0001). El runner no tiene el corpus y meter aquí una base de juguete
no probaría lo que hay que probar —que el filtro excluye material REAL de otra asignatura—.

LO QUE SE PRUEBA Y POR QUÉ ASÍ. Que el filtro de asignatura esté escrito en la consulta no demuestra
nada: **un filtro que nunca se ha visto excluir algo no es un filtro**. Se le enseña trabajando con
el instrumento que este proyecto ya tiene plantado para esto, el documento COLADO del 1.7: el mismo
contenido vive en Bases de Datos (0484) y en Programación (0485), así que una búsqueda que lo toque
tiene que traer solo el lado que corresponde, y sin filtro tiene que traer los dos.
"""
import os

import psycopg
import pytest

from app.core.recuperacion import buscar_lexico

URL = os.environ.get("DATABASE_URL", "postgresql://veridica:veridica_local@127.0.0.1:5434/veridica")


def hay_base() -> bool:
    try:
        with psycopg.connect(URL, connect_timeout=2) as con, con.cursor() as cur:
            cur.execute("SELECT count(*) FROM fragmentos")
            return cur.fetchone()[0] > 0
    except Exception:
        return False


sin_base = pytest.mark.skipif(not hay_base(),
                              reason="necesita Postgres con el corpus cargado (ADR 0001)")


@pytest.fixture(scope="module")
def asignaturas() -> dict:
    with psycopg.connect(URL) as con, con.cursor() as cur:
        cur.execute("SELECT codigo, id FROM asignaturas WHERE titulacion='daw'")
        return dict(cur.fetchall())


@pytest.fixture(scope="module")
def colado() -> dict:
    """El documento plantado en el 1.7: mismo contenido, dos asignaturas, dos rutas."""
    with psycopg.connect(URL) as con, con.cursor() as cur:
        cur.execute("""
            SELECT a.codigo, d.ruta FROM documentos d JOIN asignaturas a ON a.id = d.asignatura_id
             WHERE d.hash_sha256 IN (SELECT hash_sha256 FROM documentos
                                      GROUP BY hash_sha256 HAVING count(DISTINCT asignatura_id) > 1)
             ORDER BY a.codigo""")
        return dict(cur.fetchall())


# --- el filtro, VISTO excluyendo -----------------------------------------------------------------

@sin_base
def test_el_colado_esta_plantado_en_las_dos_asignaturas(colado):
    """Si esto falla, los dos tests de abajo no prueban nada: estarían buscando un instrumento que
    ya no existe y saldrían en verde por vacío."""
    assert set(colado) == {"0484", "0485"}, colado
    assert "bases-de-datos" in colado["0484"] and "programacion" in colado["0485"]


@sin_base
def test_con_filtro_solo_vuelve_la_asignatura_pedida(asignaturas, colado):
    consulta = "modelo relacional clave ajena integridad referencial tuplas"
    for codigo in ("0484", "0485"):
        candidatos = buscar_lexico(URL, asignaturas[codigo], consulta, k=20)
        assert candidatos, f"la busqueda no trae nada en {codigo}"
        ajenas = {c.asignatura_id for c in candidatos} - {asignaturas[codigo]}
        assert not ajenas, f"filtrando por {codigo} se han colado asignaturas {ajenas}"


@sin_base
def test_SIN_filtro_la_misma_busqueda_trae_material_de_otra_asignatura(asignaturas, colado):
    """LA DIRECCIÓN QUE DEMUESTRA QUE EL FILTRO HACE ALGO. Sin él, la misma consulta cruza la
    frontera: el colado del 1.7 aparece por sus dos caras. Con él, no. Ese contraste es la prueba,
    y es la misma contaminación cruzada que el 3.5 mide."""
    consulta = "modelo relacional clave ajena integridad referencial tuplas"
    con_filtro = buscar_lexico(URL, asignaturas["0485"], consulta, k=20)
    sin_filtro = buscar_lexico(URL, asignaturas["0485"], consulta, k=20, sin_filtro=True)

    assert {c.asignatura_id for c in con_filtro} == {asignaturas["0485"]}
    assert len({c.asignatura_id for c in sin_filtro}) > 1, \
        "sin filtro deberian venir varias asignaturas: si no, este test no prueba nada"

    rutas_sin_filtro = {c.documento for c in sin_filtro}
    assert colado["0484"] in rutas_sin_filtro, "sin filtro tiene que asomar la cara de Bases de Datos"
    assert colado["0484"] not in {c.documento for c in con_filtro}, \
        "el filtro no ha excluido el gemelo de la otra asignatura"


# --- terminologia exacta, que es la verificacion que pide el encargo ------------------------------

@sin_base
@pytest.mark.parametrize("termino,fichero", [
    ("@ModelAttribute", "estado-seguridad"),
    ("PasswordEncoder", "seguridad"),
])
def test_un_identificador_exacto_encuentra_su_material(asignaturas, termino, fichero):
    """La verificación del 3.1 -"terminología exacta en el top 5"- hecha con términos que salen de
    las preguntas de los pares oro, no con ejemplos inventados. Y de paso comprueba lo que se midió
    antes de elegir la configuración: que el lematizador trunque `@ModelAttribute` a `modelattribut`
    da igual, porque trunca lo mismo en el documento y en la consulta."""
    candidatos = buscar_lexico(URL, asignaturas["0613"], termino, k=5)
    assert candidatos, f"'{termino}' no encuentra nada en el 0613"
    assert any(fichero in c.documento.lower() for c in candidatos[:5]), \
        f"'{termino}' no trae su material en el top 5: {[c.documento for c in candidatos[:5]]}"


@sin_base
def test_la_consulta_une_los_terminos_con_o_y_no_con_y(asignaturas):
    """EL HALLAZGO QUE DECIDIÓ EL RECALL. `websearch_to_tsquery` une con AND: una pregunta de
    alumno se convierte en "el fragmento contiene las diez raíces a la vez", y eso casi nunca pasa
    en 512 tokens. Medido sobre los 100 pares oro: 19,0 % de recall@20 con AND, 61,0 % con OR."""
    pregunta = ("¿Dónde se almacenan los datos de la sesión de un usuario en Spring Boot, "
                "y qué es lo único que viaja en la cookie?")
    con_and = buscar_lexico(URL, asignaturas["0613"], pregunta, k=20, conjuncion=True)
    con_or = buscar_lexico(URL, asignaturas["0613"], pregunta, k=20)
    assert len(con_or) > len(con_and), \
        "si el OR no trae mas candidatos que el AND, la consulta no se esta armando como se cree"


# --- la via vectorial del 3.2 --------------------------------------------------------------------
#
# Estos necesitan ademas torch y el modelo en cache, que solo estan en el interprete declarado
# (miniconda). Se saltan solos donde no esten, igual que los de arriba se saltan sin base.

def hay_embebedor() -> bool:
    try:
        import torch  # noqa: F401
        from sentence_transformers import SentenceTransformer  # noqa: F401
        return True
    except Exception:
        return False


sin_embebedor = pytest.mark.skipif(not (hay_base() and hay_embebedor()),
                                   reason="necesita torch y el modelo BGE-M3 en cache")


@pytest.fixture(scope="module")
def embebedor():
    from app.core.embebedor import Embebedor
    return Embebedor()


@sin_embebedor
def test_el_embebedor_usa_la_revision_con_la_que_se_embebio_el_corpus(embebedor):
    """EL PRINCIPIO 8 EN SU FORMA MAS CARA. Un vector calculado con otra revision sigue siendo un
    vector valido de 1024 dimensiones: la base lo acepta, la consulta corre, no falla nada y los
    resultados salen peor sin que nadie sepa por que. Por eso el anclaje se COMPRUEBA."""
    import json
    medidas = json.load(open("corpus/medidas-ingesta.json", encoding="utf-8"))
    assert embebedor.anclaje["revision"] == medidas["revision"]
    assert embebedor.anclaje["modelo"] == medidas["modelo"]


@sin_embebedor
def test_el_anclaje_se_niega_a_arrancar_si_la_dimension_no_cuadra(tmp_path):
    """La otra direccion: la comprobacion tiene que verse decir que NO. Se le da un anclaje mutado
    -mismas medidas, otra dimension- y tiene que negarse en vez de seguir con vectores que la base
    aceptaria igual."""
    import json

    from app.core.embebedor import AnclajeRoto, Embebedor
    medidas = json.load(open("corpus/medidas-ingesta.json", encoding="utf-8"))
    medidas["dimension"] = 768
    falso = tmp_path / "medidas-mutadas.json"
    falso.write_text(json.dumps(medidas), encoding="utf-8")
    with pytest.raises(AnclajeRoto) as e:
        Embebedor(ruta_medidas=str(falso))
    assert "no son comparables" in str(e.value)


@sin_embebedor
@pytest.mark.parametrize("parafrasis,fichero,orden", [
    # oro-009, sin "directiva" ni "plantilla".
    ("¿Que se escribe en Pebble para meter un trozo reutilizable como la barra de navegacion dentro "
     "de otra pagina?", "02-pebble", 13),
])
def test_una_parafrasis_de_pregunta_oro_encuentra_su_fragmento(asignaturas, embebedor, parafrasis,
                                                               fichero, orden):
    """LA VERIFICACION QUE PIDE EL 3.2, y es la que la lexica no puede aprobar: la pregunta se
    reescribe con OTRAS PALABRAS y el fragmento correcto tiene que seguir apareciendo.

    La parafrasis quita a proposito el vocabulario que la busqueda por palabras usaria -`directiva`,
    `plantilla`- y conserva el termino que nombra la tecnologia (`Pebble`).

    **AQUI SOLO HAY UN CASO ANCLADO, Y EL MOTIVO ES UN HALLAZGO, NO UNA ELECCION COMODA.** Se
    probaron dos parafrasis del mismo tipo y **una de las dos falla**: la de oro-005, escrita sin
    `Model` ni `redirigir`, no trae su fragmento. Anclar solo la que pasa y callar la otra seria
    ajustar el test al resultado, asi que la que falla esta escrita en la evidencia con su texto
    exacto. Lo que mide este test es que la via vectorial aguanta ALGUNAS parafrasis, no todas, y
    hasta donde llega esta medido y declarado.
    """
    from app.core.recuperacion import buscar_vectorial
    candidatos = buscar_vectorial(URL, asignaturas["0613"], embebedor.embeber(parafrasis), k=5)
    assert candidatos
    assert any(fichero in c.documento and c.orden == orden for c in candidatos),         f"la parafrasis no trae su fragmento: {[(c.documento[-34:], c.orden) for c in candidatos]}"


@sin_embebedor
def test_el_filtro_tambien_se_ve_excluir_en_la_via_vectorial(asignaturas, colado, embebedor):
    """El mismo contraste que en la lexica, con el mismo instrumento: el colado del 1.7. Que el
    filtro funcione en una via no dice nada de la otra, y son dos consultas SQL distintas."""
    from app.core.recuperacion import buscar_vectorial
    vector = embebedor.embeber("modelo relacional, claves ajenas e integridad referencial")
    con_filtro = buscar_vectorial(URL, asignaturas["0485"], vector, k=20)
    sin_filtro = buscar_vectorial(URL, asignaturas["0485"], vector, k=20, sin_filtro=True)
    assert {c.asignatura_id for c in con_filtro} == {asignaturas["0485"]}
    assert len({c.asignatura_id for c in sin_filtro}) > 1, \
        "sin filtro deberian venir varias asignaturas: si no, este test no prueba nada"
    assert colado["0484"] not in {c.documento for c in con_filtro}


@sin_embebedor
def test_el_recall_es_exacto_porque_gana_el_escaneo(asignaturas, embebedor):
    """La regla de lectura del 3.2, comprobada por el lado que la desactiva: si el planificador
    usara el HNSW, el recall seria aproximado (`ef_search` 40 por defecto) y habria que repetir con
    el escaneo forzado. Aqui los dos caminos dan lo MISMO, que es la prueba de que no hay
    aproximacion de por medio."""
    from app.core.recuperacion import buscar_vectorial
    vector = embebedor.embeber("¿Qué es una clave primaria?")
    con_indice = buscar_vectorial(URL, asignaturas["0484"], vector, k=20)
    forzado = buscar_vectorial(URL, asignaturas["0484"], vector, k=20, forzar_escaneo=True)
    assert [c.fragmento_id for c in con_indice] == [c.fragmento_id for c in forzado]
