"""El contrato de generación tipada de la sección 7, como modelos tipados (encargo 2.2).

LO QUE ESTE MÓDULO COMPRUEBA ES LA **FORMA**, NO LA **VERDAD**, Y LA DISTINCIÓN NO ES UN MATIZ.

`validar_forma()` responde a una sola pregunta: *¿esto es el JSON de la sección 7?* Que los campos
estén, que `tipo` sea uno de los cinco, que una afirmación `literal` traiga `cita`. Nada más.

**No** comprueba que la cita esté de verdad en el fragmento, ni que la paráfrasis se siga del
temario, ni que el cálculo dé ese resultado, ni la regla de oro de la cobertura. Eso es la
**verificación**, vive en la **fase 4** (encargos 4.2 a 4.5) y es independiente por diseño: el
principio 6 dice que el que comprueba no comparte el supuesto del que produce, y aquí el productor
es el proveedor de inferencia mientras que la verificación irá contra el corpus y contra un modelo
distinto del generador.

Por eso una respuesta que sale de aquí lleva `veredicto = "sin_verificar"` en cada afirmación, y por
eso `afirmaciones.veredicto` es NOT NULL en la base: para que nadie pueda leer "validado" y entender
"verificado" dentro de dos semanas. Un JSON impecable puede estar mintiendo entero.

Que el mismo modelo tipado genere el `json_schema` que se envía Y valide lo que vuelve es correcto
**aquí**, y solo aquí: quien produce el texto es el proveedor, no nosotros, así que el modelo no
está auditando su propia salida. En la fase 4, donde produciríamos nosotros, no valdría.
"""
from typing import Annotated, Any, Literal

from pydantic import (BaseModel, ConfigDict, Field, ValidationError, field_validator,
                      model_validator)

MODOS = ("responder", "acompanar", "corregir")
TIPOS = ("literal", "parafrasis", "calculo", "conocimiento", "andamiaje")
TIPOS_FACTUALES = ("literal", "parafrasis", "calculo", "conocimiento")
ANDAMIAJES = ("transicion", "pregunta_al_alumno", "analogia", "resumen", "animo")
CONFIANZAS = ("alta", "media", "baja")

#: El campo del contrato que lleva la prosa que ve el alumno. Lo usa el emisor incremental del SSE.
CAMPO_PROSA = "respuesta_redactada"

#: El veredicto que llevan TODAS las afirmaciones que salen del 2.2. No es relleno: es la única
#: respuesta honesta mientras la fase 4 no exista.
SIN_VERIFICAR = "sin_verificar"


class ContratoRoto(ValueError):
    """El proveedor no devolvió el JSON de la sección 7. Un reintento y después abstención."""


class _Base(BaseModel):
    # `extra="forbid"` es el espejo exacto de `additionalProperties: false` del esquema que se envía.
    # Sin esto, el esquema prohibiría el campo de más y el validador lo tiraría en silencio: el
    # cliente sería estricto y el que comprueba, permisivo, que es la mitad equivocada.
    model_config = ConfigDict(extra="forbid")

    id: int
    texto: str


#: LA REFERENCIA A UN FRAGMENTO NO ES UN NÚMERO PELADO, Y ESO CIERRA UN FALLO MEDIDO.
#:
#: El 13 de agosto de 2026, de 337 citas reales, **9 apuntaban a un fragmento que no estuvo en el
#: contexto**, y leídas una a una resultaron ser tres casos: dos de ellos, el modelo **copiando el
#: número de una pregunta de test que prefijaba el texto que estaba citando**. El fragmento 2936
#: contiene literalmente `45. Para activar la validación…` y el modelo escribió `fragmento_id: 45`.
#: No se lo inventó: leyó "esto es el 45" y lo creyó. Con 223 fragmentos `enunciado_ejercicio`
#: numerados en el corpus, la superficie es grande.
#:
#: **Con `pattern` en el esquema y decodificación restringida, un número pelado se vuelve
#: INGRAMÁTICO: el modelo no puede escribir `45` aunque quiera.** Pasa de improbable a imposible,
#: que es la diferencia entre pedirlo en el prompt y que lo imponga la gramática (principio 7). Y no
#: introduce ninguna traducción de las que el 2.2 quería evitar: es el **id real** con un prefijo, y
#: `numero_de_referencia` lo devuelve con un `int()`.
REFERENCIA_FRAGMENTO = r"^F\d+$"


def numero_de_referencia(ref: str | None) -> int | None:
    """`F2936` -> 2936. `None` si no hay referencia. No lanza con basura: devuelve None."""
    if not ref:
        return None
    try:
        return int(str(ref)[1:])
    except (ValueError, IndexError):
        return None


class AfirmacionLiteral(_Base):
    tipo: Literal["literal"]
    fragmento_id: str = Field(pattern=REFERENCIA_FRAGMENTO,
                              description="referencia del fragmento tal como se te dio, con su F "
                                          "delante (por ejemplo F2936). NUNCA un número suelto")
    #: TOPE DE 120 CARACTERES, EN LA GRAMÁTICA Y NO EN EL PROMPT, y con dos motivos medidos —cada
    #: uno bastaría, y juntos hacen que este número sea de los pocos que no hay que discutir—:
    #:
    #: 1. **LATENCIA.** La `cita` es el **55 %** del bloque de afirmaciones, que a su vez es el
    #:    **60 %** de la espera hasta que el alumno ve el primer carácter. Y no es que haya más
    #:    afirmaciones en las consultas que se cortan: son las **mismas** (×1,12) con citas **×2,3
    #:    más largas** (88 caracteres por afirmación en las que llegan a tiempo, 202 en las que se
    #:    cortan).
    #: 2. **VERIFICABILIDAD**, que apareció midiendo el 4.2 y no se buscaba: sobre 328 citas reales,
    #:    las que **pasan** la comprobación literal tienen mediana **42** caracteres y las que
    #:    **fallan**, **124**. Por encima de 120 caracteres falla el **54 %**; por debajo, el 30 %.
    #:    Una cita más larga tiene más superficie donde equivocarse, así que el tope no solo abarata
    #:    la respuesta: **la hace más comprobable**.
    #:
    #: El valor sale de la DISTRIBUCIÓN y no de elegirlo: con la mediana sana en 88-98 caracteres,
    #: 120 no toca una cita normal y parte por la mitad las atípicas de 202 y 445. Muerde solo a los
    #: atípicos, que es lo que se le pide a un tope.
    #:
    #: **Y va en el esquema, no en el prompt**, por el principio 7: un campo que la gramática permite
    #: es un campo que el modelo rellena. Pedirlo por prompt sería pedir un favor.
    cita: str = Field(min_length=1, max_length=120,
                      description="texto exacto copiado del fragmento, sin cambiar una coma; la "
                                  "cita MÁS CORTA que sostenga la afirmación, máximo 120 caracteres")

    @field_validator("cita")
    @classmethod
    def _no_en_blanco(cls, v: str) -> str:
        # `minLength: 1` es lo que la gramática sabe decir, y deja pasar "   ". Una cita en blanco
        # supera cualquier comprobación de presencia y no se puede verificar contra nada: es el
        # hueco por el que se cuela una afirmación sin fuente con aspecto de tenerla.
        if not v.strip():
            raise ValueError("cita en blanco: no se puede verificar contra ningún fragmento")
        return v


class AfirmacionParafrasis(_Base):
    tipo: Literal["parafrasis"]
    fragmento_id: str = Field(pattern=REFERENCIA_FRAGMENTO,
                              description="referencia del fragmento, con su F delante")


#: EL RESULTADO AFIRMADO ES UN CAMPO, Y ES UNA CADENA CON PATRÓN NUMÉRICO (ADR 0016).
#:
#: **Por qué campo y no extracción:** hasta el 4.4, el resultado que el modelo AFIRMA vivía dentro de
#: la prosa —*"hay 7 combinaciones posibles"*—, así que comparar lo recalculado con lo afirmado
#: obligaba al servidor a sacar ese número del texto. Esa extracción es un paso nuevo **sin
#: verificar** metido justo dentro del verificador, y es el mismo fallo del `F2936` visto desde el
#: otro lado del cable: allí el modelo leía un número dentro de un texto y se lo creía.
#:
#: **Por qué CADENA y no `float`, que es donde esto se decidió de verdad:** la tolerancia del 4.4 se
#: apoya en *los decimales que el modelo ESCRIBIÓ* —`3.30` afirma dos decimales y `3.3` uno—, y un
#: `float` los borra: los dos son el mismo número máquina. Con `float`, la regla de tolerancia se
#: queda sin su entrada. Y de paso, por encima de 2^53 un `float` deja de ser exacto, que en un
#: temario con combinatoria (`20!` son 19 dígitos, `binomial(52,5)` es corriente) no es teórico.
#:
#: El `pattern` hace **ingramático** cualquier valor que no sea un número, igual que la `F` del
#: fragmento: la forma escrita sobrevive intacta y aun así no puede llegar basura (principio 7).
#:
#: **Y el `description` dice "sin separadores de millar" por una razón medida, no por gusto.** En el
#: humo real del 4.4, el modelo quiso escribir `4.294.967.296` —correcto en español, y así salió en
#: la prosa— y la decodificación restringida, al forzar un valor que casara con el patrón, dejó
#: **`4.294967296`**: un número **gramatical y equivocado**, cuatro coma tres en vez de cuatro mil
#: millones. El verificador lo podó bien, pero la avería la había causado nuestra propia gramática.
#: Es el 7bis por tercera vez: **cuando el campo no admite la forma que el modelo necesita, el modelo
#: no se calla, deforma**. Un patrón que aceptase los puntos de millar es imposible sin ambigüedad
#: (`4.294` sería a la vez cuatro mil y cuatro coma tres), así que lo que se arregla es lo otro: se
#: le dice, **en la descripción del campo**, cómo escribirlo. Y ahí sí funciona una descripción,
#: que es el complemento exacto de la lección del prompt: el `description` **no decide qué rama
#: elige** el modelo, pero **sí guía lo que escribe dentro** de un campo al que ya ha llegado.
#: **Y EL SEPARADOR DECIMAL ES LA COMA, QUE ES LO QUE ARREGLA EL FALLO MEDIDO.** Con el punto como
#: decimal (`^-?\d+(\.\d+)?$`), el modelo quiso escribir `4.294.967.296` —correcto en español, y así
#: salió en la prosa de esa misma respuesta— y la decodificación restringida, que permite **un** punto
#: y no dos, dejó **`4.294967296`**: cuatro coma tres en vez de cuatro mil millones. Un número
#: **gramatical y equivocado**, que es la peor clase de salida porque no falla, miente. Decírselo en
#: el `description` NO bastó: se probó, y el modelo volvió a escribir lo mismo.
#:
#: Con la coma decimal, las dos costumbres españolas caen **bien** por construcción: los puntos de
#: millar son ingramáticos desde el primer carácter, así que `4.294.967.296` sale `4294967296`, que
#: es exactamente lo que se quería; y `302,50` sale tal cual. **No queda ninguna ambigüedad que
#: resolver, porque solo hay un separador y solo significa una cosa** — un patrón que aceptara los
#: puntos de millar la tendría siempre (`4.294` sería a la vez cuatro mil y cuatro coma tres).
RESULTADO_NUMERICO = r"^-?\d+(,\d+)?$"


class AfirmacionCalculo(_Base):
    tipo: Literal["calculo"]
    fragmento_id: str | None = Field(default=None, pattern=REFERENCIA_FRAGMENTO)
    #: SIN `maxLength`, a diferencia de la `cita`, y la excepción tiene motivo: este campo lleva
    #: **también el código** del caso que el 4.4 deja declarado y no construido (el sandbox). Un tope
    #: en la gramática obligaría a un modelo con un fragmento de código de 300 caracteres a
    #: **deformar el campo** para poder emitirlo, que es exactamente el principio 7bis. El tope de la
    #: aritmética lo pone el verificador —donde sabe distinguir una expresión de un programa— y lo
    #: que no cabe sale `no_verificable`, que es lo que es.
    expresion: str = Field(min_length=1,
                           description="la expresión aritmética que hay que recalcular, con + - * / "
                                       "** ( ) y funciones como sqrt, factorial o binomial; o el "
                                       "código cuya salida afirmas")
    resultado_afirmado: str | None = Field(
        default=None, pattern=RESULTADO_NUMERICO,
        description="el resultado que AFIRMAS, en cifras, con COMA decimal y sin separador de "
                    "millar: 4294967296, o 302,50. null si tu resultado no es un número")

    @field_validator("expresion")
    @classmethod
    def _no_en_blanco(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("expresión en blanco: no hay nada que recalcular")
        return v


class AfirmacionConocimiento(_Base):
    tipo: Literal["conocimiento"]
    fragmento_id: str | None = Field(default=None, pattern=REFERENCIA_FRAGMENTO)


class AfirmacionAndamiaje(_Base):
    tipo: Literal["andamiaje"]
    andamiaje: Literal[ANDAMIAJES] = Field(description="qué clase de andamiaje pedagógico es")


#: LA FORMA DEL CONTRATO SE IMPONE EN LA GRAMÁTICA, NO SE CORRIGE DESPUÉS. La sección 7 escribe
#: "`cita` solo si tipo=literal", y la primera versión de esto era un solo modelo con los tres
#: campos opcionales y un validador que rechazaba las combinaciones malas. La primera llamada real
#: enseñó por qué no vale: en las TRES repeticiones el modelo rellenó `cita` en afirmaciones de tipo
#: `conocimiento`, copiando su propio texto. Con la salida restringida por esquema, un campo que
#: existe en la gramática es un campo que el modelo puede rellenar, y regañarle después solo produce
#: abstenciones. Partido en cinco variantes -una por tipo, cada una con exactamente los campos que
#: la sección 7 le permite-, `cita` no existe fuera de `literal` y el decodificador no la puede
#: emitir. Se comprueba igual al validar, porque el esquema lo pone el cliente y el que comprueba no
#: se fía del que produce; pero ya no es la comprobación la que sostiene la regla.
Afirmacion = Annotated[
    AfirmacionLiteral | AfirmacionParafrasis | AfirmacionCalculo | AfirmacionConocimiento
    | AfirmacionAndamiaje,
    Field(discriminator="tipo"),
]


class SiguientePaso(BaseModel):
    """Lo que el modelo PROPONE como siguiente paso.

    **`ref` no está aquí, y es el mismo caso que `confianza_recuperacion`** (ADR 0014, barrido de la
    sección 7): la guía lo define como *"ruta en el árbol"*, y el modelo **no ve el árbol**. Cualquier
    ruta que escribiera sería inventada, exactamente igual que un `fragmento_id` inventado, y con el
    agravante de que una ruta plausible del BOE es indistinguible de una real sin ir a comprobarla.
    El modelo propone `tipo` y `texto`; **la `ref` la resuelve el servidor contra el árbol**, que es
    lo que el 5.4 hace.
    """

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["concepto_arbol", "pregunta_al_alumno"]
    texto: str


class RespuestaTipada(BaseModel):
    """El orden de los campos ES el de la sección 7, y no es cosmético: con salida restringida por
    esquema, el modelo emite las claves en el orden declarado, así que este orden decide cuándo
    empieza a llegar la prosa que ve el alumno. Se mantiene el del contrato —las afirmaciones
    primero, la redacción que las hila después— y el coste se mide en vez de esconderse (ADR 0009).

    **`confianza_recuperacion` NO ESTÁ EN ESTE MODELO, y su ausencia es una decisión** (ADR 0014):
    lo pone el servidor, que es el único que sabe cuánto destacaba el primer candidato sobre el
    sexto. Dejarlo en el esquema sería pagar tokens por una opinión que se descarta, y sobre todo
    sería el principio 7 incumplido una planta más arriba: un campo que existe en la gramática es un
    campo que el modelo puede rellenar. El campo sigue existiendo en el contrato que SALE —va en el
    evento `afirmaciones` y en la traza—, pero no en el que el modelo escribe.
    """

    model_config = ConfigDict(extra="forbid")

    modo: Literal[MODOS]
    afirmaciones: list[Afirmacion]
    respuesta_redactada: str
    siguiente_paso: SiguientePaso

    @model_validator(mode="after")
    def _ids_distintos(self) -> "RespuestaTipada":
        ids = [a.id for a in self.afirmaciones]
        if len(ids) != len(set(ids)):
            raise ValueError(f"ids de afirmación repetidos: {ids}")
        return self


def _estricto(nodo: Any) -> Any:
    """Deja el esquema como lo quiere el proveedor: todo `required` y nada de extras.

    La documentación de Scaleway lo pide literalmente ("you are expected to set
    `additionalProperties` to false, and to specify all your properties as required"). Y no es
    burocracia del SDK: con schema mode el decodificador restringe token a token contra esta
    gramática, así que un campo opcional es una rama por la que el modelo se puede escapar sin
    emitirlo. Los campos que solo aplican a un tipo siguen siendo opcionales POR VALOR —admiten
    `null`—, que es distinto de ser opcionales por presencia.
    """
    if isinstance(nodo, dict):
        # `discriminator` es una extensión de OpenAPI que pydantic añade a las uniones y que el
        # decodificador restringido no necesita: la unión ya está expresada con `oneOf` y con el
        # literal de `tipo` en cada rama. Se quita para no meterle al proveedor palabras de un
        # vocabulario que no es el suyo. `default` se va por lo mismo: aquí no hay opcionales.
        nodo = {k: _estricto(v) for k, v in nodo.items() if k not in ("discriminator", "default")}
        if nodo.get("type") == "object" and "properties" in nodo:
            nodo["additionalProperties"] = False
            nodo["required"] = list(nodo["properties"])
        return nodo
    if isinstance(nodo, list):
        return [_estricto(x) for x in nodo]
    return nodo


def esquema_json() -> dict:
    """El `json_schema` que viaja en `response_format`. Sale del MISMO modelo que luego valida."""
    return _estricto(RespuestaTipada.model_json_schema())


def response_format() -> dict:
    """El bloque `response_format` completo, en modo esquema.

    Modo esquema y no `json_object`: la propia documentación de Scaleway llama a `json_object`
    método heredado y avisa de que "producirá resultados de peor calidad". Aquí además no vale,
    porque sin esquema el modelo se inventa la forma y el contrato deja de ser un contrato.
    """
    return {"type": "json_schema",
            "json_schema": {"name": "RespuestaTipada", "schema": esquema_json()}}


def validar_forma(objeto: dict) -> RespuestaTipada:
    """Valida la FORMA del contrato. No verifica nada de lo que dice (eso es la fase 4)."""
    try:
        return RespuestaTipada.model_validate(objeto)
    except ValidationError as e:
        raise ContratoRoto(_resumen(e)) from e


def _resumen(e: ValidationError) -> str:
    """Un mensaje corto y accionable: el reintento único de la sección 7 se le manda al modelo."""
    partes = []
    for fallo in e.errors()[:5]:
        donde = ".".join(str(x) for x in fallo["loc"]) or "(raíz)"
        partes.append(f"{donde}: {fallo['msg']}")
    return "; ".join(partes)
