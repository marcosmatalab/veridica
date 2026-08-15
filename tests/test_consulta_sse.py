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
    # EL PRIMERO PASA A SER `modo` EL 15/08/2026, y va delante a propósito: es lo único del flujo
    # que no depende de nada más que del turno recién escrito, y un modo que llegara al final ya no
    # se podría cambiar sin haberse leído entera la respuesta equivocada. Lo que este test protege
    # —que lo primero NO sea la respuesta— sigue en pie con la etapa detrás.
    assert nombres[0] == "modo", "el modo elegido se enseña antes que nada"
    assert nombres[1] == "etapa", "lo primero que llega es una etapa real, no la respuesta"
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
    # `recuperacion.construido` es un hecho DE ESTA CONSULTA -aqui el embebedor esta apagado a
    # proposito, asi que se respondio sin fragmentos- y sigue siendo False con razon.
    assert resp["etapas"]["recuperacion"]["construido"] is False
    # `verificacion.construido`, en cambio, era una CAPACIDAD, y desde el 4.5 vale True: hasta el
    # 2.5 se persistia False en todas las respuestas mientras las cuatro capas corrian. Un `false`
    # guardado se lee como una medida, asi que este test pasa a anclar lo contrario a proposito.
    assert resp["etapas"]["verificacion"]["construido"] is True
    assert resp["etapas"]["verificacion"]["solicitada_tiene_efecto"] is False


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
    """Las tres salidas del verificador, por el camino real del SSE y no llamando a la funcion.

    **El NLI se apaga a proposito**: desde el 4.4 una literal DEGRADADA sigue camino hacia el NLI y
    recibe un segundo veredicto, asi que con el puesto este test estaria mirando el final de la
    cadena en vez de la etapa literal, que es lo que dice comprobar."""
    app.state.cliente_inferencia = ClienteFalso(en_trozos(CON_CITA, tam=8))
    app.state.embebedor = None
    app.state.nli = None
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x"}))
    por_id = {d["id_en_contrato"]: d for n, d in ev if n == "veredicto"}

    assert set(por_id) == {1, 2, 3}
    assert por_id[3]["veredicto"] == "podada", "una procedencia inventada no se podo"
    assert por_id[3]["motivo"] == "procedencia_fabricada"
    assert por_id[2]["veredicto"] == "degradada_a_parafrasis"
    assert all(d["durante_la_redaccion"] for d in por_id.values())


CON_CALCULO = {
    "modo": "corregir",
    "afirmaciones": [
        {"id": 1, "tipo": "calculo", "texto": "En esa subred caben 62 equipos.",
         "fragmento_id": "F7", "expresion": "2**6-2", "resultado_afirmado": "62"},
        {"id": 2, "tipo": "calculo", "texto": "Y en la anterior, 30.",
         "fragmento_id": None, "expresion": "2**5-2", "resultado_afirmado": "31"},
        {"id": 3, "tipo": "calculo", "texto": "El script imprime diez lineas.",
         "fragmento_id": None, "expresion": "for i in range(10): print(i)",
         "resultado_afirmado": "10"},
    ],
    "respuesta_redactada": "En esa subred caben 62 equipos y en la anterior 30.",
    "siguiente_paso": {"tipo": "pregunta_al_alumno", "texto": "Cuantos bits quedan?"},
}


def test_el_calculo_se_verifica_por_el_camino_REAL_del_sse_y_no_llamando_a_la_funcion(con_contexto):
    """El 4.4 enchufado donde va: en el mismo hueco que el literal, mientras el modelo escribe.

    Los tres casos que importan, y el tercero es el que se cuela solo: un cálculo correcto pasa, uno
    incorrecto poda, y **código sale `no_verificable`, no podado** — porque el sandbox está declarado
    y no construido, así que podarlo castigaría al modelo por una capacidad que no construimos."""
    app.state.cliente_inferencia = ClienteFalso(en_trozos(CON_CALCULO, tam=8))
    app.state.embebedor = None
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x", "modo": "corregir"}))
    por_id = {d["id_en_contrato"]: d for n, d in ev if n == "veredicto"}

    assert set(por_id) == {1, 2, 3}, "no salio un veredicto por cada calculo"
    assert por_id[1]["veredicto"] == "verificada"
    assert por_id[2]["veredicto"] == "podada" and por_id[2]["motivo"] == "resultado_no_coincide"
    assert por_id[3]["veredicto"] == "no_verificable", "el codigo se podo en vez de declararse"
    assert all(d["tipo"] == "calculo" for d in por_id.values())
    assert all(d["durante_la_redaccion"] for d in por_id.values())


def test_la_referencia_del_modelo_lleva_F_y_vuelve_a_ser_NUMERO_en_la_traza(con_contexto):
    """El modelo escribe `F7` porque un numero pelado es ingramatico para el -asi no puede copiar
    el `45.` de una pregunta de test-, pero de la frontera hacia dentro todo sigue con el id real."""
    app.state.cliente_inferencia = ClienteFalso(en_trozos(CON_CITA, tam=8))
    app.state.embebedor = None
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x"}))
    datos = [d for n, d in ev if n == "afirmaciones"][0]
    assert [a["fragmento_id"] for a in datos["afirmaciones"]] == [7, 7, 999]


# --- el respaldo lexico y la degradacion de la recuperacion (encargo 4.4) --------------------------

def test_sin_embebedor_se_RECUPERA_POR_LEXICA_en_vez_de_no_recuperar(cliente_http, monkeypatch):
    """EL ARREGLO QUE SALIÓ DE REVISAR `/salud`. Hasta el 4.4, `embebedor is None` devolvía **cero
    fragmentos**: el sistema respondía de memoria, que es exactamente lo que dice no ser. Y no era
    una consecuencia técnica —`recuperar()` acepta `vector=None` desde el 3.3 y hace léxica y
    glosario—: es que nadie escribió el respaldo.

    Con él, quedarse sin torch es **degradación anunciada** —se recupera peor, y el 3.1 midió cuánto:
    58 % frente al 80,9 %— en vez de una caída disfrazada de respuesta."""
    from app.api import consulta as mod
    llamadas = []
    monkeypatch.setattr(mod, "recuperar",
                        lambda url, aid, texto, **kw: llamadas.append(kw.get("vector", "AUSENTE")) or [])
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    app.state.embebedor = None
    ev = eventos(cliente_http.post("/consulta", json={"texto": "x", "asignatura_id": 29}))

    assert llamadas, "sin embebedor no se busco NADA: el respaldo lexico no esta"
    assert llamadas[0] is None, "se paso un vector sin embebedor"
    nombres = [n for n, _ in ev]
    assert "etapa" in nombres
    etapas = [d.get("nombre") for n, d in ev if n == "etapa"]
    assert "sin_embebedor" in etapas, "la degradacion no se anuncia, y anunciarla es la mitad"


def test_una_recuperacion_que_REVIENTA_degrada_en_vez_de_tumbar_la_peticion(cliente_http,
                                                                            monkeypatch):
    """La otra cara del respaldo: ahora esta ruta **toca la base**, así que puede fallar donde antes
    no podía. Una base caída no puede llevarse la petición con una excepción cruda a mitad del SSE —
    el alumno vería una frase cortada—: se responde sin fragmentos **y se dice**, que es lo mismo que
    hace el reordenador cuando no contesta."""
    from app.api import consulta as mod

    def revienta(*a, **k):
        raise RuntimeError("la base dijo que no")

    monkeypatch.setattr(mod, "recuperar", revienta)
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    app.state.embebedor = None
    ev = eventos(cliente_http.post("/consulta", json={"texto": "x", "asignatura_id": 29}))

    assert [n for n, _ in ev if n == "token"], "la peticion no llego a responder"
    etapas = [d.get("nombre") for n, d in ev if n == "etapa"]
    assert "sin_recuperacion" in etapas
    detalle = app.state.traza.respuestas[-1]["etapas"]["recuperacion"]
    assert "la base dijo que no" in json.dumps(detalle, ensure_ascii=False), \
        "el motivo del fallo no llego a la traza: se perdio la causa"


# --- el NLI del 4.3, ENCHUFADO en el 4.4 ----------------------------------------------------------

CON_PARAFRASIS = {
    "modo": "responder",
    "afirmaciones": [
        {"id": 1, "tipo": "parafrasis", "texto": "La sesion se guarda en el servidor.",
         "fragmento_id": "F7"},
        {"id": 2, "tipo": "literal", "texto": "Esto no esta.", "fragmento_id": "F7",
         "cita": "esta frase no aparece en ningun sitio"},
        {"id": 3, "tipo": "parafrasis", "texto": "Procedencia inventada.", "fragmento_id": "F999"},
    ],
    "respuesta_redactada": "La sesion se guarda en el servidor y la cookie lleva solo el id.",
    "siguiente_paso": {"tipo": "pregunta_al_alumno", "texto": "Y la cookie?"},
}


class NLIFalso:
    """Un NLI de mentira: el de verdad son 279 M de parametros y estos tests son del ENCHUFE.

    Registra lo que se le pregunta, que es justo lo que hay que comprobar: a QUE afirmaciones se
    llama y con que premisa."""

    dispositivo, umbral = "cpu", 0.8

    def __init__(self, veredicto="verificada"):
        self.pares = []
        self.veredicto = veredicto

    def verificar(self, hipotesis, fragmento, cita=None, apoyo=None):
        self.pares.append((hipotesis, fragmento))
        return {"veredicto": self.veredicto, "motivo": None, "nli": "entailment",
                "probabilidad": 0.97, "detalle": "el fragmento sostiene la afirmacion"}


def test_la_PARAFRASIS_recibe_su_veredicto_del_nli_por_el_camino_real(con_contexto):
    """LO QUE ESTE ENCARGO ARREGLA. El 4.3 dejó el verificador construido, con sus tests, y **nadie
    lo llamaba**: toda afirmación `parafrasis` salía `sin_verificar`, o sea que el sistema comprobaba
    lo que se copiaba y no lo que se reformulaba — la mitad difícil de la tesis."""
    nli = NLIFalso()
    app.state.cliente_inferencia = ClienteFalso(en_trozos(CON_PARAFRASIS, tam=8))
    app.state.embebedor = None
    app.state.nli = nli
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x"}))
    por_id = {d["id_en_contrato"]: d for n, d in ev if n == "veredicto"}

    assert 1 in por_id, "la parafrasis salio SIN veredicto: el NLI no esta enchufado"
    assert por_id[1]["veredicto"] == "verificada" and por_id[1]["nli"] == "entailment"


def test_la_LITERAL_DEGRADADA_tambien_pasa_por_el_nli(con_contexto):
    """El circuito que el 4.2 dejó abierto: una cita que no aparece letra a letra **se degrada a
    paráfrasis**, y esa degradación no significaba nada mientras nadie la recogiera. Ahora la
    recoge."""
    nli = NLIFalso()
    app.state.cliente_inferencia = ClienteFalso(en_trozos(CON_PARAFRASIS, tam=8))
    app.state.embebedor = None
    app.state.nli = nli
    eventos(con_contexto.post("/consulta", json={"texto": "x"}))
    hipotesis = [h for h, _ in nli.pares]
    assert "Esto no esta." in hipotesis, "la literal degradada no llego al NLI"


def test_una_parafrasis_con_procedencia_INVENTADA_no_se_juzga_se_poda(con_contexto):
    """La misma puerta que el 4.2, y va ANTES de preguntarle al modelo: si el fragmento no estuvo en
    el contexto no hay premisa que valga, y darle al NLI 'la mejor disponible' es pedirle un falso
    positivo confiado."""
    nli = NLIFalso()
    app.state.cliente_inferencia = ClienteFalso(en_trozos(CON_PARAFRASIS, tam=8))
    app.state.embebedor = None
    app.state.nli = nli
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x"}))
    por_id = {d["id_en_contrato"]: d for n, d in ev if n == "veredicto"}
    assert por_id[3]["veredicto"] == "podada" and por_id[3]["motivo"] == "procedencia_fabricada"
    assert all("Procedencia inventada." != h for h, _ in nli.pares), "se le pregunto igualmente"


def test_sin_nli_la_respuesta_sale_igual_y_la_parafrasis_queda_sin_verificar(con_contexto):
    """Degradación declarada: sin torch no hay NLI, y entonces se responde igual pero la paráfrasis
    NO se verifica. Que sea aceptable no lo decide este módulo; que se sepa, sí."""
    app.state.cliente_inferencia = ClienteFalso(en_trozos(CON_PARAFRASIS, tam=8))
    app.state.embebedor = None
    app.state.nli = None
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x"}))
    assert [n for n, _ in ev if n == "token"], "sin NLI la respuesta tiene que salir igual"
    por_id = {d["id_en_contrato"]: d for n, d in ev if n == "veredicto"}
    assert 1 not in por_id, "hay veredicto de parafrasis sin NLI cargado"


def test_una_literal_degradada_recibe_DOS_veredictos_y_el_bueno_es_el_ultimo(con_contexto):
    """Comportamiento nuevo del 4.4 y hay que declararlo: una `literal` cuya cita no aparece letra a
    letra emite **dos** eventos —primero `degradada_a_parafrasis` del 4.2, después el del NLI—, y el
    que vale es el segundo. No es ruido: es la cadena de verificación enseñándose a sí misma, que es
    lo que el alumno tiene que poder ver."""
    nli = NLIFalso()
    app.state.cliente_inferencia = ClienteFalso(en_trozos(CON_PARAFRASIS, tam=8))
    app.state.embebedor = None
    app.state.nli = nli
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x"}))
    del_dos = [d for n, d in ev if n == "veredicto" and d["id_en_contrato"] == 2]
    assert len(del_dos) == 2, f"se esperaban dos veredictos para la literal degradada: {del_dos}"
    assert del_dos[0]["veredicto"] == "degradada_a_parafrasis"
    assert del_dos[1]["veredicto"] == "verificada"


def test_un_veredicto_que_pide_REINTENTO_dice_que_no_lo_tiene(con_contexto):
    """La sección 8 manda que `neutral` dispare el reintento único con la señal. **Verificar en curso
    se lo come**: cuando el NLI contesta, la prosa ya está en pantalla y repetirla sería reescribirle
    al alumno lo que acaba de leer. Es el precio del solape, y va DICHO en el evento — si no, la tasa
    de `neutral` del 4.6 se leería como "se reintentó y siguió mal", que es otra cosa."""
    nli = NLIFalso(veredicto="reintento_con_señal")
    app.state.cliente_inferencia = ClienteFalso(en_trozos(CON_PARAFRASIS, tam=8))
    app.state.embebedor = None
    app.state.nli = nli
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x"}))
    uno = [d for n, d in ev if n == "veredicto" and d["id_en_contrato"] == 1][-1]
    assert uno["veredicto"] == "reintento_con_señal"
    assert uno["reintento_disponible"] is False
    assert "ya estaba en pantalla" in uno["por_que_no"]


SIN_RESPALDO = {
    "modo": "responder",
    "afirmaciones": [
        {"id": 1, "tipo": "parafrasis", "texto": "La sesion vive en el servidor.",
         "fragmento_id": "F7"},
    ],
    "respuesta_redactada": "El teorema de Pitagoras relaciona los catetos con la hipotenusa.",
    "siguiente_paso": {"tipo": "pregunta_al_alumno", "texto": "Y la cookie?"},
}


PROSA_VACIA = {**SIN_RESPALDO, "respuesta_redactada": "   \n  "}


def test_UNA_PANTALLA_EN_BLANCO_ES_UNA_ABSTENCION_y_no_una_respuesta_entregada(con_contexto):
    """EL PEOR RESULTADO QUE ESTE SISTEMA PUEDE DAR, y hasta el 14/08/2026 lo daba en silencio: el
    alumno veía una pantalla en blanco sin explicación **y la métrica lo contaba como entregado**.
    Mentía en las dos direcciones a la vez, y la mentira a la métrica es la peor porque se acumula.

    **EL DISPARADOR CAMBIÓ Y ESTE TEST CON ÉL, a propósito.** Nació cazando el caso *"el portero
    podó todas las frases"*; desde que el portero **marca**, ese caso ya no existe —la prosa llega
    entera, señalada—. Pero el resultado que el test protege **sí sigue existiendo**: el modelo
    puede cumplir el contrato y devolver una redacción vacía. Si al cambiar el mecanismo se hubiera
    retirado la rama en vez de re-condicionarla, la pantalla en blanco habría vuelto sin declarar,
    que es exactamente el fallo que costó medio día encontrar.
    """
    app.state.cliente_inferencia = ClienteFalso(en_trozos(PROSA_VACIA, tam=8))
    app.state.embebedor = None
    app.state.nli = None
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x"}))

    visible = "".join(d["t"] for n, d in ev if n == "token").strip()
    assert visible == "", "el fixture ya no prueba lo que dice: algo se enseño"
    abst = [d for n, d in ev if n == "abstencion"]
    assert abst, "pantalla en blanco y NINGUNA abstencion: se cuenta como respuesta entregada"
    assert abst[0]["por_prosa_vacia"] is True
    assert "sin_prosa" in abst[0]["motivo"]
    assert [d for n, d in ev if n == "fin"][0]["abstencion"] is True
    assert app.state.traza.respuestas[-1]["abstencion"] is True


def test_la_prosa_SIN_RESPALDO_ya_no_abstiene_SE_ENSENA_MARCADA(con_contexto):
    """LA OTRA MITAD DEL CAMBIO, y la que impide que el test de arriba se cumpla por el motivo
    equivocado. El mismo caso que ANTES abstenía —redacción que ninguna afirmación respalda— ahora
    tiene que llegar al alumno, marcada, y la respuesta cuenta como entregada: el umbral dejó de
    decidir SI se ve algo y pasó a decidir CÓMO se ve."""
    app.state.cliente_inferencia = ClienteFalso(en_trozos(SIN_RESPALDO, tam=8))
    app.state.embebedor = None
    app.state.nli = None
    ev = eventos(con_contexto.post("/consulta", json={"texto": "x"}))

    tokens = [d for n, d in ev if n == "token"]
    assert tokens, "la prosa sin respaldo desaparecio: el portero sigue podando"
    assert all(t["respaldada"] is False for t in tokens), "llego SIN marca, que es el error caro"
    assert "Pitagoras" in "".join(t["t"] for t in tokens)
    assert not [d for n, d in ev if n == "abstencion"], \
        "abstenerse con texto util en pantalla es esconder que el modelo lo dijo"
    cobertura = [d for n, d in ev if n == "cobertura"]
    assert cobertura and cobertura[0]["frases_marcadas"] >= 1
    assert app.state.traza.respuestas[-1]["abstencion"] is False


def test_una_frase_QUE_CITA_SU_FRAGMENTO_no_se_poda_por_citarlo(con_contexto):
    """REGRESIÓN DEL CASO QUE OBLIGÓ A ARREGLAR LA MEDIDA. *"…, según el fragmento F5962 del
    temario"* se podaba porque `según`, `fragmento` y `temario` no están en ninguna afirmación — no
    pueden estarlo, son la referencia a la fuente—. **El sistema castigaba a la prosa por citar su
    procedencia**, que es el comportamiento que el proyecto premia."""
    from app.core.cobertura import PorteroDeFrases
    afs = [{"id": 1, "tipo": "parafrasis",
            "texto": "En jornada continua de mas de 6 horas el descanso minimo es de 15 minutos."}]
    con_cita = ("En una jornada continua de 7 horas, el descanso minimo es de 15 minutos, "
                "segun el fragmento F5962 del temario.")
    # Desde el 14/08 el portero MARCA en vez de podar, asi que lo que se lee es la marca y no si la
    # frase sale: lo que el test protege -que citar la procedencia no penalice- es lo mismo.
    assert PorteroDeFrases(afs).alimentar(con_cita)[0]["respaldada"] is True, \
        "se marco una frase por citar su procedencia"
    # LA OTRA MITAD, y hubo que corregir el test antes que el codigo: una frase de PURO relleno
    # meta no afirma nada del mundo, asi que dejarla pasar no es un agujero. El agujero seria que
    # citar la fuente sirviera para COLAR una afirmacion no respaldada, y eso sigue sin pasar:
    # quitado el vocabulario meta, las palabras de contenido se juzgan igual.
    colada = ("Segun el fragmento F7 del temario, la cookie guarda directamente la contrasena "
              "cifrada del usuario.")
    assert PorteroDeFrases(afs).alimentar(colada)[0]["respaldada"] is False, \
        "citar la fuente esta sirviendo para colar una afirmacion que nadie declaro"


# --- la cascada: fuera de asignatura se RESPONDE, no se deriva -----------------------------------
#
# EL ENCARGO, con la corrección del propietario dentro: hasta hoy el sistema decía "esto no está
# aquí, está en Bases de datos" y se quedaba ahí. Eso es **un muro con buenos modales**: obliga al
# alumno a cambiar de asignatura y repreguntar. Ahora se responde desde el resto de la titulación,
# verificado contra ESE fragmento, y diciendo de dónde sale.

class EmbebedorFalso:
    def embeber(self, texto):
        return [0.1] * 8


class CatalogoDeDos:
    """Dos asignaturas de la misma titulación. `asignaturas()` es lo único que la cascada usa."""

    def asignaturas(self, titulacion):
        return [{"id": 29, "nombre": "Bases de datos"}, {"id": 7, "nombre": "Programación"}]


def _candidato(fid, aid):
    from app.core.recuperacion import Candidato
    return Candidato(fragmento_id=fid, asignatura_id=aid, documento="corpus/x/y.md", orden=1,
                     unidad="Unidad 3", texto="una clave primaria identifica cada fila",
                     puntuacion=0.5, origen="vectorial")


@pytest.fixture
def cascada(cliente_http, monkeypatch):
    """Monta las dos vueltas: en la asignatura 7 no hay nada bueno, en la 29 sí."""
    from app.api import consulta as mod
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    app.state.embebedor = EmbebedorFalso()
    app.state.catalogo = CatalogoDeDos()
    monkeypatch.setattr(mod, "recuperar",
                        lambda url, aid, texto, **kw: [_candidato(1, 7)] if aid == 7
                        else [_candidato(99, 29)])
    monkeypatch.setattr(mod, "buscar_vectorial", lambda url, aid, v, **kw: [])
    return mod


def test_si_no_hay_material_aqui_se_responde_desde_OTRA_asignatura_de_la_titulacion(cascada,
                                                                                    cliente_http,
                                                                                    monkeypatch):
    # primera vuelta baja, segunda alta: la cascada tiene que adoptar la segunda
    niveles = iter([("baja", {}), ("alta", {})])
    monkeypatch.setattr(cascada, "confianza_de", lambda v: next(niveles))
    ev = eventos(cliente_http.post("/consulta", json={"texto": "x", "asignatura_id": 7,
                                                      "titulacion": "daw"}))
    etapas = {d.get("nombre"): d for n, d in ev if n == "etapa"}
    assert "segunda_recuperacion" in etapas, "no se buscó en el resto de la titulación"
    assert etapas["segunda_recuperacion"]["confianza_antes"] == "baja"
    assert etapas["segunda_recuperacion"]["confianza_despues"] == "alta"
    fragmentos = etapas["fragmentos_recuperados"]["fragmentos"]
    assert [f["id"] for f in fragmentos] == [99], "se sirvió el material pobre de la elegida"


def test_y_LA_PROCEDENCIA_VIAJA_con_el_fragmento_porque_es_la_mitad_del_cambio(cascada,
                                                                               cliente_http,
                                                                               monkeypatch):
    """Responder sin decir de dónde sale sería media reforma: el alumno tiene que poder leer
    *«esto es de Bases de datos, que también cursas»* sin abrir la traza."""
    niveles = iter([("baja", {}), ("alta", {})])
    monkeypatch.setattr(cascada, "confianza_de", lambda v: next(niveles))
    ev = eventos(cliente_http.post("/consulta", json={"texto": "x", "asignatura_id": 7,
                                                      "titulacion": "daw"}))
    fragmentos = [d for n, d in ev if n == "etapa"
                  and d.get("nombre") == "fragmentos_recuperados"][0]["fragmentos"]
    assert fragmentos[0]["asignatura"] == "Bases de datos"


def test_el_fragmento_de_TU_asignatura_no_lleva_etiqueta_de_procedencia(cascada, cliente_http,
                                                                        monkeypatch):
    """La otra dirección, y es la que evita el ruido: *«de Programación»* en una consulta de
    Programación no informa de nada. Sin este test, poner la etiqueta SIEMPRE pasaría el de arriba."""
    monkeypatch.setattr(cascada, "confianza_de", lambda v: ("alta", {}))
    ev = eventos(cliente_http.post("/consulta", json={"texto": "x", "asignatura_id": 7,
                                                      "titulacion": "daw"}))
    fragmentos = [d for n, d in ev if n == "etapa"
                  and d.get("nombre") == "fragmentos_recuperados"][0]["fragmentos"]
    assert "asignatura" not in fragmentos[0]


def test_con_material_AQUI_no_se_va_a_buscar_fuera(cascada, cliente_http, monkeypatch):
    """La cascada es un respaldo, no una ampliación del alcance: si la asignatura elegida responde,
    no se toca el resto de la titulación — ni se paga su coste."""
    monkeypatch.setattr(cascada, "confianza_de", lambda v: ("media", {}))
    ev = eventos(cliente_http.post("/consulta", json={"texto": "x", "asignatura_id": 7,
                                                      "titulacion": "daw"}))
    etapas = [d.get("nombre") for n, d in ev if n == "etapa"]
    assert "segunda_recuperacion" not in etapas


def test_el_EMPATE_se_resuelve_a_favor_de_la_asignatura_que_el_alumno_eligio(cascada, cliente_http,
                                                                             monkeypatch):
    """Traer material de al lado hace falta justificarlo, no empatarlo: el alumno preguntó aquí.
    Sin este test, un `>=` en vez de `>` pasaría todos los demás."""
    monkeypatch.setattr(cascada, "confianza_de", lambda v: ("baja", {}))
    ev = eventos(cliente_http.post("/consulta", json={"texto": "x", "asignatura_id": 7,
                                                      "titulacion": "daw"}))
    etapas = [d.get("nombre") for n, d in ev if n == "etapa"]
    assert "segunda_recuperacion" not in etapas, "un empate adoptó la otra asignatura"


def test_sin_titulacion_la_cascada_no_puede_correr_y_no_lo_finge(cascada, cliente_http,
                                                                 monkeypatch):
    """Una asignatura transversal vive en varias titulaciones, así que deducirla del `asignatura_id`
    daría la equivocada justo en las que más se comparten. Sin `titulacion` no hay cascada, y eso es
    correcto: mejor no hacerla que hacerla contra el conjunto de otro."""
    monkeypatch.setattr(cascada, "confianza_de", lambda v: ("baja", {}))
    ev = eventos(cliente_http.post("/consulta", json={"texto": "x", "asignatura_id": 7}))
    etapas = [d.get("nombre") for n, d in ev if n == "etapa"]
    assert "segunda_recuperacion" not in etapas


# --- la puente no se cruza: la asignatura tiene que ser de la titulacion elegida -----------------

class CatalogoDeTitulaciones:
    def asignaturas(self, titulacion):
        return {"daw": [{"id": 29, "nombre": "Bases de datos"}],
                "asir": [{"id": 1, "nombre": "Implantación de Sistemas Operativos"}]}[titulacion]


def test_una_asignatura_de_OTRA_titulacion_se_rechaza_en_el_servidor(cliente_http):
    """EL FALLO QUE ESTO CIERRA, y lo vio el propietario mirando la pantalla: si el desplegable de
    asignaturas no se repuebla al cambiar de titulación —por un fallo de red en esa petición, por
    una carrera entre dos cambios seguidos, o por un `curl` a mano— llega un par cruzado y **la
    consulta se responde igual**, con material de una titulación que el alumno no cursa, y la traza
    lo registra como una consulta normal. Contaminación entre titulaciones **sin una sola línea
    roja**.

    El navegador tiene ahora sus dos guardas, pero una promesa del cliente no es una garantía: la
    que no depende de nadie es esta."""
    app.state.catalogo = CatalogoDeTitulaciones()
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    r = cliente_http.post("/consulta", json={"texto": "x", "asignatura_id": 1,
                                             "titulacion": "daw"})
    assert r.status_code == 400
    assert "no pertenece" in r.json()["detail"]


def test_el_par_CORRECTO_pasa_sin_estorbar(cliente_http):
    """La otra dirección, que es la que dice si la guarda sirve o solo molesta: sin ella, un rechazo
    a todo pasaría el test de arriba igual de bien."""
    app.state.catalogo = CatalogoDeTitulaciones()
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    r = cliente_http.post("/consulta", json={"texto": "x", "asignatura_id": 29,
                                             "titulacion": "daw"})
    assert r.status_code == 200


def test_sin_titulacion_no_se_inventa_un_rechazo(cliente_http):
    """Una petición sin `titulacion` es legítima —el campo nace hoy y hay clientes que no lo
    mandan—: no hay nada que comprobar, así que no se rechaza. Rechazar por no poder comprobar
    convertiría una guarda en una avería."""
    app.state.catalogo = CatalogoDeTitulaciones()
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    assert cliente_http.post("/consulta", json={"texto": "x", "asignatura_id": 1}).status_code == 200
