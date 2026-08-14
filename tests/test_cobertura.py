"""La regla de cobertura del 4.5, comprobada **frase a frase** y en las dos direcciones.

POR QUÉ ESTE MÓDULO EXISTE, en una línea: la prosa se emite en streaming, así que la cobertura se
comprueba frase a frase según se escriben, contra unas afirmaciones que ya están cerradas.

**QUÉ CAMBIÓ EL 14 DE AGOSTO DE 2026, y por qué estos tests se reescribieron a propósito: el
portero MARCA en vez de PODAR.** Una frase por debajo del umbral **se emite señalada** en lugar de
desaparecer. Marcar es etiquetar —la promesa del proyecto—, y podar además ocultaba que el modelo lo
había dicho.

**Y eso INVIERTE la asimetría, que es lo que hay que tener delante al leer estos tests.** Mientras
podaba, el falso negativo era el caro: se llevaba una frase legítima de un texto que alguien está
leyendo. Ahora un falso negativo solo pone una marca injusta —cosmético— y el caro es el falso
POSITIVO: una frase sin respaldo llegando **sin marca**, o sea contenido no declarado con aspecto de
respaldado. Los tests siguen cubriendo las dos direcciones, pero lo que cada una cuesta ya no es lo
mismo, y el umbral se re-barre por eso (ADR 0021).
"""
from app.core.cobertura import MINIMO_PALABRAS, PorteroDeFrases

AFIRMACIONES = [
    {"id": 1, "tipo": "literal", "texto": "La sesion vive en el servidor.",
     "cita": "la cookie solo contiene el identificador"},
    {"id": 2, "tipo": "andamiaje", "texto": "Vamos por partes con las cookies."},
]


def portero(afirmaciones=None, solape=0.5):
    return PorteroDeFrases(AFIRMACIONES if afirmaciones is None else afirmaciones, solape)


def texto_de(tramos):
    """Lo que el alumno ve, sin las marcas: los tests de emisión miran esto."""
    return "".join(t["texto"] for t in tramos)


def respaldadas(tramos):
    return [t["respaldada"] for t in tramos]


# --- que juzgue bien lo cubierto ------------------------------------------------------------------

def test_una_frase_respaldada_sale_EN_CUANTO_cierra_y_SIN_marca():
    """No al final: en cuanto se cierra la frase. Esa es la diferencia entre una frase de retraso y
    esperar la redacción entera."""
    p = portero()
    assert p.alimentar("La sesion vive en el servidor") == [], "salio antes de cerrar la frase"
    tramos = p.alimentar(".")
    assert texto_de(tramos) == "La sesion vive en el servidor."
    assert respaldadas(tramos) == [True]
    assert p.emitidas == 1 and p.huerfanas == []


def test_la_CITA_tambien_respalda_y_no_solo_el_texto_de_la_afirmacion():
    """REGRESIÓN DE UN FALSO NEGATIVO POR CONSTRUCCIÓN, encontrado por el primer test que se corrió.

    La prosa *"la cookie lleva solo el identificador"* se marcaría porque ninguna afirmación tiene
    `cookie` en su `texto`… y sí la tiene en su `cita`, que es contenido **declarado en el contrato
    y verificado letra a letra** por el 4.2. Si algo puede respaldar una frase, es precisamente lo
    que está comprobado contra el temario."""
    tramos = portero().alimentar("La cookie contiene el identificador.")
    assert respaldadas(tramos) == [True], "se marco una frase respaldada por la CITA"


def test_una_frase_CORTA_no_se_juzga_y_pasa_sin_marca():
    """*"Vamos por partes."* no tiene vocabulario suficiente para cubrirse, así que juzgarla sería
    marcarla siempre: el falso positivo por construcción **del lado de la marca**."""
    tramos = portero().alimentar("Vale.")
    assert texto_de(tramos) == "Vale."
    assert respaldadas(tramos) == [True] and tramos[0]["sin_juzgar_por_corta"] is True


def test_el_ANDAMIAJE_respalda_y_sin_el_la_regla_marca_las_transiciones():
    """La excepción del andamiaje no es un permiso: es lo que evita marcar **todas** las
    transiciones y preguntas al alumno. Marcar de más es barato; marcar TODO es no marcar nada."""
    con = portero().alimentar("Vamos por partes con las cookies.")
    sin = portero(afirmaciones=[AFIRMACIONES[0]]).alimentar("Vamos por partes con las cookies.")
    assert respaldadas(con) == [True], "el andamiaje declarado no respaldo su propia frase"
    assert respaldadas(sin) == [False], "sin el andamiaje la frase pasa igual: la excepcion no hace nada"


# --- que MARQUE lo huérfano, y que NO lo esconda --------------------------------------------------

def test_una_frase_SIN_respaldo_SE_EMITE_MARCADA_y_se_anota():
    """EL CAMBIO DEL 14/08 EN UNA LÍNEA. Antes esto devolvía cadena vacía: la frase desaparecía y el
    alumno leía un párrafo con un salto. Ahora llega entera **y señalada**, que es lo que permite
    juzgarla en vez de ignorar que el modelo la dijo."""
    p = portero()
    tramos = p.alimentar("El teorema de Pitagoras relaciona catetos e hipotenusa.")
    assert texto_de(tramos) == "El teorema de Pitagoras relaciona catetos e hipotenusa.", \
        "la frase sin respaldo desaparecio: eso es podar, y el portero ya no poda"
    assert respaldadas(tramos) == [False]
    assert len(p.huerfanas) == 1 and p.huerfanas[0]["solape"] < 0.5


def test_sin_NINGUNA_afirmacion_toda_la_prosa_sale_MARCADA():
    """Una respuesta con prosa y cero afirmaciones viola la regla entera: no hay nada declarado que
    la respalde. Se enseña marcada de arriba abajo, que es la lectura honesta de lo que pasó."""
    p = portero(afirmaciones=[])
    tramos = p.alimentar("Una clave primaria identifica cada fila de la tabla.")
    assert respaldadas(tramos) == [False] and texto_de(tramos)
    assert len(p.huerfanas) == 1


def test_lo_huerfano_del_CIERRE_tambien_se_marca_y_tampoco_se_cuela_sin_marca():
    """El caso que se escapa fácil: la última frase casi nunca trae punto, y `cerrar` podría dejarla
    pasar sin juzgar 'porque es la última'. No es una excepción a la regla."""
    p = portero()
    p.alimentar("El teorema de Pitagoras relaciona catetos e hipotenusa")
    tramos = p.cerrar()
    assert texto_de(tramos), "la ultima frase se perdio: el cierre no puede podar"
    assert respaldadas(tramos) == [False]
    assert len(p.huerfanas) == 1


def test_la_ultima_frase_CUBIERTA_sale_SIN_marca_por_el_cierre():
    """La otra mitad: sin esto, el test de arriba pasaría con un `cerrar` que marcara siempre."""
    p = portero()
    p.alimentar("La sesion vive en el servidor")
    tramos = p.cerrar()
    assert texto_de(tramos) == "La sesion vive en el servidor"
    assert respaldadas(tramos) == [True] and p.emitidas == 1


def test_NINGUNA_frase_se_pierde_nunca():
    """LA PROPIEDAD QUE EL CAMBIO COMPRA, anclada como tal: lo que entra, sale. El defecto de
    experiencia —respuesta comida, párrafo con salto, pantalla en blanco— se va a CERO por
    construcción, y deja de depender de dónde esté el umbral."""
    entrada = ("La sesion vive en el servidor. El teorema de Pitagoras relaciona catetos. "
               "Vale. Y la cookie contiene el identificador")
    p = portero()
    visto = texto_de(p.alimentar(entrada)) + texto_de(p.cerrar())
    assert visto == entrada, "se perdio texto por el camino: el portero esta podando"


# --- lo que se declara ----------------------------------------------------------------------------

def test_el_umbral_va_declarado_SIN_CALIBRAR_y_el_estado_cuenta_las_dos_cosas():
    p = portero()
    p.alimentar("La sesion vive en el servidor. El teorema de Pitagoras relaciona catetos.")
    e = p.estado()
    # `frases_marcadas` sustituye a `frases_huerfanas` A PROPOSITO: ahora las marcadas TAMBIEN se
    # emiten, asi que los dos contadores dejaron de ser disjuntos y quien los sumara contaria de
    # mas. Las dos emitidas incluyen la marcada.
    assert e["frases_emitidas"] == 2 and e["frases_marcadas"] == 1
    # ACTUALIZADO tras el barrido del 14/08 (corridas 41-42): el umbral pasa de SIN CALIBRAR a
    # BARRIDO Y MANTENIDO en 0,50, y la procedencia lleva su RESERVA -al 0,50 ya se marcan 10-12
    # de 23 frases legitimas, o sea que el problema es QUE se mide-. Un test que siguiera anclando
    # "SIGUE SIN CALIBRAR" defenderia el mundo viejo contra su correccion.
    assert e["calibrado"] is True and "BARRIDO" in e["calibracion"]
    assert "RESERVA" in e["calibracion"], "el numero sin su reserva es media verdad"


def test_el_minimo_de_palabras_es_el_que_dice_la_constante():
    """Ancla la DECISIÓN: si alguien lo sube, que sea a propósito y sabiendo que cada punto de más
    convierte frases cortas legítimas en frases marcadas."""
    assert MINIMO_PALABRAS == 3


def test_una_frase_CORTA_no_cuenta_como_texto_ensenado():
    """EL FALLO QUE SE ESCONDIÓ MEDIO DÍA, anclado. Una frase de menos de `MINIMO_PALABRAS` palabras
    de contenido pasa **por diseño**, así que un punto suelto deja `emitidas` en 1 **con la pantalla
    vacía**. Cualquier comprobación de *"¿se enseñó algo?"* tiene que mirar `caracteres_emitidos`, no
    el contador de frases — y desde el 14/08 esa comprobación es la que dispara la abstención por
    prosa vacía, que es su único disparador posible ahora que nada se poda."""
    p = portero()
    p.alimentar(".")
    assert p.emitidas == 1, "el punto suelto pasa, y esta bien que pase"
    assert p.caracteres_emitidos == 1
    q = portero()
    q.alimentar("\n \n")
    assert q.caracteres_emitidos == 0, "espacios contando como texto ensenado"


def test_el_vocabulario_META_no_cuenta_para_el_solape():
    """El caso medido el 14/08/2026: *"…, según el fragmento F5962 del temario"* se podaba porque
    `según`, `fragmento` y `temario` no están en ninguna afirmación — **no pueden estarlo**, son la
    referencia a la fuente—. La medida castigaba a la prosa por citar su procedencia."""
    con_cita = "La sesion vive en el servidor, segun el fragmento F7 del temario."
    assert respaldadas(portero().alimentar(con_cita)) == [True], \
        "se marco una frase por citar su procedencia"
