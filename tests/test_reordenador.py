"""El reordenador del 3.4, probado en las DOS direcciones: sano y mutado.

QUÉ CORRE EN CI Y QUÉ NO, Y POR QUÉ ESTÁ PARTIDO ASÍ. El cross-encoder son 2,27 GB de pesos y el
runner no los tiene, igual que no tiene el corpus (ADR 0001). Pero **la parte que más importa no
necesita el modelo**: la sonda de anclaje es la que decide si este módulo puede existir, y se prueba
contra un reordenador falso que devuelve números perfectamente válidos y no ordena nada. Esa es
justo la avería que el modelo real no enseñaría —cargar mal un cross-encoder no da error, da
puntuaciones—, así que probarla sin modelo no es una concesión: es el sitio correcto.

Lo que sí necesita el modelo va detrás de un `skipif`, y comprueba lo único que no se puede deducir
leyendo el código: que ante un caso plantado el orden **cambia de verdad**.
"""
import os

import pytest

from app.core.recuperacion import Candidato
from app.core.reordenador import LARGO_MAXIMO, TOP_CONTEXTO, AnclajeRoto, Reordenador

CACHE = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub",
                     "models--BAAI--bge-reranker-v2-m3")
sin_modelo = pytest.mark.skipif(
    not os.path.isdir(CACHE), reason="necesita BAAI/bge-reranker-v2-m3 en cache (2,27 GB)")


def sonda_con(puntuaciones):
    """Un Reordenador SIN modelo, con `puntuar` sustituido. Se construye con `__new__` a propósito:
    `__init__` cargaría 2,27 GB para probar diez líneas que no dependen de ellos."""
    r = object.__new__(Reordenador)
    r.puntuar = lambda consulta, textos: list(puntuaciones)
    return r


# --- la sonda de anclaje, en las dos direcciones -------------------------------------------------

def test_la_sonda_pasa_cuando_el_reordenador_separa():
    """Dirección SANA. Sin esta mitad, la mitad de abajo probaría solo que sabe lanzar excepciones."""
    r = sonda_con([3.0, -2.0])
    r._comprobar()
    assert r.margen_sonda == pytest.approx(5.0)


def test_la_sonda_caza_al_que_no_separa():
    """Dirección MUTADA, y es la avería REAL: un cross-encoder mal cargado no falla, devuelve
    números. Aquí devuelve el mismo para el fragmento que responde y para el que no."""
    with pytest.raises(AnclajeRoto, match="NO separa"):
        sonda_con([0.5, 0.5])._comprobar()


def test_la_sonda_caza_al_que_ordena_al_reves():
    """Peor que no separar: separar hacia el otro lado. Un `num_labels` o un signo cambiados dan
    exactamente esto, y el sistema quedaría poniendo lo peor primero con total aplomo."""
    with pytest.raises(AnclajeRoto, match="NO separa"):
        sonda_con([-2.0, 3.0])._comprobar()


def test_la_sonda_caza_un_numero_de_puntuaciones_distinto():
    with pytest.raises(AnclajeRoto, match="puntuaciones"):
        sonda_con([1.0])._comprobar()


# --- el reordenado en sí -------------------------------------------------------------------------

def candidatos(textos):
    return [Candidato(fragmento_id=i, asignatura_id=1, documento=f"d{i}.md", orden=i,
                      unidad=None, texto=t, puntuacion=1.0 / (i + 1), origen="fusion")
            for i, t in enumerate(textos)]


def test_reordena_de_verdad_con_puntuaciones_plantadas():
    """LA MUTACIÓN SE ENSEÑA ANTES DE LEER EL RESULTADO (regla de CLAUDE.md).

    Se planta un pool donde el bueno va el ÚLTIMO y se comprueba que está el último **antes** de
    reordenar. Si esa comprobación previa no estuviera, este test pasaría igual sobre un reordenador
    que no hiciera nada, siempre que la lista ya viniera ordenada."""
    pool = candidatos(["relleno a", "relleno b", "relleno c", "el bueno"])
    assert pool[-1].texto == "el bueno", "el plantado no se aplicó: no hay nada que probar"
    assert [c.texto for c in pool][:1] != ["el bueno"]

    r = sonda_con([0.1, 0.2, 0.3, 9.0])
    salida = r.reordenar("da igual", pool, top=2)

    assert [c.texto for c in salida] == ["el bueno", "relleno c"]
    assert salida[0].puntuacion == pytest.approx(9.0), "la puntuación tiene que ser la del cross-encoder"


def test_respeta_el_top_y_conserva_el_origen():
    pool = candidatos([f"t{i}" for i in range(30)])
    r = sonda_con(list(range(30)))
    salida = r.reordenar("da igual", pool)
    assert len(salida) == TOP_CONTEXTO
    assert all(c.origen == "fusion" for c in salida), "origen se conserva: es lo que hace legible la fusión"
    assert [c.texto for c in salida] == [f"t{i}" for i in range(29, 23, -1)]


def test_la_puntuacion_se_SUSTITUYE_y_no_se_acumula():
    """Una es un rango RRF sin calibrar y la otra un logit. Sumarlas no significaría nada, y el
    error sería invisible: saldría un número plausible."""
    pool = candidatos(["uno", "dos"])
    previas = [c.puntuacion for c in pool]
    salida = sonda_con([5.0, -5.0]).reordenar("da igual", pool, top=2)
    assert [c.puntuacion for c in salida] == [5.0, -5.0]
    assert previas == [1.0, 0.5], "el pool de entrada no se muta"


def test_pool_vacio_no_revienta():
    assert sonda_con([]).reordenar("da igual", []) == []


# --- la política de servicio: GPU o nada, y el respaldo ANUNCIADO --------------------------------

def test_para_servicio_no_devuelve_NUNCA_uno_de_cpu(monkeypatch):
    """La regla que sostiene el ADR 0015, probada en vez de comentada.

    Sin esta prueba, `para_servicio` sería una frase en un docstring y el día que alguien "arregle"
    la excepción quitándola tendríamos catorce segundos de pantalla muerta en producción sin que
    nada se pusiera rojo. El respaldo correcto es NO reordenar, no reordenar despacio."""
    import torch
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    from app.core.reordenador import SinGPU, para_servicio
    with pytest.raises(SinGPU, match="NO cae a CPU"):
        para_servicio()


class ReordenadorFalso:
    """Ordena al revés de como venga. Basta para ver si `_recuperar` lo usa o lo ignora."""

    def reordenar(self, consulta, candidatos, top):
        return list(reversed(candidatos))[:top]


def _candidatos_falsos(n=30):
    return candidatos([f"fragmento {i}" for i in range(n)])


def _peticion():
    from app.api.consulta import Consulta
    return Consulta(texto="¿qué es una clave primaria?", asignatura_id=25)


def _sin_base(monkeypatch, pool):
    """Aparta Postgres y el embebedor: lo que se prueba aquí es la RAMA, no la recuperación."""
    from app.api import consulta as mod
    monkeypatch.setattr(mod, "recuperar", lambda *a, **k: pool)
    monkeypatch.setattr(mod, "buscar_vectorial", lambda *a, **k: [])
    return type("EmbebedorFalso", (), {"embeber": lambda self, t: [0.0]})()


def test_sin_gpu_no_se_reordena_Y_SE_DICE(monkeypatch):
    """Degradar anunciando, jamás degradar en silencio (patrón del 8.2). Se comprueban las DOS
    mitades: que el orden es el de la fusión **y** que hay una etapa que lo cuenta. Solo la primera
    dejaría pasar una degradación muda, que es la avería que importa."""
    from app.api import consulta as mod
    pool = _candidatos_falsos()
    emb = _sin_base(monkeypatch, pool)

    marcas, _, _, _, elegidos = mod._recuperar(_peticion(), emb, "", 0.0, reordenador=None)

    nombres = [m["nombre"] for m in marcas]
    assert "sin_reordenar" in nombres, "degradó en silencio: no hay etapa que lo diga"
    assert "reordenado" not in nombres
    dicho = next(m["detalle"] for m in marcas if m["nombre"] == "sin_reordenar")
    assert "sin reordenar" in dicho and "GPU" in dicho
    assert [c.texto for c in elegidos] == [f"fragmento {i}" for i in range(6)]


def test_con_reordenador_se_reordena_y_la_etapa_lo_marca(monkeypatch):
    from app.api import consulta as mod
    pool = _candidatos_falsos()
    emb = _sin_base(monkeypatch, pool)

    marcas, _, _, _, elegidos = mod._recuperar(_peticion(), emb, "", 0.0,
                                               reordenador=ReordenadorFalso())

    nombres = [m["nombre"] for m in marcas]
    assert "reordenado" in nombres and "sin_reordenar" not in nombres
    assert [c.texto for c in elegidos] == [f"fragmento {i}" for i in range(29, 23, -1)]
    etapa = next(m for m in marcas if m["nombre"] == "reordenado")
    assert "reordenado_ms" in etapa, "la etapa tiene que llevar SU coste, no solo el acumulado"


# --- lo que sí necesita el modelo ----------------------------------------------------------------

@sin_modelo
def test_el_modelo_real_separa_y_ordena():
    """El caso que no se puede deducir leyendo el código: con el modelo de verdad, un fragmento que
    responde tiene que subir por encima de tres que no, estando plantado el último."""
    r = Reordenador(dispositivo="cpu")
    pregunta = "¿Dónde se almacenan los datos de la sesión en Spring Boot?"
    pool = candidatos([
        "AutoMapper se configura creando un Profile con los mapeos entre entidades y DTOs.",
        "El algoritmo LRU descarta la entrada de caché usada hace más tiempo.",
        "BCrypt es lento a propósito para encarecer los ataques por fuerza bruta.",
        "La sesión se almacena en el servidor; la cookie solo lleva el identificador.",
    ])
    assert "sesión se almacena en el servidor" in pool[-1].texto, "el plantado no se aplicó"

    salida = r.reordenar(pregunta, pool, top=1)
    assert "sesión se almacena en el servidor" in salida[0].texto


@sin_modelo
def test_el_largo_maximo_cubre_el_p99_del_corpus_y_lo_que_no_se_cuenta():
    """El truncado NO es simétrico: recorta el fragmento, no la pregunta. Y `oro-001` se responde
    con la última línea de su fragmento, así que un truncado silencioso es un fallo de fidelidad,
    no de eficiencia. Aquí se comprueba que el contador existe y cuenta."""
    r = Reordenador(dispositivo="cpu")
    assert r.largo_maximo == LARGO_MAXIMO
    corto = "palabra " * 50
    largo = "palabra " * 2000
    assert r.truncados("pregunta", [corto]) == 0
    assert r.truncados("pregunta", [largo]) == 1
