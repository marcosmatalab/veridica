"""Sacar el array `afirmaciones` de un JSON que todavía se está escribiendo (encargo 4.2/4.3).

POR QUÉ SE PUEDE, Y ES CONSECUENCIA DEL ORDEN DEL CONTRATO: `afirmaciones` va **antes** de
`respuesta_redactada`, así que **en el instante en que aparece el primer carácter de prosa, el array
de afirmaciones ya está cerrado y completo** dentro del JSON parcial. No hay que adivinar nada ni
parsear a medias: hay que encontrar dónde acaba, y eso es contar corchetes.

PARA QUÉ SIRVE: para verificar **mientras el modelo sigue escribiendo**. La comparación literal es
instantánea y el NLI del 4.3 tarda ~350 ms, mientras la prosa sigue llegando ~823 ms más. O sea que
los veredictos pueden salir a pantalla **durante** la redacción, y el alumno ve el sistema
comprobándose a sí mismo en vez de un rótulo encendido. Es el efecto que buscaba partir la
generación en dos llamadas, sin partir nada y sin pagar un segundo prefill.

**Se cuenta con estados y no con una expresión regular**, por el mismo motivo que `ProsaEnCurso`: un
corchete dentro de una cadena —y el corpus es medio código, así que los hay a montones— rompería
cualquier regex, y las comillas escapadas rompen el contador ingenuo de comillas.
"""
import json

CLAVE = '"afirmaciones"'


def extraer(crudo: str) -> list | None:
    """El array `afirmaciones` si ya está CERRADO en `crudo`; `None` si aún no.

    Nunca lanza: esto corre en mitad de un flujo SSE y una excepción aquí le dejaría la pantalla a
    medias al alumno. Si algo no cuadra, devuelve None y el camino normal —validar el JSON entero al
    final— sigue funcionando igual.
    """
    i = crudo.find(CLAVE)
    if i < 0:
        return None
    inicio = crudo.find("[", i + len(CLAVE))
    if inicio < 0:
        return None

    profundidad = 0
    en_cadena = False
    escapado = False
    for j in range(inicio, len(crudo)):
        c = crudo[j]
        if escapado:
            escapado = False
            continue
        if c == "\\":
            escapado = True
            continue
        if c == '"':
            en_cadena = not en_cadena
            continue
        if en_cadena:
            continue
        if c == "[":
            profundidad += 1
        elif c == "]":
            profundidad -= 1
            if profundidad == 0:
                try:
                    return json.loads(crudo[inicio:j + 1])
                except json.JSONDecodeError:
                    return None
    return None
