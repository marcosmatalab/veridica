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


@pytest.mark.parametrize("opcional", ["embebedor", "reordenador", "nli", "worker", "redis"])
def test_un_componente_OPCIONAL_ausente_es_200_degradado_y_NO_una_averia(monkeypatch, opcional):
    """El caso real: el contenedor sin torch. Se responde peor y se dice, que es degradación
    declarada. Devolver 503 aquí es afirmar que el sistema no puede contestar cuando sí puede."""
    r = sondas(monkeypatch, rotas=[opcional]).get("/salud")
    assert r.status_code == 200, "un componente opcional ausente NO es una averia"
    cuerpo = r.json()
    assert cuerpo["estado"] == "degradado" and cuerpo["puede_responder"] is True
    assert cuerpo["degradadas"] == [opcional] and cuerpo["rotas"] == []


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
    consecuencia declarada" el día que se caiga, que es el peor momento para descubrirlo."""
    from app.api.main import salud
    import inspect
    nombres = {n for n in CONSECUENCIA}
    fuente = inspect.getsource(salud)
    for sonda in ("db", "extensiones", "redis", "embebedor", "reordenador", "nli", "worker"):
        assert f'"{sonda}": _sonda' in fuente and sonda in nombres
