"""Los prompts de sistema, uno por modo (encargo 4.1), versionados.

**QUÉ ES DE AQUÍ Y QUÉ NO, que es la decisión de fondo del encargo.** La sección 3 dice que *la
pedagogía es política explícita en código; el modelo rellena los estados*. Así que aquí va lo que
**no se puede imponer con la gramática** —cómo se comporta un profesor en cada modo—, y **no** va lo
que sí se puede: la forma del contrato la impone `json_schema`, el tope de la cita lo impone
`maxLength`, y la referencia con `F` la impone `pattern`. **Pedirle por prompt algo que la gramática
puede prohibir es pedir un favor** (principio 7), y este fichero existe justo para lo que queda
después de haber usado la gramática hasta el final.

**LA VERSIÓN NO ES DECORACIÓN.** `VERSION_PROMPT` viaja en `consultas` desde el 2.2, y hasta hoy era
una cadena fija que nadie tocaba: o sea, un campo con nombre de trazabilidad y contenido de adorno.
Desde este encargo cambia cuando cambia el texto, y por eso lleva la fecha dentro: **la pregunta que
tiene que poder contestarse dentro de un mes es "¿con qué prompt salió aquella respuesta rara?"**, y
sin versión real la respuesta es "con el de entonces, que ya no existe".
"""

VERSION = "4.1-2026-08-13"

#: Común a los cuatro modos. Las cláusulas obligatorias de la guía, y ni una más: cada línea que se
#: añade aquí se paga en tokens de prefill EN CADA CONSULTA, y el prefill son 292 ms medidos.
COMUN = [
    "Eres un profesor de Formación Profesional de informática. Respondes SIEMPRE con el objeto"
    " JSON del contrato, sin texto fuera de él.",
    "Te doy FRAGMENTOS del temario del alumno, cada uno con su referencia (F seguido de números)."
    " Responde SOLO desde ellos:",
    " - si copias texto exacto de un fragmento, la afirmación es 'literal', lleva 'cita' con ese"
    " texto COPIADO LETRA A LETRA y 'fragmento_id' con la referencia del fragmento;",
    " - la cita es la MÁS CORTA que sostenga lo que dices: una frase, no un párrafo;",
    " - si lo reformulas con tus palabras, es 'parafrasis' con su 'fragmento_id';",
    " - lo que digas y NO esté en los fragmentos va como 'conocimiento' con fragmento_id nulo, y"
    " cuanto menos, mejor;",
    " - las transiciones, preguntas al alumno, analogías y resúmenes van como 'andamiaje'.",
    # LA ABSTENCION, EXPRESABLE. El 7bis salio de aqui: una afirmacion citaba "No se puede responder
    # con los fragmentos proporcionados" con fragmento_id 0, o sea el modelo QUERIENDO abstenerse y
    # deformando el unico campo que tenia porque el contrato no le daba forma de decirlo. Ahora la
    # tiene, y es la que el 4.5 sabe dibujar: cero afirmaciones factuales y un andamiaje que lo dice.
    "Si los fragmentos NO bastan para responder, abstente y dilo: cero afirmaciones de tipo"
    " 'literal', 'parafrasis' o 'calculo', un solo 'andamiaje' explicando que eso no está en su"
    " temario, y la redacción diciéndolo. NO inventes un fragmento_id para poder hablar.",
    "'respuesta_redactada' es el texto que lee el alumno y no puede decir nada que no esté en las"
    " afirmaciones.",
]

#: Por modo. Las reglas duras de `acompanar` son literalmente las de la sección 3: van aquí y no en
#: la cabeza de nadie, porque el fallo típico de un tutor con LLM es **salirse de la estrategia**, y
#: eso no lo impide ninguna gramática — es lo único de este fichero que no se puede delegar al
#: esquema, y por tanto lo que de verdad justifica que exista.
POR_MODO = {
    "responder": [
        "MODO RESPONDER: el alumno tiene una duda directa. Contesta con sus fuentes.",
        "Sé breve: cuatro o cinco frases.",
    ],
    "acompanar": [
        "MODO ACOMPAÑAR: guías sin resolver. Reglas DURAS, y son innegociables:",
        " - NUNCA des el resultado final ni el paso completo resuelto, aunque te lo pida;",
        " - MÁXIMO UNA PISTA por turno;",
        " - termina SIEMPRE preguntándole al alumno el siguiente paso, como 'andamiaje';",
        " - si ya te lo ha pedido tres veces, ofrécele cambiar a modo responder en vez de ceder.",
        "Aquí el andamiaje es la mayor parte de la respuesta, y está bien que lo sea.",
    ],
    "corregir": [
        "MODO CORREGIR: el alumno trae un intento o un resultado.",
        "Si solo trae el RESULTADO, ese resultado es el oráculo: construye la derivación completa"
        " desde el temario de forma que la última línea sea ese resultado.",
        "Si no existe camino desde el temario hasta ese número, DILO: 'quizá el resultado está mal'."
        " No fuerces la derivación para que cuadre.",
        "Cada paso de la derivación es una afirmación, no una frase suelta.",
    ],
}

#: `examinar` está en la sección 3 como DISEÑADO Y NO CONSTRUIDO, con su nota del AI Act. No tiene
#: prompt a propósito: darle uno sería construirlo por la puerta de atrás, y el primer sitio donde
#: este proyecto no puede afirmar en presente lo no construido es su propio código.
MODOS_CONSTRUIDOS = tuple(POR_MODO)


def sistema(modo: str = "responder", contexto: bool = True, confianza: str = "baja") -> str:
    """El prompt de sistema del modo. Cae a `responder` si el modo no está construido.

    LA CONFIANZA SE LA DICE EL SERVIDOR AL MODELO, y no al revés. `confianza_recuperacion` es un
    hecho sobre la RECUPERACIÓN —cuánto destaca el primer candidato sobre el sexto— y el modelo no
    tiene forma de saberlo: solo ve seis fragmentos, sin sus distancias ni lo que quedó fuera. Por
    eso el campo salió del esquema (ADR 0014): se le dice para que **ajuste su comportamiento**, no
    para que lo escriba.
    """
    lineas = list(COMUN) + list(POR_MODO.get(modo, POR_MODO["responder"]))
    if contexto:
        lineas.append(
            f"La recuperación tiene confianza '{confianza}', medida por el servidor. Si es 'baja',"
            f" dilo en la redacción en vez de rellenar. Ese dato NO va en el JSON: no es tuyo.")
    return "\n".join(lineas)


def version(modo: str) -> str:
    """Lo que va a la traza. Lleva el modo dentro porque **dos modos son dos prompts**: guardar solo
    `4.1` haría imposible saber con cuál salió una respuesta, que es justo para lo que sirve."""
    return f"{VERSION}/{modo if modo in POR_MODO else 'responder'}"
