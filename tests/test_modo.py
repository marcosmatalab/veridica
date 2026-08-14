"""El clasificador de modo (5.1) contra SU RÚBRICA, cláusula a cláusula.

**LOS CASOS DE ESTE FICHERO SALEN DE `rubrica_modos.md`, NO DEL CONJUNTO CIEGO**, y eso es
deliberado: si los tests copiaran los 45 turnos, estarían anclando lo que mi clasificador contesta
hoy en vez de lo que la rúbrica manda, y el conjunto ciego dejaría de ser ciego — quedaría escrito
dentro de la suite con mis respuestas al lado. Aquí se comprueba la ESPECIFICACIÓN; el conjunto se
corre aparte y sus etiquetas las abre el propietario **después** de congelar esto.

Cada test cita su cláusula en el nombre, para que un rojo diga qué regla se ha roto y no solo que
algo cambió.
"""
import pytest

from app.core.modo import clasificar_modo


def modo(t):
    return clasificar_modo(t)["modo"]


# --- R1: contiene o declara un resultado, una respuesta o un intento -----------------------------

@pytest.mark.parametrize("turno", [
    "¿Está bien esto que he hecho?",          # el ejemplo literal de R1
    "Mira mi código y dime si va bien.",      # el otro ejemplo literal de R1
    "He puesto la anotación antes del parámetro.",
    "Me sale 4.096 y no lo veo claro.",
])
def test_R1_un_intento_declarado_manda_a_corregir(turno):
    """*«Aplica aunque esté redactado como pregunta y aunque el intento no venga pegado, siempre que
    el turno afirme que existe.»*"""
    assert modo(turno) == "corregir"


def test_R1_aplica_aunque_NO_haya_signo_de_interrogacion():
    """R1 dice *«aunque esté redactado como pregunta»*, de donde se sigue que también aplica cuando
    no lo está: **el signo de interrogación no es un rasgo**. Una afirmación suelta sobre el propio
    trabajo trae intento igual, y leerla como enunciado sería leer puntuación en vez de rasgos."""
    assert modo("Mi esquema pone que el controlador habla con la base de datos.") == "corregir"


# --- D1: intento + concepto -> corregir ----------------------------------------------------------

def test_D1_intento_mas_pregunta_de_concepto_gana_R1():
    """*«R1 gana: hay algo que evaluar, y evaluarlo no impide explicar.»* Sin este test, poner R3
    delante pasaría igual: la mayoría de los turnos con intento no preguntan además por un
    concepto."""
    r = clasificar_modo("He puesto /26 y me salen 64 direcciones. ¿Y por qué se usa /26?")
    assert r["modo"] == "corregir" and r["clausula"] == "R1 + D1"


# --- D4: manda el rasgo, no el verbo -------------------------------------------------------------

def test_D4_la_palabra_corregir_SIN_intento_no_es_corregir():
    """*«El turno usa la palabra "corregir" pero no hay intento → `acompanar`. Manda el rasgo, no el
    verbo.»* Es la trampa exacta de leer verbos: `no lo he hecho` **contiene** `he hecho`."""
    assert modo("Ayúdame a corregir el ejercicio 2, aún no lo he hecho.") == "acompanar"


def test_y_la_negacion_no_se_come_un_intento_que_SI_esta():
    """LA OTRA DIRECCIÓN, que es la que dice si la guarda de negación sirve: si mirase la frase
    entera en vez de la ventana anterior al rasgo, un `no` en cualquier sitio anularía un intento
    real y todo se iría a `acompanar` sin que el test de arriba se enterase."""
    assert modo("No entiendo la herencia, pero he escrito esto: class Coche extends Vehiculo {}") \
        == "corregir"


# --- D2: "cómo se hace X" en general -------------------------------------------------------------

def test_D2_un_ejercicio_mencionado_como_CONTEXTO_no_lo_convierte_en_acompanar():
    """El ejemplo literal de D2. **Y es el que obliga a que D2 se evalúe ANTES que R2**: con R2
    delante, la mención del ejercicio ganaba y salía `acompanar`, que es justo lo que este desempate
    existe para impedir."""
    r = clasificar_modo("¿Cómo se calcula una subred? Es para el ejercicio 5.")
    assert r["modo"] == "responder" and r["clausula"] == "D2"


# --- R2 y D3: ejercicio concreto -----------------------------------------------------------------

def test_R2_pedir_ayuda_con_un_ejercicio_concreto_sin_intento_es_acompanar():
    assert modo("¿Me ayudas a resolver el ejercicio 3 de la unidad 4?") == "acompanar"


def test_D3_pedir_la_SOLUCION_de_un_ejercicio_sigue_siendo_acompanar():
    """*«Que pida la solución es asunto de la POLÍTICA DEL MODO, no del clasificador: `acompanar` ya
    sabe no darla. Clasificar como `responder` para poder soltarla sería usar el clasificador para
    esquivar la regla pedagógica.»* Este test defiende una decisión PEDAGÓGICA desde el
    clasificador, y por eso es el que más fácil se rompería sin querer."""
    assert modo("Dame la solución del ejercicio de subredes.") == "acompanar"


# --- R3 y D5 -------------------------------------------------------------------------------------

@pytest.mark.parametrize("turno", [
    "¿Qué es una clave primaria?",
    "¿En qué se diferencian una cookie y una sesión?",
    "¿Cómo funciona el recolector de basura?",
])
def test_R3_las_preguntas_de_concepto_son_responder(turno):
    assert modo(turno) == "responder"


def test_D5_sin_ninguna_senal_se_elige_el_modo_MENOS_intrusivo():
    r = clasificar_modo("Hola, buenas tardes.")
    assert r["modo"] == "responder" and r["clausula"] == "D5"


# --- D6: el modo que no existe -------------------------------------------------------------------

def test_D6_pedir_examen_cae_a_responder_Y_LO_DICE():
    """*«El modo `examinar` está DISEÑADO Y NO CONSTRUIDO, así que cae a `responder` por D5, y el
    sistema debe decir que ese modo no existe.»*

    **Las dos mitades tienen que cumplirse, y la segunda es la que se olvida**: sin la bandera, el
    turno sale como una consulta normal y el alumno no se entera de que ha pedido algo que no hay —
    que es la forma exacta de una capacidad declarada y no construida pasando por construida.
    """
    r = clasificar_modo("¿Puedes ponerme un ejercicio de subredes para practicar?")
    assert r["modo"] == "responder"
    assert r["examen_no_construido"] is True, "cae a responder sin decir que `examinar` no existe"


def test_una_consulta_normal_NO_levanta_la_bandera_de_examinar():
    """La otra dirección de la bandera: si se levantara siempre, el aviso dejaría de significar
    nada y el test de arriba pasaría igual."""
    assert clasificar_modo("¿Qué es una subred?")["examen_no_construido"] is False


# --- lo que el clasificador devuelve, que no es solo el modo -------------------------------------

def test_devuelve_los_rasgos_para_poder_auditarlo_caso_a_caso():
    """Un clasificador que solo dice su veredicto no se puede leer a ojo, y aquí la lectura de los
    fronterizos es la mitad del trabajo. Devuelve TODOS los rasgos, no solo el que ganó."""
    r = clasificar_modo("He puesto /26. ¿Por qué se usa /26?")
    assert set(r["rasgos"]) == {"trae_intento", "ejercicio_concreto", "pregunta_de_concepto",
                                "como_se_hace_general", "pide_examen"}
    assert r["rasgos"]["trae_intento"] and r["rasgos"]["pregunta_de_concepto"]
