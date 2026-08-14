"""El vigilante de ritmo del 3.4, probado en las DOS direcciones y sin dormir ni un milisegundo.

LO QUE ESTE FICHERO PROTEGE, con su número: medido el 13 de agosto de 2026, **2 de cada 20**
consultas se hunden a 4-11 tokens/s tras arrancar bien. Con esa tasa, una sesión de ocho preguntas
tiene un **57 %** de probabilidad de comerse al menos una congelación de un minuto delante del
cliente. El vigilante es lo único que está entre eso y la demo.

EL RELOJ SE INYECTA, y no es un detalle de comodidad: un test que necesita esperar dos segundos de
verdad para comprobar una ventana de dos segundos tarda dos segundos, y multiplicado por los casos
que hacen falta se convierte en un test que nadie vuelve a correr. Con reloj falso, la suite entera
de este fichero corre en milisegundos y se puede permitir cubrir los casos raros.
"""
import pytest

from app.core.ritmo import GRACIA, RITMO_MINIMO, RitmoCaido, VigilanteDeRitmo


class Reloj:
    """Un reloj que avanza cuando se le dice. Empieza en 0."""

    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def avanza(self, s: float) -> None:
        self.t += s


def alimentar(v: VigilanteDeRitmo, reloj: Reloj, tokens: int, por_segundo: float) -> None:
    """Mete `tokens` a un ritmo constante. Levanta RitmoCaido si el vigilante decide cortar."""
    paso = 1.0 / por_segundo
    for _ in range(tokens):
        reloj.avanza(paso)
        v.anota()
        v.comprobar()


# --- dirección SANA: no cortar lo que va bien ----------------------------------------------------

def test_un_ritmo_normal_no_se_corta():
    """~105 tokens/s es lo medido en una consulta sana. Sin esta mitad, el test de abajo probaría
    solo que la clase sabe lanzar excepciones."""
    reloj = Reloj()
    v = VigilanteDeRitmo(reloj=reloj)
    alimentar(v, reloj, tokens=400, por_segundo=105.0)
    assert v.total == 400
    assert v.ritmo() == pytest.approx(105.0, rel=0.05)


def test_un_ritmo_justo_por_encima_del_minimo_tampoco_se_corta():
    """El borde por el lado bueno. Si esto cortara, el vigilante estaría de más."""
    reloj = Reloj()
    v = VigilanteDeRitmo(reloj=reloj)
    alimentar(v, reloj, tokens=300, por_segundo=RITMO_MINIMO + 3)


def test_el_ARRANQUE_lento_no_cuenta_como_averia():
    """LA RAZÓN DE SER DE LA GRACIA. El arranque tiene su propia física y las dos consultas malas
    del 13 de agosto arrancaron SANAS: juzgar ahí daría falsos positivos justo donde no hay señal."""
    reloj = Reloj()
    v = VigilanteDeRitmo(reloj=reloj)
    alimentar(v, reloj, tokens=GRACIA, por_segundo=2.0)      # lentísimo, pero es el arranque
    assert v.total == GRACIA


def test_un_hueco_corto_de_red_no_dispara():
    """Medio segundo de pausa dentro de una generación por lo demás sana no es una avería, y cortar
    ahí sería cambiar una congelación de un minuto por reintentos constantes."""
    reloj = Reloj()
    v = VigilanteDeRitmo(reloj=reloj)
    alimentar(v, reloj, tokens=200, por_segundo=105.0)
    reloj.avanza(0.5)
    v.anota()
    v.comprobar()
    alimentar(v, reloj, tokens=200, por_segundo=105.0)


# --- dirección MUTADA: cortar lo que se hunde ----------------------------------------------------

@pytest.mark.parametrize("ritmo_malo", [4.0, 11.0])
def test_los_DOS_casos_reales_medidos_se_cortan(ritmo_malo):
    """Los dos números no son inventados: son los ritmos de las dos consultas de 63 y 68 segundos
    del 13 de agosto, sacados de su traza (767 tokens en 68 s y 252 en 62 s)."""
    reloj = Reloj()
    v = VigilanteDeRitmo(reloj=reloj)
    with pytest.raises(RitmoCaido) as e:
        alimentar(v, reloj, tokens=400, por_segundo=ritmo_malo)
    assert e.value.ritmo == pytest.approx(ritmo_malo, rel=0.15)


def test_se_corta_PRONTO_y_no_al_final():
    """El valor entero de esto es el tiempo que ahorra. Con la ventana y la gracia declaradas, una
    consulta a 11 tokens/s se corta a los pocos segundos en vez de a los 68."""
    reloj = Reloj()
    v = VigilanteDeRitmo(reloj=reloj)
    with pytest.raises(RitmoCaido):
        alimentar(v, reloj, tokens=1000, por_segundo=11.0)
    assert reloj.t < 5.0, f"tardo {reloj.t:.1f} s en cortar: demasiado para servir de algo"


@pytest.mark.parametrize("ritmo_malo,tope_s", [(4.0, 3.0), (11.0, 3.0), (20.0, 3.0)])
def test_el_corte_llega_ANTES_del_presupuesto_incluso_en_el_flujo_MAS_lento(ritmo_malo, tope_s):
    """REGRESIÓN DE UN FALLO PROPIO, y el más instructivo de este módulo.

    La primera versión tenía `GRACIA = 24` tokens. Una gracia contada en TOKENS se vuelve una gracia
    contada en SEGUNDOS cuanto más lento va el flujo: a 4 tokens/s son **6 segundos**, más que el
    presupuesto entero de la consulta. O sea que el vigilante habría llegado tarde **justo en el
    caso peor**, que es el que existe para cazar — y en los casos rápidos, donde no hacía falta,
    habría llegado a tiempo. Un verde perfectamente creíble haciendo lo contrario de su trabajo.

    Este test lo ancla al revés: cuanto más lento el flujo, MÁS pronto tiene que cortar."""
    reloj = Reloj()
    v = VigilanteDeRitmo(reloj=reloj)
    with pytest.raises(RitmoCaido):
        alimentar(v, reloj, tokens=2000, por_segundo=ritmo_malo)
    assert reloj.t < tope_s, (
        f"a {ritmo_malo} tokens/s tardo {reloj.t:.1f} s en cortar; el presupuesto entero son 5 s")


def test_una_generacion_que_EMPIEZA_bien_y_se_hunde_tambien_se_caza():
    """EL CASO REAL, y el que una media global no cazaría: las dos malas del 13 de agosto arrancaron
    a ritmo normal. Una media desde el principio tarda cada vez más en reaccionar; la ventana no."""
    reloj = Reloj()
    v = VigilanteDeRitmo(reloj=reloj)
    alimentar(v, reloj, tokens=300, por_segundo=105.0)      # primero sano
    with pytest.raises(RitmoCaido):
        alimentar(v, reloj, tokens=300, por_segundo=6.0)    # y se hunde


def test_la_ventana_OLVIDA_lo_viejo():
    """Si el vigilante promediara desde el principio, treinta segundos buenos taparían treinta malos
    y el corte no llegaría nunca. Se comprueba que el ritmo reportado sigue al reciente."""
    reloj = Reloj()
    v = VigilanteDeRitmo(minimo=0.0, reloj=reloj)           # sin cortar, solo para leer el ritmo
    alimentar(v, reloj, tokens=500, por_segundo=105.0)
    assert v.ritmo() == pytest.approx(105.0, rel=0.05)
    alimentar(v, reloj, tokens=100, por_segundo=10.0)
    assert v.ritmo() == pytest.approx(10.0, rel=0.15), "la ventana no olvidó: promedia con lo viejo"


# --- que no se rompa en los bordes ---------------------------------------------------------------

def test_sin_datos_no_hay_ritmo_Y_ESO_NO_ES_CERO():
    """Devolver 0 cuando aún no se sabe haría que el vigilante cortara toda consulta en su primer
    instante. `None` significa 'todavía no', que es lo que pasa."""
    v = VigilanteDeRitmo(reloj=Reloj())
    assert v.ritmo() is None
    v.anota()
    assert v.ritmo() is None
    v.comprobar()


def test_el_estado_se_declara_SIN_CALIBRAR():
    """Igual que el 0,80 del NLI y los márgenes de confianza: el umbral sale de dos casos malos, y
    decir que está calibrado sería inventarse un respaldo que no existe."""
    e = VigilanteDeRitmo(reloj=Reloj()).estado()
    # ACTUALIZADO EN EL 2.5, y el cambio de texto lleva dentro una CORRECCION: el 4.6 declaro que
    # "el ritmo por consulta no se persiste" y al ir a barrerlo habia 330 de 391 respuestas con su
    # ritmo guardado. Lo que de verdad faltaba era el PEOR momento -el umbral pregunta "¿bajo
    # alguna vez de 35?" y el campo guardado contestaba "¿a que ritmo iba al final?"-. Sigue sin
    # calibrar, pero por otro motivo, y el motivo es lo que se ancla.
    assert e["calibrado"] is False and "SIGUE SIN CALIBRAR" in e["calibracion"]
    assert "PEOR momento" in e["calibracion"]
    assert e["minimo"] == RITMO_MINIMO
    assert "minimo_observado" in e, "sin el peor momento no se puede calibrar este umbral"
