"""El verificador NLI del 4.3: la SELECCIÓN DE FRASE y la política, sin cargar el modelo.

QUÉ CORRE AQUÍ Y QUÉ NO. Cargar mDeBERTa son 279 M de parámetros que el CI no tiene, así que lo que
se prueba es **todo lo que decide sin el modelo**: qué frase se le da, cuándo NO se le pregunta, y
qué se hace con cada etiqueta. Eso no es la parte fácil — es donde estaba el fallo:

**Con el fragmento entero como premisa, el NLI da `entailment 0.988` a una hipótesis que la premisa
no sostiene.** Medido con un caso plantado el 13 de agosto de 2026, y confirmado con el control de
darle solo el relleno. La ventana son 512 tokens totales y el 33 % de los fragmentos la desborda
ellos solos, así que la librería trunca en silencio. **La selección de frase no es una optimización:
es lo que hace que el veredicto signifique algo**, y por eso se prueba aquí y no en un humo.
"""
import pytest

from app.core.verificador_nli import (COBERTURA_MINIMA, CONTRADICCION, ENTAILMENT, NEUTRAL,
                                      NO_VERIFICABLE, PODADA, REINTENTO, VERIFICADA,
                                      VerificadorNLI, parece_codigo, seleccionar_frase)

RELLENO = ("El controlador recibe la peticion y delega en el servicio. El servicio contiene la "
           "logica de negocio y no sabe nada de HTTP. El repositorio habla con la base de datos. "
           ) * 14
COLA = "La sesion se almacena en el servidor y la cookie solo contiene el identificador."
HIPOTESIS = "Los datos de la sesion se guardan en el servidor."


def verificador_falso(etiqueta, probabilidad):
    """Un VerificadorNLI SIN modelo: `clasificar` devuelve lo que se le diga. La política es lo que
    se prueba, y la política no necesita 279 M de parámetros para equivocarse."""
    v = object.__new__(VerificadorNLI)
    v.umbral = 0.80
    v.clasificar = lambda premisa, hipotesis: (etiqueta, probabilidad)
    return v


# --- la selección de frase, que es donde estaba el fallo -----------------------------------------

def test_encuentra_la_frase_de_apoyo_AUNQUE_ESTE_AL_FINAL():
    """EL CASO PLANTADO, y la regresión del tope heredado.

    `mejor_par_de_frases` del 1.8 acota a las 12 primeras frases porque compara fragmento contra
    fragmento —O(n²)—. Aquí la comparación es fragmento contra hipótesis corta —O(n)— y ese mismo
    tope **tira la cola**: en este caso la frase de apoyo está en la posición 42 de 43."""
    frase, cobertura = seleccionar_frase(RELLENO + " " + COLA, HIPOTESIS)
    assert frase is not None and "sesion se almacena en el servidor" in frase, (
        f"se eligio otra frase: «{frase}». El tope del 1.8 no transfiere a este problema")
    assert cobertura > COBERTURA_MINIMA


def test_si_NO_hay_frase_relacionada_no_se_le_pregunta_al_NLI():
    """La otra dirección: sin esto, el test de arriba pasaría con un selector que devolviera
    siempre la última frase."""
    frase, cobertura = seleccionar_frase(RELLENO, HIPOTESIS)
    assert cobertura < 0.5, "el relleno no habla de sesiones y aun asi cubre la hipotesis"


def test_la_seleccion_es_ASIMETRICA_y_no_penaliza_las_frases_largas():
    """Se mide **cobertura de la hipótesis** y no Jaccard, porque la comparación es asimétrica:
    premisa larga contra hipótesis corta. Jaccard le restaría puntos a una frase por ser larga,
    que es justo lo contrario de lo que hace falta (principio 8)."""
    largo = ("La sesion se almacena en el servidor junto con muchos otros datos de la aplicacion "
             "que no vienen al caso pero alargan la frase considerablemente.")
    corto = "El repositorio habla con la base de datos."
    frase, _ = seleccionar_frase(f"{corto} {largo}", HIPOTESIS)
    assert frase == largo, "la frase correcta se descarto por ser larga"


# --- la política, con las cuatro salidas ----------------------------------------------------------

def test_entailment_por_encima_del_umbral_verifica():
    v = verificador_falso(ENTAILMENT, 0.95)
    assert v.verificar(HIPOTESIS, COLA)["veredicto"] == VERIFICADA


def test_entailment_POR_DEBAJO_del_umbral_no_verifica():
    """El umbral tiene que morder, o no es un umbral."""
    v = verificador_falso(ENTAILMENT, 0.70)
    assert v.verificar(HIPOTESIS, COLA)["veredicto"] == REINTENTO


def test_una_CONTRADICCION_poda_SIN_MIRAR_el_umbral():
    """Sección 8: `contradiction` poda siempre. Es la señal más cara de ignorar, y someterla a un
    umbral sería dejar pasar contradicciones detectadas por poco margen."""
    v = verificador_falso(CONTRADICCION, 0.35)
    r = v.verificar(HIPOTESIS, COLA)
    assert r["veredicto"] == PODADA and r["motivo"] == "contradice_al_fragmento"


def test_neutral_dispara_el_reintento_con_señal():
    v = verificador_falso(NEUTRAL, 0.99)
    assert v.verificar(HIPOTESIS, COLA)["veredicto"] == REINTENTO


# --- lo que NO se juzga, que es lo honesto -------------------------------------------------------

def test_el_CODIGO_no_entra_al_NLI_y_se_declara_no_verificable():
    """El 1.8 ya lo decidió con su test y aquí se hereda: un modelo entrenado en prosa sobre un
    bloque de Java da ruido con dos decimales, y aquí ese ruido sería un veredicto."""
    codigo = ('El metodo se declara asi: public String verCarrito(@SessionAttribute(name = '
              '"sesion") Map<Long, Item> carrito, Model model) { return "ver"; }')
    v = verificador_falso(ENTAILMENT, 0.99)
    r = v.verificar("La sesion guarda el carrito del usuario en el servidor.", codigo)
    assert r["veredicto"] == NO_VERIFICABLE and r["motivo"] == "contenido_es_codigo"


def test_sin_vocabulario_en_comun_se_declara_no_verificable_en_vez_de_inventar():
    v = verificador_falso(ENTAILMENT, 0.99)
    r = v.verificar("El teorema de Pitagoras relaciona los catetos con la hipotenusa siempre.",
                    RELLENO)
    assert r["veredicto"] == NO_VERIFICABLE and r["motivo"] == "sin_frase_relacionada"


def test_el_umbral_va_declarado_SIN_CALIBRAR():
    v = verificador_falso(ENTAILMENT, 0.95)
    r = v.verificar(HIPOTESIS, COLA)
    assert r["calibrado"] is False and r["calibracion"] == "encargo 4.6"
    assert r["umbral"] == pytest.approx(0.80)


# --- el detector de codigo, EN LAS DOS DIRECCIONES ------------------------------------------------
#
# La primera version heredo el detector del 1.8 tal cual y fallaba 3 de los 4 pares con
# identificadores del humo: caza `@\w+`, asi que marcaba como CODIGO una frase en prosa que
# MENCIONA una anotacion. En un corpus medio codigo eso es casi toda la prosa util, y el efecto era
# declarar `no_verificable` justo las afirmaciones mas tipicas de este temario.

PROSA_CON_IDENTIFICADORES = [
    "Para validar un formulario en un POST hay que anotar el parametro con @Valid y poner "
    "BindingResult justo detras.",
    "La anotacion @Repository marca el componente que accede a la base de datos del proyecto.",
    "El metodo findAll() devuelve todos los registros de la tabla sin ningun filtro aplicado.",
]

BLOQUES_DE_CODIGO = [
    '@GetMapping("/ver")\npublic String verCarrito(@SessionAttribute(name = "carrito") '
    'Map<Long, Item> carrito, Model model) {\n    return "carrito/ver";\n}',
    'if (carrito == null) {\n    carrito = new HashMap<>();\n    session.setAttribute("c", carrito);\n}',
]


@pytest.mark.parametrize("frase", PROSA_CON_IDENTIFICADORES)
def test_la_prosa_que_MENCIONA_identificadores_NO_es_codigo(frase):
    """LA DIRECCION QUE FALTABA, y la que habria cazado el fallo antes del humo. Sin ella, un
    detector que dijera "codigo" siempre pasaria el test de abajo con nota."""
    assert not parece_codigo(frase), (
        "una frase en prosa se clasifico como codigo por mencionar un identificador: en este corpus "
        "eso deja sin verificar justo las afirmaciones mas tipicas del temario")


@pytest.mark.parametrize("bloque", BLOQUES_DE_CODIGO)
def test_un_bloque_de_codigo_SI_es_codigo(bloque):
    assert parece_codigo(bloque)


def test_por_DEBAJO_del_suelo_NO_se_le_pregunta_al_NLI():
    """EL SUELO, y se prueba que corta ANTES de llamar al modelo y no despues de creerselo.

    El modo de fallo de este NLI ante un par malo no es abstenerse: es `entailment 0.988` sobre una
    premisa que no menciona el tema, medido. Asi que "darle el mejor par disponible" cuando el mejor
    par es malo no produce un neutral prudente: produce dos decimales de seguridad sobre nada. Mismo
    razonamiento que `fragmento_en_contexto` en el 4.2: cuando la precondicion del instrumento no se
    cumple, NO SE USA el instrumento."""
    llamadas = []
    v = object.__new__(VerificadorNLI)
    v.umbral = 0.80

    def espia(premisa, hipotesis):
        llamadas.append((premisa, hipotesis))
        return ENTAILMENT, 0.988          # lo que de verdad devuelve ante un par malo

    v.clasificar = espia
    r = v.verificar("El teorema de Pitagoras relaciona los catetos con la hipotenusa siempre.",
                    RELLENO)
    assert r["veredicto"] == NO_VERIFICABLE
    assert llamadas == [], "se consulto al NLI por debajo del suelo: su 0.988 habria pasado por bueno"
    assert r["calibrado"] is False and r["calibracion"] == "encargo 4.6"
    assert r["suelo"] == pytest.approx(COBERTURA_MINIMA)
