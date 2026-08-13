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
from datetime import datetime, timezone
from typing import Iterator

import httpx

CAMINO_CHAT = "/chat/completions"

#: Tope de tokens de salida, dimensionado CONTRA EL CONTRATO y no "generoso". Medido en llamadas
#: reales del 2.2: una respuesta del contrato con dos a cuatro afirmaciones ocupa entre 274 y 434
#: tokens de salida. 900 deja el doble del peor caso observado y corta en seco el bucle degenerado
#: que avisa la documentación del proveedor, que con temperatura 0 y salida tipada es el riesgo
#: real. Si ocurre, se paga hasta aquí y se ve en los tokens de la corrida (ADR 0009).
#:
#: **Y UN AVISO DEL BARRIDO DEL 13 DE AGOSTO, porque este tope es el ejemplo de manual de la regla:
#: 900 TOKENS NO SON UNA COTA DE TIEMPO.** Valen ~8,6 s a ritmo sano (105 tokens/s) y **225 s a los
#: 4 tokens/s medidos en el peor caso**: como cota del bucle degenerado sirve —el bucle escupe rápido
#: y llega al tope enseguida—, pero como protección del alumno **no sirve para nada**, y durante un
#: día fue lo único que había. Lo que acota el tiempo es el **plazo** de `app/api/consulta.py`, y este
#: número se queda donde está haciendo el trabajo para el que sí vale: acotar el GASTO.
MAX_TOKENS_CONTRATO = 900

#: Semilla fija: la mitad de la petición de determinismo. La otra mitad es `temperatura=0`, y que
#: las dos juntas basten es cosa del servidor, no nuestra (se comprueba en scripts/humo_proveedor.py).
SEMILLA = 20260812

TRANSITORIOS = (408, 409, 429, 500, 502, 503, 504)


class ErrorDefinitivo(RuntimeError):
    """No tiene sentido reintentar: contrato mal formado, credencial mala, modelo inexistente."""


class ErrorTransitorio(RuntimeError):
    """Puede salir bien a la segunda: 429, 5xx, timeout, corte de red."""

    #: Segundos que el proveedor pidió esperar (cabecera `Retry-After`), o None si no dijo nada.
    retry_after: float | None = None


#: Tope de cordura para `Retry-After`. Un proveedor puede mandar un valor enorme -o un reloj
#: descuadrado puede producirlo al restar fechas- y obedecerlo a ciegas dejaría la petición colgada
#: muchísimo más que el presupuesto de la consulta.
#:
#: **BAJADO DE 30 A 4 SEGUNDOS el 13 de agosto de 2026, y no por gusto: 30 s era SEIS VECES el
#: presupuesto entero de la consulta.** Es el hallazgo del barrido que mandó la regla nueva —un tope
#: expresado en una unidad que no es la que manda—: aquí la unidad era la correcta (segundos) pero
#: la ESCALA estaba tomada del mundo de los trabajos por lotes, donde esperar medio minuto es
#: razonable. En una consulta interactiva con 5 s de plazo, esperar 30 s para reintentar no es
#: prudente: es garantizar que se agota el plazo esperando. Si el proveedor pide más de esto, la
#: respuesta honesta no es obedecer sino **abstenerse por plazo**, que es lo que pasa.
RETRY_AFTER_MAXIMO_S = 4.0

#: LO QUE SCALEWAY MANDA DE VERDAD, leído de una respuesta real el 13 de agosto de 2026 (no de la
#: documentación, que publica los nombres pero no los números por modelo):
#:
#:     x-ratelimit-limit-requests: 600        x-ratelimit-limit-tokens: 2000000
#:     x-ratelimit-remaining-requests: 299    x-ratelimit-remaining-tokens: 999987
#:     x-ratelimit-reset-requests: 100ms      x-ratelimit-reset-tokens: 0ms
#:
#: O sea **600 peticiones/min y 2.000.000 tokens/min** para `mistral-small-3.2-24b`. NO manda
#: `Retry-After` en las respuestas buenas; si tampoco lo mandara en un 429, estos `reset` son lo
#: único que dice cuándo volver, así que se leen como respaldo antes de caer a la conjetura.
RESET_SCALEWAY = ("x-ratelimit-reset-requests", "x-ratelimit-reset-tokens")


def _reset_de_scaleway(cabeceras) -> float | None:
    """El mayor de los dos `x-ratelimit-reset-*`, en segundos. Respaldo de `Retry-After`.

    Se toma el MAYOR y no el primero porque las dos cuotas son independientes —peticiones y
    tokens— y volver cuando se repone una mientras la otra sigue agotada es volver a por otro 429.
    Los valores llegan como `100ms`, `1s` o `2m`; un formato que no se entienda devuelve None y se
    cae al retroceso, que es lo que había antes y no es peor.
    """
    mayor = None
    for nombre in RESET_SCALEWAY:
        try:
            crudo = cabeceras.get(nombre)
        except Exception:
            return None
        if not crudo:
            continue
        texto = str(crudo).strip().lower()
        for sufijo, factor in (("ms", 0.001), ("s", 1.0), ("m", 60.0), ("h", 3600.0)):
            if texto.endswith(sufijo):
                try:
                    valor = float(texto[: -len(sufijo)]) * factor
                except ValueError:
                    break
                mayor = valor if mayor is None else max(mayor, valor)
                break
    if mayor is None:
        return None
    return min(max(mayor, 0.0), RETRY_AFTER_MAXIMO_S)


def leer_retry_after(cabeceras, ahora=None) -> float | None:
    """Los segundos que pide `Retry-After`, en sus DOS formatos, o None si no viene o no se entiende.

    El RFC admite delta-segundos (`Retry-After: 3`) y fecha HTTP (`Retry-After: Wed, 13 Aug 2026
    10:00:00 GMT`). Se aceptan los dos porque cuál manda cada pasarela no es cosa nuestra, y leer
    solo uno sería volver a reintentar a ciegas justo la mitad de las veces.

    Nunca lanza: una cabecera rara es un motivo para caer al retroceso exponencial, no para tumbar
    una petición que solo iba con prisa.
    """
    if not cabeceras:
        return None
    crudo = None
    try:
        crudo = cabeceras.get("retry-after") or cabeceras.get("Retry-After")
    except Exception:
        return None
    if not crudo:
        return _reset_de_scaleway(cabeceras)
    crudo = str(crudo).strip()
    try:
        return min(max(float(crudo), 0.0), RETRY_AFTER_MAXIMO_S)
    except ValueError:
        pass
    try:
        from email.utils import parsedate_to_datetime
        cuando = parsedate_to_datetime(crudo)
        if cuando.tzinfo is None:
            cuando = cuando.replace(tzinfo=timezone.utc)
        referencia = ahora or datetime.now(timezone.utc)
        return min(max((cuando - referencia).total_seconds(), 0.0), RETRY_AFTER_MAXIMO_S)
    except Exception:
        return None


@dataclass
class Ajustes:
    base_url: str
    api_key: str
    modelo: str
    temperatura: float = 0.0
    semilla: int = SEMILLA
    max_tokens: int = MAX_TOKENS_CONTRATO
    timeout_conexion: float = 10.0
    #: TIEMPO MÁXIMO ENTRE DOS BYTES del flujo, no de la respuesta entera.
    #:
    #: **BAJADO DE 60 A 5 SEGUNDOS el 13 de agosto de 2026, y este es el hallazgo más serio del
    #: barrido, porque tapa un agujero que seguía abierto.** El vigilante de ritmo caza un flujo
    #: LENTO, y el plazo caza una respuesta larga; pero los dos viven **dentro del bucle que consume
    #: trozos**, así que un flujo **PARADO DEL TODO** no dispara ninguno de los dos: sin trozos no
    #: hay nada que contar ni ningún sitio donde mirar el reloj. Lo único que corta ahí es este
    #: timeout, y estaba en 60 s: **doce veces el presupuesto entero**, o sea un minuto de pantalla
    #: congelada todavía posible justo después de haber construido dos mecanismos para impedirlo.
    #:
    #: Con 5 s el peor caso de un flujo parado pasa a ser del orden del presupuesto. Y no aprieta a
    #: los sanos: es el hueco ENTRE TROZOS, y hasta la peor consulta medida (4 tokens/s) tiene 250 ms
    #: entre uno y otro, veinte veces por debajo.
    timeout_lectura: float = 5.0
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
        # SU PROPIA VARIABLE, Y NO `TIMEOUT_ETAPA_MS`. Esto leia el tope de ETAPA -que compose trae
        # en 60000 desde el 0.3, cuando no existia ni el plazo ni el vigilante- y lo usaba como
        # timeout de LECTURA. O sea que el valor por defecto del dataclass decia 5.0, el codigo
        # parecia correcto al leerlo, y el contenedor corria con 60.
        #
        # LO CAZO UNA MEDIDA, NO UNA REVISION: en un lote de 20 consultas con el codigo de hoy, una
        # se quedo 62 SEGUNDOS congelada -`PlazoAgotado ... (van 61924)`-, doce veces el presupuesto
        # entero y justo el minuto de pantalla muerta que dos mecanismos existen para impedir.
        #
        # Y el fallo es de la familia que ya tiene regla: una constante compartida haciendo DOS
        # trabajos con optimos distintos. El tope de etapa acota una fase entera; el de lectura acota
        # el HUECO ENTRE TROZOS, y hasta la peor consulta medida (4 tokens/s) tiene 250 ms entre uno
        # y otro. Mismo numero para las dos preguntas: la respuesta correcta a una es absurda para la
        # otra.
        lectura = float(os.environ.get("TIMEOUT_LECTURA_MS") or 5000) / 1000
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
    #: EL CÓDIGO DE CADA TRANSITORIO, no solo cuántos hubo. Añadido el 13 de agosto de 2026 tras una
    #: corrida en la que dos de veinte consultas reintentaron y **la traza no sabía decir si habían
    #: sido 429 o 5xx**, que son cosas distintas con respuestas distintas: un 429 se espera y se
    #: reintenta, un 503 puede ser una caída. Contar reintentos sin su motivo obliga a adivinar justo
    #: cuando hace falta decidir.
    codigos: list = field(default_factory=list)


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
            except ErrorTransitorio as e:
                traza.codigos.append(getattr(e, "codigo", None) or type(e).__name__)
                if emitido or intento == self.a.intentos:
                    raise
                espera = self._espera(intento, getattr(e, "retry_after", None))
                traza.esperas.append(round(espera, 3))
                time.sleep(espera)

    def _un_intento(self, cuerpo: dict, traza: Llamada) -> Iterator[Trozo]:
        t0 = time.perf_counter()
        try:
            with self._http.stream("POST", self.a.url, json=cuerpo,
                                   headers=self._cabeceras) as r:
                if r.status_code != 200:
                    r.read()
                    self._levantar(r.status_code, r.text, r.headers)
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
            pedido = None      # lo que el proveedor pida en Retry-After, si lo manda
            try:
                r = self._http.post(self.a.url, json=cuerpo, headers=self._cabeceras)
                if r.status_code != 200:
                    self._levantar(r.status_code, r.text, r.headers)
                datos = r.json()
                traza.ttft_proveedor_ms = (time.perf_counter() - t0) * 1000
                uso = Uso(tokens_entrada=(datos.get("usage") or {}).get("prompt_tokens", 0),
                          tokens_salida=(datos.get("usage") or {}).get("completion_tokens", 0))
                return datos["choices"][0]["message"]["content"], uso, traza
            except httpx.HTTPError as e:
                traza.codigos.append(type(e).__name__)
                if intento == self.a.intentos:
                    raise ErrorTransitorio(self.a.tapar(f"{type(e).__name__}: {e}")) from e
            except ErrorTransitorio as e:
                traza.codigos.append(getattr(e, "codigo", None) or type(e).__name__)
                if intento == self.a.intentos:
                    raise
                pedido = getattr(e, "retry_after", None)
            espera = self._espera(intento, pedido)
            traza.esperas.append(round(espera, 3))
            time.sleep(espera)
        raise ErrorTransitorio("agotados los intentos")

    # --- política ----------------------------------------------------------------------------------

    def _levantar(self, codigo: int, cuerpo: str, cabeceras=None) -> None:
        detalle = self.a.tapar((cuerpo or "")[:300])
        if codigo in TRANSITORIOS:
            error = ErrorTransitorio(f"HTTP {codigo}: {detalle}")
            error.retry_after = leer_retry_after(cabeceras)
            error.codigo = codigo
            raise error
        raise ErrorDefinitivo(f"HTTP {codigo} (no se reintenta): {detalle}")

    def _espera(self, intento: int, retry_after: float | None = None) -> float:
        """Retroceso exponencial con jitter completo: 0,5 s, 1 s, 2 s... por el tope, al azar dentro
        del tramo. El jitter no es adorno: sin él, N clientes que fallan a la vez vuelven a llamar a
        la vez y el 429 se repite exactamente igual.

        **`Retry-After` MANDA SOBRE EL RETROCESO CUANDO EL PROVEEDOR LO ENVÍA**, y se corrige aquí
        (13 de agosto de 2026) porque hasta hoy se reintentaba a ciegas. La diferencia importa: el
        retroceso es una *conjetura* nuestra sobre cuánto esperar, y `Retry-After` es el proveedor
        **diciendo el dato**. Reintentar antes de lo que pide no adelanta la respuesta —vuelve a dar
        429— y además gasta cuota del minuto siguiente, o sea que la conjetura no solo falla: empeora
        lo que intenta arreglar.

        Se toma el MÁXIMO de los dos y no el del header a secas: si el proveedor pide 1 s y nuestro
        retroceso ya iba por 4, volver a 1 s sería acelerar justo después de que nos frenaran."""
        retroceso = random.uniform(0, self.a.espera_base * (2 ** (intento - 1)))
        if retry_after is None:
            return retroceso
        # Un jitter pequeno por encima del valor pedido: N clientes con el MISMO Retry-After
        # volverian a la vez, que es la manada que el 429 venia a cortar.
        return max(retroceso, retry_after + random.uniform(0, 0.5))
