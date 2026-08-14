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
    nada se pusiera rojo. El respaldo correcto es NO reordenar, no reordenar despacio.

    CORREGIDO EL 14/08/2026: la versión anterior hacía `import torch` en el propio test, así que en
    el runner de CI —que no lleva torch a propósito— moría por `ModuleNotFoundError` en vez de
    probar nada. Se descubrió al EMPUJAR la rama tras día y medio sin push: el CI no había visto
    ninguno de los commits desde el 3.4, y su verde local convivía con un rojo remoto que nadie
    miró. Ahora el torch del test es un doble sin GPU inyectado en `sys.modules`: la regla se
    prueba igual aquí y en el CI, sin depender de que torch exista."""
    import sys
    import types
    falso_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
    monkeypatch.setitem(sys.modules, "torch", falso_torch)
    from app.core.reordenador import SinGPU, para_servicio
    with pytest.raises(SinGPU, match="NO cae a CPU"):
        para_servicio()


class ReordenadorFalso:
    """Ordena al revés de como venga. Basta para ver si `_recuperar` lo usa o lo ignora."""

    def reordenar(self, consulta, candidatos, top):
        return list(reversed(candidatos))[:top]

    def reordenar_o_rendirse(self, consulta, candidatos, top):
        return self.reordenar(consulta, candidatos, top), None


class ReordenadorColgado:
    """Nunca contesta a tiempo. `motivo` distingue las dos averias que producen lo mismo."""

    def __init__(self, motivo="gpu_no_contesta"):
        self.motivo = motivo

    def reordenar_o_rendirse(self, consulta, candidatos, top):
        return None, self.motivo


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


def test_sin_reordenador_CONFIGURADO_no_se_anuncia_degradacion_porque_no_la_hay(monkeypatch):
    """CORREGIDO EL 14/08/2026 tras la pasada adversarial del cierre. La versión anterior de este
    test exigía una etapa `sin_reordenar` con "sin GPU" en el detalle para `reordenador=None` — y
    desde el descarte del ADR 0019 eso obligaba al sistema a MENTIR dos veces en cada consulta de
    producción: hay GPU (el descarte es una decisión, no una avería) y no hay degradación (la
    fusión sin reordenar mide MEJOR: 58,7 % contra 56,0 % en `lectura`). `reordenador=None` es la
    configuración por defecto, y una configuración no se anuncia como avería.

    Degradar anunciando (8.2) sigue vigente donde hay degradación de verdad: los tests de abajo
    —reordenador ENCENDIDO que no contesta o está saturado— siguen exigiendo la etapa."""
    from app.api import consulta as mod
    pool = _candidatos_falsos()
    emb = _sin_base(monkeypatch, pool)

    marcas, _, _, _, elegidos = mod._recuperar(_peticion(), emb, "", 0.0, reordenador=None)

    nombres = [m["nombre"] for m in marcas]
    assert "sin_reordenar" not in nombres, "la configuracion por defecto se anuncia como averia"
    assert "reordenado" not in nombres
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


def test_si_la_GPU_no_contesta_a_tiempo_se_degrada_igual_que_si_no_hubiera(monkeypatch):
    """"NO CANCELABLE" NO ES "NO ACOTABLE". Una operación de GPU no se puede matar, pero sí se puede
    dejar de esperar: la petición no tiene por qué depender de un kernel colgado.

    Se comprueban las dos mitades, igual que en el caso sin GPU: que el orden es el de la fusión
    **y** que hay una etapa que lo cuenta, con su motivo distinto —no es lo mismo "no hay GPU" que
    "la GPU no contesta", y en pantalla el alumno ve lo mismo pero en la traza no."""
    from app.api import consulta as mod
    pool = _candidatos_falsos()
    emb = _sin_base(monkeypatch, pool)

    marcas, _, _, _, elegidos = mod._recuperar(_peticion(), emb, "", 0.0,
                                               reordenador=ReordenadorColgado())

    nombres = [m["nombre"] for m in marcas]
    assert "sin_reordenar" in nombres and "reordenado" not in nombres
    etapa = next(m for m in marcas if m["nombre"] == "sin_reordenar")
    assert etapa["motivo"] == "gpu_no_contesta"
    assert "no contesto a tiempo" in etapa["detalle"]
    assert [c.texto for c in elegidos] == [f"fragmento {i}" for i in range(6)]


def test_la_saturacion_llega_a_la_traza_con_SU_motivo_y_su_texto(monkeypatch):
    """Tres averias, tres motivos. En pantalla el alumno puede leer algo parecido; en la traza no
    pueden ser lo mismo, porque de ahi sale el diagnostico."""
    from app.api import consulta as mod
    pool = _candidatos_falsos()
    emb = _sin_base(monkeypatch, pool)

    marcas, _, _, _, elegidos = mod._recuperar(
        _peticion(), emb, "", 0.0, reordenador=ReordenadorColgado("reordenador_saturado"))

    etapa = next(m for m in marcas if m["nombre"] == "sin_reordenar")
    assert etapa["motivo"] == "reordenador_saturado"
    assert "varias consultas por delante" in etapa["detalle"], \
        "el texto de saturacion es el de averia: al alumno se le dice que algo fallo cuando hay cola"
    assert [c.texto for c in elegidos] == [f"fragmento {i}" for i in range(6)]


def _reordenador_lento(segundos=5.0):
    import time as _t
    from concurrent.futures import ThreadPoolExecutor

    r = object.__new__(Reordenador)
    r.rendiciones = r.rendiciones_por_gpu = r.rendiciones_por_cola = 0
    r.reordenar = lambda *a, **k: _t.sleep(segundos)
    r._ejecutor = ThreadPoolExecutor(max_workers=1)
    r._reloj_gpu = _t.perf_counter
    return r


def test_rendirse_no_LANZA_y_devuelve_None(monkeypatch):
    """La rendición no puede ser una excepción: si lo fuera, cualquier `except` mal puesto en la
    ruta convertiría una degradación anunciada en un 500 delante del alumno."""
    r = _reordenador_lento()
    salida, motivo = r.reordenar_o_rendirse("x", _candidatos_falsos(3), top=2, espera_s=0.05)
    assert salida is None and motivo == "gpu_no_contesta"
    assert r.rendiciones == 1, "la rendicion no se cuenta: /salud no podria decir que esta pasando"
    r._ejecutor.shutdown(wait=False)


def test_la_COLA_no_se_cuenta_como_averia_de_la_GPU():
    """LA SATURACION NO ES UN FALLO, y confundirlas es diagnosticar mal.

    Con un solo hilo, la segunda petición de una ráfaga se queda esperando SIN QUE LA GPU TENGA
    NADA QUE VER. Si eso se contara como "la GPU no responde", el circuit breaker del 8.2 abriría
    el circuito por una punta de tráfico y el sistema anunciaría una avería que no existe: el mismo
    error que ya se evitó con los 429. El discriminante es si el trabajo llegó a EMPEZAR."""
    import threading

    r = _reordenador_lento(segundos=1.0)
    # La primera ocupa el unico hilo; la segunda se queda en la cola sin arrancar.
    hilo = threading.Thread(target=lambda: r.reordenar_o_rendirse(
        "primera", _candidatos_falsos(3), top=2, espera_s=5.0), daemon=True)
    hilo.start()
    while not r._ejecutor._work_queue.empty() or not hilo.is_alive():
        break
    salida, motivo = r.reordenar_o_rendirse("segunda", _candidatos_falsos(3), top=2, espera_s=0.05)
    assert salida is None
    assert motivo == "reordenador_saturado", (
        f"una peticion que ni siquiera arranco se declaro como averia de GPU ({motivo})")
    assert r.rendiciones_por_cola == 1 and r.rendiciones_por_gpu == 0
    hilo.join(timeout=3)
    r._ejecutor.shutdown(wait=False)


def test_si_la_GPU_esta_colgada_ESO_si_es_averia():
    """La otra direccion: el trabajo arranco con tiempo de sobra y no termina. Sin este caso, el de
    arriba pasaria igual con un discriminante que dijera 'saturado' siempre."""
    r = _reordenador_lento(segundos=5.0)
    salida, motivo = r.reordenar_o_rendirse("x", _candidatos_falsos(3), top=2, espera_s=2.0)
    assert salida is None and motivo == "gpu_no_contesta"
    assert r.rendiciones_por_gpu == 1 and r.rendiciones_por_cola == 0
    r._ejecutor.shutdown(wait=False)


def test_arrancar_JUSTO_ANTES_del_plazo_es_COLA_y_no_averia_de_GPU():
    """EL FALLO QUE LA CORRIDA 12 ENSEÑÓ, anclado como regresión.

    `futuro.running()` a secas decía "está corriendo" de un trabajo que había pasado casi todo el
    plazo en la cola y arrancó en el último instante. Salía **una vez en cada nivel** de
    concurrencia: inflaba la avería de GPU y desinflaba la saturación **justo donde importa
    distinguirlas**, que es cuando hay carga. Un diagnóstico que se equivoca solo bajo carga es
    peor que ninguno, porque solo miente cuando se le consulta."""
    import time as _t
    from concurrent.futures import ThreadPoolExecutor

    r = object.__new__(Reordenador)
    r.rendiciones = r.rendiciones_por_gpu = r.rendiciones_por_cola = 0
    r._ejecutor = ThreadPoolExecutor(max_workers=1)
    r._reloj_gpu = _t.perf_counter
    r.reordenar = lambda *a, **k: _t.sleep(5)

    # Un trabajo ocupa el hilo casi todo el plazo; el nuestro arranca al final y no le da tiempo.
    ocupante = r._ejecutor.submit(_t.sleep, 0.9)
    salida, motivo = r.reordenar_o_rendirse("x", _candidatos_falsos(3), top=2, espera_s=1.0)
    assert salida is None
    assert motivo == "reordenador_saturado", (
        "arranco en el ultimo instante tras esperar en cola y se declaro averia de GPU")
    assert r.rendiciones_por_cola == 1 and r.rendiciones_por_gpu == 0
    ocupante.result()
    r._ejecutor.shutdown(wait=False)


def test_los_DOS_plazos_son_independientes_de_verdad_y_no_dos_constantes_iguales():
    """Hasta el 13 de agosto un SOLO número hacía dos trabajos con óptimos distintos: detectar una
    GPU colgada (quiere ser holgado sobre el p95 de 554 ms) y descartar por carga (quiere elegirse
    contra la curva de calidad frente a latencia). El segundo se heredó del primero por accidente.

    Hoy valen lo mismo a propósito, así que un test sobre sus VALORES no probaría nada. Lo que se
    prueba es que el mecanismo los usa por separado: con un plazo de cola corto y uno de avería
    largo, un trabajo que ya arrancó tiene que poder pasarse del de cola y aun así terminar."""
    import time as _t
    from concurrent.futures import ThreadPoolExecutor

    r = object.__new__(Reordenador)
    r.rendiciones = r.rendiciones_por_gpu = r.rendiciones_por_cola = 0
    r._ejecutor = ThreadPoolExecutor(max_workers=1)
    r._reloj_gpu = _t.perf_counter

    def lento(consulta, candidatos, top):
        _t.sleep(0.3)
        return candidatos[:top]

    r.reordenar = lento
    # Cola 0,1 s (se pasa) pero averia 2 s (llega): tiene que SALIR BIEN, no degradarse.
    salida, motivo = r.reordenar_o_rendirse("x", _candidatos_falsos(3), top=2,
                                            espera_s=2.0, espera_cola_s=0.1)
    assert motivo is None and salida is not None, (
        "un trabajo que ya habia arrancado se descarto al vencer el plazo de COLA: los dos plazos "
        "estan conflados y el de averia no sirve de nada")
    assert r.rendiciones == 0
    r._ejecutor.shutdown(wait=False)


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
