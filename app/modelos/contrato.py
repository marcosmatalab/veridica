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


class AfirmacionLiteral(_Base):
    tipo: Literal["literal"]
    fragmento_id: int
    cita: str = Field(min_length=1,
                      description="texto exacto copiado del fragmento, sin cambiar una coma")

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
    fragmento_id: int


class AfirmacionCalculo(_Base):
    tipo: Literal["calculo"]
    fragmento_id: int | None = None
    expresion: str = Field(min_length=1, description="expresión o código que se va a recalcular")

    @field_validator("expresion")
    @classmethod
    def _no_en_blanco(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("expresión en blanco: no hay nada que recalcular")
        return v


class AfirmacionConocimiento(_Base):
    tipo: Literal["conocimiento"]
    fragmento_id: int | None = None


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
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["concepto_arbol", "pregunta_al_alumno"]
    ref: str | None = None
    texto: str


class RespuestaTipada(BaseModel):
    """El orden de los campos ES el de la sección 7, y no es cosmético: con salida restringida por
    esquema, el modelo emite las claves en el orden declarado, así que este orden decide cuándo
    empieza a llegar la prosa que ve el alumno. Se mantiene el del contrato —las afirmaciones
    primero, la redacción que las hila después— y el coste se mide en vez de esconderse (ADR 0009).
    """

    model_config = ConfigDict(extra="forbid")

    modo: Literal[MODOS]
    afirmaciones: list[Afirmacion]
    respuesta_redactada: str
    siguiente_paso: SiguientePaso
    confianza_recuperacion: Literal[CONFIANZAS]

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
