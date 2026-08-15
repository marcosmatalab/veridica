"""Contar lo que sale del arnés de evaluación **declarando su unidad**: filas o casos.

## EL FALLO QUE ESTE MÓDULO HACE IMPOSIBLE, con su fecha y su tamaño

14 de agosto de 2026. Todos los titulares del día —la prueba de identidad del juez NLI, el plano de
calibración, las tasas de verificación— salieron **contando filas** de `afirmaciones` creyendo que
se contaban casos. Y no era una diferencia de matiz: **158 "positivos" eran 74 pares distintos, y
uno solo aparecía 20 veces** —el 12,7 % del denominador él solo—. Las medianas y los porcentajes
publicados estaban pesando cada caso por **cuántas veces se le había preguntado**.

**La causa no es del NLI ni del portero: es del ARNÉS.** El banco de evaluación repite las mismas
preguntas a propósito —así se mide la dispersión— y cada repetición vuelve a escribir las mismas
afirmaciones, las mismas citas y casi la misma prosa. **Cualquier** número calculado sobre esas
tablas hereda la repetición. La regla del repo —*ocurrencias y hallazgos se cuentan por separado*—
llevaba meses escrita; lo que faltó fue preguntar **qué es una fila** en ese arnés.

## POR QUÉ UNA FUNCIÓN Y NO UN RECORDATORIO

Un aviso en la guía es prosa que alguien tiene que acordarse de leer; **una función que devuelve las
dos cifras juntas hace que la confusión sea imposible en vez de improbable**. Quien agrega no puede
publicar un número sin tener delante su gemelo, y quien lo lee ve la diferencia sin preguntar.

Y la **clave** forma parte del resultado a propósito: *"la misma cita"* y *"la misma afirmación"* y
*"la misma frase de prosa"* son preguntas distintas, así que el conteo lleva escrito **por qué dos
elementos se consideraron el mismo caso**.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Conteo:
    """Las dos cifras y su clave, siempre juntas. `casos` nunca se publica solo, ni `ocurrencias`."""

    ocurrencias: int
    casos: int
    clave: str
    elementos: list = field(default_factory=list, repr=False)

    @property
    def factor(self) -> float:
        """Cuántas veces se repite el caso medio. 1,0 = no hay repetición."""
        return round(self.ocurrencias / self.casos, 2) if self.casos else 0.0

    def __str__(self) -> str:
        return (f"{self.casos} casos distintos de {self.ocurrencias} ocurrencias "
                f"(x{self.factor}, clave: {self.clave})")

    def a_dict(self) -> dict:
        """Lo que se persiste en `corridas_eval`. Las dos cifras y la clave: nunca una sola."""
        return {"ocurrencias": self.ocurrencias, "casos": self.casos, "factor": self.factor,
                "clave": self.clave}


def contar(items, clave_de, clave: str) -> Conteo:
    """Deduplica `items` por `clave_de(x)` y devuelve **las dos cifras**.

    `clave` es la descripción legible de qué hace iguales a dos elementos, y es obligatoria: un
    conteo sin ella no se puede auditar, porque el número depende de la pregunta que contesta.

    Los elementos devueltos son los PRIMEROS de cada clase, en orden de entrada: determinista, sin
    azar que no se pueda reproducir.
    """
    if not clave:
        raise ValueError("un conteo sin clave declarada no se puede auditar: di qué hace iguales "
                         "a dos elementos")
    vistos, unicos, n = set(), [], 0
    for x in items:
        n += 1
        k = clave_de(x)
        if k in vistos:
            continue
        vistos.add(k)
        unicos.append(x)
    return Conteo(ocurrencias=n, casos=len(unicos), clave=clave, elementos=unicos)


def porcentaje(parte: Conteo, total: Conteo) -> str:
    """Un porcentaje **en las dos unidades**, para que no se pueda publicar solo el que gusta."""
    def pct(a, b):
        return f"{100 * a / b:.1f} %" if b else "n/a"
    return (f"{pct(parte.casos, total.casos)} en casos ({parte.casos}/{total.casos}) | "
            f"{pct(parte.ocurrencias, total.ocurrencias)} en filas "
            f"({parte.ocurrencias}/{total.ocurrencias})")
