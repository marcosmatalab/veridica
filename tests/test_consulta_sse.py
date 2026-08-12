"""`POST /consulta` en SSE: el eco verificado del contrato (encargo 2.2).

Estos tests no llaman al proveedor ni a Postgres: el cliente de inferencia esta simulado y la traza
va en memoria. Lo que se prueba es la decision de diseno del endpoint -que se emite PROSA y no JSON
crudo, que el TTFT del alumno es un numero distinto del del proveedor, y cuando se puede reintentar
y cuando no-, que es justo lo que no se ve mirando una respuesta correcta.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core.inferencia import Trozo, Uso
from app.core.traza import TrazaEnMemoria

BUENO = {
    "modo": "responder",
    "afirmaciones": [
        {"id": 1, "tipo": "conocimiento", "texto": "Identifica cada fila.", "fragmento_id": None},
        {"id": 2, "tipo": "andamiaje", "texto": "Vamos por partes.", "andamiaje": "transicion"},
    ],
    "respuesta_redactada": "Una clave primaria identifica cada fila de la tabla.",
    "siguiente_paso": {"tipo": "pregunta_al_alumno", "ref": None, "texto": "Y la ajena?"},
    "confianza_recuperacion": "baja",
}


class AjustesFalsos:
    modelo, max_tokens = "modelo-de-prueba", 900


class ClienteFalso:
    """Devuelve guiones preparados. Cuenta las llamadas: media docena de tests dependen de eso."""

    def __init__(self, *guiones):
        self.guiones = list(guiones)
        self.llamadas = 0
        self.a = AjustesFalsos()

    def stream(self, mensajes, response_format=None, traza=None):
        guion = self.guiones[min(self.llamadas, len(self.guiones) - 1)]
        self.llamadas += 1
        if traza is not None:
            traza.ttft_proveedor_ms = 12.5
        for trozo in guion:
            yield Trozo(texto=trozo)
        yield Trozo(fin="stop", uso=Uso(tokens_entrada=100, tokens_salida=200))


def en_trozos(objeto, tam=13) -> list:
    crudo = json.dumps(objeto, ensure_ascii=False)
    return [crudo[i:i + tam] for i in range(0, len(crudo), tam)]


@pytest.fixture
def cliente_http():
    app.state.traza = TrazaEnMemoria()
    with TestClient(app) as c:
        yield c


def eventos(respuesta) -> list:
    salida = []
    for bloque in respuesta.text.split("\n\n"):
        if not bloque.strip():
            continue
        nombre = bloque.split("event: ", 1)[1].split("\n", 1)[0]
        datos = json.loads(bloque.split("data: ", 1)[1])
        salida.append((nombre, datos))
    return salida


def test_el_camino_bueno_emite_prosa_y_no_json_crudo(cliente_http):
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    r = cliente_http.post("/consulta", json={"texto": "que es una clave primaria?"})
    assert r.status_code == 200
    evs = eventos(r)
    nombres = [n for n, _ in evs]
    assert nombres[0] == "etapa", "lo primero que llega es una etapa real, no la respuesta"
    assert "ttft" in nombres
    assert nombres[-1] == "fin"
    assert "afirmaciones" in nombres
    texto = "".join(d["t"] for n, d in evs if n == "token")
    assert texto == BUENO["respuesta_redactada"]
    assert "{" not in texto and '"' not in texto, "se esta emitiendo JSON crudo al alumno"


def test_el_ttft_del_alumno_y_el_del_proveedor_son_dos_numeros_distintos(cliente_http):
    """Con salida tipada, el primer token del proveedor es `{`. Emitir un solo TTFT es contar como
    tiempo de respuesta algo que el alumno no ha visto."""
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    evs = eventos(cliente_http.post("/consulta", json={"texto": "x"}))
    ttft = [d for n, d in evs if n == "ttft"]
    assert len(ttft) == 1, "el evento ttft se emite UNA vez, al primer caracter de prosa"
    assert ttft[0]["ttft_prosa_ms"] > 0 and ttft[0]["ttft_proveedor_ms"] == 12.5
    fin = [d for n, d in evs if n == "fin"][0]
    assert fin["ttft_prosa_ms"] and fin["total_ms"] >= fin["ttft_prosa_ms"]


def test_las_afirmaciones_salen_sin_verificar_y_lo_dicen(cliente_http):
    """El 2.2 comprueba la FORMA del contrato, no la verdad. Si esto se pusiera en 'verificada'
    algun dia sin que exista la fase 4, seria la mentira mas cara del proyecto."""
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    evs = eventos(cliente_http.post("/consulta", json={"texto": "x"}))
    datos = [d for n, d in evs if n == "afirmaciones"][0]
    assert [a["veredicto"] for a in datos["afirmaciones"]] == ["sin_verificar", "sin_verificar"]
    assert "no la verdad" in datos["aviso"]
    assert all(a["veredicto"] == "sin_verificar" for a in app.state.traza.afirmaciones)


def test_la_traza_guarda_los_dos_tiempos_y_el_gasto(cliente_http):
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    cliente_http.post("/consulta", json={"texto": "x", "asignatura_id": 29})
    assert len(app.state.traza.consultas) == 1
    resp = app.state.traza.respuestas[0]
    assert resp["tokens_entrada"] == 100 and resp["tokens_salida"] == 200
    assert resp["ttft_ms"] and resp["total_ms"]
    etapas = resp["etapas"]["generacion"]
    assert etapas["ttft_proveedor_ms"] == 12.5 and etapas["ttft_prosa_ms"]
    assert resp["etapas"]["recuperacion"]["construido"] is False
    assert resp["etapas"]["verificacion"]["construido"] is False


def test_un_json_roto_sin_prosa_emitida_se_reintenta_una_vez(cliente_http):
    """El reintento unico de la seccion 7. Aqui se puede: no ha salido nada a pantalla."""
    roto = ['{"modo": "responder", "afirmaciones": [', "  esto no es JSON"]
    app.state.cliente_inferencia = ClienteFalso(roto, en_trozos(BUENO))
    evs = eventos(cliente_http.post("/consulta", json={"texto": "x"}))
    assert app.state.cliente_inferencia.llamadas == 2
    assert [n for n, _ in evs][-1] == "fin"
    assert [d for n, d in evs if n == "fin"][0]["abstencion"] is False
    # Y el alumno recibe la prosa de la SEGUNDA pasada: un reintento que valida pero no emite
    # dejaria la pantalla en blanco con un 'fin' en verde, que es la peor combinacion posible.
    texto = "".join(d["t"] for n, d in evs if n == "token")
    assert texto == BUENO["respuesta_redactada"]


def test_si_ya_salio_prosa_no_se_reintenta_y_se_abstiene(cliente_http):
    """EL PRECIO DE EMITIR PRONTO, escrito como test. Un reintento aqui le repetiria al alumno el
    texto que ya tiene en pantalla, asi que se abstiene y se le dice a la interfaz que lo retire."""
    cortado = ['{"modo": "responder", "afirmaciones": [], "respuesta_redactada": "empieza y se',
               ' corta aqui mismo']
    app.state.cliente_inferencia = ClienteFalso(cortado, en_trozos(BUENO))
    evs = eventos(cliente_http.post("/consulta", json={"texto": "x"}))
    assert app.state.cliente_inferencia.llamadas == 1, "reintento con prosa ya emitida"
    abst = [d for n, d in evs if n == "abstencion"]
    assert abst and abst[0]["ya_habia_prosa_en_pantalla"] is True
    assert [d for n, d in evs if n == "fin"][0]["abstencion"] is True
    assert app.state.traza.respuestas[0]["abstencion"] is True


def test_dos_intentos_rotos_acaban_en_abstencion(cliente_http):
    app.state.cliente_inferencia = ClienteFalso(["no es JSON"])
    evs = eventos(cliente_http.post("/consulta", json={"texto": "x"}))
    assert app.state.cliente_inferencia.llamadas == 2
    assert "abstencion" in [n for n, _ in evs]
    assert app.state.traza.afirmaciones == []


def test_un_contrato_bien_formado_pero_con_cita_donde_no_toca_tambien_abstiene(cliente_http):
    """La validacion de forma no es decorativa: el JSON de abajo es JSON perfecto y rompe el
    contrato de la seccion 7. Es exactamente lo que devolvio el proveedor en la primera llamada
    real, antes de partir el esquema en variantes."""
    malo = json.loads(json.dumps(BUENO))
    malo["afirmaciones"][0]["cita"] = "Identifica cada fila."
    app.state.cliente_inferencia = ClienteFalso(en_trozos(malo))
    evs = eventos(cliente_http.post("/consulta", json={"texto": "x"}))
    assert "abstencion" in [n for n, _ in evs]


def test_sin_proveedor_configurado_lo_dice_en_vez_de_reventar(cliente_http):
    app.state.cliente_inferencia = None
    app.state.sin_proveedor = "faltan variables de entorno: INFERENCIA_API_KEY"
    r = cliente_http.post("/consulta", json={"texto": "x"})
    assert r.status_code == 503
    assert "INFERENCIA_API_KEY" in r.json()["detail"]
