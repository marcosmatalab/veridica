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

#: Umbral de `entailment` para dar por buena una paráfrasis. **CALIBRADO EL 14/08/2026 (4.6, ADR
#: 0020): 0,60**, elegido en el plano (suelo × umbral) con el desempate PRE-escrito —cero negativos
#: aprobados manda; luego máximos positivos verificados; luego el umbral más bajo—. Los datos:
#: 189 positivos entailed por construcción (pasan el 4.2) y 189 negativos emparejados excluyendo
#: los casi-duplicados del 1.8; el 0,80 inicial **aprobaba un negativo** y verificaba 25 positivos
#: contra 34 del punto elegido (corrida 32 de `corridas_eval`). n del tramo de umbral: 56 —los
#: otros 133 positivos fallan por SELECCIÓN, no por umbral, y están contados aparte—.
UMBRAL = float(os.environ.get("UMBRAL_NLI") or 0.60)

#: SUELO DE LA SELECCIÓN: cobertura mínima de la hipótesis para molestar al NLI. Por debajo, la
#: afirmación sale `no_verificable` **y al NLI no se le pregunta**.
#:
#: **Y el motivo no es el ahorro, es que el modo de fallo de este modelo ante un par malo NO es
#: abstenerse: es el falso positivo confiado.** Medido el 13 de agosto: con una premisa que no
#: menciona el tema, `entailment 0.988`. Así que darle "el mejor par disponible" cuando el mejor
#: par es malo no produce un `neutral` prudente, produce **dos decimales de seguridad sobre nada**.
#:
#: Es el mismo razonamiento que `fragmento_en_contexto` en el 4.2: **cuando la precondición del
#: instrumento no se cumple, no se usa el instrumento** — no se usa igualmente y se cree el
#: resultado.
#:
#: **RE-CALIBRADO LA TARDE DEL 14/08/2026 sobre el instrumento ARREGLADO (ancla de cita): 0,10**
#: (ADR 0020 v2, corrida 36). La mañana había dado 0,30 (corrida 32) porque sin ancla el suelo era
#: la única guarda contra pares malos; con el ancla puesta Y el conjunto de control limpio -39
#: positivos tenían texto='literal', el generador emitiendo el TIPO como texto- el plano baja el
#: suelo a 0,10 con CERO negativos aprobados: el negativo que se colaba estaba emparejado a una
#: fila rota. Se calibra sobre el instrumento arreglado, nunca sobre el roto.
COBERTURA_MINIMA = float(os.environ.get("NLI_COBERTURA_MINIMA") or 0.10)

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


def seleccionar_frase(fragmento: str, hipotesis: str, cita: str | None = None):
    """La frase del fragmento que más cubre la hipótesis. **Sin tope: la comparación es lineal.**

    Se mide **cobertura de la hipótesis** y no Jaccard: la comparación es asimétrica —premisa larga
    contra hipótesis corta— y Jaccard penaliza las frases largas por serlo. Es el principio 8 leído
    al derecho: lo que rompe una comparación es la asimetría, así que la medida tiene que tenerla en
    cuenta en vez de fingir que no está.

    **Y EL ANCLA DE LA CITA (14/08 tarde), medida antes de construirla:** la hipótesis es el TEXTO
    de la afirmación, no su cita, así que la frase que CONTIENE la cita no tiene por qué ser la de
    mayor solape con el texto — la selección buscaba en el sitio equivocado en 133 de 189 positivos
    de la calibración. Cuando el llamador CONOCE la cita (una `literal` degradada la lleva exacta),
    la búsqueda se restringe a las frases que la contienen, si las hay; la cobertura devuelta sigue
    siendo la de la hipótesis sobre la frase elegida, y el suelo se aplica igual — el ancla no
    esquiva ninguna guarda. Techo medido del arreglo: 37 de las 133; las 96 citas que CRUZAN frases
    quedan fuera y declaradas (selección multi-frase: no construida).
    """
    ph = palabras_de(hipotesis)
    if not ph:
        return None, 0.0
    candidatas = frases_de(fragmento)
    objetivo = (cita or "").strip()
    if objetivo:
        con_cita = [f for f in candidatas if objetivo in f]
        if con_cita:
            candidatas = con_cita
    mejor, punto = None, 0.0
    for f in candidatas:
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

    def verificar(self, hipotesis: str, fragmento: str, cita: str | None = None) -> dict:
        """Veredicto de UNA paráfrasis contra su fragmento. No lanza.

        Las cuatro salidas, con la política de la sección 8: `entail` por encima del umbral pasa,
        `contradiction` **poda siempre** —sin umbral, porque una contradicción detectada es la señal
        más cara de ignorar—, `neutral` dispara el reintento único con la señal, y lo que no se puede
        juzgar se declara **no verificable** en vez de inventarle un veredicto.
        """
        frase, cobertura = seleccionar_frase(fragmento, hipotesis, cita)
        if frase is None or cobertura < COBERTURA_MINIMA:
            # EL SUELO, y no se le pregunta al NLI. Su modo de fallo ante un par malo no es
            # abstenerse: es `entailment 0.988` sobre nada. Ver COBERTURA_MINIMA.
            return {"veredicto": NO_VERIFICABLE, "motivo": "sin_frase_relacionada",
                    "cobertura": round(cobertura, 2), "suelo": COBERTURA_MINIMA,
                    "calibrado": True, "calibracion": "4.6, ADR 0020 (14/08/2026), corrida 32",
                    "detalle": "ninguna frase del fragmento cubre la afirmacion por encima del "
                               "suelo: no se consulta al NLI, porque su fallo aqui no es dudar "
                               "sino acertar con aplomo por casualidad"}
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
                # De donde salio la frase: la traza tiene que poder contar cuantos veredictos
                # llegaron por el ancla y cuantos por cobertura, o el arreglo seria inauditable.
                "seleccion": ("por_cita" if (cita or "").strip()
                              and (cita or "").strip() in frase else "por_cobertura"),
                "calibrado": True, "calibracion": "4.6, ADR 0020 (14/08/2026), corrida 32"}
        if etiqueta == CONTRADICCION:
            return {**base, "veredicto": PODADA, "motivo": "contradice_al_fragmento",
                    "detalle": "el fragmento dice lo contrario: se poda sin mirar el umbral"}
        if etiqueta == ENTAILMENT and probabilidad >= self.umbral:
            return {**base, "veredicto": VERIFICADA, "motivo": None,
                    "detalle": "el fragmento sostiene la afirmación"}
        return {**base, "veredicto": REINTENTO, "motivo": "no_se_sigue_del_fragmento",
                "detalle": "el fragmento no sostiene la afirmación; dispara el reintento único"}
