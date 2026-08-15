"""`/salud` distingue lo que impide responder de lo que degrada (encargo 4.4).

**POR QUÉ ESTO ES UN DIAGNÓSTICO Y NO UN CÓDIGO DE ESTADO.** Con todas las dependencias en la misma
lista, el contenedor —que no lleva torch a propósito— devolvía **503**, y `docker compose up --wait`
no arrancaba por una capacidad que decidimos **nosotros** no empaquetar. Un 503 dice *"no puedo
responder"*; lo que pasaba era *"respondo peor y lo digo"*. Es el mismo criterio que el 8.2 aplica al
429 del proveedor: **degradar anunciando no es estar roto**, y confundirlos hace que el despliegue no
arranque.
"""
import pytest
from fastapi.testclient import TestClient

from app.api.main import CONSECUENCIA, ESENCIALES, app


def sondas(monkeypatch, rotas=()):
    """Cada sonda en verde salvo las que se pidan rotas."""
    from app.api import main as mod
    for nombre, funcion in (("db", "_db"), ("extensiones", "_extensiones"), ("redis", "_redis"),
                            ("embebedor", "_embebedor"), ("reordenador", "_reordenador"),
                            # El NLI entro en /salud al enchufarlo (4.4) y este bucle no lo cubria:
                            # su sonda real fallaba en el proceso de test y ensuciaba `degradadas`.
                            ("nli", "_nli"), ("worker", "_worker")):
        if nombre in rotas:
            def rota(_n=nombre):
                raise RuntimeError(f"{_n} caido: No module named 'torch'")
            monkeypatch.setattr(mod, funcion, rota)
        else:
            monkeypatch.setattr(mod, funcion, lambda _n=nombre: f"{_n} ok")
    return TestClient(app)


def test_todo_en_verde_es_200_y_ok(monkeypatch):
    r = sondas(monkeypatch).get("/salud")
    assert r.status_code == 200
    assert r.json()["estado"] == "ok" and r.json()["que_falta"] == []


@pytest.mark.parametrize("opcional", ["embebedor", "reordenador", "nli"])
def test_un_componente_OPCIONAL_ausente_es_200_degradado_y_NO_una_averia(monkeypatch, opcional):
    """El caso real: el contenedor sin torch. Se responde peor y se dice, que es degradación
    declarada. Devolver 503 aquí es afirmar que el sistema no puede contestar cuando sí puede.

    **`worker` y `redis` salieron de esta lista el 14/08/2026 y NO por conveniencia**: ver abajo.
    Este test anclaba que los cinco eran `degradadas`, y cuando la clasificación cambió su verde
    era el problema — es la regla de la casa sobre los tests que anclan el mundo viejo, así que se
    movieron a propósito con su motivo escrito en vez de dejarlos rojos o borrarlos.
    """
    r = sondas(monkeypatch, rotas=[opcional]).get("/salud")
    assert r.status_code == 200, "un componente opcional ausente NO es una averia"
    cuerpo = r.json()
    assert cuerpo["estado"] == "degradado" and cuerpo["puede_responder"] is True
    assert cuerpo["degradadas"] == [opcional] and cuerpo["rotas"] == []


@pytest.mark.parametrize("pieza", ["redis", "worker"])
def test_una_pieza_SIN_CONSUMIDOR_construido_no_se_presenta_como_degradacion(monkeypatch, pieza):
    """UN ROJO QUE NO IMPIDE NADA NO ES UN ROJO, y una sonda que los mezcla obliga a explicarse.

    **El caso que lo pide:** la cabecera de la interfaz **enlaza `/salud`** e invita a pulsarlo
    diciendo que ahí está lo que la instancia sabe hacer. En el anfitrión (ADR 0023) `redis` y
    `worker` salen abajo —`redis:6379` es un nombre de la red de compose que fuera no resuelve— y
    **ninguna ruta construida los usa**: la caché semántica y la cola están declaradas y no
    construidas. Quien pulse el enlace vería dos rojos que no tienen nada que ver con lo que se
    está enseñando.

    **No se esconden**: se declaran en `sin_consumidor` con su porqué. Lo que cambia es que no se
    cuentan como degradación de lo que se sirve.

    **MOVIDO EL 15/08/2026, y a propósito: este test exigía `pieza in caidas`, o sea exigía que se
    SONDEARAN.** Al medirlo salió el motivo para dejar de hacerlo por defecto (ver
    `test_por_defecto_NO_se_sondean...`), así que la exigencia vieja se traslada a `?todo=1`, que es
    donde sigue siendo verdad, en vez de borrarse.
    """
    cuerpo = sondas(monkeypatch, rotas=[pieza]).get("/salud?todo=1").json()
    assert cuerpo["estado"] == "ok", "una pieza que no usa nadie no degrada lo que se sirve"
    assert cuerpo["degradadas"] == [] and cuerpo["rotas"] == []
    assert pieza in cuerpo["caidas"], "se ha escondido en vez de clasificarse"
    sin = {x["pieza"]: x for x in cuerpo["sin_consumidor"]}
    assert pieza in sin and sin[pieza]["esta"] == "abajo"
    assert "NO construido" in sin[pieza]["por_que_no_degrada"]


@pytest.mark.parametrize("pieza", ["redis", "worker"])
def test_por_defecto_NO_se_sondean_las_piezas_que_no_usa_nadie_Y_SE_DICE(monkeypatch, pieza):
    """**LO QUE CUESTA PREGUNTAR, Y POR QUÉ SE DEJÓ DE PREGUNTAR (15 de agosto de 2026).**

    Medido en los dos procesos vivos el mismo minuto: `/salud` tardaba **10,1 s** en el anfitrión y
    **2,1 s** en el contenedor, y todo menos ~25 ms era estas dos piezas. El `worker` cuesta **2 s
    ESTANDO SANO** —`control.ping` es un *broadcast* que espera su ventana entera— y **7,4 s caído,
    con un plazo nominal de 2**: su propio `timeout` no lo sujeta.

    **Ese par de cifras descarta la alternativa de "plazo corto"**, que era la otra opción sobre la
    mesa: cualquier plazo por debajo de 2 s daría por caído un worker **sano**, o sea inventarse una
    avería para no esperar — la guarda fabricando el fallo que perseguía, otra vez. Así que no se
    sondean, que es lo que la clasificación de al lado ya venía diciendo: **nada construido las
    usa.**

    Y `no_sondeada` **no es** `fallo`: no saber el estado de algo que nadie usa no es una caída.
    """
    cuerpo = sondas(monkeypatch, rotas=[pieza]).get("/salud").json()
    assert cuerpo["dependencias"][pieza]["estado"] == "no_sondeada"
    assert cuerpo["dependencias"][pieza]["ms"] == 0.0, "no se sonda: no puede costar tiempo"
    assert pieza not in cuerpo["caidas"], "'no sondeada' no es 'caida': no se sabe"
    assert cuerpo["estado"] == "ok" and cuerpo["degradadas"] == []
    sin = {x["pieza"]: x for x in cuerpo["sin_consumidor"]}
    assert sin[pieza]["esta"] == "sin preguntar", "se ha callado que no se ha preguntado"
    assert "/salud?todo=1" in sin[pieza]["detalle"], "no dice como preguntarle"


def test_todo_1_SIGUE_sondeandolas(monkeypatch):
    """La otra dirección: `?todo=1` no puede ser un parámetro decorativo. Si lo fuera, la única
    forma de saber si redis está vivo habría desaparecido sin que nada se pusiera rojo."""
    cuerpo = sondas(monkeypatch).get("/salud?todo=1").json()
    for pieza in ("redis", "worker"):
        assert cuerpo["dependencias"][pieza]["estado"] == "ok", f"{pieza} no se sondeo con todo=1"
    assert cuerpo["sin_consumidor"] == [], "sanas y sondeadas: no hay nada que declarar"


def test_la_clasificacion_NO_es_una_lista_de_lo_que_molesta_ver_en_rojo(monkeypatch):
    """LA TRAMPA EVIDENTE DE ESTE CAMBIO, y por eso tiene puerta. `sin_consumidor` no sale de una
    lista escrita a mano de piezas cómodas: sale de **quién las consumiría**, y cada consumidor
    tiene que estar en `NO_CONSTRUIDO`. En cuanto la caché semántica exista, `redis` vuelve a
    `degradadas` **por construcción** y no porque alguien se acuerde.

    Se comprueba mutando el inventario: con la caché declarada como construida, `redis` deja de
    tener excusa."""
    from app.api import main as mod
    sin_cache = tuple(x for x in mod.NO_CONSTRUIDO if x != "cache semantica")
    monkeypatch.setattr(mod, "NO_CONSTRUIDO", sin_cache)
    cuerpo = sondas(monkeypatch, rotas=["redis"]).get("/salud").json()
    assert cuerpo["degradadas"] == ["redis"], \
        "con su consumidor construido, redis sigue sin contarse como degradacion"
    # Y LA CONSECUENCIA QUE ESTE TEST GANA AL CAMBIAR LA SONDA: en cuanto redis tiene un consumidor
    # construido, **vuelve a sondearse por defecto**, sin que nadie se acuerde de quitarlo de una
    # lista. La rapidez de /salud es una consecuencia de "nadie la usa", no una excepcion escrita.
    assert cuerpo["dependencias"]["redis"]["estado"] == "fallo", \
        "con consumidor construido tiene que volver a sondearse, no quedarse en no_sondeada"
    assert [x["pieza"] for x in cuerpo["sin_consumidor"]] == ["worker"], \
        "solo el worker sigue sin consumidor construido"


def test_y_una_pieza_que_SI_usa_una_ruta_construida_sigue_degradando(monkeypatch):
    """La otra dirección de la misma puerta: si `sin_consumidor` se comiera cualquier caída, el
    contenedor sin torch saldría 'ok' y la sesión enseñaría media tesis con la pantalla en verde."""
    cuerpo = sondas(monkeypatch, rotas=["nli"]).get("/salud").json()
    assert cuerpo["estado"] == "degradado" and cuerpo["degradadas"] == ["nli"]
    # `sin_consumidor` lista redis y worker porque no se han sondeado, que es lo correcto; lo que
    # este test defiende es que el NLI NO se cuela ahi.
    assert "nli" not in [x["pieza"] for x in cuerpo["sin_consumidor"]]


@pytest.mark.parametrize("esencial", ESENCIALES)
def test_lo_que_IMPIDE_responder_sigue_siendo_503(monkeypatch, esencial):
    """La otra mitad, sin la cual lo de arriba pasaría con un endpoint que devuelve 200 siempre."""
    r = sondas(monkeypatch, rotas=[esencial]).get("/salud")
    assert r.status_code == 503
    assert r.json()["estado"] == "roto" and r.json()["puede_responder"] is False


def test_la_respuesta_dice_EN_TEXTO_que_falta_y_que_se_pierde(monkeypatch):
    """Un booleano no distingue "falta el reordenador" de "falta torch", que son dos conversaciones
    distintas a las nueve de la mañana. Van los tres: el nombre, la consecuencia y el detalle crudo
    de la sonda."""
    cuerpo = sondas(monkeypatch, rotas=["embebedor"]).get("/salud").json()
    linea = cuerpo["que_falta"][0]
    assert linea.startswith("embebedor: ")
    assert "solo por palabras y glosario" in linea, "no dice QUE se pierde"
    assert "No module named 'torch'" in linea, "no arrastra el detalle de la sonda"


def test_toda_dependencia_tiene_su_consecuencia_escrita():
    """Si alguien añade una sonda y no declara qué se pierde sin ella, `que_falta` diría "sin
    consecuencia declarada" el día que se caiga, que es el peor momento para descubrirlo.

    **REESCRITO EL 15/08/2026 sobre la ESTRUCTURA y no sobre el texto del fuente.** La versión
    anterior hacía `'"db": _sonda' in inspect.getsource(salud)`, o sea comprobaba **cómo estaba
    escrita** la función: se puso roja al mover el inventario de sondas fuera del cuerpo sin que
    cambiara ni un comportamiento. Un test que se rompe al reordenar código y no al romper una
    garantía está anclando la forma en vez del fondo — y el que lo lea después no sabrá cuál de las
    dos cosas defendía.
    """
    from app.api.main import SONDAS
    import app.api.main as mod
    assert set(SONDAS) == set(CONSECUENCIA), \
        "hay una sonda sin consecuencia declarada (o al reves): se veria el dia que se caiga"
    for nombre, atributo in SONDAS.items():
        assert callable(getattr(mod, atributo, None)), \
            f"la sonda {nombre} apunta a {atributo}, que no existe o no es llamable"


# --- el techo del threadpool (0.4) ---------------------------------------------------------------

def test_el_threadpool_lo_fijamos_NOSOTROS_y_no_la_libreria():
    """**EL DEFECTO DE ANYIO Y EL NUESTRO VALEN LO MISMO HOY (40), Y ESE ES EL PROBLEMA DEL TEST.**

    Comprobar que el limitador vale 40 no distingue "lo hemos fijado" de "lo hemos heredado": el
    verde saldría igual con el `lifespan` borrado, que es una sonda que no puede ponerse roja. Así
    que se comprueba con un valor que la librería no elegiría jamás.

    Y lo que defiende importa: todas las rutas son síncronas, o sea que este número **es** el techo
    de peticiones simultáneas. Si una actualización de anyio mueve su defecto, nuestro techo se
    movería sin que nadie tocara el repo.
    """
    from app.api import main as mod
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(mod, "HILOS_DE_BLOQUEO", 7)
        with TestClient(mod.app) as cliente:
            vivos = cliente.get("/salud").json()["hilos_de_bloqueo"]
            assert vivos["vivos"] == 7, "el ciclo de vida no fija el pozo: el 40 es herencia"
            assert vivos["declarados"] == 7
    finally:
        monkeypatch.undo()
        # Se devuelve el valor real: `total_tokens` es del proceso, no del test, y dejarlo en 7
        # estrecharia el pozo para todo lo que corra despues en esta misma suite.
        with TestClient(mod.app):
            pass


def test_el_valor_declarado_es_el_que_de_verdad_corre():
    """La otra mitad: que el número publicado en `/salud` salga del limitador VIVO y no de la
    constante. Es la regla de la casa —se comprueba dentro del proceso que sirve— aplicada al
    endpoint que lo cuenta."""
    from app.api import main as mod
    with TestClient(mod.app) as cliente:
        vivos = cliente.get("/salud").json()["hilos_de_bloqueo"]
    assert vivos["declarados"] == vivos["vivos"] == mod.HILOS_DE_BLOQUEO == 40
    assert "techo de peticiones simultaneas" in vivos["que_significa"]
