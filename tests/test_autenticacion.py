"""La puerta del token (0.3, 15 de agosto de 2026) y el redactor de `/salud`.

**Las dos direcciones, que aquí son especialmente fáciles de confundir con una sola:** que sin token
se rechace **y** que con token se pase. Un middleware que devolviera 401 a todo pasaría la mitad de
esta suite y rompería la sesión entera; uno que dejara pasar todo pasaría la otra mitad.
"""
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core import autenticacion

TOKEN = "un-token-de-prueba-largo-y-tonto"
#: Rutas que SÍ piden token. Baratas de llamar: las que tocan base devolverían 500 sin ella, y lo
#: que se comprueba aquí es la puerta, que va ANTES.
PROTEGIDAS = ("/consulta", "/titulaciones", "/asignaturas", "/trazas/1")


#: `raise_server_exceptions=False` NO es para tapar errores: es lo que hace que este fichero mida
#: LA PUERTA y no la base de datos. Sin él, `/titulaciones` revienta con el error de psycopg —aquí
#: no hay Postgres— y el test no llega nunca a mirar el código; con él, ese fallo es un 500, que se
#: distingue perfectamente del 401. **Un 500 aquí es un aprobado**: significa que la petición
#: atravesó la puerta y se estrelló después, que es exactamente lo que se quiere comprobar.
def cliente() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def con_token(monkeypatch):
    monkeypatch.setenv("VERIDICA_TOKEN", TOKEN)
    return cliente()


@pytest.fixture
def sin_token(monkeypatch):
    monkeypatch.delenv("VERIDICA_TOKEN", raising=False)
    return cliente()


@pytest.mark.parametrize("ruta", PROTEGIDAS)
def test_sin_cabecera_es_401(con_token, ruta):
    r = con_token.get(ruta) if ruta != "/consulta" else con_token.post(ruta, json={"texto": "x"})
    assert r.status_code == 401, f"{ruta} se sirve sin token"
    assert "token" in r.json()["error"]


@pytest.mark.parametrize("ruta", PROTEGIDAS)
def test_con_la_cabecera_correcta_la_puerta_DEJA_PASAR(con_token, ruta):
    """La otra dirección. No se comprueba qué contesta la ruta —eso es cosa suya y aquí no hay base
    de datos—, solo que **la puerta no fue quien la paró**."""
    cab = {autenticacion.CABECERA: TOKEN}
    r = (con_token.post(ruta, json={"texto": "x"}, headers=cab) if ruta == "/consulta"
         else con_token.get(ruta, headers=cab))
    assert r.status_code != 401, f"{ruta} rechaza el token correcto"


def test_tambien_vale_Authorization_Bearer(con_token):
    r = con_token.get("/titulaciones", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code != 401


def test_un_token_PARECIDO_no_pasa(con_token):
    """El control negativo que separa "comprueba el token" de "comprueba que hay una cabecera"."""
    for malo in (TOKEN[:-1], TOKEN + "x", TOKEN.upper(), "", "   "):
        r = con_token.get("/titulaciones", headers={autenticacion.CABECERA: malo})
        assert r.status_code == 401, f"paso un token que no es: {malo!r}"


@pytest.mark.parametrize("ruta", ["/salud", "/api", "/"])
def test_las_rutas_ABIERTAS_siguen_abiertas_con_la_puerta_puesta(con_token, ruta):
    """**Sin esto la puerta rompe tres cosas a la vez** y no se sabría hasta el lunes: el
    healthcheck de compose llama a `/salud` sin cabeceras, `servir_anfitrion.py` decide con ella si
    abre el túnel, y la página tiene que poder cargar para poder pedir el token."""
    assert con_token.get(ruta).status_code != 401


def test_sin_VERIDICA_TOKEN_no_hay_puerta_pero_SE_DICE(sin_token):
    """La demo local sigue funcionando sin ceremonia — y el defecto abierto se declara en vez de
    quedarse callado, que es la mitad que importa."""
    assert sin_token.get("/titulaciones").status_code != 401
    assert sin_token.get("/salud").json()["autenticacion"] == "ABIERTA"
    assert "ABIERTA" in sin_token.get("/api").json()["autenticacion"]


def test_con_token_lo_dice_y_NO_LO_ENSEÑA(con_token):
    """Decir *si* hay puerta sin decir *cuál* es la llave. La regla de la casa sobre las salidas que
    enumeran configuración, aplicada a la que además va a estar publicada en internet."""
    for ruta in ("/salud", "/api"):
        cuerpo = con_token.get(ruta).text
        assert "token" in cuerpo.lower(), f"{ruta} no declara que hay puerta"
        assert TOKEN not in cuerpo, f"{ruta} PUBLICA EL TOKEN"


def test_la_puerta_se_aplica_a_TODA_ruta_que_no_este_declarada_abierta():
    """**LA PROPIEDAD QUE HACE QUE ESTO NO SE PUEDA OLVIDAR.** La lista que se mantiene es la de lo
    ABIERTO, así que una ruta nueva nace protegida. Este test lo comprueba sobre las rutas
    registradas de verdad en la app, no sobre una lista escrita a mano que envejecería sola."""
    rutas = {r.path for r in app.routes if getattr(r, "path", "").startswith("/")}
    sin_parametros = {r for r in rutas if "{" not in r}
    protegidas = {r for r in sin_parametros if not autenticacion.esta_abierta(r)}
    assert protegidas, "todas las rutas estan abiertas: la puerta no protege nada"
    abiertas = sin_parametros - protegidas
    assert abiertas <= set(autenticacion.ABIERTAS) | {"/estatico"}, \
        f"hay rutas abiertas que no estan declaradas con su motivo: {abiertas}"


# --- el redactor -------------------------------------------------------------------------------

@pytest.mark.parametrize("crudo,prohibido", [
    ("OperationalError: connection to server at postgresql://veridica:s3cr3t0@db:5432/veridica "
     "failed", "s3cr3t0"),
    ("RuntimeError: INFERENCIA_API_KEY=sk-live-abcdef no vale", "sk-live-abcdef"),
    ("error con password: hunter2 dentro", "hunter2"),
    ("Authorization: Bearer ey.JHBGciOi", "ey.JHBGciOi"),
])
def test_el_redactor_tapa_el_secreto(crudo, prohibido):
    limpio = autenticacion.redactar(crudo)
    assert prohibido not in limpio, f"el secreto sigue saliendo: {limpio}"
    assert "(oculto)" in limpio, "no dice que ha tapado algo"


def test_el_redactor_NO_se_come_lo_que_hay_que_leer():
    """La otra dirección, y es la que decide si la sonda sigue sirviendo para algo. *Se puede decir
    **si** difiere sin decir **cuánto** vale*: aquí, que la conexión falló y contra qué host."""
    limpio = autenticacion.redactar(
        "OperationalError: connection to server at postgresql://veridica:s3cr3t0@db:5432/veridica "
        "failed: Connection refused")
    for hay_que_verlo in ("OperationalError", "db:5432", "Connection refused", "veridica"):
        assert hay_que_verlo in limpio, f"el redactor se ha comido {hay_que_verlo!r}: {limpio}"


def test_el_detalle_de_las_sondas_de_salud_pasa_por_el_redactor(monkeypatch, sin_token):
    """**No basta con que el redactor funcione: hay que comprobar que ALGUIEN LO LLAMA.** Es la
    familia del NLI construido y no enchufado — una capacidad correcta que no está en el camino no
    protege nada, y aquí el camino es el que va a estar publicado."""
    from app.api import main as mod
    monkeypatch.setattr(mod, "_db", lambda: (_ for _ in ()).throw(
        RuntimeError("no conecta a postgresql://veridica:s3cr3t0@db:5432/veridica")))
    cuerpo = sin_token.get("/salud").text
    assert "s3cr3t0" not in cuerpo, "/salud publica la contrasena de la base"
    assert "(oculto)" in cuerpo
