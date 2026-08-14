"""La regla de cobertura del 4.5, comprobada **frase a frase** y en las dos direcciones.

POR QUÉ ESTE MÓDULO EXISTE, en una línea: la prosa se emite en streaming, así que si la cobertura se
comprobara al final, podar significaría **retirar texto que el alumno ya ha leído**. Como las
afirmaciones están cerradas **antes** de que empiece la prosa, se comprueba frase a frase según se
escriben: cuesta **una frase de retraso** en vez de la espera entera.

**Y LA ASIMETRÍA AQUÍ ES DISTINTA de la del 4.2 y el 4.3, que es lo que hace estos tests
importantes.** Allí el falso negativo era barato. Aquí **poda una frase legítima de un texto que
alguien está leyendo y deja un agujero en mitad de un párrafo**: se ve. Por eso hay tantos tests de
la dirección "no podar de más" como de la otra.
"""
from app.core.cobertura import MINIMO_PALABRAS, PorteroDeFrases

AFIRMACIONES = [
    {"id": 1, "tipo": "literal", "texto": "La sesion vive en el servidor.",
     "cita": "la cookie solo contiene el identificador"},
    {"id": 2, "tipo": "andamiaje", "texto": "Vamos por partes con las cookies."},
]


def portero(afirmaciones=None, solape=0.5):
    return PorteroDeFrases(AFIRMACIONES if afirmaciones is None else afirmaciones, solape)


# --- que deje pasar lo cubierto (la dirección cara aquí) -----------------------------------------

def test_una_frase_respaldada_sale_EN_CUANTO_cierra():
    """No al final: en cuanto se cierra la frase. Esa es la diferencia entre una frase de retraso y
    esperar la redacción entera."""
    p = portero()
    assert p.alimentar("La sesion vive en el servidor") == ""
    assert p.alimentar(".") == "La sesion vive en el servidor."
    assert p.emitidas == 1 and p.huerfanas == []


def test_la_CITA_tambien_respalda_y_no_solo_el_texto_de_la_afirmacion():
    """REGRESIÓN DE UN FALSO NEGATIVO POR CONSTRUCCIÓN, encontrado por el primer test que se corrió.

    La prosa *"la cookie lleva solo el identificador"* se podaba porque ninguna afirmación tenía
    `cookie` en su `texto`… y sí la tenía en su `cita`, que es contenido **declarado en el contrato
    y verificado letra a letra** por el 4.2. Si algo puede respaldar una frase, es precisamente lo
    que está comprobado contra el temario."""
    p = portero()
    salida = p.alimentar("La cookie contiene el identificador.")
    assert salida, "se podo una frase respaldada por la CITA de una afirmacion"


def test_una_frase_CORTA_no_se_juzga_y_pasa():
    """*"Vamos por partes."* no tiene vocabulario suficiente para cubrirse, así que juzgarla sería
    podarla siempre: el falso negativo por construcción, otra vez."""
    p = portero()
    assert p.alimentar("Vale.") == "Vale."
    assert p.huerfanas == []


def test_el_ANDAMIAJE_respalda_y_sin_el_la_regla_se_lleva_las_transiciones():
    """La excepción del andamiaje no es un permiso: es lo que evita el falso negativo MASIVO. Sin
    ella, la regla se llevaría por delante todas las transiciones y preguntas al alumno, dejando una
    respuesta correcta y mutilada."""
    con = portero().alimentar("Vamos por partes con las cookies.")
    sin = portero(afirmaciones=[AFIRMACIONES[0]]).alimentar("Vamos por partes con las cookies.")
    assert con, "el andamiaje declarado no respaldo su propia frase"
    assert not sin, "sin el andamiaje la frase pasaria igual: la excepcion no esta haciendo nada"


# --- que NO deje pasar lo huérfano ----------------------------------------------------------------

def test_una_frase_SIN_respaldo_no_sale_y_se_anota():
    p = portero()
    assert p.alimentar("El teorema de Pitagoras relaciona catetos e hipotenusa.") == ""
    assert len(p.huerfanas) == 1
    assert p.huerfanas[0]["solape"] < 0.5


def test_sin_NINGUNA_afirmacion_no_sale_prosa():
    """Una respuesta con prosa y cero afirmaciones viola la regla entera: no hay nada declarado que
    la respalde. Es incómodo y es correcto."""
    p = portero(afirmaciones=[])
    assert p.alimentar("Una clave primaria identifica cada fila de la tabla.") == ""
    assert len(p.huerfanas) == 1


def test_lo_huerfano_se_queda_dentro_y_no_se_cuela_por_el_cierre():
    """El caso que se escapa fácil: la última frase casi nunca trae punto, y `cerrar` podría dejarla
    pasar sin juzgar 'porque es la última'. No es una excepción a la regla."""
    p = portero()
    p.alimentar("El teorema de Pitagoras relaciona catetos e hipotenusa")
    assert p.cerrar() == ""
    assert len(p.huerfanas) == 1


def test_la_ultima_frase_CUBIERTA_si_sale_por_el_cierre():
    """La otra mitad: sin esto, el test de arriba pasaría con un `cerrar` que tirara siempre."""
    p = portero()
    p.alimentar("La sesion vive en el servidor")
    assert p.cerrar() == "La sesion vive en el servidor"
    assert p.emitidas == 1


# --- lo que se declara ----------------------------------------------------------------------------

def test_el_umbral_va_declarado_SIN_CALIBRAR_y_el_estado_cuenta_las_dos_cosas():
    p = portero()
    p.alimentar("La sesion vive en el servidor. El teorema de Pitagoras relaciona catetos.")
    e = p.estado()
    assert e["frases_emitidas"] == 1 and e["frases_huerfanas"] == 1
    # ACTUALIZADO EN EL 2.5: sigue SIN CALIBRAR -eso no ha cambiado y por eso el `False` se queda-,
    # pero la procedencia dice ahora QUE FALTABA. El 4.6 lo declaro como "la prosa no se persiste" y
    # al ir a construir la traza resulto ser mas fino: el denominador estaba y faltaba el VALOR del
    # solape por frase. Un texto de procedencia que se queda con el diagnostico viejo manda a quien
    # lo lea a arreglar lo que ya estaba bien.
    assert e["calibrado"] is False and "SIGUE SIN CALIBRAR" in e["calibracion"]
    assert "solape de CADA frase" in e["calibracion"]


def test_el_minimo_de_palabras_es_el_que_dice_la_constante():
    """Ancla la DECISIÓN: si alguien lo sube, que sea a propósito y sabiendo que cada punto de más
    convierte frases cortas legítimas en agujeros."""
    assert MINIMO_PALABRAS == 3

def test_una_frase_CORTA_no_cuenta_como_texto_ensenado():
    """EL FALLO QUE SE ESCONDIÓ MEDIO DÍA, anclado. Una frase de menos de `MINIMO_PALABRAS` palabras
    de contenido pasa **por diseño** —podar *"Vale."* sería el falso negativo por construcción—, así
    que un punto suelto deja `emitidas` en 1 **con la pantalla vacía**. Cualquier comprobación de
    *"¿se enseñó algo?"* tiene que mirar `caracteres_emitidos`, no el contador de frases."""
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
    p = portero()
    con_cita = "La sesion vive en el servidor, segun el fragmento F7 del temario."
    assert p.alimentar(con_cita), "se podo una frase por citar su procedencia"
