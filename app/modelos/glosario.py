"""El contrato de extracción del glosario y su validación SIN MODELO (encargo 2.6).

DOS PIEZAS QUE NO PUEDEN COMPARTIR SUPUESTO, y por eso están juntas en un fichero pero separadas en
el código: el **extractor** le pide al modelo pequeño `{termino, definicion}` sobre la frase
definitoria de un fragmento; el **validador** comprueba que esa definición está de verdad en el
fragmento. Preguntarle al mismo modelo si su propia definición sale del texto sería un eco, no una
comprobación (principio 6), así que aquí el validador **no usa ningún modelo**: normaliza y busca la
subcadena. Si no está, la entrada no entra.

**Y esa es toda la validación de este encargo, a propósito.** La guía admite una segunda vía —NLI
distinto del extractor, para las definiciones parafraseadas—, y se secuencia: primero la literal
sola y se mide. Un glosario que solo admite definiciones copiadas letra a letra es más pequeño, y a
cambio su garantía es **más fuerte**, porque no hay ningún modelo en el lazo de verificación. Si con
eso basta para lo que el encargo tiene que decidir, el NLI no entra hoy y llega en el 4.3, donde ese
modelo tiene que existir de todas formas.

La normalización es la de la sección 8, la misma que usará el verificador `literal` de la fase 4:
minúsculas, espacios colapsados, **tildes conservadas**. Conservar las tildes no es un detalle
estético: "cómo" y "como" no son la misma palabra, y un validador que las iguale acepta citas que no
son citas.
"""
import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

RE_ESPACIOS = re.compile(r"\s+")

#: Lo que se le permite escribir al modelo. `definicion` es lo único que se va a comparar contra el
#: fragmento, así que el prompt le pide copiarla tal cual: cuanto menos redacte, más entra.
LONGITUD_MAXIMA = 400


class ContratoDeGlosarioRoto(ValueError):
    """El modelo no devolvió `{termino, definicion}` con la forma pedida."""


class EntradaDeGlosario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # SIN `min_length`, y no por descuido: el contrato tiene una salida legítima para "aquí no se
    # define nada", y en ella los dos campos van con un guion. Un mínimo de longitud convertiría esa
    # respuesta correcta en "contrato roto", o sea que movería casos de un cubo de descarte a otro
    # **sin que nadie se enterara**, y esos cubos alimentan la decisión de este encargo. Quien filtra
    # de verdad es la validación literal, no una restricción de tamaño.
    termino: str = Field(max_length=80,
                         description="el término que se define, en singular y sin artículo")
    definicion: str = Field(max_length=LONGITUD_MAXIMA,
                            description="la definición COPIADA LETRA A LETRA del texto dado")
    hay_definicion: Literal["si", "no"] = Field(
        description="'no' si el texto no define ningún término; entonces término y definición van "
                    "vacíos con un guion")

    @field_validator("termino", "definicion")
    @classmethod
    def _sin_blancos(cls, v: str) -> str:
        return v.strip()


def esquema_de_extraccion() -> dict:
    """El `response_format` de la extracción, en modo esquema como todo lo demás del proyecto."""
    esquema = EntradaDeGlosario.model_json_schema()
    esquema["additionalProperties"] = False
    esquema["required"] = list(esquema["properties"])
    return {"type": "json_schema",
            "json_schema": {"name": "EntradaDeGlosario", "schema": esquema}}


def normalizar(texto: str) -> str:
    """Minúsculas, espacios colapsados y tildes CONSERVADAS (sección 8).

    Se quitan además los caracteres de control y se unifica la forma Unicode: el corpus viene de
    conversiones de PDF y una 'é' precompuesta y una 'e' + acento combinante se ven iguales en
    pantalla y son cadenas distintas. Sin esto, el validador rechazaría citas correctas y nadie
    entendería por qué.
    """
    texto = unicodedata.normalize("NFC", texto)
    return RE_ESPACIOS.sub(" ", texto).strip().lower()


def validar_literal(definicion: str, texto_del_fragmento: str) -> tuple:
    """¿Está esa definición, letra a letra, en el fragmento? Devuelve (pasa, evidencia).

    Sin umbral, sin modelo y sin porcentaje de parecido: o está o no está. Es la misma regla que la
    sección 8 le exige a una afirmación `literal`, y se usa aquí por el mismo motivo: lo que el
    glosario diga se le va a citar a un alumno.
    """
    aguja, pajar = normalizar(definicion), normalizar(texto_del_fragmento)
    if not aguja:
        return False, "definicion vacia"
    posicion = pajar.find(aguja)
    if posicion < 0:
        return False, "no aparece en el fragmento"
    return True, f"literal en el fragmento, posicion {posicion} de {len(pajar)} caracteres"


def leer_entrada(objeto: dict) -> EntradaDeGlosario:
    try:
        return EntradaDeGlosario.model_validate(objeto)
    except ValidationError as e:
        raise ContratoDeGlosarioRoto(
            "; ".join(f"{'.'.join(str(x) for x in f['loc'])}: {f['msg']}" for f in e.errors()[:3])
        ) from e
