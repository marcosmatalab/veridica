"""El verificador de cálculo del 4.4, en las dos direcciones y con las tres puertas.

Lo que aquí se ancla no son "casos que pasan": son las **decisiones** del encargo, cada una con el
caso que la obligó. Si alguien cambia una de ellas, este fichero se pone rojo y dice cuál.
"""
import time

import pytest
import sympy

from app.core.verificador_calculo import (MAX_DIGITOS, NO_VERIFICABLE, PODADA, VERIFICADA, _INERTE,
                                          admisible, comparar, evaluar, verificar)


def v(expresion, afirmado="1"):
    return verificar({"expresion": expresion, "resultado_afirmado": afirmado})


# --- lo que la sección 8 pide: correcto pasa, incorrecto poda -------------------------------------

@pytest.mark.parametrize("expresion,afirmado", [
    ("2+2", "4"),
    ("(255-192)+1", "64"),
    ("2**32", "4294967296"),
    ("binomial(7,2)", "21"),
    ("factorial(20)", "2432902008176640000"),
    ("sqrt(16)", "4"),
    ("1024*1024", "1048576"),
])
def test_un_calculo_correcto_PASA(expresion, afirmado):
    assert v(expresion, afirmado)["veredicto"] == VERIFICADA


@pytest.mark.parametrize("expresion,afirmado", [
    ("2+2", "5"),
    ("10/3", "3,5"),
    ("binomial(7,2)", "20"),
    ("2**32", "4294967295"),
])
def test_un_calculo_INCORRECTO_poda(expresion, afirmado):
    assert v(expresion, afirmado)["veredicto"] == PODADA


def test_la_aritmetica_CON_OPERADORES_se_verifica_y_no_sale_no_verificable():
    """REGRESIÓN DE UN FALLO QUE NO REVENTABA: el parseo del guarda reescribe `2+2` como
    `Add(Integer(2), Integer(2))`, así que `Add`, `Mul` y `Pow` tienen que estar en el espacio de
    nombres interno. Faltaban, y el resultado no era una excepción: era `no_verificable`, un
    veredicto **legítimo**. O sea que toda la aritmética con operadores —toda— salía sin verificar
    con la cara tranquila de lo que se abstiene con prudencia."""
    assert v("2+2", "4")["veredicto"] == VERIFICADA
    assert v("10/2", "5")["veredicto"] == VERIFICADA
    assert v("3*3", "9")["veredicto"] == VERIFICADA


# --- lo que NO se puede comprobar: `no_verificable`, JAMÁS `podada` -------------------------------

@pytest.mark.parametrize("expresion", [
    "for i in range(10): print(i)",
    "sum([x for x in range(10)])",
    '__import__("os").system("dir")',
    "lambda x: x+1",
    "int(input())",
    "x + 1",
    "2 == 2",
])
def test_lo_que_no_se_puede_comprobar_NO_SE_PODA(expresion):
    """LA DISTINCIÓN QUE MÁS IMPORTA DE ESTE MÓDULO. *"No he podido comprobarlo"* no es *"es
    falso"*: el código no se verifica porque el sandbox está **declarado y no construido**, o sea
    que podarlo sería castigar al modelo por una capacidad que decidimos nosotros no construir. Y
    además envenenaría la tasa de poda del 4.6 con casos que no son podas.

    Es el `else` cómodo que se cuela solo, y por eso tiene test propio."""
    resultado = v(expresion, "10")
    assert resultado["veredicto"] == NO_VERIFICABLE, "una expresion no comprobable NO se poda"


def test_el_null_del_contrato_se_respeta_en_vez_de_castigarse():
    """El 7bis al derecho: al campo se le dio forma de decir *"mi resultado no es un número"*, así
    que cuando lo dice se le cree. Podar aquí sería volver a dejarlo sin salida honesta."""
    r = v("2+2", None)
    assert r["veredicto"] == NO_VERIFICABLE and r["motivo"] == "sin_resultado_afirmado"


def test_dividir_por_cero_no_es_una_poda():
    assert v("10/0", "5")["veredicto"] == NO_VERIFICABLE


# --- la guarda: qué para, y que lo pare DEPRISA ---------------------------------------------------

@pytest.mark.parametrize("bomba", [
    "2**2**2**30",
    "10**999999999",
    "factorial(100000)",
    "factorial(100000)/factorial(100000)",     # la cancelación: magnitud final 0, coste enorme
    "binomial(10**9,10**8)",
    "sin(10**900)",
    "exp(10**6)",
])
def test_la_guarda_para_la_bomba_y_la_para_rapido(bomba):
    """Rechazarla no basta: **hay que rechazarla deprisa**. Una guarda que tarda tres segundos en
    decir que no es la misma denegación de servicio que pretendía evitar, con otro nombre. El peor
    rechazo medido son 0,24 ms; el margen de este test es cien veces mayor a propósito, para que
    falle solo cuando algo se rompa de verdad y no cuando la máquina esté ocupada."""
    t = time.perf_counter()
    r = v(bomba)
    assert r["veredicto"] == NO_VERIFICABLE
    assert (time.perf_counter() - t) < 1.0, "la guarda ha tardado demasiado en decir que no"


def test_la_guarda_NO_evalua_nada_durante_su_propia_pasada():
    """REGRESIÓN DEL BOQUETE GORDO: `evaluate=False` desactiva los **operadores**, no las **llamadas
    a función**, así que `factorial(100000)` se calculaba dentro del parseo del guarda —antes de que
    el guarda pudiera mirarlo—. Por eso la pasada del guarda usa funciones **indefinidas**, que
    construyen un nodo y no calculan nada."""
    assert _INERTE["factorial"] is not sympy.factorial
    assert _INERTE["binomial"] is not sympy.binomial
    nodo = _INERTE["factorial"](sympy.Integer(100000))
    assert nodo.func.__name__ == "factorial" and nodo.args == (sympy.Integer(100000),)


def test_el_nan_no_se_cuela_por_la_comparacion_del_tope():
    """`0.0 * inf` da `nan`, y **`nan` no es mayor que nada**: atraviesa el `>` del tope sin
    despeinarse.

    **SE PRUEBA LA COMPROBACIÓN, NO UNA EXPRESIÓN QUE LA ROCE.** La primera versión de este test
    afirmaba `2**2**2**30 -> no_verificable`, y pasaba **igual con la comprobación quitada**: una vez
    arreglado `_digitos`, esa torre se caza antes por el exponente, así que el test daba verde sobre
    código mutado. Era exactamente la trampa que este repo persigue, cometida dentro de la
    herramienta de comprobar. Ahora se llama a la función del tope con un `nan` en la mano."""
    from app.core.verificador_calculo import Desbordada, _dentro_del_tope
    with pytest.raises(Desbordada):
        _dentro_del_tope(float("nan"))
    assert _dentro_del_tope(10.0) == 10.0                 # y la otra mitad: lo finito pasa


def test_los_digitos_llevan_la_PARTE_DECIMAL_del_logaritmo():
    """REGRESIÓN DEL AGUJERO MÁS GRANDE DE LA GUARDA. Contar cifras (`len(str(n)) - 1`) es el log10
    redondeado hacia abajo, y para la base 2 da **0**. Como la magnitud de una potencia es
    `log10(base) * exponente`, ese cero se multiplica por el exponente: **`2**999999999` salía con
    magnitud cero y la guarda lo daba por inofensivo**. Un error de 0,3 en la base es un error sin
    techo en el resultado."""
    from app.core.verificador_calculo import _digitos
    assert _digitos(sympy.Integer(2)) == pytest.approx(0.301, abs=0.001), "el log10 esta truncado"
    assert v("2**999999999")["veredicto"] == NO_VERIFICABLE


def test_lo_que_cabe_justo_por_debajo_del_tope_SI_se_verifica():
    """La otra mitad, sin la cual el test de arriba pasaría con una guarda que rechace todo. El tope
    tiene que dejar sitio a la criptografía de ASIR: `2**2048` son 617 cifras."""
    assert MAX_DIGITOS >= 617
    assert v("2**2048", str(2**2048))["veredicto"] == VERIFICADA


def test_una_funcion_sin_crecimiento_declarado_se_rechaza_en_vez_de_adivinarse():
    """Si mañana alguien mete una función nueva en la lista blanca sin declarar cómo crece, lo que
    tiene que salir es `no_verificable`, no un hueco por el que pase una bomba."""
    from app.core import verificador_calculo as vc
    original = dict(vc._INERTE)
    try:
        vc._INERTE["gamma"] = sympy.Function("gamma")
        vc.PERMITIDO["gamma"] = sympy.gamma
        with pytest.raises(Exception, match="funcion_sin_crecimiento_declarado"):
            evaluar("gamma(5)")
    finally:
        vc._INERTE.clear()
        vc._INERTE.update(original)
        vc.PERMITIDO.pop("gamma", None)


# --- la tolerancia, DERIVADA de lo que el modelo escribió ------------------------------------------

def test_la_tolerancia_sale_de_los_DECIMALES_ESCRITOS_y_por_eso_el_campo_es_cadena():
    """**EL TEST QUE SOSTIENE LA DECISIÓN DEL CONTRATO.** `2/3` es 0,666…: afirmarlo como `0,7` es
    correcto con un decimal, y afirmarlo como `0,70` es incorrecto con dos —porque con dos, lo
    correcto es 0,67—. Los dos valores son **el mismo `float`**, así que con un campo numérico esta
    distinción no se puede hacer: el dato que decide el veredicto se habría perdido al parsear."""
    assert v("2/3", "0,7")["veredicto"] == VERIFICADA
    assert v("2/3", "0,67")["veredicto"] == VERIFICADA
    assert v("2/3", "0,70")["veredicto"] == PODADA


def test_un_resultado_MAL_FORMADO_no_es_una_poda_y_este_caso_es_real():
    """EL FALLO QUE MÁS CARO HABRÍA SALIDO, y lo encontró el humo con el proveedor de verdad.

    Con el punto como separador decimal, el modelo quiso escribir `4.294.967.296` —así salió en la
    prosa de esa misma respuesta— y la decodificación restringida, que permite **un** punto y no dos,
    dejó `4.294967296`: **un número gramatical y equivocado**. El veredicto era `podada`, o sea *"el
    alumno se ha equivocado"*, cuando el alumno tenía razón y quien había roto el número era nuestra
    propia gramática. Ahora el separador es la coma —los puntos de millar son ingramáticos desde el
    primer carácter— y un valor mal formado sale `no_verificable`, que es lo que es: un error de
    transporte, no un juicio sobre quien responde."""
    r = v("2^32", "4.294967296")
    assert r["veredicto"] == NO_VERIFICABLE and r["motivo"] == "resultado_mal_formado"
    assert v("2^32", "4294967296")["veredicto"] == VERIFICADA


def test_los_TRES_FORMATOS_de_numero_espanol_y_el_que_rompio():
    """EL ARREGLO DEL NÚMERO FALSO INTRODUJO UNA RESPONSABILIDAD NUEVA EN EL SERVIDOR —parsear un
    número con convención española— y por eso lleva test propio con los tres formatos.

    Y la lección que generaliza, escrita donde se comprueba: **un patrón que acota una salida cercana
    al lenguaje natural está codificando una convención cultural.** El nuestro decidió sin querer que
    los números se escriben a la inglesa, y lo mismo espera con fechas, decimales y unidades.
    """
    #  1. entero sin separadores: lo que el contrato pide y lo que ahora llega de verdad
    assert v("2^32", "4294967296")["veredicto"] == VERIFICADA
    #  2. el que ROMPIÓ: con punto de millar el modelo escribía 4.294.967.296 y la gramática dejaba
    #     `4.294967296`. Hoy es ingramático, y si llegara igual NO se juzga al alumno.
    roto = v("2^32", "4.294967296")
    assert roto["veredicto"] == NO_VERIFICABLE and roto["motivo"] == "resultado_mal_formado"
    assert v("2^32", "4.294.967.296")["motivo"] == "resultado_mal_formado"
    #  3. decimal con coma, que es como se escribe aquí
    assert v("314/100", "3,14")["veredicto"] == VERIFICADA
    assert v("314/100", "3,15")["veredicto"] == PODADA


def test_el_empate_se_redondea_MEDIA_HACIA_ARRIBA_y_solo_asi():
    """UNA convención, no dos (ADR 0018). **Aceptar las dos era aceptar una banda más ancha que
    cualquiera de ellas**: `50 * 1,21 = 60` salía verificada porque 60,5 al par a cero decimales es
    60 — encontrado escribiendo el test del cálculo no declarado, el 14/08. Aquí el falso positivo es
    el caro —dar por buena una cuenta que no sale—, así que se queda la estricta, la del alumno con
    lápiz: media hacia arriba. El precio declarado: quien redondee al par (`1/8` → `0,12`) se poda,
    y ese trade-off vive en el ADR, no escondido en el código."""
    assert v("1/8", "0,13")["veredicto"] == VERIFICADA
    assert v("1/8", "0,12")["veredicto"] == PODADA, "el redondeo al par ya no es una segunda salida"
    assert v("1/8", "0,11")["veredicto"] == PODADA
    # El caso exacto que forzó la decisión, anclado tal cual:
    assert v("50 * 1,21", "60")["veredicto"] == PODADA, "60,5 no es 60: la banda doble ha vuelto"
    assert v("50 * 1,21", "61")["veredicto"] == VERIFICADA
    assert v("50 * 1,21", "60,5")["veredicto"] == VERIFICADA


def test_un_entero_grande_se_compara_EXACTO_y_no_por_aproximacion():
    """Por encima de 2^53 un `float` deja de representar los enteros uno a uno, y en un temario con
    combinatoria eso no es teórico. La comparación exacta va por `Rational`, que no tiene techo."""
    grande = 2**60 + 1
    assert v("2**60+1", str(grande))["veredicto"] == VERIFICADA
    assert v("2**60+1", str(grande + 1))["veredicto"] == PODADA
    assert comparar(evaluar("2**60+1"), str(grande)) == (True, "exacta")


def test_el_veredicto_dice_QUE_recalculo_y_no_solo_que_no_coincide():
    """Una poda sin el número recalculado al lado es imposible de auditar: la traza tiene que poder
    contestar *"¿qué salió y qué decía?"* sin volver a correr nada."""
    r = v("2+2", "5")
    assert r["recalculado"] == "4" and r["resultado_afirmado"] == "5"


def test_la_coma_decimal_de_la_EXPRESION_solo_se_convierte_cuando_no_hay_ambiguedad():
    """SALE DE LOS DATOS: en el humo real, las tres respuestas que calcularon con decimales
    escribieron `250 + 52,5`. El modelo redacta en español y escribe los números en español, también
    dentro de un campo que nosotros pensábamos como notación de programación.

    Y la regla es **exacta, no heurística**: solo se convierte si no hay ni una letra. Sin nombres de
    función una coma no puede separar argumentos —no hay a qué separar—, así que solo puede ser
    decimal. Con letras no se toca, porque ahí sí significa otra cosa."""
    assert v("250 + 52,5", "302,5")["veredicto"] == VERIFICADA
    assert v("binomial(7,2)", "21")["veredicto"] == VERIFICADA, "se rompio el separador de argumentos"
    assert v("7! / (2! * (7-2)!)", "21")["veredicto"] == VERIFICADA


def test_las_expresiones_REALES_del_humo_se_verifican():
    """Las cinco que el proveedor escribió de verdad el 13/08/2026. Si una deja de pasar, el
    verificador ha dejado de entender lo que el modelo escribe — que es distinto de estar roto, y
    más fácil de no notar."""
    for expresion, afirmado in [("2^32", "4294967296"), ("64 - 2", "62"),
                                ("7! / (2! * (7-2)!)", "21"), ("250 * (21 / 100)", "52,5"),
                                ("250 + 52,5", "302,5")]:
        assert v(expresion, afirmado)["veredicto"] == VERIFICADA, expresion


# --- las dos primeras puertas, antes de sympy -----------------------------------------------------

@pytest.mark.parametrize("expresion,motivo", [
    ("2 + __class__", "caracter_no_aritmetico"),
    ("open('x')", "caracter_no_aritmetico"),
    ("2 ; 3", "caracter_no_aritmetico"),
    ("eval(2)", "nombre_no_permitido"),
    ("Symbol('x')", "caracter_no_aritmetico"),
    ("9" * 500, "expresion_demasiado_larga"),
])
def test_la_lista_blanca_para_lo_que_no_es_aritmetica(expresion, motivo):
    """Las dos primeras puertas son de lista blanca —lo que no está, no pasa— y no de lista negra.
    Una lista negra hay que acertarla entera; una lista blanca hay que acertarla una vez."""
    ok, m = admisible(expresion)
    assert not ok and m == motivo


# --- la cuenta que NO se declaro como cuenta (14 de agosto) ----------------------------------------

def test_una_cuenta_escrita_en_un_ANDAMIAJE_se_recalcula_igual():
    """**EL `tipo` ES UNA AFIRMACIÓN DEL MODELO SOBRE SU PROPIA SALIDA**, y la verificación se
    despachaba sobre él sin comprobarlo. Fiarse de la etiqueta para decidir SI se verifica es
    pedirle al productor que diga cuándo hay que comprobarlo — el eco que el principio 6 rechaza.

    Medido: de 629 afirmaciones reales, 4 `andamiaje` y 1 `conocimiento` llevaban una cuenta con `=`
    dentro de su texto, incluida la derivación fabricada que cazó el conjunto del 5.0."""
    from app.core.verificador_calculo import verificar_texto
    v = verificar_texto("el numero de equipos utiles en una subred es 64 - 2 = 62", "andamiaje")
    assert v is not None and v["calculo_no_declarado"] is True and v["tipo_declarado"] == "andamiaje"
    # `50 * 1,21 = 60` salia VERIFICADA con la manga ancha de dos convenciones (60,5 al par a cero
    # decimales es 60): fue escribir este test lo que la destapo, y el ADR 0018 fijo media-hacia-
    # arriba el mismo dia. Se ancla aqui el caso que la destapo, ademas de en su propio test.
    malo = verificar_texto("El calculo es 50 * 1,21 = 60", "conocimiento")
    assert malo["veredicto"] == PODADA, "una cuenta que no sale, colada como conocimiento, pasa"
    # Y EL LIMITE, EN EL MISMO TEST PARA QUE NO SE LEA DE MAS: si la prosa de delante lleva numeros,
    # la extraccion se ensucia y sale `no_verificable`. Es el precio declarado de detectar de mas.
    sucio = verificar_texto("Un articulo de 50 euros sale por 50 * 1,21 = 61 euros", "conocimiento")
    assert sucio["veredicto"] == NO_VERIFICABLE


def test_la_deteccion_es_GENEROSA_y_lo_que_no_parsea_no_se_poda():
    """La asimetría que la distingue de la extracción que el ADR 0016 evitó: allí una extracción mala
    producía un **veredicto falso**; aquí produce un *"no pude comprobarlo"*. Un falso positivo del
    detector cuesta un intento de parseo; un falso negativo deja pasar una cuenta inventada."""
    from app.core.verificador_calculo import verificar_texto
    v = verificar_texto("en una subred /26 caben 64 - 2 = 62 equipos", "andamiaje")
    assert v["veredicto"] == NO_VERIFICABLE, "el /26 ensucia la expresion y aun asi se PODA"


def test_el_alcance_del_detector_va_declarado_y_el_igual_es_una_COTA_INFERIOR():
    """`=` no es toda la aritmética. Esto **no cierra** el agujero, lo estrecha, y leerlo como
    "ya cubrimos la aritmética encubierta" sería el verde mentiroso de siempre."""
    from app.core.verificador_calculo import cuenta_en_el_texto
    assert cuenta_en_el_texto("El doble de 40 son 80.") is None
    assert cuenta_en_el_texto("Un 21 % de 100 euros son 21 euros.") is None
    assert cuenta_en_el_texto("160 horas - 20 horas = 140 horas") is not None


def test_el_contador_de_operandos_ve_el_caso_real_y_calla_en_el_sano():
    """**EL RECÁLCULO COMPRUEBA LA OPERACIÓN, NO LOS OPERANDOS.** Un operando inventado con
    aritmética correcta sale `verificada` —"160 − 20 = 140" cuadra; lo fabricado era el 20—, y ese
    es el modo de fallo MÁS probable de un modelo: inventar la premisa, no sumar mal. El contador
    marca en la traza los `calculo` cuyos operandos no están en su fuente. No es una puerta.

    La sonda se valida EN LAS DOS DIRECCIONES, que es la regla del repo: el caso sano en vacío y el
    caso real del 5.0 en rojo, ANTES de creerse ningún verde."""
    from app.core.verificador_calculo import operandos_sin_fuente
    fragmento = "Una jornada son 40 horas semanales y el proyecto dura 4 semanas completas."
    # sano: todos los operandos vienen del fragmento -> lista vacia
    assert operandos_sin_fuente("4 * 40", [fragmento]) == []
    # la sonda vista en ROJO con el caso real: ni el 160 ni el 20 estan en la fuente
    assert operandos_sin_fuente("160 - 20", [fragmento, "¿Cuántas horas quedan?"]) == ["160", "20"]
    # y con el 160 como resultado de una afirmacion anterior de la misma respuesta, queda el 20:
    # exactamente el operando fabricado, señalado
    assert operandos_sin_fuente("160 - 20", [fragmento, "160"]) == ["20"]


def test_el_contraste_de_operandos_respeta_FRONTERAS_y_las_dos_grafias():
    """Sin frontera, el `4` se "encuentra" dentro del `40` y el contador se queda ciego justo donde
    mira; sin las dos grafías, `52,5` no casa con el `52.5` de un fragmento escrito a la inglesa."""
    from app.core.verificador_calculo import operandos_sin_fuente
    assert operandos_sin_fuente("400 + 4", ["hay 40 equipos y 4 salas"]) == ["400"]
    assert operandos_sin_fuente("664", ["el coseno mediano es 0,664"]) == ["664"]
    assert operandos_sin_fuente("52,5 + 250", ["el complemento es 52.5 sobre 250 euros"]) == []


def test_un_andamiaje_con_una_cuenta_deja_de_RESPALDAR_la_prosa():
    """El agujero eran DOS privilegios: no se verifica **y** cuenta como respaldo de cobertura. Una
    cuenta metida ahí no solo esquivaba al verificador — encima **autorizaba prosa**."""
    from app.core.cobertura import PorteroDeFrases
    con_cuenta = [{"id": 1, "tipo": "andamiaje",
                   "texto": "El numero de equipos utiles en la subred es 64 - 2 = 62 equipos."}]
    sin_cuenta = [{"id": 1, "tipo": "andamiaje",
                   "texto": "El numero de equipos utiles en la subred son sesenta y dos equipos."}]
    frase = "En la subred caben sesenta y dos equipos utiles disponibles."
    # ACTUALIZADO EL 14/08 (el portero MARCA en vez de podar): lo que se comprueba sigue siendo
    # exactamente lo mismo -si ese andamiaje RESPALDA la prosa o no-, pero ya no se lee en si la
    # frase sale, porque ahora sale siempre: se lee en su marca. El fallo que ancla es el mismo.
    assert PorteroDeFrases(sin_cuenta).alimentar(frase)[0]["respaldada"] is True, \
        "el andamiaje normal ya no respalda"
    assert PorteroDeFrases(con_cuenta).alimentar(frase)[0]["respaldada"] is False, \
        "un andamiaje con una cuenta dentro sigue autorizando prosa"
