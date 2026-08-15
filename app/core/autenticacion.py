"""Token compartido por cabecera (encargo 0.3, añadido el 15 de agosto de 2026).

**POR QUÉ EXISTE, dicho como el riesgo que es y no como una buena práctica.** La API no tenía
ninguna autenticación, y el montaje de la sesión la publica **en internet** por un túnel de
Cloudflare — con una **clave de pago** detrás, porque `/consulta` llama al proveedor. Una URL de
túnel es adivinable y la rastrean bots: sin puerta, cualquiera que dé con ella gasta nuestro saldo,
lee la traza de las consultas ajenas y se pasea por el corpus. No es un endurecimiento teórico: es
la diferencia entre enseñar el sistema y regalarlo.

## Las tres decisiones, con su porqué

**1. Se deniega POR DEFECTO y la lista es de lo ABIERTO, no de lo protegido.** Una lista de rutas a
proteger deja fuera la siguiente ruta que alguien añada, y la deja fuera **en silencio**: nada se
pone rojo cuando una ruta nueva nace sin puerta. Al revés, el olvido se nota en la primera petición.
Es la misma forma que el resto de las puertas de este repo: que el descuido falle ruidoso.

**2. `/salud` y `/api` se quedan ABIERTAS a propósito, y por eso van redactadas.** El *healthcheck*
de compose las llama sin cabeceras, `scripts/servir_anfitrion.py` decide con ellas si abre el túnel,
y la cabecera de la interfaz **enlaza `/salud`** para que quien mire sepa qué sabe hacer esta
instancia. Cerrarlas rompería las tres cosas. Lo que sí se hace es **no publicar por ahí lo que no
debe salir**: el detalle crudo de una sonda puede arrastrar una cadena de conexión, y este fichero
trae el redactor que lo tapa.

**3. Sin `VERIDICA_TOKEN`, la puerta NO EXISTE — y eso se dice en voz alta en tres sitios.** Es la
única forma de que la demo local y los tests sigan corriendo sin ceremonia, pero un defecto abierto
que nadie ve es exactamente la avería que este repo persigue. Así que **el defecto se declara**:
`/salud` y `/api` publican `autenticacion: "ABIERTA"`, y sobre todo
**`scripts/servir_anfitrion.py` se niega a imprimir el comando del túnel sin token**. Ese script es
el único sitio del proyecto donde se sabe con certeza que lo siguiente es *publicar esto en
internet*, así que la comprobación vive ahí: si un paso puede olvidarse, se convierte en salida del
paso anterior, como el hash del manifiesto en `fusionar.py`.
"""
import hmac
import os
import re

#: La cabecera. Se acepta también `Authorization: Bearer <token>` porque es lo que espera cualquier
#: cliente de HTTP, y `curl -H` con la propia es lo más corto de dictar en voz alta.
CABECERA = "X-Veridica-Token"

#: **RUTAS ABIERTAS, y esta lista es la excepción: todo lo demás pide token.** Cada una con el
#: motivo por el que no puede pedirlo, porque una excepción sin motivo escrito se copia sola.
ABIERTAS = {
    "/salud": "el healthcheck de compose y servir_anfitrion.py la llaman sin cabeceras",
    "/api": "dice qué está construido; sin ella no se puede diagnosticar una instancia a ciegas",
    "/": "la página tiene que cargar para poder pedir el token",
    "/estilos": "muestra de estilos con datos inventados: no toca ni el corpus ni el proveedor",
    "/favicon.ico": "lo pide el navegador solo",
}
#: Los prefijos abiertos: los estáticos que la página necesita antes de tener token.
PREFIJOS_ABIERTOS = ("/estatico/",)

#: LA LISTA DE LO QUE NO SE IMPRIME, PRIMERO. Es la regla del repo desde que
#: `comparar_configuracion.py` sacó una clave entera por pantalla en su primera corrida: todo lo que
#: enumere entorno, cabeceras, configuración o trazas empieza por aquí. `/salud` es justo eso —y
#: además va a estar abierta en internet—, así que el detalle crudo de sus sondas pasa por el
#: redactor: una `OperationalError` de psycopg puede traerse la cadena de conexión entera.
SENSIBLES = ("key", "password", "secret", "token", "clave", "passwd", "pwd", "authorization")

#: TRES formas de que un secreto se cuele en un texto de error, y las tres salieron de escribir el
#: test antes de darlas por cubiertas —las dos últimas fallaban con la primera versión—:
#:   1. dentro de una URL con credenciales: `postgresql://usuario:CLAVE@host`;
#:   2. como `nombre=valor` o `nombre: valor`, donde el nombre CONTIENE una palabra sensible. Ojo al
#:      cuantificador: la primera versión pedía `[A-Za-z_][A-Za-z0-9_]*` **antes** de la palabra, o
#:      sea al menos un carácter, así que `INFERENCIA_API_KEY=...` sí y un `password: ...` pelado
#:      **no**. El prefijo es opcional;
#:   3. `Authorization: Bearer <token>`, que la regla 2 no tapa porque su valor se corta en el
#:      primer espacio: redactaba la palabra "Bearer" y dejaba el token detrás, intacto y visible.
#:      **Tapar lo de al lado del secreto es peor que no tapar nada**, porque parece que se ha
#:      hecho algo.
_RE_URL_CON_CLAVE = re.compile(r"(?P<esquema>[a-zA-Z][\w+.-]*://)(?P<usuario>[^:/@\s]+):[^@\s]+@")
_RE_PORTADOR = re.compile(r"(?i)\b(?P<tipo>bearer|basic|token)\s+(?P<valor>[^\s,;'\"]+)")
_RE_ASIGNACION = re.compile(
    r"(?i)\b(?P<nombre>[A-Za-z0-9_]*(?:" + "|".join(SENSIBLES) + r")[A-Za-z0-9_]*)"
    r"\s*[=:]\s*(?P<valor>[^\s,;'\"]+)")


def redactar(texto) -> str:
    """Tapa credenciales dejando ver que HAY algo. *Se puede decir **si** difiere sin decir **cuánto**
    vale* — aquí, se puede decir que la conexión falló y contra qué host sin regalar la contraseña.

    Devuelve el texto tal cual si no es una cadena: las sondas devuelven a veces otras cosas.
    """
    if not isinstance(texto, str):
        return texto
    texto = _RE_URL_CON_CLAVE.sub(r"\g<esquema>\g<usuario>:(oculto)@", texto)
    # El portador ANTES que la asignación: si fuera al revés, la regla de `nombre: valor` habría
    # convertido "Authorization: Bearer xxx" en "Authorization=(oculto) xxx" y el token seguiría ahí.
    texto = _RE_PORTADOR.sub(lambda m: f"{m.group('tipo')} (oculto)", texto)
    return _RE_ASIGNACION.sub(lambda m: f"{m.group('nombre')}=(oculto)", texto)


def token_configurado() -> str:
    """Se lee del entorno EN CADA LLAMADA y no al importar.

    Un módulo importado una vez congelaría el valor del arranque, y esto lo leen tests que lo ponen
    y lo quitan con `monkeypatch`. Además hace que la puerta se pueda encender sin reconstruir nada.
    """
    return (os.environ.get("VERIDICA_TOKEN") or "").strip()


def esta_abierta(ruta: str) -> bool:
    return ruta in ABIERTAS or ruta.startswith(PREFIJOS_ABIERTOS)


def token_de(cabeceras) -> str:
    """El token que trae la petición, por cualquiera de las dos formas aceptadas."""
    propio = cabeceras.get(CABECERA) or cabeceras.get(CABECERA.lower()) or ""
    if propio.strip():
        return propio.strip()
    autorizacion = (cabeceras.get("authorization") or "").strip()
    if autorizacion.lower().startswith("bearer "):
        return autorizacion[7:].strip()
    return ""


def autorizada(ruta: str, cabeceras) -> bool:
    """¿Puede pasar esta petición?

    La comparación va con `hmac.compare_digest` y no con `==`: comparar cadenas secretas con el
    operador normal termina en cuanto encuentra el primer byte distinto, y ese tiempo se puede medir
    a través de la red para adivinar el token carácter a carácter. Es barato hacerlo bien.
    """
    esperado = token_configurado()
    if not esperado or esta_abierta(ruta):
        return True
    return hmac.compare_digest(token_de(cabeceras), esperado)
