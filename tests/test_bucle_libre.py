"""EL BUCLE DE EVENTOS NO SE BLOQUEA, y esto es una PUERTA y no una medición de una vez.

POR QUÉ ESTÁ AQUÍ Y NO EN UN INFORME. El 13 de agosto de 2026 se comprobó a mano que `/api`
responde en 1,5 ms mientras diez consultas pesadas están en vuelo (0,8 ms en reposo), y eso zanjó
una pregunta importante: lo que crece con la concurrencia es la cola de la GPU, no un bucle
bloqueado. Pero una medición contesta la pregunta **el día que se hace**. Lo que la mantiene
contestada es un test.

**Y la avería que vigila es de las que se meten sin querer.** Basta con que alguien convierta
`/consulta` en `async def` sin mover el trabajo a un hilo, o que meta una llamada síncrona —una
consulta a la base, un `reordenar()`, un `requests.get`— dentro de un manejador `async`. Nada falla,
nada se pone rojo, y el sistema sigue funcionando **con una sola consulta**. El daño solo aparece
con varias a la vez: un reordenado de 419 ms en el bucle congela a TODOS los alumnos que ya estaban
recibiendo texto. Es exactamente la clase de fallo que este repo persigue —silencioso, invisible en
la prueba fácil, y caro justo delante del cliente—.

CÓMO SE PRUEBA SIN GPU NI PROVEEDOR: el trabajo pesado se simula con un `time.sleep` dentro de un
endpoint de prueba montado sobre la MISMA aplicación. `time.sleep` bloquea el hilo que lo ejecuta,
igual que lo haría `modelo(**lote)`. Si ese endpoint es síncrono, FastAPI lo lleva al threadpool y
el bucle sigue libre; si fuera `async`, el bucle se pararía. Eso es justo la distinción que hay que
vigilar, y se puede comprobar sin un solo gramo de infraestructura.
"""
import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.consulta import consulta as manejador_consulta

#: Lo que tarda el trabajo pesado simulado. Del orden del reordenado real (419 ms de p50).
PESADO_S = 0.4

#: Techo para el endpoint trivial mientras hay carga. En la medida real fueron 1,5 ms contra 0,8 en
#: reposo; 150 ms deja tres órdenes de margen para no volverse inestable en un runner cargado, y aun
#: así está MUY por debajo de los 400 ms que costaría una sola tarea bloqueando el bucle.
TECHO_MS = 150.0


@pytest.fixture
def app_con_carga():
    app = FastAPI()

    @app.get("/trivial")
    def trivial() -> dict:
        return {"ok": True}

    @app.get("/pesado")
    def pesado() -> dict:
        """Síncrono A PROPÓSITO: es la forma correcta, y la que este test protege."""
        time.sleep(PESADO_S)
        return {"ok": True}

    return app


def test_el_endpoint_trivial_responde_mientras_hay_carga_pesada(app_con_carga):
    """La dirección SANA: con el trabajo pesado en endpoints síncronos, el bucle sigue libre."""
    with TestClient(app_con_carga) as cli:
        t = time.perf_counter()
        cli.get("/trivial")
        en_reposo_ms = (time.perf_counter() - t) * 1000

        hilos = [threading.Thread(target=lambda: cli.get("/pesado")) for _ in range(8)]
        for h in hilos:
            h.start()
        time.sleep(0.05)
        t = time.perf_counter()
        cli.get("/trivial")
        bajo_carga_ms = (time.perf_counter() - t) * 1000
        for h in hilos:
            h.join()

    assert bajo_carga_ms < TECHO_MS, (
        f"/trivial tardo {bajo_carga_ms:.0f} ms con 8 peticiones pesadas en vuelo (en reposo: "
        f"{en_reposo_ms:.1f} ms). Eso es el bucle de eventos BLOQUEADO: alguien ha metido trabajo "
        f"sincrono en un manejador async, y con varios alumnos a la vez se congelan todos")


def test_la_sonda_CAZA_un_manejador_async_que_bloquea():
    """La dirección MUTADA, y sin ella el test de arriba no probaría nada: si la sonda no supiera
    distinguir un bucle bloqueado de uno libre, su verde no significaría nada.

    Aquí el endpoint pesado es `async def` **con un `time.sleep` dentro**, que es el error real —no
    uno inventado—: se escribe así por costumbre, no falla nunca con una sola petición, y tumba la
    concurrencia entera."""
    app = FastAPI()

    @app.get("/trivial")
    def trivial() -> dict:
        return {"ok": True}

    @app.get("/pesado")
    async def pesado() -> dict:
        time.sleep(PESADO_S)          # bloquea el BUCLE, no un hilo del pool
        return {"ok": True}

    with TestClient(app) as cli:
        hilos = [threading.Thread(target=lambda: cli.get("/pesado")) for _ in range(4)]
        for h in hilos:
            h.start()
        time.sleep(0.05)
        t = time.perf_counter()
        cli.get("/trivial")
        bajo_carga_ms = (time.perf_counter() - t) * 1000
        for h in hilos:
            h.join()

    assert bajo_carga_ms > TECHO_MS, (
        f"la sonda no distingue: /trivial tardo solo {bajo_carga_ms:.0f} ms con cuatro manejadores "
        f"async bloqueando el bucle. Si no caza esto, su verde en el test de arriba no vale nada")


def test_consulta_sigue_siendo_un_manejador_SINCRONO():
    """El ancla directa, barata y sin carga: `/consulta` es un `def`, no un `async def`.

    Es la comprobación que habría cazado el cambio antes de que costara una demo, y complementa a
    las de arriba: aquellas miden el SÍNTOMA con carga, esta mira la CAUSA en una línea. Si algún
    día `/consulta` tiene que ser `async`, este test se cambia a propósito y el trabajo pesado se
    mueve a `asyncio.to_thread` en el mismo commit."""
    import inspect
    assert not inspect.iscoroutinefunction(manejador_consulta), (
        "/consulta paso a ser `async def`. El generador `_flujo` hace trabajo sincrono -embebido, "
        "SQL, reordenado en GPU- y desde un manejador async eso corre EN EL BUCLE: congelaria a "
        "todos los alumnos con SSE abierto. Si el cambio es querido, mueve el trabajo a un hilo")
