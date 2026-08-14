"""Verificador de citas literales (encargo 4.2). **Sin modelo: comparación de cadenas.**

Es el principio 6 hecho código. El que comprueba no puede compartir supuesto con el que produce, y
aquí el productor es un modelo de lenguaje: si el verificador fuera otro modelo, un fallo de
comprensión compartido pasaría inadvertido en los dos lados. Una comparación de subcadena no
comparte nada con nadie — no entiende, y por eso no se equivoca de la misma manera.

## EL ORDEN NO ES UNA PREFERENCIA: `fragmento_en_contexto` ES PUERTA Y VA ANTES

El verificador comprueba que la cita esté **dentro del fragmento**; eso no comprueba que ese
fragmento **estuviera en el contexto**. Con 11.282 fragmentos que se solapan 64 tokens, **un
`fragmento_id` inventado que apunte a prosa del mismo tema puede contener una frase que case**, y
entonces esta capa daría por buena una cita fabricada — el fallo exacto que existe para impedir.

Y el orden importa: si la comparación corre primero y pasa, **ya se ha producido un veredicto
favorable** sobre una cita que el modelo no pudo haber leído. Una afirmación cuyo `fragmento_id` no
estuvo en el contexto **no se compara: se poda**, y se registra como procedencia fabricada, que
además es una señal del generador que conviene contar.

## LA NORMALIZACIÓN SE QUEDA CORTA A PROPÓSITO, Y LA CARGA DE LA PRUEBA LA TIENE CADA PASO

**Cada paso de normalización cambia un falso negativo por un falso positivo, y en un verificador el
falso positivo es el caro.** Una cita rechazada de más degrada a `parafrasis` y la comprueba el NLI:
coste acotado. Una aceptada de más es una fabricación pasando por verificada: **coste sin fondo.**
Con esa asimetría, el punto de equilibrio no está en el medio, y **un paso que no demuestre que
compra algo no entra** — no al revés.

Los niveles están separados para poder medirlos uno a uno (`docs/evidencia/`), y las tildes **nunca**
se tocan: si el modelo pierde un acento es porque está **reescribiendo**, y esa diferencia es la
SEÑAL, no ruido que limpiar.
"""
import re
import unicodedata

#: Comillas y guiones tipográficos que un modelo cambia al copiar sin que eso signifique nada: son
#: sustituciones de RENDERIZADO, no de contenido.
TIPOGRAFICOS = {
    "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',
    "‘": "'", "’": "'", "‚": "'",
    "–": "-", "—": "-", "−": "-",
    "…": "...", " ": " ",
}

_ESPACIOS = re.compile(r"\s+")


def n0_crudo(t: str) -> str:
    return t


def n1_espacios(t: str) -> str:
    """Colapsa espacios. Es el único paso que casi no puede hacer daño: los saltos de línea y la
    sangría son del troceado, no del texto, y ningún par de citas distintas se distingue por ellos."""
    return _ESPACIOS.sub(" ", t).strip()


def n2_tipograficos(t: str) -> str:
    """`n1` más comillas y guiones tipográficos a ASCII."""
    return n1_espacios("".join(TIPOGRAFICOS.get(c, c) for c in t))


def n3_minusculas(t: str) -> str:
    """`n2` más minúsculas. **Este es el paso discutido**, y la sección 8 lo pide.

    El argumento en contra es concreto y del corpus de este proyecto, que es medio código:
    ignorando mayúsculas, `bindingresult` pasaría como cita literal de `BindingResult`, y en un
    lenguaje sensible a mayúsculas eso **no es la misma cadena ni significa lo mismo**. Se mide
    antes de decidir si entra.
    """
    return n2_tipograficos(t).lower()


#: Los niveles del barrido, de menos a más agresivo. **Las tildes no se tocan en ninguno** (sección
#: 8: "tildes conservadas"), y el motivo va más allá del acuerdo con la especificación: perder un
#: acento al copiar es la firma de que el modelo REESCRIBIÓ en vez de copiar.
NIVELES = {
    "crudo": n0_crudo,
    "espacios": n1_espacios,
    "espacios+tipograficos": n2_tipograficos,
    "espacios+tipograficos+minusculas": n3_minusculas,
}

#: EL QUE SE USA EN SERVICIO, fijado el 13 de agosto de 2026 con el barrido delante (n=337 citas,
#: `docs/evidencia/2026-08-13-verificador-literal.md`) y con la asimetría decidiendo:
#:
#:   crudo                            179/328
#:   espacios                         195/328   +16  -> ENTRA
#:   espacios+tipograficos            195/328    +0  -> NO ENTRA
#:   espacios+tipograficos+minusculas 197/328    +2  -> NO ENTRA (ver abajo)
#:
#: **Los tipográficos no demostraron ganancia**, así que no entran: la carga de la prueba es suya.
#:
#: **Y las minúsculas ganaban 2, pero leídas una a una las dos diferían EN LA LETRA INICIAL** —el
#: modelo empezó la cita como si fuera frase—. O sea que bajar todo el texto a minúsculas, y con ello
#: aceptar `bindingresult` como cita literal de `BindingResult` en un corpus medio código, compra
#: exactamente dos mayúsculas iniciales. Esas dos degradan a `parafrasis` y las verificará el NLI sin
#: esfuerzo, porque son la misma frase: **coste acotado, que es el lado barato de la asimetría.**
#:
#: **Esto CORRIGE la sección 8 de la guía**, que pedía "minúsculas" en la normalización. Se corrige
#: con la medida delante y queda declarado en el 4.2.
NIVEL_POR_DEFECTO = "espacios"

#: Veredictos. `sin_verificar` NO es un aprobado: es un pendiente.
VERIFICADA = "verificada"
DEGRADADA = "degradada_a_parafrasis"
PODADA = "podada"

#: QUIÉN FIRMA ESTE VEREDICTO, y por qué hace falta: este módulo y el NLI del 4.3 escriben **el
#: mismo valor** `verificada` sobre la misma tabla —el 4.2 cuando la cita casa letra a letra, el
#: 4.3 cuando el fragmento sostiene una degradada—, así que sin firma una consulta que filtre por
#: `veredicto = 'verificada'` devuelve una mezcla de dos instrumentos. Ocurrió: los positivos de la
#: calibración del NLI llevaban 12 filas que el propio NLI había aprobado (garantía circular).
INSTRUMENTO = "4.2/comparacion_de_cadenas"


def hay_acentos_perdidos(cita: str, fragmento: str) -> bool:
    """¿La cita casaría si se le quitaran las tildes a las dos partes? Señal de reescritura.

    No cambia el veredicto —las tildes no se normalizan—, pero saberlo distingue "el modelo se
    inventó la cita" de "el modelo la reescribió de memoria", que son dos averías distintas del
    generador y se cuentan por separado."""
    def sin_tildes(t: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFD", n2_tipograficos(t))
                       if unicodedata.category(c) != "Mn")
    return sin_tildes(cita) in sin_tildes(fragmento)


def verificar(afirmacion: dict, textos_en_contexto: dict, nivel: str = NIVEL_POR_DEFECTO) -> dict:
    """Verifica UNA afirmación `literal`. `textos_en_contexto` es `{fragmento_id: texto}`.

    Devuelve el veredicto y el porqué. No lanza: un verificador que revienta con una entrada rara
    convierte una poda en un 500.
    """
    normalizar = NIVELES[nivel]
    fragmento_id = afirmacion.get("fragmento_id")
    cita = afirmacion.get("cita") or ""
    firma = {"nivel": nivel, "instrumento": INSTRUMENTO}

    # PUERTA, antes de comparar nada. Ver la cabecera: si esto corriera después, ya se habría
    # emitido un veredicto favorable sobre una cita que el modelo no pudo leer.
    if fragmento_id not in textos_en_contexto:
        return {**firma, "veredicto": PODADA, "motivo": "procedencia_fabricada",
                "detalle": f"el fragmento {fragmento_id} no estuvo en el contexto: no se compara"}

    if not cita.strip():
        return {**firma, "veredicto": DEGRADADA, "motivo": "sin_cita",
                "detalle": "una afirmacion literal sin cita no tiene nada que verificar"}

    fragmento = textos_en_contexto[fragmento_id]
    if normalizar(cita) in normalizar(fragmento):
        return {**firma, "veredicto": VERIFICADA, "motivo": None,
                "detalle": f"subcadena exacta tras normalizar en nivel '{nivel}'"}

    # NO SE PODA: se DEGRADA, y el 4.3 la recoge con el NLI.
    #
    # **CORREGIDO EL 13/08/2026 POR LA TARDE, y la corrección es del tipo que este repo persigue:**
    # este mensaje decía *"el NLI del 4.3 (hoy no existe)"*, y desde el 4.3 sí existe —
    # `app/core/verificador_nli.py`, con sus tests—. Lo que pasa es otra cosa y hay que decirla con
    # precisión: **está construido y NADIE LO LLAMA desde la ruta de petición.** Un módulo que existe
    # y no se invoca deja la afirmación igual de sin verificar que uno que no existe, pero el
    # diagnóstico es distinto y el arreglo también.
    return {**firma, "veredicto": DEGRADADA, "motivo": "no_es_subcadena",
            "solo_tildes": hay_acentos_perdidos(cita, fragmento),
            "detalle": "la cita no aparece literalmente en su fragmento; baja a parafrasis y la "
                       "verifica el NLI del 4.3, que desde el 4.4 SI corre en la ruta de peticion "
                       "-en un hilo, con la ventana anclada en la cita como premisa-"}
