"""Conexión a Postgres con los dos plazos puestos, para todo lo que está en la RUTA DE PETICIÓN.

POR QUÉ EXISTE ESTE MÓDULO, que es una regla y no una comodidad: **un detector que se alimenta del
flujo que vigila es ciego al flujo ausente.** Salió el 13 de agosto de 2026 con el `timeout_lectura`
del proveedor: el vigilante de ritmo cuenta tokens y el plazo de la consulta mira el reloj, pero los
dos viven **dentro del bucle que consume trozos**, así que un flujo parado del todo no dispara
ninguno —sin trozos no hay nada que contar ni ningún sitio donde mirar la hora—. La red de ese caso
**siempre está fuera**: era el timeout de lectura, y estaba en 60 s.

Al buscar el mismo patrón en los demás sitios donde algo nuestro consume de algo ajeno salieron
**ocho conexiones a Postgres en la ruta de petición sin ningún plazo** —tres en `recuperacion.py`,
tres en `catalogo.py` y dos en `traza.py`—. Una base colgada las dejaba esperando lo que el sistema
operativo quisiera, que son minutos: o sea que el requisito de 5 s tenía un agujero del tamaño de la
base de datos, justo después de haberlo hecho cumplir en la generación.

**DOS PLAZOS, PORQUE SON DOS AVERÍAS DISTINTAS Y UNA NO CUBRE A LA OTRA:**

- `connect_timeout` acota **abrir** la conexión. No dice nada de lo que pase después.
- `statement_timeout` acota **la consulta ya abierta**, y lo impone el servidor. Sin él, una conexión
  que se establece bien y luego se queda esperando un bloqueo o un plan malo espera para siempre.
  Poner solo el primero es el error cómodo: se ve la protección y no está.
"""
import os

import psycopg

#: Abrir la conexión. Contra una base local sana son milisegundos; 3 s es holgadísimo y aun así
#: veinte veces menos que el plazo de la consulta.
CONEXION_S = float(os.environ.get("DB_TIMEOUT_CONEXION_S") or 3)

#: Techo de una consulta. La más lenta medida en el 3.3 es la vectorial con 29 ms, así que 2 s deja
#: casi dos órdenes de margen: si algo tarda más, no es lentitud, es que algo va mal.
SENTENCIA_MS = int(os.environ.get("DB_TIMEOUT_SENTENCIA_MS") or 2000)


def conectar(url: str, **extra):
    """`psycopg.connect` con los dos plazos. Se usa en TODO lo que corre dentro de una petición.

    Los scripts de medida y de carga NO la usan a propósito: una ingesta legítimamente tarda minutos,
    y ponerle el techo de una consulta interactiva sería cortar trabajo bueno. La distinción es
    quién espera al otro lado —un alumno o nadie—, y por eso vive en el módulo y no en un parámetro.
    """
    opciones = f"-c statement_timeout={SENTENCIA_MS}"
    if "options" in extra:
        opciones = f"{extra.pop('options')} {opciones}"
    return psycopg.connect(url, connect_timeout=CONEXION_S, options=opciones, **extra)
