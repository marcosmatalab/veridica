"""Clasificación del MODO desde el turno del alumno (encargo 5.1), POR REGLAS sobre rasgos.

## Qué es esto y contra qué se implementa

Contra `rubrica_modos.md`, que es la **especificación** y la escribió el propietario ANTES de
redactar ninguna pregunta. **Este módulo no implementa mi intuición sobre qué modo pide un turno:
implementa R1-R3 y D1-D6.** Cada regla de abajo cita su cláusula, y esa es la disciplina: si un caso
concreto sale raro pero la rúbrica lo manda, sale así y se anota; **si un cambio no puede citar una
cláusula, no se hace** — sería ajustar el clasificador a los casos que tengo delante, que es
exactamente el sesgo que el conjunto ciego existe para evitar.

## Por qué REGLAS y no un modelo, dicho antes de medir nada

Es lo que ya pasó con el detector de código, donde la densidad de marcas ganó al `@\\w+` heredado.
Unas reglas sobre rasgos estructurales son **gratis en latencia, inspeccionables y no pueden
alucinar**, y esto corre en cada consulta antes de tocar el proveedor. **Un modelo entra solo si las
reglas se quedan cortas Y el número lo justifica**, y esa decisión se toma con la tabla delante.

## Los rasgos son PROPIEDADES DEL TEXTO, no juicios de valor

Es lo que hace el problema casi mecánico y encoge el problema de independencia del etiquetado: dos
personas leyendo *"¿está bien esto que he hecho?"* ven el mismo rasgo —**el turno declara que existe
un intento**— aunque discrepen sobre qué debería hacer el sistema con él.

## LO QUE ESTE MÓDULO NO SABE, y va aquí para que no se lea de más

- **No sabe si el alumno acertó**: `corregir` significa *"hay algo que evaluar"*, no *"está mal"*.
- **No decide política**: que un turno pida la solución de un ejercicio lo manda a `acompanar` (D3),
  y es `acompanar` quien sabe **no darla**. Clasificar como `responder` para poder soltarla sería
  usar el clasificador para esquivar la regla pedagógica.
- **No es multiturno.** Lee UN turno. El modo `acompanar` está diseñado para una conversación que
  el sistema hoy no puede tener, y eso es el límite grande del proyecto, declarado y no construido.
- **Y lo que su número NO va a significar**, escrito antes de medirlo: las etiquetas las pone quien
  escribió la rúbrica, así que lo que se mide es **fidelidad a la rúbrica**, no acuerdo con la
  intención real de un alumno. Eso último necesita usuarios y queda sin medir.
"""
import re
import unicodedata

MODOS = ("responder", "acompanar", "corregir")

#: R1 — EL TURNO CONTIENE O DECLARA UN RESULTADO, UNA RESPUESTA O UN INTENTO.
#: Tres familias, y las tres son rasgos del texto: posesivo sobre trabajo propio, primera persona
#: de haberlo hecho, y resultado declarado. La cláusula dice explícitamente que **el intento no
#: tiene que venir pegado**: basta con que el turno afirme que existe ("esto que he hecho").
#: Y "aplica aunque esté redactado como pregunta" — de donde se sigue que también aplica aunque NO
#: lo esté: una afirmación suelta ("Mi diagrama pone que…") trae intento igual. El signo de
#: interrogación no es un rasgo.
INTENTO = (
    r"\bmi(s)? (codigo|respuesta|solucion|resultado|consulta|query|funcion|clase|metodo|programa|"
    r"planteamiento|razonamiento|version|intento|calculo|diagrama|esquema|tabla|diseno)\b",
    r"\b(he|hemos) (hecho|puesto|escrito|calculado|resuelto|planteado|programado|montado|"
    r"implementado|contestado|respondido|sacado|obtenido|dividido|llegado)\b",
    r"\bme (sale|da|salio|dio|queda|quedo|salen|dan)\b",
    r"\b(esto|eso|lo) que (he|hemos) (hecho|puesto|escrito|resuelto)\b",
    r"\b(el|mi) resultado (es|me da|da)\b",
    r"\blo tengo (asi|hecho|resuelto)\b",
    r"\bcreo que\b.{0,40}?\b(es|son|seria|serian)\b",
    # "En el examen PUSE que…", "yo DIJE que…": una respuesta ya dada es una respuesta declarada.
    r"\b(puse|dije|conteste|respondi|calcule|escribi|hice|monte|plantee)\b",
    # "Resultado: 64 direcciones por subred." Un resultado declarado ES R1, con o sin pregunta.
    r"\bresultado\s*:\s*\S",
    # POSESIVO SOBRE TRABAJO PROPIO, forma corta: "lo mío", "la mía".
    r"\b(lo|la|los|las) mi[oa]s?\b",
)

#: LA NEGACIÓN, QUE ES EL DESEMPATE D4 CONVERTIDO EN RASGO. *"Ayúdame a corregir el ejercicio, AÚN
#: NO LO HE HECHO"* casa con `he hecho` y saldría `corregir` **leyendo el verbo en vez del rasgo**,
#: que es justo lo que D4 prohíbe. La rúbrica manda el rasgo *hay algo que evaluar*: si el turno
#: dice que no lo hay, no lo hay. Se mira la ventana inmediatamente anterior al rasgo y no la frase
#: entera, para que *"no entiendo X pero he hecho Y"* siga trayendo intento.
NIEGA_INTENTO = r"\b(no|aun no|todavia no|ni siquiera)\b[^.;?!]{0,24}$"

#: R2 — PIDE AYUDA PARA RESOLVER UN EJERCICIO CONCRETO. Lo que lo hace concreto es que hay **una
#: tarea determinada delante**, no el sustantivo que se use: un encargo del profesor o un enunciado
#: es tan concreto como "el ejercicio 5".
EJERCICIO = (
    r"\b(el|este|ese|del|al) (ejercicio|problema|apartado|actividad|practica|supuesto|enunciado)\b",
    r"\b(ejercicio|actividad|practica|tarea) \d+\b",
    r"\bno se (como|por donde|que|cual)\b",
    r"\b(me he atascado|estoy atascad[oa])\b",
    r"\bayudame a (hacer|resolver|sacar|plantear|terminar)\b",
    r"\b(me ayudas|ayudame) a\b",
    r"\bcomo (lo )?(hago|resuelvo|planteo|saco|empiezo)\b",
    r"\b(me han mandado|me piden|el profesor (pide|manda))\b",
    r"\btengo que (hacer|montar|implementar|crear|dividir|calcular|programar|escribir)\b",
    r"\bnecesito (hacer|montar|implementar|crear|resolver)\b",
    r"\b(guiame|dame la solucion|resuelveme)\b",
    r"\bpor donde (empiezo|empezar)\b",
    r"\bno entiendo que me pide\b",
    r"\bpaso a paso\b",
    r"\bquiero hacer el\b",
)

#: R3 — PREGUNTA POR UN CONCEPTO, DEFINICIÓN, DIFERENCIA O FUNCIONAMIENTO.
CONCEPTO = (
    r"\bque (es|son|significa|hace|pasa si|partes tiene|elementos tiene)\b",
    r"\bpara que (sirve|vale|se usa)\b",
    r"\bpor que\b",
    r"\bdiferencia(s)?\b.{0,20}?\bentre\b",
    r"\bcomo funciona\b",
    r"\ben que se diferencian\b",
    r"\bcuando (se usa|hay que usar|conviene)\b",
    r"\bcual es (la|el)\b",
    r"\bexplicame\b",
    r"\bno entiendo (que significa|el concepto)\b",
)

#: D2 — "CÓMO SE HACE X" EN GENERAL: impersonal o infinitivo. Su propio texto dice que un ejercicio
#: mencionado como contexto NO lo convierte en `acompanar`, y de ahí sale el orden de decisión.
GENERAL = (
    r"\bcomo se (hace|escribe|declara|configura|define|implementa|usa|crea|protege|calcula|"
    r"gestiona|evita|divide)\b",
    r"\bcomo (hacer|escribir|declarar|configurar|definir|implementar|usar|crear|proteger)\b",
    r"\bque hay que (hacer|poner|escribir) para\b",
)

#: D6 — PIDE QUE LE EXAMINEN O QUE LE PONGAN UN EJERCICIO. El modo `examinar` está DISEÑADO Y NO
#: CONSTRUIDO: cae a `responder` por D5 **y el sistema debe decir que ese modo no existe**, que es
#: para lo que existe la bandera del resultado. Sin la bandera, el turno saldría como una consulta
#: normal y el alumno no se enteraría de que ha pedido algo que no hay.
EXAMEN = (
    r"\bpon(er)?(me|game|nos)?\b.{0,30}?\b(ejercicio|pregunta|test|examen)s?\b",
    r"\bexamina(me)?\b",
    r"\bhazme (un|unas|unos|preguntas)\b",
    r"\btomame la leccion\b",
    r"\bevaluame\b",
)


def _plano(texto: str) -> str:
    """Minúsculas y sin tildes. Un alumno escribe `codigo` y `código` con la misma intención, y un
    rasgo que dependiera de la tilde sería un rasgo sobre el teclado, no sobre el turno."""
    sin = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin if unicodedata.category(c) != "Mn")


def _casa(patrones, texto: str) -> str | None:
    for p in patrones:
        if re.search(p, texto):
            return p
    return None


def _casa_sin_negacion(patrones, texto: str) -> str | None:
    """Como `_casa`, pero descarta el rasgo si lo que hay JUSTO ANTES lo niega (D4)."""
    for p in patrones:
        m = re.search(p, texto)
        if m and not re.search(NIEGA_INTENTO, texto[:m.start()]):
            return p
    return None


def rasgos_de(turno: str) -> dict:
    """Los rasgos ESTRUCTURALES del turno. Se devuelven TODOS, no solo el que gana: un clasificador
    que solo dice su veredicto no se puede auditar caso a caso, y aquí la lectura a ojo de los
    fronterizos es la mitad del trabajo."""
    t = _plano(turno)
    return {
        "trae_intento": _casa_sin_negacion(INTENTO, t),
        "ejercicio_concreto": _casa(EJERCICIO, t),
        "pregunta_de_concepto": _casa(CONCEPTO, t),
        "como_se_hace_general": _casa(GENERAL, t),
        "pide_examen": _casa(EXAMEN, t),
    }


def clasificar_modo(turno: str) -> dict:
    """Devuelve `{modo, clausula, motivo, rasgos, examen_no_construido}`.

    EL ORDEN DE DECISIÓN SALE DE LOS DESEMPATES, no de lo que a mí me parezca más importante:

    1. **R1 + D1** — hay intento → `corregir`, aunque además pregunte por un concepto. *"R1 gana:
       hay algo que evaluar, y evaluarlo no impide explicar."* Con **D4** dentro del rasgo: el verbo
       *corregir* sin intento no cuenta, porque manda el rasgo y no el verbo.
    2. **D6** — pide examen → `responder`, con la bandera de que ese modo no existe.
    3. **D2** — "cómo se hace X" en general → `responder`. **VA ANTES QUE R2 Y ESO ES LA REGLA, no
       una preferencia**: su propio ejemplo —*"un ejercicio mencionado como contexto ('es para el
       ejercicio 5') no lo convierte en `acompanar`"*— solo se cumple si D2 se mira primero. Con R2
       delante, *"¿Cómo se calcula una subred? Es para el ejercicio 5"* salía `acompanar`, que es
       exactamente el caso que D2 existe para resolver al revés.
    4. **R2 + D3** — ejercicio concreto sin intento → `acompanar`, **pida o no la solución**.
    5. **R3** — concepto → `responder`.
    6. **D5** — ninguna señal → `responder`, por ser el modo menos intrusivo.
    """
    r = rasgos_de(turno)
    if r["trae_intento"]:
        return {"modo": "corregir",
                "clausula": "R1" + (" + D1" if r["pregunta_de_concepto"] else ""),
                "motivo": "el turno declara o contiene un intento del alumno",
                "rasgos": r, "examen_no_construido": False}
    if r["pide_examen"]:
        return {"modo": "responder", "clausula": "D6",
                "motivo": "pide que le examinen: el modo `examinar` esta disenado y NO construido",
                "rasgos": r, "examen_no_construido": True}
    if r["como_se_hace_general"]:
        return {"modo": "responder", "clausula": "D2",
                "motivo": "como se hace X en general; el ejercicio, si se menciona, es contexto",
                "rasgos": r, "examen_no_construido": False}
    if r["ejercicio_concreto"]:
        return {"modo": "acompanar", "clausula": "R2",
                "motivo": "pide ayuda con un ejercicio concreto y no trae intento",
                "rasgos": r, "examen_no_construido": False}
    if r["pregunta_de_concepto"]:
        return {"modo": "responder", "clausula": "R3",
                "motivo": "pregunta por un concepto, definicion, diferencia o funcionamiento",
                "rasgos": r, "examen_no_construido": False}
    return {"modo": "responder", "clausula": "D5",
            "motivo": "ninguna senal de las tres: se elige el modo menos intrusivo",
            "rasgos": r, "examen_no_construido": False}
