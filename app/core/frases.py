"""Trocear en frases y comparar vocabulario. **Una sola implementación, la del 1.8.**

Estas tres funciones nacieron en `scripts/detectar_conflictos.py` (encargo 1.8) y las valida su
test. Se mueven aquí para que el verificador NLI del 4.3 use **exactamente el mismo código** y no
una copia que se separe: dos implementaciones de "trocear en frases" acaban discrepando en el caso
raro, y el caso raro es donde se decide un veredicto.

LA LECCIÓN QUE VIENE CON ELLAS, y que el 1.8 pagó con un número: **el NLI se entrenó con FRASES.**
Darle dos trozos de 500 tokens lo saca de su terreno y marcaba 4.255 contradicciones, entre ellas
dos salidas de `ping` con distinta IP. A nivel de frase acierta de lleno.
"""
import re

#: **EXACTAMENTE la lista del 1.8, ni una palabra más.** La primera versión de este módulo traía una
#: lista ampliada "de sentido común" —`cuando`, `porque`, `puede`, `tiene`…— y eso habría cambiado en
#: silencio el comportamiento de `detectar_conflictos.py`, que es código **validado por su test**:
#: los conflictos del 1.8 se midieron con ESTA lista y no con otra. Compartir una implementación
#: significa compartirla entera, incluidos sus datos; ampliarla "de paso" es reescribir el
#: instrumento por el camino y quedarse con los números viejos.
VACIAS = set("de la el los las un una y o que en para con por se es son del al como su sus".split())

#: Frases utiles: ni fragmentos de linea ni parrafos enteros. Los limites son los del 1.8.
RE_FRASE = re.compile(r"(?<=[.!?])\s+|\n+")


def frases_de(texto: str) -> list:
    return [f.strip() for f in RE_FRASE.split(texto) if 40 < len(f.strip()) < 400]


def palabras_de(frase: str) -> set:
    return {p for p in re.findall(r"[a-záéíóúñ]{4,}", frase.lower()) if p not in VACIAS}
