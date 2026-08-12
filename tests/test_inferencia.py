"""La politica del cliente de inferencia (encargo 2.2).

Lo que se prueba aqui no es que sepa hablar HTTP: es que sepa CUANDO callarse. Un cliente que
reintenta lo que no debe factura de mas y tarda de mas; uno que reintenta a media respuesta le
repite el texto al alumno en pantalla. Las dos cosas son silenciosas si nadie las prueba.

Ni un solo test de este fichero llama al proveedor: el transporte esta simulado. La llamada real
vive en scripts/humo_proveedor.py, que gasta dinero y por eso no esta en la puerta.
"""
import httpx
import pytest

from app.core.inferencia import (Ajustes, ClienteInferencia, ErrorDefinitivo, ErrorTransitorio,
                                 Llamada)

CLAVE = "clave-secreta-que-no-debe-salir"


def ajustes(**extra) -> Ajustes:
    return Ajustes(base_url="https://api.ejemplo.ai/proyecto-1234/v1", api_key=CLAVE,
                   modelo="modelo-pequeno", espera_base=0.0, **extra)


def sse(*textos, uso=(11, 22)) -> bytes:
    lineas = []
    for t in textos:
        lineas.append('data: {"choices":[{"delta":{"content":"%s"},"finish_reason":null}]}' % t)
    lineas.append('data: {"choices":[{"delta":{},"finish_reason":"stop"}],'
                  '"usage":{"prompt_tokens":%d,"completion_tokens":%d}}' % uso)
    lineas.append("data: [DONE]")
    return ("\n\n".join(lineas) + "\n\n").encode()


def cliente_con(manejador) -> ClienteInferencia:
    return ClienteInferencia(ajustes(), httpx.Client(transport=httpx.MockTransport(manejador)))


def test_la_url_base_se_usa_entera_y_solo_se_le_anade_el_camino_del_endpoint():
    """La URL de Scaleway lleva el identificador de proyecto dentro. Componerla a trozos es apuntar
    a otro sitio el dia que cambie el proyecto."""
    a = ajustes()
    assert a.url == "https://api.ejemplo.ai/proyecto-1234/v1/chat/completions"
    b = Ajustes(base_url="https://api.ejemplo.ai/proyecto-1234/v1/", api_key="x", modelo="m")
    assert b.url == "https://api.ejemplo.ai/proyecto-1234/v1/chat/completions"


def test_lo_que_se_mide_va_a_temperatura_cero_y_con_semilla():
    cuerpo = ClienteInferencia(ajustes(), httpx.Client()).cuerpo([{"role": "user", "content": "x"}])
    assert cuerpo["temperature"] == 0.0
    assert cuerpo["seed"] and cuerpo["max_tokens"]
    # Sin esto, un flujo no trae el conteo de tokens y la corrida se queda sin coste.
    assert cuerpo["stream_options"] == {"include_usage": True}


def test_un_429_se_reintenta_y_a_la_segunda_sale():
    intentos = {"n": 0}

    def manejador(peticion):
        intentos["n"] += 1
        if intentos["n"] == 1:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, content=sse("hola"))

    cli = cliente_con(manejador)
    traza = Llamada()
    texto = "".join(t.texto for t in cli.stream([{"role": "user", "content": "x"}], traza=traza))
    assert texto == "hola"
    assert intentos["n"] == 2 and traza.intentos == 2


@pytest.mark.parametrize("codigo", [400, 401, 403, 404, 422])
def test_un_error_de_contrato_o_de_credencial_no_se_reintenta_jamas(codigo):
    """Repetir la misma peticion mal formada con la misma clave mala da el mismo error tres veces,
    mas lento. El 401 es ademas el que se ve en rojo a proposito en el flujo del proveedor."""
    intentos = {"n": 0}

    def manejador(peticion):
        intentos["n"] += 1
        return httpx.Response(codigo, text="no")

    cli = cliente_con(manejador)
    with pytest.raises(ErrorDefinitivo):
        list(cli.stream([{"role": "user", "content": "x"}]))
    assert intentos["n"] == 1, f"un {codigo} se reintento: {intentos['n']} llamadas"


def test_agotados_los_intentos_el_transitorio_sale_como_lo_que_es():
    intentos = {"n": 0}

    def manejador(peticion):
        intentos["n"] += 1
        return httpx.Response(503, text="caido")

    cli = cliente_con(manejador)
    with pytest.raises(ErrorTransitorio):
        list(cli.stream([{"role": "user", "content": "x"}]))
    assert intentos["n"] == 3


def test_si_ya_salio_el_primer_caracter_no_se_reintenta():
    """LA REGLA QUE NO ES DE CODIGO SINO DE HONESTIDAD. Un reintento a media respuesta le repetiria
    al alumno el texto que acaba de leer. Lo reintentable es la llamada que aun no ha escrito nada.
    """
    intentos = {"n": 0}

    class CorteAMedias(httpx.SyncByteStream):
        def __iter__(self):
            yield b'data: {"choices":[{"delta":{"content":"ya he escrito esto"}}]}\n\n'
            raise httpx.ReadError("se corto la conexion")

    def manejador(peticion):
        intentos["n"] += 1
        return httpx.Response(200, stream=CorteAMedias())

    cli = cliente_con(manejador)
    salida = []
    with pytest.raises(ErrorTransitorio):
        for trozo in cli.stream([{"role": "user", "content": "x"}]):
            salida.append(trozo.texto)
    assert salida == ["ya he escrito esto"]
    assert intentos["n"] == 1, "reintento despues de haber emitido: el alumno veria el texto dos veces"


def test_la_clave_no_aparece_en_el_mensaje_de_error():
    """Un proveedor que devuelve la peticion en el cuerpo del error, o una traza que se pega en un
    issue, son las dos formas normales de filtrar una credencial sin querer."""
    def manejador(peticion):
        return httpx.Response(400, text=f"bad request con Authorization: Bearer {CLAVE}")

    cli = cliente_con(manejador)
    with pytest.raises(ErrorDefinitivo) as e:
        list(cli.stream([{"role": "user", "content": "x"}]))
    assert CLAVE not in str(e.value)
    assert "***" in str(e.value)


def test_el_uso_llega_y_el_coste_sale_de_las_variables_de_entorno(monkeypatch):
    def manejador(peticion):
        return httpx.Response(200, content=sse("a", "b", uso=(1000, 2000)))

    cli = cliente_con(manejador)
    trozos = list(cli.stream([{"role": "user", "content": "x"}]))
    uso = [t.uso for t in trozos if t.uso][-1]
    assert (uso.tokens_entrada, uso.tokens_salida) == (1000, 2000)
    monkeypatch.setenv("PRECIO_ENTRADA_PEQ", "0.15")
    monkeypatch.setenv("PRECIO_SALIDA_PEQ", "0.35")
    assert uso.coste_eur() == pytest.approx((1000 * 0.15 + 2000 * 0.35) / 1_000_000)
    monkeypatch.delenv("PRECIO_ENTRADA_PEQ")
    assert uso.coste_eur() is None, "sin precios, el coste es un hueco declarado y no un cero"


def test_sin_variables_de_entorno_el_cliente_no_arranca_a_medias(monkeypatch):
    for v in ("INFERENCIA_BASE_URL", "INFERENCIA_API_KEY", "MODELO_PEQUENO"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(ErrorDefinitivo) as e:
        Ajustes.desde_entorno()
    assert "INFERENCIA_BASE_URL" in str(e.value)
