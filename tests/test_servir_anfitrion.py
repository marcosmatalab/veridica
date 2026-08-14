"""La puerta de arranque de la sesión (ADR 0023), en las dos direcciones.

**Lo que estos tests NO cubren, dicho arriba:** no levantan uvicorn ni hablan con la GPU. Prueban la
lógica que decide —¿es mi proceso?, ¿están las capacidades?— que es donde vive el fallo caro; el
arranque real se ejerce corriendo el script, y su evidencia es el log del propio proceso.
"""
import time

from scripts.servir_anfitrion import PUERTO_DEMO, es_el_mio


def test_el_puerto_de_la_sesion_es_FIJO():
    """8012 un día y 8013 al siguiente estaba bien en desarrollo —garantizaba hablar con mi proceso
    y no con un zombi— y **para la sesión es un peligro con forma de virtud**: el ensayo se hace en
    un puerto, la sesión arranca en otro, y el comando del túnel apuntado queda mal justo cuando no
    hay tiempo de averiguarlo."""
    assert isinstance(PUERTO_DEMO, int) and PUERTO_DEMO != 8000, \
        "el 8000 es el contenedor, que sirve la configuracion degradada"


def test_un_proceso_que_arranco_ANTES_que_yo_no_es_el_mio():
    """La garantía que antes daba estrenar puerto, ahora sobre un hecho del proceso: si contesta algo
    que arrancó antes de que yo lanzara el mío, hay un residuo ocupando el puerto y serviría código
    viejo. Es la media tarde del 14/08 convertida en comparación."""
    ahora = time.time()
    viejo = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ahora - 3600))
    assert es_el_mio({"arrancado_en": viejo}, lanzado_en=ahora) is False


def test_y_el_mio_SI_lo_es_aunque_el_reloj_redondee_al_segundo():
    """La otra dirección, sin la cual bastaría con devolver False siempre: `arrancado_en` viene
    redondeado al segundo, así que un proceso legítimo puede declarar una marca un pelo anterior a
    `time.time()`. Sin el margen, la guarda rechazaría su propio arranque."""
    ahora = time.time()
    mio = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ahora))
    assert es_el_mio({"arrancado_en": mio}, lanzado_en=ahora) is True


def test_sin_marca_de_arranque_no_se_da_por_bueno():
    """Un `/salud` que no dice cuándo arrancó no puede demostrar que es el mío. Se rechaza en vez de
    suponerlo: es la regla de no creerse un VACÍO."""
    assert es_el_mio({}, lanzado_en=time.time()) is False


def test_el_comando_del_TUNEL_se_imprime_con_el_puerto_dentro():
    """Si un paso puede olvidarse, se convierte en salida del comando anterior —la idea de
    `fusionar.py`—. Y aquí además cierra el hueco de apuntar al 8000 por accidente."""
    from pathlib import Path
    fuente = (Path(__file__).resolve().parents[1] / "scripts"
              / "servir_anfitrion.py").read_text(encoding="utf-8")
    assert "cloudflared tunnel --url http://127.0.0.1:{puerto}" in fuente
