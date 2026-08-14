"""Verificador de cálculo (encargo 4.4). Recálculo con sympy, **jamás `eval`**.

Es el tercer instrumento de la sección 8: el 4.2 comprueba lo que se copió letra a letra, el 4.3 lo
que se reformuló, y esto lo que se **calculó**. Y es el que menos se fía del generador de los tres:
no le pregunta a ningún modelo si el número está bien, **lo vuelve a calcular**.

## SYMPY NO ES SEGURO POR DEFECTO, Y ESO HAY QUE SABERLO ANTES DE USARLO

`sympify()` compila y evalúa la cadena con el espacio de nombres entero de sympy dentro, y
`parse_expr()` hace lo mismo si no se le pasa `global_dict`: en los dos casos, el texto que escribió
el modelo acaba en un `eval` de Python. Aquí se cierra por **tres puertas distintas**, en este orden:

1. **Lista blanca de CARACTERES**, antes de tocar sympy. Sin `_` (no hay `__class__` posible), sin
   `[`, sin `=`, sin comillas, sin `:` ni `;`.
2. **Lista blanca de NOMBRES**: cada palabra de la expresión tiene que estar en `PERMITIDO`. `lambda`
   e `import` no llegan al parser, y no porque los prohíba una regla suya: porque no están en la
   lista de los que sí.
3. **`global_dict` explícito y mínimo**, para que el `eval` interno no vea ni los builtins ni el
   `from sympy import *` que `parse_expr` mete cuando se lo dejan a él.

## LA GUARDA NO BASTA CON PONERLA: HAY QUE MEDIR QUÉ DEJA PASAR

`2**2**2**30` es una expresión de once caracteres, pasa cualquier lista blanca, y calcularla se lleva
la máquina por delante. Así que antes de evaluar nada se **acota el tamaño del resultado sin
calcularlo**: `_magnitud` estima, de abajo arriba, cuántos dígitos decimales tiene cada nodo del
árbol, y si **algún nodo intermedio** pasa de `MAX_DIGITOS`, la expresión no se evalúa.

**Y se comprueba en cada nodo, no solo en la raíz, porque si no la cancelación abre un boquete**:
`factorial(100000)/factorial(100000)` vale 1 —magnitud final 0, inofensiva— y para averiguarlo hay
que calcular dos veces el factorial de cien mil. El límite va donde está el coste.

**Una función cuyo crecimiento no está declarado se rechaza, no se adivina** (`FUNCIONES_ACOTADAS` y
`FUNCIONES_QUE_CRECEN`): si mañana alguien mete una función nueva en `PERMITIDO` sin decir cómo
crece, lo que sale es `no_verificable`, no un hueco por el que pasa una bomba.

El peor caso que esta guarda deja pasar está **medido**, con su expresión y sus milisegundos, en
`docs/evidencia/2026-08-13-verificador-calculo.md`. Poner el tope sin medirlo sería decir que está
protegido, que es distinto de estarlo.

## Y LO QUE NO SE PUEDE COMPROBAR SALE `no_verificable`, NUNCA `podada`

`expresion` lleva **también el código** del caso que este encargo deja declarado y no construido (el
sandbox). Un fragmento de código no parsea aquí, y la diferencia entre los dos veredictos no es de
matiz: *"no he podido comprobarlo"* no es *"es falso"*. Confundirlos castigaría al modelo por una
capacidad que hemos decidido **nosotros** no construir, y además envenenaría la tasa de poda del 4.6
con casos que no son podas. Es la misma línea que `fragmento_en_contexto` en el 4.2 y que el suelo de
cobertura en el 4.3: **cuando la precondición del instrumento no se cumple, no se usa el
instrumento**.
"""
import math
import os
import re
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

import sympy
from sympy.parsing.sympy_parser import convert_xor, parse_expr, standard_transformations

from app.modelos.contrato import RESULTADO_NUMERICO

#: Vocabulario compartido con el 4.2 y el 4.3, para que el 4.6 pueda contarlos en la misma tabla.
VERIFICADA = "verificada"
PODADA = "podada"
NO_VERIFICABLE = "no_verificable"

#: TOPE DE LONGITUD. Su trabajo es acotar el **parseo**, no el valor: el tamaño del resultado lo
#: acota `MAX_DIGITOS`, que es una magnitud distinta y por eso lleva su propio tope (la lección de la
#: gracia del 3.4: un tope contado en la unidad equivocada se relaja solo). 200 caracteres son
#: holgados para cualquier aritmética de FP —las tres expresiones del humo real miden 4, 6 y 18
#: caracteres: `2^32`, `64 - 2` y `7! / (2! * (7-2)!)`— y lo que
#: no cabe sale `no_verificable`, no podado.
MAX_CARACTERES = int(os.environ.get("CALCULO_MAX_CARACTERES") or 200)

#: TOPE DE DÍGITOS de cualquier valor intermedio. Sale de la medida, no de la costumbre: ver la
#: cabecera y la evidencia. 1000 dígitos cubren `2**2048` (617 dígitos, criptografía de ASIR) y
#: `binomial(1000,500)` (300), y dejan fuera `factorial(100000)` (456.574).
#:
#: **Y tiene un techo que no es nuestro**: desde Python 3.11, convertir un entero de más de 4300
#: cifras a cadena **lanza** `ValueError`. O sea que un tope configurado por encima de eso no
#: ampliaría lo que se puede verificar: rompería el verificador al imprimir el resultado, que es una
#: avería peor y en otro sitio. Se acota aquí, donde se ve, en vez de descubrirlo en producción.
MAX_DIGITOS = min(int(os.environ.get("CALCULO_MAX_DIGITOS") or 1000), 4000)

#: Tope del ARGUMENTO de las transcendentales. `sin(10**900)` tiene resultado entre -1 y 1 —o sea que
#: `MAX_DIGITOS` no lo ve— y para evaluarlo hay que reducirlo módulo pi con 900 dígitos de precisión.
#: El coste no está en el resultado, está en el camino: otro tope en su propia unidad.
MAX_DIGITOS_ARGUMENTO = int(os.environ.get("CALCULO_MAX_DIGITOS_ARGUMENTO") or 30)

#: Cifras significativas de más que se piden al evaluar, por encima de las que hagan falta. Un
#: colchón: el redondeo se decide con las últimas y no se quiere que la última sea la del error.
GUARDA_CIFRAS = 10

_RE_CARACTER_PROHIBIDO = re.compile(r"[^0-9a-zA-Z.+\-*/()%!^,\s]")
#: SEGUNDA CERRADURA sobre `resultado_afirmado`, y no es redundante con la gramática: la gramática
#: vive en el esquema que se le manda al proveedor, y **el que comprueba no se fía del que produce**.
#: Si un día el patrón se relaja o llega una respuesta de otra fuente, un `4.294967296` con punto
#: entraría como si fuera cuatro coma tres y el veredicto sería `podada` —"el alumno se equivocó"—
#: cuando lo que pasa es que el campo está mal formado. Eso no es un veredicto, es un error de
#: transporte, y sale `no_verificable`.
_RE_RESULTADO = re.compile(RESULTADO_NUMERICO)
_RE_NOMBRE = re.compile(r"[a-zA-Z]+")

#: La lista blanca de nombres. Corta a propósito: lo que hace falta para la aritmética de un temario
#: de FP. Cada añadido futuro tiene que entrar TAMBIÉN en una de las dos tablas de crecimiento de
#: abajo, o la guarda lo rechazará — que es el orden correcto de los dos errores.
PERMITIDO = {
    "sqrt": sympy.sqrt, "abs": sympy.Abs, "log": sympy.log, "ln": sympy.log, "exp": sympy.exp,
    "factorial": sympy.factorial, "binomial": sympy.binomial,
    "gcd": sympy.gcd, "lcm": sympy.lcm, "floor": sympy.floor, "ceiling": sympy.ceiling,
    "Mod": sympy.Mod, "mod": sympy.Mod,
    "sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
    "pi": sympy.pi, "E": sympy.E,
}

#: Lo que `parse_expr` necesita en su `eval` interno y NADA más. Con `global_dict=None` metería un
#: `from sympy import *` completo, que es justo lo que este diccionario existe para impedir.
#:
#: `Add`, `Mul` y `Pow` están porque **el parseo sin evaluar reescribe los operadores como llamadas**:
#: `2+2` se convierte en `Add(Integer(2), Integer(2), evaluate=False)`. Faltaban las tres en la
#: primera versión, y el modo de fallo es de los que hay que anotar: **no reventaba, devolvía
#: `no_verificable`**. O sea que toda la aritmética con operadores —que es toda la aritmética— salía
#: sin verificar con un veredicto legítimo, y la columna de resultados tenía el aspecto tranquilo de
#: lo que se abstiene con prudencia. Lo cazó mirar los casos a ojo: `sqrt(2)` y `factorial(20)`
#: pasaban (no llevan operadores) y `2+2` no.
_INTERNO = {"Integer": sympy.Integer, "Float": sympy.Float, "Rational": sympy.Rational,
            "Symbol": sympy.Symbol, "Add": sympy.Add, "Mul": sympy.Mul, "Pow": sympy.Pow}

_TRANSFORMACIONES = standard_transformations + (convert_xor,)

#: LA PASADA DEL GUARDA NO VE NI UNA FUNCIÓN DE VERDAD, y este diccionario es el arreglo de un
#: boquete que la primera versión tenía abierto.
#:
#: `evaluate=False` desactiva los **operadores**, no las **llamadas a función**: `factorial(100000)`
#: se calculaba *dentro del parseo del guarda*, o sea antes de que el guarda pudiera mirarlo, y la
#: comprobación llegaba cuando el daño ya estaba hecho. Se vio porque la prueba se colgó — pero podía
#: no haberse visto: con un argumento algo menor habría devuelto un veredicto correcto y tarde.
#:
#: Aquí cada nombre se sustituye por una función **indefinida** de sympy, que construye un nodo y no
#: calcula nada. La propiedad que da esto es la que se quería: **en la pasada del guarda no hay nada
#: que pueda ejecutarse**, en vez de una lista de funciones que se confía en que no exploten.
_INERTE = {n: (sympy.Function(n) if callable(v) else v) for n, v in PERMITIDO.items()}

#: Cómo crece cada nombre, DECLARADO. Lo que no esté en ninguna de estas tres tablas se rechaza en
#: `_magnitud`: una función cuyo crecimiento nadie ha escrito no se acota a ojo.
_ACOTADAS_POR_ARGUMENTO = ("abs", "floor", "ceiling", "Mod", "mod", "gcd")
#: Acotadas en VALOR pero caras en PRECISIÓN si el argumento es grande (`exp` además crece).
_TRANSCENDENTALES = ("sin", "cos", "tan", "log", "ln", "exp")


class Desbordada(ValueError):
    """La guarda ha parado la expresión antes de evaluarla. Lleva el motivo dentro."""


def _digitos(n) -> float:
    """log10(|n|) de un número de sympy.

    **CON LA PARTE DECIMAL, y eso no es precisión de adorno: es la diferencia entre acotar y no
    acotar.** La primera versión contaba cifras (`len(str(n)) - 1`), que es el log10 redondeado hacia
    abajo, y para la base 2 daba **0**. Como la magnitud de una potencia es `log10(base) * exponente`,
    ese cero se multiplicaba por el exponente y **`2**999999999` salía con magnitud cero**: la guarda
    lo daba por inofensivo. Un error de redondeo de 0,3 en la base es un error sin techo en el
    resultado, así que aquí se calcula, no se estima.

    `math.log10` acepta enteros grandes de Python sin pasar por `float`, así que no desborda a partir
    de 1e308 — comprobado con un entero de 500 cifras.
    """
    if n.is_zero:
        return 0.0
    try:
        return math.log10(abs(int(n))) if n.is_Integer else math.log10(abs(float(n)))
    except (OverflowError, ValueError, TypeError):
        raise Desbordada("numero_ilegible") from None


def _valor(nodo) -> float:
    """El valor numérico de un subárbol YA acotado por `_magnitud`. Solo se llama sobre exponentes y
    argumentos cuya magnitud se ha comprobado antes: evaluar sin esa comprobación es la bomba."""
    try:
        v = float(sympy.N(nodo, 20))
    except (TypeError, ValueError, OverflowError, ZeroDivisionError):
        raise Desbordada("exponente_no_numerico") from None
    if not math.isfinite(v):
        raise Desbordada("exponente_excesivo")
    return v


def _magnitud(nodo) -> float:
    """Dígitos decimales que tendría el nodo, estimados **sin calcularlo**, de abajo arriba.

    Lanza `Desbordada` en cuanto un nodo —cualquiera, no solo la raíz— se pasa de `MAX_DIGITOS`.
    """
    if nodo.is_Number:
        return _digitos(nodo)
    if nodo.is_NumberSymbol:                       # pi, E: constantes de tamaño conocido
        return _digitos(sympy.Float(nodo, 15))
    if nodo.free_symbols:
        raise Desbordada("expresion_con_incognitas")

    hijos = nodo.args
    nombre = getattr(nodo.func, "__name__", "")
    if isinstance(nodo, sympy.Mul):
        m = sum(_magnitud(x) for x in hijos)
    elif isinstance(nodo, sympy.Add):
        # El mayor sumando, más lo que puede aportar juntarlos: log10(n) de n sumandos.
        m = max(_magnitud(x) for x in hijos) + math.log10(max(len(hijos), 1))
    elif isinstance(nodo, sympy.Pow):
        base, exponente = hijos
        base_m = _magnitud(base)
        if _magnitud(exponente) > math.log10(MAX_DIGITOS) + 1:
            raise Desbordada("exponente_excesivo")
        m = base_m * _valor(exponente)
    elif nombre == "factorial":
        n = _argumento_acotado(hijos[0], "factorial_excesivo")
        # Stirling, que para esto sobra: log10(n!) ~ n*log10(n) - n/ln(10).
        m = 0.0 if n <= 1 else n * math.log10(n) - n / math.log(10)
    elif nombre == "binomial":
        n = _argumento_acotado(hijos[0], "binomial_excesivo")
        m = abs(n) * math.log10(2)          # C(n,k) <= 2^n, y con eso basta para acotar
    elif nombre == "sqrt":
        m = _magnitud(hijos[0]) / 2
    elif nombre == "lcm":
        m = sum(_magnitud(x) for x in hijos)
    elif nombre in _ACOTADAS_POR_ARGUMENTO:
        m = max(_magnitud(x) for x in hijos)
    elif nombre in _TRANSCENDENTALES:
        for x in hijos:
            if _magnitud(x) > MAX_DIGITOS_ARGUMENTO:
                raise Desbordada("argumento_transcendental_excesivo")
        # exp crece; sin/cos/tan y log no. El caso caro es exp, así que se acota por él.
        m = _valor(hijos[0]) / math.log(10) if nombre == "exp" else 1.0
    else:
        # NO SE ADIVINA. Una función cuyo crecimiento nadie ha declarado no se acota "por si acaso":
        # se rechaza, que es el único de los dos errores que no revienta la máquina.
        raise Desbordada("funcion_sin_crecimiento_declarado")

    return _dentro_del_tope(m)


def _dentro_del_tope(m: float) -> float:
    """El tope, con la comprobación de finitud PRIMERO y en función aparte para poder probarla.

    `0.0 * inf` da `nan`, y **`nan` no es mayor que nada** —ni menor—, así que un `nan` atraviesa el
    `>` sin despeinarse y la guarda dice que sí. Así se colaba `2**2**2**30` mientras `_digitos`
    truncaba el logaritmo. Arreglado `_digitos`, esa expresión ya se caza antes por el exponente y
    este `nan` deja de ser alcanzable **por ese camino**: la comprobación se queda como segunda
    cerradura, con su propio test directo, porque una defensa que ningún test toca es una defensa que
    nadie sabe si sigue ahí.
    """
    if not math.isfinite(m) or abs(m) > MAX_DIGITOS:
        raise Desbordada("resultado_desbordado")
    return m


def _argumento_acotado(nodo, motivo: str) -> float:
    if _magnitud(nodo) > math.log10(MAX_DIGITOS) + 1:
        raise Desbordada(motivo)
    return _valor(nodo)


def admisible(expresion: str) -> tuple[bool, str]:
    """Las dos primeras puertas, antes de sympy: caracteres y nombres. `(ok, motivo)`."""
    if len(expresion) > MAX_CARACTERES:
        return False, "expresion_demasiado_larga"
    malo = _RE_CARACTER_PROHIBIDO.search(expresion)
    if malo:
        return False, "caracter_no_aritmetico"
    for nombre in _RE_NOMBRE.findall(expresion):
        if nombre not in PERMITIDO:
            return False, "nombre_no_permitido"
    return True, ""


def _coma_decimal(expresion: str) -> str:
    """La coma decimal española dentro de `expresion`, cuando significa eso **sin ambigüedad**.

    **Sale de los datos, no de la prudencia**: en el humo real, las TRES respuestas que produjeron un
    cálculo con decimales escribieron `250 + 52,5`. El modelo redacta en español y escribe los
    números en español, también dentro de un campo que nosotros pensábamos como notación de
    programación.

    La regla es estrecha a propósito y es **exacta, no heurística**: la coma solo se convierte si la
    expresión **no tiene ni una letra**. Sin nombres de función, una coma no puede ser un separador de
    argumentos —no hay a qué separar—, así que solo puede ser decimal. Con letras (`binomial(7,2)`)
    no se toca nada, porque ahí la coma sí significa otra cosa y adivinar entre las dos sería
    exactamente la interpretación que este verificador no hace.
    """
    return expresion.replace(",", ".") if not _RE_NOMBRE.search(expresion) else expresion


def evaluar(expresion: str):
    """Parsea dos veces: la primera **sin evaluar**, para que la guarda mire el árbol antes de que
    nada se calcule; la segunda, ya evaluando. El doble parseo cuesta microsegundos y es lo que hace
    que la guarda llegue a tiempo — con `evaluate=True` a la primera, la bomba estalla dentro del
    parser y no hay dónde ponerse delante."""
    expresion = _coma_decimal(expresion)
    arbol = parse_expr(expresion, local_dict=_INERTE, global_dict=_INTERNO,
                       transformations=_TRANSFORMACIONES, evaluate=False)
    _magnitud(arbol)
    return parse_expr(expresion, local_dict=PERMITIDO, global_dict=_INTERNO,
                      transformations=_TRANSFORMACIONES, evaluate=True)


def _en_punto(afirmado: str) -> str:
    """La coma decimal del contrato, en el punto que entiende `Decimal`. **Y solo la coma**: el
    contrato no permite puntos, así que aquí no hay nada que adivinar (ver `RESULTADO_NUMERICO`)."""
    return str(afirmado).strip().replace(",", ".")


def _decimales_escritos(afirmado: str) -> int:
    """Los decimales que el modelo ESCRIBIÓ, que es la entrada de la tolerancia. Por eso el campo es
    una cadena: `3,30` afirma dos decimales y `3,3` uno, y un `float` no distingue."""
    p = _en_punto(afirmado)
    return len(p.split(".")[1]) if "." in p else 0


def _a_decimal(valor, decimales: int) -> Decimal:
    """El valor exacto, con cifras significativas de sobra para poder redondear a `decimales`."""
    enteras = max(1, int(_digitos(valor)) + 1) if not valor.is_zero else 1
    return Decimal(str(sympy.N(valor, enteras + decimales + GUARDA_CIFRAS)))


def comparar(valor, afirmado: str) -> tuple[bool, str]:
    """¿El resultado afirmado es el que sale del recálculo? `(coincide, cómo)`.

    LA TOLERANCIA SE DERIVA, NO SE ADIVINA, que es la diferencia entre un criterio y un número
    puesto a ojo:

    - Si el recálculo es **exacto** (entero o racional), se compara **exacto**, y en aritmética de
      precisión infinita: `Rational("0.1")` es un décimo, no el flotante más cercano a un décimo. Un
      entero de 30 cifras se compara bien, que es lo que un `float` no hacía.
    - Si es **decimal** (una raíz, un pi), pasa si el valor exacto **redondeado a los decimales que
      el modelo escribió** es el afirmado. O sea: la precisión de la comparación sale de la propia
      afirmación. Decir "10/3 son 3,33" es correcto y "10/3 son 3,5" no lo es, y esta regla los
      separa sin que nadie tenga que elegir un epsilon.

    Se aceptan **las dos convenciones de redondeo** en el empate. `1/8` es `0,125` exacto: quien
    redondea a dos decimales como se enseña en el instituto escribe `0,13`, y quien redondea al par
    escribe `0,12`. (El contrato escribe la coma decimal; aquí se pasa a punto para `Decimal`.) Las dos son respuestas correctas del mismo cálculo, y podar una sería castigar
    una convención. El caso solo existe en el empate exacto, así que la manga ancha es de un dígito
    en el último decimal y está declarada.
    """
    afirmado = _en_punto(afirmado)
    decimales = _decimales_escritos(afirmado)
    if valor.is_Rational and sympy.Rational(afirmado) == valor:
        return True, "exacta"
    try:
        exacto = _a_decimal(valor, decimales)
        cuanto = Decimal(1).scaleb(-decimales)
        # La precisión del contexto se SUBE a la del número, porque la de fábrica son 28 cifras y
        # `2**100` tiene 31: con la de fábrica, `quantize` no devuelve un `False`, lanza. Otra vez
        # el instrumento, esta vez el de comparar.
        with localcontext() as ctx:
            ctx.prec = max(len(exacto.as_tuple().digits) + decimales + GUARDA_CIFRAS, ctx.prec)
            for modo in (ROUND_HALF_UP, ROUND_HALF_EVEN):
                if exacto.quantize(cuanto, rounding=modo) == Decimal(afirmado):
                    return True, f"redondeo_a_{decimales}_decimales"
    except (InvalidOperation, ValueError, TypeError, ArithmeticError, Desbordada):
        return False, ""
    return False, ""


def verificar(afirmacion: dict) -> dict:
    """Veredicto de UNA afirmación `calculo`. No lanza: un verificador que revienta con una entrada
    rara convierte una poda en un 500."""
    expresion = (afirmacion.get("expresion") or "").strip()
    afirmado = afirmacion.get("resultado_afirmado")
    base = {"expresion": expresion[:200], "resultado_afirmado": afirmado}

    if not expresion:
        return {**base, "veredicto": NO_VERIFICABLE, "motivo": "sin_expresion",
                "detalle": "no hay nada que recalcular"}
    if afirmado is None or not str(afirmado).strip():
        # El `null` del contrato: "mi resultado no es un número". Es una respuesta honesta y se
        # trata como tal — el 7bis al derecho: se le dio forma de decirlo, así que se le cree.
        return {**base, "veredicto": NO_VERIFICABLE, "motivo": "sin_resultado_afirmado",
                "detalle": "la afirmación no declara un resultado numérico que comparar"}

    if not _RE_RESULTADO.match(str(afirmado).strip()):
        return {**base, "veredicto": NO_VERIFICABLE, "motivo": "resultado_mal_formado",
                "detalle": f"'{afirmado}' no es un número del contrato (coma decimal, sin separador "
                           f"de millar): el campo está mal formado, así que no se juzga al alumno"}

    ok, motivo = admisible(expresion)
    if not ok:
        return {**base, "veredicto": NO_VERIFICABLE, "motivo": motivo,
                "detalle": "la expresión no es aritmética admisible (código, o fuera de la lista "
                           "blanca): NO se poda, porque no poder comprobarlo no es que sea falso"}

    try:
        valor = evaluar(expresion)
    except Desbordada as e:
        return {**base, "veredicto": NO_VERIFICABLE, "motivo": str(e),
                "detalle": f"la guarda paró la expresión antes de evaluarla (tope {MAX_DIGITOS} "
                           f"dígitos): no se calcula, y por tanto no se juzga"}
    except Exception:  # noqa: BLE001 - el parser de sympy lanza de todo; ninguna es un veredicto
        return {**base, "veredicto": NO_VERIFICABLE, "motivo": "expresion_no_parsea",
                "detalle": "sympy no pudo leer la expresión: no se juzga lo que no se ha calculado"}

    if valor.free_symbols or not valor.is_number:
        return {**base, "veredicto": NO_VERIFICABLE, "motivo": "expresion_con_incognitas",
                "detalle": "la expresión no da un número: no hay nada que comparar"}
    if valor.has(sympy.zoo, sympy.nan, sympy.oo, -sympy.oo):
        return {**base, "veredicto": NO_VERIFICABLE, "motivo": "sin_valor_numerico",
                "detalle": "el recálculo no da un número finito (división por cero o indefinido)"}

    coincide, como = comparar(valor, str(afirmado))
    recalculado = str(sympy.N(valor, 12)) if not valor.is_Integer else str(valor)
    base = {**base, "recalculado": recalculado}
    if coincide:
        return {**base, "veredicto": VERIFICADA, "motivo": None, "comparacion": como,
                "detalle": f"el recálculo da {recalculado} y la afirmación dice {afirmado}"}
    return {**base, "veredicto": PODADA, "motivo": "resultado_no_coincide",
            "decimales_afirmados": _decimales_escritos(str(afirmado)),
            "detalle": f"el recálculo da {recalculado} y la afirmación dice {afirmado}"}

# --- LA CUENTA QUE NO SE DECLARO COMO CUENTA (14 de agosto de 2026) -------------------------------

#: EL `tipo` ES UNA AFIRMACION DEL MODELO SOBRE SU PROPIA SALIDA, Y LA VERIFICACION SE DESPACHABA
#: SOBRE EL SIN COMPROBARLO. Esa es la premisa que rompe este bloque, y no es robustez: es el
#: principio 6 en la raiz. Fiarse de la etiqueta para decidir SI se verifica es pedirle al productor
#: que diga cuando hay que comprobarlo — el eco que el principio 6 rechaza. **El verificador no puede
#: preguntarle al modelo que instrumento le aplica.**
#:
#: Medido: la derivacion fabricada que cazo el conjunto del 5.0 —"160 horas - 20 horas = 140 horas",
#: aritmetica inventada para aterrizar en el numero que le dieron— llego etiquetada como
#: `conocimiento`, sin `expresion`, y el recalculo NUNCA la miro. Sobre 629 afirmaciones reales, 4
#: `andamiaje` y 1 `conocimiento` llevan una cuenta con `=` dentro de su texto.
#:
#: **LA DETECCION ES DELIBERADAMENTE GENEROSA, y eso es lo que la distingue de la extraccion que el
#: ADR 0016 evito.** Alli una extraccion mala producia un VEREDICTO FALSO sobre el trabajo del
#: alumno; aqui produce un "no pude comprobarlo": lo que se detecta de mas se intenta recalcular, y
#: lo que no parsea sale `no_verificable` con su motivo, JAMAS `podada`. Un falso positivo del
#: detector cuesta un intento de parseo; un falso negativo deja pasar una cuenta inventada.
#:
#: **ALCANCE DECLARADO, porque `=` es una COTA INFERIOR y no toda la aritmetica:** quedan fuera "el
#: doble de 40 son 80", "un 21 % de 100 euros" y cualquier cuenta escrita en palabras. Esto NO cierra
#: el agujero, lo estrecha; leer `calculo_no_declarado` como "ya cubrimos la aritmetica encubierta"
#: seria justo el verde mentiroso que este repo persigue.
RE_CUENTA = re.compile(
    # Se ADMITEN PALABRAS dentro de la cuenta -"160 horas - 20 horas = 140 horas"- porque en prosa
    # las unidades van pegadas a los numeros; se quitan despues. Sin esto, el caso que destapo todo
    # esto no se detectaba: la cuenta que mas importa es justo la que viene con sus unidades.
    r"(?P<izq>[-+(]?\d[\wáéíóúñ\s.,()^*/+\-×%]*?)\s*=\s*(?P<der>[-+]?\d[\d.,]*)")

#: Lo que se traduce antes de parsear: `x` y `×` son multiplicacion en prosa, `^` es potencia.
_EN_ARITMETICA = str.maketrans({"x": "*", "×": "*", "^": "^"})


def cuenta_en_el_texto(texto: str):
    """Saca `(expresion, resultado)` de una cuenta escrita en prosa, o `None`.

    Generosa a proposito (ver arriba): prefiere proponer una expresion dudosa —que como mucho saldra
    `no_verificable`— antes que dejar pasar una cuenta sin mirar.
    """
    for m in RE_CUENTA.finditer(texto or ""):
        izq = m.group("izq").translate(_EN_ARITMETICA)
        # Las PALABRAS se van despues de traducir la `x`: las unidades ("160 horas - 20 horas") no
        # son parte de la cuenta, pero la `x` de multiplicar si.
        izq = re.sub(r"[a-zA-ZáéíóúñÁÉÍÓÚÑ%]+", " ", izq).strip(" .,")
        while izq and izq[0] not in "0123456789(":
            izq = izq[1:]
        izq = izq.strip(" .,")
        # El punto final de la frase se cuela en el resultado ("= 62."): fuera.
        der = m.group("der").strip().rstrip(".,")
        if not izq or not der or not any(c in izq for c in "+-*/^"):
            continue          # "es 62 = 62" no es una cuenta, es una igualdad tonta
        return izq, der
    return None


def verificar_texto(texto: str, tipo: str = "?") -> dict | None:
    """Verifica una cuenta ENCONTRADA EN EL TEXTO de una afirmación que no se declaró `calculo`.

    Devuelve `None` si no hay ninguna cuenta que mirar. Si la hay, el veredicto lleva
    `calculo_no_declarado: True` para que la traza distinga esto de un `calculo` en regla: son la
    misma comprobación sobre dos situaciones distintas, y contarlas juntas escondería precisamente la
    que interesa.
    """
    encontrada = cuenta_en_el_texto(texto)
    if encontrada is None:
        return None
    expresion, resultado = encontrada
    v = verificar({"expresion": expresion, "resultado_afirmado": resultado.replace(".", ",")
                                                      if "," not in resultado else resultado})
    return {**v, "calculo_no_declarado": True, "tipo_declarado": tipo,
            "detalle": f"la afirmacion se declaro como '{tipo}' y su texto lleva una cuenta "
                       f"({expresion} = {resultado}); se recalcula igual, porque el tipo lo elige "
                       f"quien produce. " + (v.get("detalle") or "")}
