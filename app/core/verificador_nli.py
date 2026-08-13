"""Verificador de paráfrasis por NLI (encargo 4.3). En **CPU**, y sobre **frases**, no sobre trozos.

Es la segunda mitad de la tesis: el 4.2 comprueba lo que se copió letra a letra, y esto comprueba lo
que se reformuló. Modelo **distinto del generador** (principio 6): quien escribió la respuesta fue
Mistral en Scaleway; quien la juzga es mDeBERTa aquí dentro.

## POR QUÉ SOBRE FRASES Y NO SOBRE EL FRAGMENTO ENTERO, con el número que lo obliga

**La ventana de mDeBERTa-v3-base son 512 tokens TOTALES** —premisa más hipótesis— y los fragmentos
se trocearon a 512 **más su línea de contexto**. Medido sobre 300 fragmentos reales con el
tokenizador del propio NLI: mediana **480**, p95 **566**, máximo **598**, y **el 33 % desborda la
ventana ellos solos**. O sea que la librería trunca **en silencio**.

**Y lo que pasa al truncar es PEOR que lo que se temía.** La predicción era un falso negativo: la
afirmación sostenida por la cola del fragmento saldría `neutral`. Comprobado con un caso plantado
—frase de apoyo puesta al final a propósito—, lo que sale es:

    premisa = fragmento entero (truncado, la frase de apoyo CORTADA) -> entailment 0.988
    control: premisa = solo el relleno, que no menciona el tema      -> entailment 0.988

**Un falso positivo con dos decimales**, que es el lado caro de la asimetría del 4.2. El modelo
entailment-ea una hipótesis que la premisa no sostiene en absoluto. Con la frase correcta como
premisa, el mismo par da `entailment 0.975`; y sin ella, `neutral 0.949`. **La selección de frase no
es una optimización: es lo que hace que el veredicto signifique algo.**

## LA MAQUINARIA ES LA DEL 1.8, PERO UN PARÁMETRO SUYO NO TRANSFIERE

`mejor_par_de_frases` compara **fragmento contra fragmento** y por eso acota a las **12 primeras**
frases de cada lado: es una comparación O(n²) y sin tope se dispara. Aquí la comparación es
**fragmento contra una hipótesis corta**, o sea **O(n)**, y ese mismo tope **tira la cola del
fragmento**: en el caso plantado, la frase de apoyo estaba en la posición **42 de 43** y el tope
cortaba en 12. El selector elegía otra frase y devolvía `neutral` — falso negativo, esta vez.

**La lección, que vale más que el arreglo: se reutiliza el código validado, pero se comprueba que
sus PARÁMETROS transfieren.** Un tope de coste puesto para acotar un cuadrático deja de tener
sentido cuando el problema pasa a ser lineal, y lo único que sigue haciendo es perder datos.
"""
import os
import re

from app.core.frases import frases_de, palabras_de

MODELO = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"

#: Umbral de `entailment` para dar por buena una paráfrasis. **DECLARADO SIN CALIBRAR**, igual que
#: los márgenes de `confianza_recuperacion`: sale de la sección 8 y su barrido es el encargo 4.6.
UMBRAL = float(os.environ.get("UMBRAL_NLI") or 0.80)

#: Cobertura mínima de la hipótesis para molestar al NLI. Por debajo, la frase y la hipótesis hablan
#: de cosas distintas y el veredicto sería ruido: se declara NO VERIFICABLE en vez de inventarlo.
COBERTURA_MINIMA = 0.20

#: CÓDIGO: el 1.8 ya decidió que NO entra al NLI, con su test. Un modelo entrenado en prosa sobre un
#: bloque de Java da ruido con dos decimales, y aquí ese ruido sería un veredicto sobre una
#: afirmación.
#:
#: **PERO EL DETECTOR DEL 1.8 NO TRANSFERÍA, y lo enseñó el humo: 6 de 10, con 3 de los 4 fallos en
#: los pares que llevan identificadores.** Aquel detector caza `@\w+` y cualquier paréntesis, lo cual
#: es correcto para su trabajo —descartar pares de FRAGMENTOS que son bloques de código— y desastroso
#: para este, donde la premisa es **una frase en prosa que MENCIONA identificadores**. En un corpus
#: medio código eso es casi toda la prosa útil: *"Sin `@Valid` la validación no se ejecuta"* salía
#: clasificada como código y por tanto **no verificable**.
#:
#: La distinción no es la presencia de un identificador, es la **DENSIDAD de estructura**: una frase
#: menciona una anotación; un bloque tiene llaves, puntos y coma y varias marcas a la vez. Medido
#: sobre 6 frases de prosa reales y 4 bloques de código reales: el detector heredado falla **4 de
#: 10** y este **1 de 10** —y el que falla es una lista de opciones tipo test, que la selección de
#: frase descarta igualmente por cobertura—.
RE_ESTRUCTURA = re.compile(r"[{};]|\)\s*\{|=>|->|\bnew\b|\breturn\b|\bpublic\b|\bprivate\b|\bvoid\b")


def parece_codigo(frase: str) -> bool:
    """Densidad de estructura, no una sola coincidencia. Ver el bloque de arriba."""
    marcas = len(RE_ESTRUCTURA.findall(frase))
    varias_lineas = sum(1 for x in frase.split("\n") if x.strip()) > 1
    return marcas >= 3 or (marcas >= 2 and varias_lineas)

ENTAILMENT, NEUTRAL, CONTRADICCION = "entailment", "neutral", "contradiction"
VERIFICADA = "verificada"
PODADA = "podada"
NO_VERIFICABLE = "no_verificable"
REINTENTO = "reintento_con_señal"


def seleccionar_frase(fragmento: str, hipotesis: str):
    """La frase del fragmento que más cubre la hipótesis. **Sin tope: la comparación es lineal.**

    Se mide **cobertura de la hipótesis** y no Jaccard: la comparación es asimétrica —premisa larga
    contra hipótesis corta— y Jaccard penaliza las frases largas por serlo. Es el principio 8 leído
    al derecho: lo que rompe una comparación es la asimetría, así que la medida tiene que tenerla en
    cuenta en vez de fingir que no está.
    """
    ph = palabras_de(hipotesis)
    if not ph:
        return None, 0.0
    mejor, punto = None, 0.0
    for f in frases_de(fragmento):
        pf = palabras_de(f)
        if not pf:
            continue
        c = len(pf & ph) / len(ph)
        if c > punto:
            mejor, punto = f, c
    return mejor, punto


class VerificadorNLI:
    """Carga mDeBERTa una vez por proceso. **CPU por defecto y a propósito.**

    La GPU ya es el cuello —embebedor y reordenador serializan desde el quinto alumno— y meter allí
    un tercer modelo bajaría otra vez el techo de concurrencia. Medido en CPU: 216 ms por par a 16
    hilos, y como solo van al NLI las paráfrasis y las literales degradadas (~40 %), son 1-2 pares
    por respuesta. Cabe entero dentro de la ventana en la que el modelo aún está escribiendo la
    prosa (~823 ms), o sea que **en tiempo de pared sale gratis**.
    """

    def __init__(self, dispositivo: str = "cpu", umbral: float = UMBRAL):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.umbral = umbral
        self.dispositivo = dispositivo
        self.tokenizador = AutoTokenizer.from_pretrained(MODELO)
        self.modelo = AutoModelForSequenceClassification.from_pretrained(MODELO,
                                                                        dtype=torch.float32)
        self.modelo.to(dispositivo).eval()
        self.etiquetas = [self.modelo.config.id2label[k].lower()
                          for k in sorted(self.modelo.config.id2label)]

    def clasificar(self, premisa: str, hipotesis: str) -> tuple:
        import torch

        with torch.no_grad():
            e = self.tokenizador(premisa, hipotesis, truncation=True, max_length=512,
                                 return_tensors="pt").to(self.dispositivo)
            p = torch.softmax(self.modelo(**e).logits, dim=-1)[0]
        i = int(p.argmax())
        return self.etiquetas[i], float(p[i])

    def verificar(self, hipotesis: str, fragmento: str) -> dict:
        """Veredicto de UNA paráfrasis contra su fragmento. No lanza.

        Las cuatro salidas, con la política de la sección 8: `entail` por encima del umbral pasa,
        `contradiction` **poda siempre** —sin umbral, porque una contradicción detectada es la señal
        más cara de ignorar—, `neutral` dispara el reintento único con la señal, y lo que no se puede
        juzgar se declara **no verificable** en vez de inventarle un veredicto.
        """
        frase, cobertura = seleccionar_frase(fragmento, hipotesis)
        if frase is None or cobertura < COBERTURA_MINIMA:
            return {"veredicto": NO_VERIFICABLE, "motivo": "sin_frase_relacionada",
                    "cobertura": round(cobertura, 2),
                    "detalle": "ninguna frase del fragmento comparte vocabulario con la afirmación: "
                               "un veredicto aquí sería ruido"}
        if parece_codigo(frase):
            # El 1.8 ya lo decidió con su test y aquí se hereda: un NLI de prosa sobre un bloque de
            # código da ruido con dos decimales. Lo honesto es decir que no se puede juzgar.
            return {"veredicto": NO_VERIFICABLE, "motivo": "contenido_es_codigo",
                    "cobertura": round(cobertura, 2), "frase": frase[:200],
                    "detalle": "la frase de apoyo es código: el NLI está entrenado en prosa y su "
                               "veredicto aquí no significa nada"}

        etiqueta, probabilidad = self.clasificar(frase, hipotesis)
        base = {"nli": etiqueta, "probabilidad": round(probabilidad, 3), "frase": frase[:200],
                "cobertura": round(cobertura, 2), "umbral": self.umbral,
                "calibrado": False, "calibracion": "encargo 4.6"}
        if etiqueta == CONTRADICCION:
            return {**base, "veredicto": PODADA, "motivo": "contradice_al_fragmento",
                    "detalle": "el fragmento dice lo contrario: se poda sin mirar el umbral"}
        if etiqueta == ENTAILMENT and probabilidad >= self.umbral:
            return {**base, "veredicto": VERIFICADA, "motivo": None,
                    "detalle": "el fragmento sostiene la afirmación"}
        return {**base, "veredicto": REINTENTO, "motivo": "no_se_sigue_del_fragmento",
                "detalle": "el fragmento no sostiene la afirmación; dispara el reintento único"}
