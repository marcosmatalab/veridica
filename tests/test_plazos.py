"""TODO LO QUE ESPERA A ALGO AJENO TIENE PLAZO, Y EL PLAZO CABE EN EL PRESUPUESTO.

De dónde sale esta puerta, que es una regla aprendida y no una precaución genérica: **un detector que
se alimenta del flujo que vigila es ciego al flujo ausente.** El vigilante de ritmo cuenta tokens y
el plazo de la consulta mira el reloj, pero los dos viven **dentro del bucle que consume trozos**, o
sea que un flujo parado del todo no dispara ninguno. La red de ese caso siempre está **fuera**: era
el `timeout_lectura` del cliente, y estaba en 60 s, doce veces el presupuesto.

Buscado el mismo patrón donde algo nuestro consume de algo ajeno, salieron **ocho conexiones a
Postgres en la ruta de petición sin ningún plazo** —tres en `recuperacion.py`, tres en `catalogo.py`
y dos en `traza.py`—. Una base colgada las dejaba esperando lo que quisiera el sistema operativo.

Estos tests anclan **relaciones y no valores**, que es lo que sobrevive a que alguien cambie el
presupuesto: los valores envejecen solos.
"""
import re
from pathlib import Path

import pytest

from app.api.consulta import PRESUPUESTO_MS
from app.core.conexion import CONEXION_S, SENTENCIA_MS

RAIZ = Path(__file__).resolve().parents[1]

#: Lo que corre DENTRO de una petición y por tanto no puede esperar sin límite. `main.py` queda
#: fuera porque sus conexiones son las sondas de `/salud` y ya llevan su `connect_timeout` explícito.
EN_LA_RUTA = ["app/core/recuperacion.py", "app/core/catalogo.py", "app/core/traza.py"]

RE_CRUDA = re.compile(r"psycopg\.connect\(")


@pytest.mark.parametrize("ruta", EN_LA_RUTA)
def test_nada_en_la_ruta_de_peticion_abre_una_conexion_SIN_PLAZO(ruta):
    """`psycopg.connect` sin plazos espera lo que quiera el sistema operativo, que son minutos.

    Se comprueba el TEXTO y no el comportamiento a propósito: reproducir una base colgada en un test
    es caro y frágil, mientras que la avería real es de una línea —alguien añade una consulta nueva
    copiando el patrón de al lado— y se caza leyendo."""
    texto = (RAIZ / ruta).read_text(encoding="utf-8")
    assert not RE_CRUDA.search(texto), (
        f"{ruta} abre una conexion con psycopg.connect directamente. En la ruta de peticion se usa "
        f"app.core.conexion.conectar, que pone connect_timeout Y statement_timeout: sin el segundo, "
        f"una conexion que abre bien y luego se queda esperando espera para siempre")


def test_los_plazos_de_la_base_CABEN_en_el_presupuesto_de_la_consulta():
    """La relación, que es lo que se rompe al cambiar el presupuesto y olvidarse de mirar hacia
    abajo. Y son DOS plazos porque son dos averías: abrir y consultar."""
    presupuesto_s = PRESUPUESTO_MS / 1000
    assert CONEXION_S < presupuesto_s, (
        f"abrir la conexion puede tardar {CONEXION_S} s con un plazo de consulta de {presupuesto_s} s")
    assert SENTENCIA_MS < PRESUPUESTO_MS, (
        f"una sola consulta a la base puede tardar {SENTENCIA_MS} ms del presupuesto de "
        f"{PRESUPUESTO_MS} ms, y en una peticion hay varias")
    # Y en una peticion hay TRES vias mas la traza: los plazos sumados no pueden comerse el
    # presupuesto ellos solos, o el plazo de la consulta no significaria nada.
    assert 4 * SENTENCIA_MS <= 2 * PRESUPUESTO_MS, (
        "las cuatro consultas de una peticion, cada una en su techo, se pasan del doble del "
        "presupuesto: el techo por consulta esta puesto sin mirar cuantas hay")


def test_el_statement_timeout_va_de_verdad_en_la_conexion():
    """Que la cadena de opciones se componga no demuestra que Postgres la acepte; lo que demuestra
    algo es preguntarselo a la base. Sin base, se salta: es la puerta local del ADR 0001."""
    import os

    import psycopg
    url = os.environ.get("DATABASE_URL",
                         "postgresql://veridica:veridica_local@127.0.0.1:5434/veridica")
    from app.core.conexion import conectar
    try:
        with conectar(url) as con, con.cursor() as cur:
            cur.execute("SHOW statement_timeout")
            valor = cur.fetchone()[0]
    except psycopg.Error:
        pytest.skip("necesita Postgres levantado (puerta local, ADR 0001)")
    assert valor not in ("0", "0ms"), "la conexion no lleva statement_timeout: Postgres dice 0"


def test_el_timeout_de_LECTURA_no_lo_decide_la_variable_de_ETAPA():
    """REGRESIÓN DE UN VALOR DECLARADO QUE EL DESPLIEGUE NO CUMPLÍA.

    `timeout_lectura` decía **5.0** en el dataclass y el contenedor corría con **60**: `desde_entorno`
    leía `TIMEOUT_ETAPA_MS`, que `compose.yml` trae en 60000 desde el encargo 0.3 —cuando no existían
    ni el plazo ni el vigilante—. El código parecía correcto al leerlo; **lo cazó una medida**: en un
    lote de 20 consultas, una se quedó **62 segundos** congelada.

    Es la familia de "una constante compartida haciendo dos trabajos con óptimos distintos": el tope
    de etapa acota una fase entera y el de lectura acota el hueco ENTRE TROZOS, que hasta en la peor
    consulta medida son 250 ms."""
    import os

    from app.core.inferencia import Ajustes
    guardado = {k: os.environ.get(k) for k in
                ("INFERENCIA_BASE_URL", "INFERENCIA_API_KEY", "MODELO_PEQUENO",
                 "TIMEOUT_ETAPA_MS", "TIMEOUT_LECTURA_MS")}
    try:
        os.environ.update({"INFERENCIA_BASE_URL": "http://x", "INFERENCIA_API_KEY": "k",
                           "MODELO_PEQUENO": "m", "TIMEOUT_ETAPA_MS": "60000"})
        os.environ.pop("TIMEOUT_LECTURA_MS", None)
        a = Ajustes.desde_entorno()
        assert a.timeout_lectura == 5.0, (
            "el tope de ETAPA esta decidiendo el de LECTURA: un flujo parado del todo se cortaria "
            f"a los {a.timeout_lectura} s en vez de a los 5")
        os.environ["TIMEOUT_LECTURA_MS"] = "2000"
        assert Ajustes.desde_entorno().timeout_lectura == 2.0
    finally:
        for k, v in guardado.items():
            os.environ.pop(k, None) if v is None else os.environ.update({k: v})
