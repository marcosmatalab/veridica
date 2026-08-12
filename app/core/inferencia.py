"""Cliente único de inferencia, con interfaz OpenAI-compatible (encargo 2.2).

Es el enchufe del principio 1: cambiar de Scaleway a un vLLM local o a un pool de producción es
cambiar `INFERENCIA_BASE_URL`, no tocar código. Por eso hay UN cliente y todo pasa por aquí.

**LA URL BASE SE LEE ENTERA Y NO SE CONSTRUYE.** La de Scaleway lleva el identificador de proyecto
dentro (`https://api.scaleway.ai/<id-de-proyecto>/v1`), así que cualquier intento de componerla a
partir de trozos —host por un lado, proyecto por otro— acaba apuntando a otro sitio el día que
cambie el proyecto. Lo único que este módulo añade es el camino del endpoint (`/chat/completions`),
que es parte de la interfaz OpenAI, no del despliegue.

**Sin SDK, con `httpx` a pelo**, y no por purismo: el SDK oficial trae su propia política de
reintentos, que pelearía con la de aquí abajo y volvería imposible responder a "cuántas llamadas se
hicieron de verdad". Un cliente que reintenta por su cuenta es un cliente que factura por su cuenta.

REINTENTOS: retroceso exponencial con jitter y **solo en transitorios** (429, 5xx, timeout, corte de
red). Un 400 de contrato o un 401 de credencial no se reintentan jamás: repetir la misma petición
mal formada con la misma clave mala da el mismo error tres veces, más lento y pagando el triple de
espera. Y hay un límite que no es de código sino de honestidad: **en cuanto ha salido el primer
carácter hacia el alumno, ya no se reintenta**, porque un reintento a media respuesta le repetiría
texto en pantalla. Lo que se puede reintentar es la llamada que aún no ha escrito nada.

TEMPERATURA 0, con un aviso escrito para quien lo lea luego: la documentación de Scaleway recomienda
NO usar 0 porque puede encerrar al modelo repitiendo un token, y avisa de que eso pasa más con
salida tipada. Se usa 0 igualmente porque lo que se mide tiene que ser reproducible —medir con
muestreo aleatorio no es medir—, y el bucle degenerado se acota con `max_tokens`, que es un tope
duro: si ocurre, se paga hasta ahí y se ve en los tokens de la corrida, no en la factura del mes.
"""
import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Iterator

import httpx

CAMINO_CHAT = "/chat/completions"

#: Tope de tokens de salida, dimensionado CONTRA EL CONTRATO y no "generoso". Medido en llamadas
#: reales del 2.2: una respuesta del contrato con dos a cuatro afirmaciones ocupa entre 274 y 434
#: tokens de salida. 900 deja el doble del peor caso observado y corta en seco el bucle degenerado
#: que avisa la documentación del proveedor, que con temperatura 0 y salida tipada es el riesgo
#: real. Si ocurre, se paga hasta aquí y se ve en los tokens de la corrida (ADR 0009).
MAX_TOKENS_CONTRATO = 900

#: Semilla fija: la mitad de la petición de determinismo. La otra mitad es `temperatura=0`, y que
#: las dos juntas basten es cosa del servidor, no nuestra (se comprueba en scripts/humo_proveedor.py).
SEMILLA = 20260812

TRANSITORIOS = (408, 409, 429, 500, 502, 503, 504)


class ErrorDefinitivo(RuntimeError):
    """No tiene sentido reintentar: contrato mal formado, credencial mala, modelo inexistente."""


class ErrorTransitorio(RuntimeError):
    """Puede salir bien a la segunda: 429, 5xx, timeout, corte de red."""


@dataclass
class Ajustes:
    base_url: str
    api_key: str
    modelo: str
    temperatura: float = 0.0
    semilla: int = SEMILLA
    max_tokens: int = MAX_TOKENS_CONTRATO
    timeout_conexion: float = 10.0
    timeout_lectura: float = 60.0
    intentos: int = 3
    espera_base: float = 0.5

    @classmethod
    def desde_entorno(cls, grande: bool = False, **extra) -> "Ajustes":
        base = os.environ.get("INFERENCIA_BASE_URL", "").strip()
        clave = os.environ.get("INFERENCIA_API_KEY", "").strip()
        modelo = os.environ.get("MODELO_GRANDE" if grande else "MODELO_PEQUENO", "").strip()
        faltan = [n for n, v in (("INFERENCIA_BASE_URL", base), ("INFERENCIA_API_KEY", clave),
                                 ("MODELO_GRANDE" if grande else "MODELO_PEQUENO", modelo)) if not v]
        if faltan:
            raise ErrorDefinitivo(f"faltan variables de entorno: {', '.join(faltan)}")
        lectura = float(os.environ.get("TIMEOUT_ETAPA_MS") or 60000) / 1000
        return cls(base_url=base, api_key=clave, modelo=modelo, timeout_lectura=lectura, **extra)

    @property
    def url(self) -> str:
        return self.base_url.rstrip("/") + CAMINO_CHAT

    def tapar(self, texto: str) -> str:
        """Quita la clave de cualquier texto que vaya a un log, a una traza o a una excepción."""
        return texto.replace(self.api_key, "***") if self.api_key else texto


@dataclass
class Uso:
    """Lo que costó la llamada. Se anota SIEMPRE, aunque sean céntimos: la contabilidad del 2.6 se
    construye sumando líneas de estas, y una que falte no se puede reconstruir después."""

    tokens_entrada: int = 0
    tokens_salida: int = 0

    def coste_eur(self) -> float | None:
        """Precio del millón de tokens, de las variables de entorno. `None` si no están puestas: un
        coste inventado en un cuadro de costes es peor que un hueco declarado."""
        try:
            entrada = float(os.environ["PRECIO_ENTRADA_PEQ"])
            salida = float(os.environ["PRECIO_SALIDA_PEQ"])
        except (KeyError, ValueError):
            return None
        return (self.tokens_entrada * entrada + self.tokens_salida * salida) / 1_000_000


@dataclass
class Trozo:
    """Un evento del flujo: texto nuevo, o el cierre con el motivo y el gasto."""

    texto: str = ""
    fin: str | None = None
    uso: Uso | None = None


@dataclass
class Llamada:
    """Lo que hay que saber de una llamada después de hacerla, para la traza del 2.5."""

    intentos: int = 1
    esperas: list = field(default_factory=list)
    ttft_proveedor_ms: float | None = None


class ClienteInferencia:
    def __init__(self, ajustes: Ajustes, cliente: httpx.Client | None = None):
        self.a = ajustes
        self._propio = cliente is None
        self._http = cliente or httpx.Client(
            timeout=httpx.Timeout(connect=ajustes.timeout_conexion, read=ajustes.timeout_lectura,
                                  write=ajustes.timeout_conexion, pool=ajustes.timeout_conexion))

    def cerrar(self) -> None:
        if self._propio:
            self._http.close()

    # --- petición ---------------------------------------------------------------------------------

    def cuerpo(self, mensajes: list, response_format: dict | None = None,
               stream: bool = True) -> dict:
        cuerpo = {
            "model": self.a.modelo,
            "messages": mensajes,
            "temperature": self.a.temperatura,
            "seed": self.a.semilla,
            "max_tokens": self.a.max_tokens,
            "stream": stream,
        }
        if stream:
            # Sin esto, un flujo no trae el conteo de tokens y la corrida se queda sin coste.
            cuerpo["stream_options"] = {"include_usage": True}
        if response_format is not None:
            cuerpo["response_format"] = response_format
        return cuerpo

    @property
    def _cabeceras(self) -> dict:
        return {"Authorization": f"Bearer {self.a.api_key}", "Content-Type": "application/json"}

    # --- flujo ------------------------------------------------------------------------------------

    def stream(self, mensajes: list, response_format: dict | None = None,
               traza: Llamada | None = None) -> Iterator[Trozo]:
        """Emite `Trozo`s según llegan. Reintenta SOLO mientras no haya salido nada."""
        traza = traza if traza is not None else Llamada()
        cuerpo = self.cuerpo(mensajes, response_format, stream=True)
        for intento in range(1, self.a.intentos + 1):
            traza.intentos = intento
            emitido = False
            try:
                for trozo in self._un_intento(cuerpo, traza):
                    emitido = True
                    yield trozo
                return
            except ErrorTransitorio:
                if emitido or intento == self.a.intentos:
                    raise
                espera = self._espera(intento)
                traza.esperas.append(round(espera, 3))
                time.sleep(espera)

    def _un_intento(self, cuerpo: dict, traza: Llamada) -> Iterator[Trozo]:
        t0 = time.perf_counter()
        try:
            with self._http.stream("POST", self.a.url, json=cuerpo,
                                   headers=self._cabeceras) as r:
                if r.status_code != 200:
                    r.read()
                    self._levantar(r.status_code, r.text)
                for linea in r.iter_lines():
                    if not linea.startswith("data:"):
                        continue
                    dato = linea[5:].strip()
                    if dato == "[DONE]":
                        return
                    trozo = self._leer_evento(dato)
                    if trozo is None:
                        continue
                    if trozo.texto and traza.ttft_proveedor_ms is None:
                        traza.ttft_proveedor_ms = (time.perf_counter() - t0) * 1000
                    yield trozo
        except httpx.HTTPError as e:
            raise ErrorTransitorio(self.a.tapar(f"{type(e).__name__}: {e}")) from e

    def _leer_evento(self, dato: str) -> Trozo | None:
        try:
            evento = json.loads(dato)
        except json.JSONDecodeError:
            return None
        uso = None
        if evento.get("usage"):
            uso = Uso(tokens_entrada=evento["usage"].get("prompt_tokens", 0),
                      tokens_salida=evento["usage"].get("completion_tokens", 0))
        opciones = evento.get("choices") or []
        if not opciones:
            return Trozo(uso=uso) if uso else None
        delta = opciones[0].get("delta") or {}
        return Trozo(texto=delta.get("content") or "",
                     fin=opciones[0].get("finish_reason"), uso=uso)

    # --- sin flujo, para el humo y para el arnés ---------------------------------------------------

    def completar(self, mensajes: list, response_format: dict | None = None) -> tuple:
        """Devuelve (texto, Uso, Llamada). Misma política de reintentos, sin la regla del primer
        carácter: aquí no hay nada emitido hasta que la llamada termina."""
        traza = Llamada()
        cuerpo = self.cuerpo(mensajes, response_format, stream=False)
        for intento in range(1, self.a.intentos + 1):
            traza.intentos = intento
            t0 = time.perf_counter()
            try:
                r = self._http.post(self.a.url, json=cuerpo, headers=self._cabeceras)
                if r.status_code != 200:
                    self._levantar(r.status_code, r.text)
                datos = r.json()
                traza.ttft_proveedor_ms = (time.perf_counter() - t0) * 1000
                uso = Uso(tokens_entrada=(datos.get("usage") or {}).get("prompt_tokens", 0),
                          tokens_salida=(datos.get("usage") or {}).get("completion_tokens", 0))
                return datos["choices"][0]["message"]["content"], uso, traza
            except httpx.HTTPError as e:
                if intento == self.a.intentos:
                    raise ErrorTransitorio(self.a.tapar(f"{type(e).__name__}: {e}")) from e
            except ErrorTransitorio:
                if intento == self.a.intentos:
                    raise
            espera = self._espera(intento)
            traza.esperas.append(round(espera, 3))
            time.sleep(espera)
        raise ErrorTransitorio("agotados los intentos")

    # --- política ----------------------------------------------------------------------------------

    def _levantar(self, codigo: int, cuerpo: str) -> None:
        detalle = self.a.tapar((cuerpo or "")[:300])
        if codigo in TRANSITORIOS:
            raise ErrorTransitorio(f"HTTP {codigo}: {detalle}")
        raise ErrorDefinitivo(f"HTTP {codigo} (no se reintenta): {detalle}")

    def _espera(self, intento: int) -> float:
        """Retroceso exponencial con jitter completo: 0,5 s, 1 s, 2 s... por el tope, al azar dentro
        del tramo. El jitter no es adorno: sin él, N clientes que fallan a la vez vuelven a llamar a
        la vez y el 429 se repite exactamente igual."""
        return random.uniform(0, self.a.espera_base * (2 ** (intento - 1)))
