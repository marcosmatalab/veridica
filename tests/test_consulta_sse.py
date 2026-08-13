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
    "siguiente_paso": {"tipo": "pregunta_al_alumno", "texto": "Y la ajena?"},
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
    # El embebedor se apaga a proposito: estos tests son del CONTRATO y del streaming, no de la
    # recuperacion. Con el puesto, /consulta iria a buscar fragmentos a una base que aqui no hay.
    app.state.embebedor = None
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
    # La afirmacion respalda la prosa a proposito: sin ella el portero de frases del 4.5 la
    # podaria por no estar cubierta, y este test es del REINTENTO, no de la cobertura.
    cortado = ['{"modo": "responder", "afirmaciones": [{"id": 1, "tipo": "conocimiento",',
               ' "texto": "La sesion empieza y se corta en el servidor.", "fragmento_id": null}],',
               ' "respuesta_redactada": "La sesion empieza y se corta',
               ' en el servidor mismo']
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


# --- el vigilante de ritmo y el plazo, vistos desde el SSE (3.4) ---------------------------------
#
# Aqui no se prueba la clase -eso es tests/test_ritmo.py- sino el CABLEADO, que es lo que se rompe
# al refactorizar: que el corte llega al alumno como un reintento anunciado y no como una pantalla
# parada, y que lo emitido se retira en vez de borrarse a la callada.

class ClienteLento:
    """Emite el contrato token a token a un ritmo dado, con un reloj falso que avanza solo."""

    def __init__(self, objeto, por_segundo, reloj):
        self.trozos = en_trozos(objeto, tam=4)
        self.por_segundo = por_segundo
        self.reloj = reloj
        self.llamadas = 0
        self.a = AjustesFalsos()

    def stream(self, mensajes, response_format=None, traza=None):
        self.llamadas += 1
        # La segunda pasada va a ritmo normal: asi se ve que el reintento SIRVE de algo.
        ritmo = self.por_segundo if self.llamadas == 1 else 200.0
        for trozo in self.trozos:
            self.reloj.t += 1.0 / ritmo
            yield Trozo(texto=trozo)
        yield Trozo(fin="stop", uso=Uso(tokens_entrada=100, tokens_salida=200))


class RelojFalso:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture
def reloj(monkeypatch):
    r = RelojFalso()
    monkeypatch.setattr("app.api.consulta.time.perf_counter", r)
    return r


def test_un_ritmo_hundido_se_corta_y_se_REINTENTA_anunciandolo(cliente_http, reloj):
    """El caso medido: 2 de cada 20 consultas se hunden tras arrancar bien. Sin esto, el alumno ve
    la pantalla parada un minuto; con esto, ve un aviso y la respuesta buena."""
    cli = ClienteLento(BUENO, por_segundo=6.0, reloj=reloj)
    cliente_http.app.state.cliente_inferencia = cli
    r = cliente_http.post("/consulta", json={"texto": "que es una clave primaria"})
    nombres = [n for n, _ in eventos(r)]
    assert "reintento" in nombres, "se hundio el ritmo y no se anuncio nada"
    assert cli.llamadas == 2, f"no reintento: {cli.llamadas} llamada(s)"
    datos = [d for n, d in eventos(r) if n == "reintento"][0]
    assert datos["motivo"] == "ritmo_caido"
    assert datos["tokens_por_segundo"] < 35
    # Y la respuesta buena sale igualmente: el reintento no es una abstencion.
    assert "afirmaciones" in nombres and "abstencion" not in nombres


def test_si_ya_habia_prosa_el_reintento_lo_DICE_para_que_la_interfaz_la_retire(cliente_http, reloj):
    """La regla del 2.2 dice que lo emitido no se reintenta, porque repetiria texto. El ritmo caido
    es la excepcion declarada: la alternativa no es una respuesta correcta, es un minuto congelado.
    Lo que NO se hace es borrar sin decirlo."""
    cli = ClienteLento(BUENO, por_segundo=6.0, reloj=reloj)
    cliente_http.app.state.cliente_inferencia = cli
    r = cliente_http.post("/consulta", json={"texto": "x"})
    ev = eventos(r)
    corte = [i for i, (n, _) in enumerate(ev) if n == "reintento"][0]
    # La prosa que cuenta es la emitida ANTES del corte, no la de toda la respuesta: despues del
    # reintento viene la pasada buena, que por supuesto emite. Mirar el total diria que si siempre.
    hubo_prosa_antes = any(n == "token" for n, _ in ev[:corte])
    assert ev[corte][1]["ya_habia_prosa_en_pantalla"] == hubo_prosa_antes


def test_agotado_el_plazo_se_CORTA_y_se_dice_en_vez_de_congelar(cliente_http, reloj):
    """El presupuesto como plazo de verdad. Con las dos pasadas lentas no se llega, y entonces lo
    correcto no es seguir esperando: es cortar y declararlo."""
    class LargoYAceptable(ClienteLento):
        """40 tokens/s: por ENCIMA del umbral del vigilante, asi que lo que corta es el plazo."""

        def stream(self, mensajes, response_format=None, traza=None):
            self.llamadas += 1
            for trozo in en_trozos(BUENO, tam=1):
                self.reloj.t += 1 / 40.0
                yield Trozo(texto=trozo)
            yield Trozo(fin="stop", uso=Uso(tokens_entrada=1, tokens_salida=1))

    cliente_http.app.state.cliente_inferencia = LargoYAceptable(BUENO, 40.0, reloj)
    r = cliente_http.post("/consulta", json={"texto": "x"})
    ev = eventos(r)
    nombres = [n for n, _ in ev]
    assert "abstencion" in nombres, "se agoto el plazo y no se dijo nada"
    datos = [d for n, d in ev if n == "abstencion"][0]
    assert datos["por_plazo"] is True
    assert "no llego dentro del plazo" in datos["que_significa"]


def test_el_plazo_NO_se_reintenta(cliente_http, reloj):
    """Volver a pedir cuando ya se agotaron los 5 s solo puede llegar mas tarde todavia.

    OJO CON EL CASO QUE HAY QUE CONSTRUIR AQUI, que al primer intento lo puse mal: un flujo MUY
    lento no sirve para probar el plazo, porque el vigilante de ritmo lo corta antes -que es
    justamente el diseno-. El plazo solo se ve solo con un flujo que va POR ENCIMA del umbral de
    ritmo (40 tokens/s > 35) y aun asi tarda demasiado porque la respuesta es larga. Son dos
    averias distintas y cada una necesita su caso."""
    class LargoYAceptable(ClienteLento):
        def stream(self, mensajes, response_format=None, traza=None):
            self.llamadas += 1
            for trozo in en_trozos(BUENO, tam=1):     # muchos trozos, uno por caracter
                self.reloj.t += 1 / 40.0              # 40 tokens/s: el vigilante NO lo toca
                yield Trozo(texto=trozo)
            yield Trozo(fin="stop", uso=Uso(tokens_entrada=1, tokens_salida=1))

    cli = LargoYAceptable(BUENO, 40.0, reloj)
    cliente_http.app.state.cliente_inferencia = cli
    r = cliente_http.post("/consulta", json={"texto": "x"})
    nombres = [n for n, _ in eventos(r)]
    assert cli.llamadas == 1, f"reintento tras agotar el plazo: {cli.llamadas} llamadas"
    assert "reintento" not in nombres, "esto era el plazo, no el ritmo: se confundieron las averias"
    datos = [d for n, d in eventos(r) if n == "abstencion"][0]
    assert datos["por_plazo"] is True


def test_una_consulta_a_ritmo_normal_NO_se_corta(cliente_http, reloj):
    """La direccion sana. Sin ella, los cuatro de arriba probarian solo que se sabe cortar."""
    cli = ClienteLento(BUENO, por_segundo=150.0, reloj=reloj)
    cliente_http.app.state.cliente_inferencia = cli
    r = cliente_http.post("/consulta", json={"texto": "x"})
    nombres = [n for n, _ in eventos(r)]
    assert "reintento" not in nombres and "abstencion" not in nombres
    assert cli.llamadas == 1


def test_al_cortar_el_flujo_el_coste_NO_se_queda_en_cero(cliente_http, reloj):
    """Un cero en `tokens_salida` no es "no costo": es "no me entere", y son cosas distintas.

    Al cortar por plazo, el trozo con `usage` del proveedor no llega nunca. Si se dejara en cero, la
    contabilidad del 2.6 y de la fase 6 tendria un hueco silencioso justo en las consultas que peor
    van -sesgando el coste medio hacia abajo-. Medido el 13 de agosto: con el plazo puesto, 6 de
    cada 20 consultas acaban aqui, o sea un 30 % del gasto perdido."""
    class LargoYAceptable(ClienteLento):
        def stream(self, mensajes, response_format=None, traza=None):
            self.llamadas += 1
            for trozo in en_trozos(BUENO, tam=1):
                self.reloj.t += 1 / 40.0
                yield Trozo(texto=trozo)
            yield Trozo(fin="stop", uso=Uso(tokens_entrada=1, tokens_salida=1))

    cliente_http.app.state.cliente_inferencia = LargoYAceptable(BUENO, 40.0, reloj)
    r = cliente_http.post("/consulta", json={"texto": "x"})
    fin = [d for n, d in eventos(r) if n == "fin"][0]
    assert fin["tokens_salida"] > 0, "se corto el flujo y el gasto se anoto como cero"
    traza = cliente_http.app.state.traza.respuestas[-1]
    assert traza["etapas"]["generacion"]["uso_estimado"] is True, \
        "el uso va estimado y no se dice: un numero aproximado y uno medido no valen lo mismo"


# --- veredictos EN CURSO: verificar mientras el modelo sigue escribiendo (4.2) -------------------

CON_CITA = {
    "modo": "responder",
    "afirmaciones": [
        {"id": 1, "tipo": "literal", "texto": "La sesion vive en el servidor.",
         "fragmento_id": "F7", "cita": "la cookie solo contiene el identificador"},
        {"id": 2, "tipo": "literal", "texto": "Esto no esta.", "fragmento_id": "F7",
         "cita": "esta frase no aparece en ningun sitio"},
        {"id": 3, "tipo": "literal", "texto": "Procedencia inventada.", "fragmento_id": "F999",
         "cita": "la cookie solo contiene el identificador"},
    ],
    "respuesta_redactada": "La sesion se guarda en el servidor y la cookie lleva solo el id.",
    "siguiente_paso": {"tipo": "pregunta_al_alumno", "texto": "Y la cookie?"},
}

FRAGMENTO_7 = "La sesion se almacena en el servidor; la cookie solo contiene el identificador."


@pytest.fixture
def con_contexto(cliente_http, monkeypatch):
    """`/consulta` con UN fragmento de verdad en el contexto, sin base ni embebedor.

    Se sustituye `_recuperar` entero: lo que estos tests prueban es la VERIFICACION EN CURSO, no la
    recuperacion, y montarla de verdad exigiria Postgres con el corpus dentro (ADR 0001)."""
    from app.api import consulta as mod
    from app.core.recuperacion import Candidato

    c = Candidato(fragmento_id=7, asignatura_id=1, documento="d.md", orden=0, unidad=None,
                  texto=FRAGMENTO_7, puntuacion=1.0, origen="fusion")
    monkeypatch.setattr(mod, "_recuperar",
                        lambda *a, **k: ([], mod._contexto([c]), "alta", {}, [c]))
    return cliente_http


def test_los_veredictos_salen_ANTES_de_que_termine_la_prosa(con_contexto):
    """LA PROPIEDAD QUE HACE QUE ESTO VALGA, y por eso se prueba el ORDEN y no solo la presencia.

    Como `afirmaciones` va antes de `respuesta_redactada` en el contrato, el array esta cerrado
    cuando empieza la prosa. La comparacion literal es instantanea, asi que los veredictos pueden
    salir MIENTRAS el modelo sigue escribiendo: el alumno ve el sistema comprobandose a si mismo
    en vez de un rotulo encendido. Si salieran al final, esto seria un adorno."""
    app.state.cliente_inferencia = ClienteFalso(en_trozos(CON_CITA, tam=8))
    app.state.embebedor = None
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x"}))
    nombres = [n for n, _ in ev]

    assert "veredicto" in nombres, "no se emitio ni un veredicto"
    primer_veredicto = nombres.index("veredicto")
    ultimo_token = len(nombres) - 1 - nombres[::-1].index("token")
    assert primer_veredicto < ultimo_token, (
        "los veredictos salieron cuando la prosa ya habia terminado: el solape no existe y esto no "
        "es verificacion en curso, es verificacion al final con otro nombre")


def test_cada_afirmacion_literal_trae_SU_veredicto_y_los_tres_casos_se_distinguen(con_contexto):
    """Las tres salidas del verificador, por el camino real del SSE y no llamando a la funcion."""
    app.state.cliente_inferencia = ClienteFalso(en_trozos(CON_CITA, tam=8))
    app.state.embebedor = None
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x"}))
    por_id = {d["id_en_contrato"]: d for n, d in ev if n == "veredicto"}

    assert set(por_id) == {1, 2, 3}
    assert por_id[3]["veredicto"] == "podada", "una procedencia inventada no se podo"
    assert por_id[3]["motivo"] == "procedencia_fabricada"
    assert por_id[2]["veredicto"] == "degradada_a_parafrasis"
    assert all(d["durante_la_redaccion"] for d in por_id.values())


def test_la_referencia_del_modelo_lleva_F_y_vuelve_a_ser_NUMERO_en_la_traza(con_contexto):
    """El modelo escribe `F7` porque un numero pelado es ingramatico para el -asi no puede copiar
    el `45.` de una pregunta de test-, pero de la frontera hacia dentro todo sigue con el id real."""
    app.state.cliente_inferencia = ClienteFalso(en_trozos(CON_CITA, tam=8))
    app.state.embebedor = None
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x"}))
    datos = [d for n, d in ev if n == "afirmaciones"][0]
    assert [a["fragmento_id"] for a in datos["afirmaciones"]] == [7, 7, 999]
