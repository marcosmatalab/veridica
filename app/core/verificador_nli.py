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

## LA PREMISA YA NO SALE DE UNA PARTICIÓN EN FRASES: ES UNA VENTANA ANCLADA EN EL SPAN DEL APOYO

La solución estructural (14/08, tras la re-calibración del ancla). El 61 % de fallos de selección
que quedaba tras el ancla estaba medido contra la partición de `frases_de`, que parte por `\\n+` y
DESCARTA lo que mide <40 o >400 caracteres: en markdown eso convierte listas y encabezados en
pseudo-frases y borra del conjunto de candidatas justo donde vive el apoyo. **Un filtro sobre el
conjunto de candidatas borra apoyo en silencio: descartar destruye; expandir preserva.** Así que
cuando el llamador trae un ancla textual —la `cita` de una literal degradada, el `apoyo` declarado
de una paráfrasis— la premisa se corta del FRAGMENTO CRUDO: se localiza el ancla como subcadena
(la maquinaria del 4.2: si no casa literalmente, no hay ventana y se cae a la selección de antes) y
se expande a bordes sanos. El cruce de frases se vuelve imposible por construcción: la ventana
contiene el ancla entera, la parta como la parta el markdown. `frases_de` NO se toca —es del 1.8 y
su test la ancla—: el verificador simplemente deja de depender de ella cuando tiene algo mejor.
"""
import os
import re
import unicodedata

from app.core.frases import frases_de, palabras_de

#: EL JUEZ, CAMBIADO EL 14/08/2026 POR LA PRUEBA DE IDENTIDAD (corrida 44, ADR 0022).
#:
#: **La vara: darle al juez una hipótesis que está LITERALMENTE dentro de su premisa.** Si falla en
#: el caso trivialmente cierto de su tarea, ningún arreglo de premisa, selección o umbral puede
#: subir nada — y no hace falta etiquetado, ni humanos, ni desempate para medirlo.
#:
#: **CIFRAS SOBRE CASOS DISTINTOS, no sobre filas** (corregidas el mismo día por la pasada
#: adversarial: el arnés de evaluación repite preguntas, así que 70 filas eran **22 pares
#: distintos** y las medianas por fila estaban fabricadas por las repeticiones):
#:
#:     modelo                                    identidades (distintas)   mediana
#:     mDeBERTa-v3-base-xnli-multilingual-2mil7  20/22                     0,9098
#:     mDeBERTa-v3-base-mnli-xnli                22/22                     0,9977
#:
#: **Mismo tamaño (279 M), misma arquitectura, mismo coste.** El anterior fallaba **2 de 22** textos
#: que se siguen de sí mismos; el nuevo, ninguno. Sobre el plano, y también en casos distintos, la
#: verificación de positivos pasa de **49 % a 76 %** (con la ventana ampliada). Ver el ADR 0022,
#: que lleva la corrección entera y lo que tumbó: **la explicación causal que se publicó primero
#: —"el umbral estaba clavado bajo la mediana 0,66"— era un artefacto de las repeticiones.**
MODELO = os.environ.get("MODELO_NLI") or "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

#: Umbral de `entailment`. **RE-DERIVADO DESDE CERO CON EL JUEZ NUEVO: 0,90** (14/08/2026, ADR
#: 0022, corrida 46). El valor anterior era 0,60 y aguantó tres barridos sin moverse.
#:
#: **El plano con el juez nuevo es PLANO entre 0,60 y 0,90**: 52 casos distintos verificados
#: y 1 negativo aprobado, idéntico en las trece celdas. O sea que **el dato no distingue** esos
#: umbrales: el juez está polarizado (identidades en 0,93-0,995, negativos con mediana 0,008) y casi
#: nunca emite valores intermedios.
#:
#: **ANULACIÓN DECLARADA DEL DESEMPATE PRE-ESCRITO, con su motivo:** el desempate decía *"empate →
#: el umbral más bajo, la configuración menos agresiva que consigue lo mismo"*, y eso elegía 0,60.
#: No se aplica. El porqué: su razón de ser era no rechazar positivos gratis, y aquí **0,60 y 0,90
#: rechazan exactamente los mismos** —la meseta es plana—, así que esa razón no discrimina. Lo que
#: sí discrimina es el comportamiento ante valores que el juez casi nunca emite, y ahí manda la
#: asimetría declarada de la fase 4: **el falso positivo es el caro**. Se elige el punto **más
#: estricto que no cuesta ni un positivo medido**, que es 0,90 (en 0,91 ya se pierde uno).
#:
#: **Comparación PAREADA sobre CASOS DISTINTOS** (corridas 46 y 47, misma tubería, lo único que
#: cambia es el juez; los 158 positivos son **74 pares distintos** y así se cuentan):
#:
#:     juez                        verificados (de 74)   negativos aprobados
#:     mDeBERTa-...-xnli-2mil7      36 (49 %)                    0
#:     mDeBERTa-v3-base-mnli-xnli   52 (70 %)                    1
#:     ...y con la ventana ampliada 56 (76 %)                    1
#:
#: **Se ganan 20 casos y se paga 1 negativo**, y ese negativo va con su texto porque un número
#: sin su caso no se puede discutir: hipótesis *"El salario mínimo interprofesional establece un
#: contenido mínimo"* contra la premisa *"SMI salario mínimo interprofesional 900 € sin extras"*
#: (0,9919). La hipótesis es vaga —viene de una afirmación mal formada— y el fragmento sí habla del
#: SMI: es un par mal etiquetado como negativo antes que una fabricación colándose. **Ninguna celda
#: del plano llega a cero negativos**; para excluir ese par haría falta un umbral por encima de
#: 0,9919, que cuesta 21 positivos.
UMBRAL = float(os.environ.get("UMBRAL_NLI") or 0.90)

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
#:
#: **Y RE-CALIBRADO CON LA VENTANA ANCLADA: 0,25** (ADR 0020 v3, corrida 38, 138 positivos del 4.2
#: puro —los 12 cuya `verificada` era del propio NLI, fuera: garantía circular—). El suelo SUBE al
#: cambiar la premisa porque el parámetro responde a una pregunta que cambió: una ventana de ~100
#: tokens cubre más vocabulario que una frase, así que el 0,10 de la frase se vuelve laxo — con la
#: ventana, 0,10 **aprobaba un negativo** y 0,25 deja cero con los MISMOS 77 positivos verificados.
#: Es el corolario del ADR 0020 por tercera vez: re-barrer suelo y umbral JUNTOS con cada cambio de
#: instrumento es lo que caza esto; un despliegue de la ventana con el suelo viejo habría envuelto
#: el arreglo en un falso positivo.
COBERTURA_MINIMA = float(os.environ.get("NLI_COBERTURA_MINIMA") or 0.25)

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

#: QUIÉN FIRMA ESTE VEREDICTO. El 4.2 escribe `verificada` cuando la cita casa letra a letra y este
#: módulo escribe **el mismo valor** cuando el fragmento sostiene una paráfrasis o una degradada: sin
#: firma, filtrar por el valor mezcla los dos instrumentos. La factura llegó el 14/08/2026, y la
#: pagó esta misma calibración —12 de 150 positivos eran filas aprobadas por el NLI, o sea el
#: termómetro graduándose contra sus propios aciertos—.
INSTRUMENTO = f"4.3/nli:{MODELO.split('/')[-1]}"


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


#: Tope de la ventana, RE-DERIVADO para este problema y no heredado: el ancla mide como mucho 120
#: caracteres (el `maxLength` de `cita` y de `apoyo`), y 400 caracteres son ~100 tokens de mDeBERTa
#: sobre prosa en español — premisa más hipótesis quedan lejos de los 512 totales que truncan en
#: silencio, que es el fallo que obligó a seleccionar premisa en primer lugar.
VENTANA_MAX_CARACTERES = 400

#: Borde sano donde cortar una ventana: fin de frase o salto de línea. **Casa la RACHA y no el
#: carácter**, y la diferencia no es cosmética: `".\n"` son dos caracteres de corte y **un** corte.
#: Con el patrón de un solo carácter, "retrocede dos bordes" se comía uno de los dos en el mismo
#: sitio y se quedaba en la misma frase — o sea que la ampliación por deíctico no ampliaba nada, y
#: el test lo enseñó antes de que llegara a la medida.
RE_BORDE = re.compile(r"[.!?\n]+")

#: TOPE DE LA VENTANA AMPLIADA. 600 caracteres son ~150 tokens de mDeBERTa sobre prosa española:
#: premisa más hipótesis siguen lejos de los 512 que truncan en silencio, que es la guarda que no
#: se puede perder al ampliar.
VENTANA_MAX_AMPLIADA = 600

#: DEÍCTICOS SIN ANTECEDENTE: la avería que esto arregla, medida el 14/08/2026 leyendo a ojo los
#: 61 positivos que se perdían **con la premisa correcta**. Cuatro de quince fallaban así, y en los
#: cuatro **el modelo tenía razón**: la ventana empezaba después del antecedente, así que la premisa
#: que se le daba no decía de qué hablaba.
#:
#:     premisa «Spring deja los errores de validación aquí»      -> ¿dónde es *aquí*?
#:     premisa «Si los invertís, Spring mostrará un error 400»    -> ¿qué es *los*?
#:     premisa «Cuando el ordenador se apaga, se pierde su contenido» -> ¿el contenido DE QUÉ?
#:
#: **La lista es corta y conservadora a propósito.** Se dejan fuera `lo`, `los`, `las`, `le`, `les`:
#: en español son clíticos **y** artículos, y distinguirlos pide análisis morfológico. Meterlos
#: dispararía la ampliación en casi toda frase —*"los errores"*, *"las cookies"*— y ampliar por
#: sistema no es gratis: una ventana más grande sube la cobertura, que es justo la magnitud con la
#: que el SUELO decide, así que el arreglo acabaría aflojando una guarda sin decirlo.
DEICTICOS = frozenset("""
aqui aquí ahi ahí alli allí esto esta este estos estas esa ese eso esos esas
aquel aquella aquello su sus dicho dicha dichos dichas mismo misma ello anterior
""".split())

#: Cuánto se mira para decidir si la ventana **abre** sin antecedente. No es la ventana entera: un
#: `su` en la última línea de un párrafo largo ya tiene su antecedente dentro, y ampliar por él
#: sería ampliar por nada.
#:
#: **MEDIDO (corrida 48, mismos 158 positivos y mismo juez que la 46, lo único que cambia es esto):
#: la ampliación dispara en 32 de 158 (20 %) y crece 53 caracteres de mediana** —una frase corta—,
#: así que es quirúrgica y no "hacer la ventana más grande". Lo que compra, pareado y en CASOS
#: DISTINTOS (74): **52 → 56
#: verificados** (70 % → 76 %), **sin ningún negativo nuevo**. El efecto colateral que
#: había que vigilar —una ventana mayor sube la cobertura y afloja el SUELO— se midió y es de **un**
#: par (12 → 11 bajo el suelo): existe, es pequeño, y queda dicho.
CABEZA_DEICTICA = 80

RE_PALABRA = re.compile(r"[\wáéíóúñÁÉÍÓÚÑ@_.]+")


def _normalizar_con_mapa(texto: str, permisivo: bool = False):
    """El colapso de espacios de `n1_espacios` (4.2), pero conservando el mapa índice normalizado →
    índice crudo, que es lo que permite volver del hallazgo a un SPAN del fragmento original. Con
    `permisivo`, además minúsculas y sin tildes — solo para LOCALIZAR, nunca para dar un veredicto
    (ver `localizar`)."""
    salida, mapa, espacio_pendiente = [], [], False
    for i, c in enumerate(texto):
        if c.isspace():
            espacio_pendiente = bool(salida)
            continue
        if permisivo:
            c = "".join(x for x in unicodedata.normalize("NFD", c.lower())
                        if unicodedata.category(x) != "Mn")
            if not c:
                continue
        if espacio_pendiente:
            salida.append(" ")
            mapa.append(i)
            espacio_pendiente = False
        for x in c:
            salida.append(x)
            mapa.append(i)
    return "".join(salida), mapa


def localizar(fragmento: str, objetivo: str):
    """El span crudo `(ini, fin)` de `objetivo` dentro de `fragmento`, o `None`.

    Dos niveles, en orden: el de SERVICIO del 4.2 (espacios colapsados) y uno permisivo (minúsculas
    y sin tildes) que el 4.2 rechaza para VEREDICTOS y aquí es legítimo porque **localizar no es
    verificar**: la ventana que salga la juzgan el suelo, `parece_codigo` y el propio NLI, así que
    una localización laxa no puede aprobar nada por sí sola — como mucho centra la premisa donde el
    4.2 ya midió que el modelo REESCRIBIÓ (las degradadas `solo_tildes`), que es exactamente donde
    el NLI tiene que mirar."""
    objetivo = (objetivo or "").strip()
    if not objetivo:
        return None
    for permisivo in (False, True):
        pajar, mapa = _normalizar_con_mapa(fragmento, permisivo)
        aguja, _ = _normalizar_con_mapa(objetivo, permisivo)
        if not aguja:
            return None
        i = pajar.find(aguja)
        if i >= 0:
            return mapa[i], mapa[i + len(aguja) - 1] + 1
    return None


def abre_sin_antecedente(ventana: str, hipotesis: str = "") -> bool:
    """¿La ventana **empieza** apoyándose en algo que no contiene?

    Dos señales, y las dos salieron de leer los casos, no de suponerlas:

    1. Un **deíctico** en la cabeza de la ventana (`aquí`, `su`, `esto`…): la frase se refiere a
       algo que quedó a la izquierda del corte.
    2. La hipótesis **nombra** algo con pinta de identificador —`BindingResult`, `@Valid`, `RAM`,
       mayúscula interior o arroba— que **no aparece** en la ventana. Es el mismo fallo visto desde
       el otro lado: el sujeto del que habla la premisa está fuera.

    Se mira solo la CABEZA porque un deíctico al final de un párrafo largo ya tiene su antecedente
    dentro; ampliar por él sería ampliar por nada.
    """
    cabeza = ventana[:CABEZA_DEICTICA].lower()
    if any(p in DEICTICOS for p in RE_PALABRA.findall(cabeza)):
        return True
    v = ventana.lower()
    for p in RE_PALABRA.findall(hipotesis or ""):
        # Identificador: lleva arroba o una mayúscula que no es la inicial (BindingResult, RAM,
        # ArrayList). Una palabra normal capitalizada por ir tras punto no cuenta.
        if (p.startswith("@") or any(c.isupper() for c in p[1:])) and p.lower() not in v:
            return True
    return False


def ventana_anclada(fragmento: str, span: tuple, max_caracteres: int = VENTANA_MAX_CARACTERES,
                    hipotesis: str = "", ampliar: bool = True):
    """La ventana de texto CRUDO alrededor de `span`, expandida a bordes sanos.

    Sin particiones, sin filtros, sin descartes: el span queda dentro SIEMPRE, la parta como la
    parta el markdown — que es la garantía que ninguna selección sobre `frases_de` puede dar. El
    presupuesto sobrante se reparte a los dos lados y cada lado retrocede hasta el corte más
    cercano (fin de frase o salto de línea) si lo hay dentro del presupuesto.

    **Y SI LA VENTANA ABRE SIN ANTECEDENTE, SE AMPLÍA UNA VEZ HACIA ATRÁS** (14/08/2026): se retrocede
    un borde más, con el tope de `VENTANA_MAX_AMPLIADA`. Una sola vez y no en bucle: el objetivo es
    cerrar la referencia, no arrastrar el fragmento entero — que es el fallo del que veníamos.
    """
    ini, fin = span
    ventana, izq = _recortar(fragmento, ini, fin, max_caracteres)
    if ampliar and izq > 0 and abre_sin_antecedente(ventana, hipotesis):
        ampliada, _ = _recortar(fragmento, ini, fin, VENTANA_MAX_AMPLIADA, saltar_bordes=2)
        if len(ampliada) > len(ventana):
            return ampliada
    return ventana


def _recortar(fragmento: str, ini: int, fin: int, max_caracteres: int, saltar_bordes: int = 1):
    """La ventana y dónde empieza. `saltar_bordes` dice cuántos cortes sanos se retroceden por la
    izquierda: 1 es la frase del ancla; 2 mete además la anterior, que es la que suele traer el
    antecedente."""
    sobra = max(0, max_caracteres - (fin - ini))
    izq = max(0, ini - sobra // 2)
    der = min(len(fragmento), fin + (sobra - (ini - izq)))
    bordes = list(RE_BORDE.finditer(fragmento[izq:ini]))
    # El borde `saltar_bordes`-ésimo contando desde el ancla hacia atrás. Si NO hay tantos, no se
    # recorta por la izquierda: se abre hasta donde llegue el presupuesto. Acotar al borde más
    # lejano que existe -que es lo que hacía la primera versión con un `max(0, ...)`- dejaba la
    # ventana EXACTAMENTE igual que sin ampliar, así que "ampliar" no ampliaba y el número habría
    # salido plano sin que nada se pusiera rojo.
    indice = len(bordes) - saltar_bordes
    if indice >= 0:
        izq += bordes[indice].end()
    primero = RE_BORDE.search(fragmento[fin:der])
    if primero:
        der = fin + primero.end()
    return fragmento[izq:der].strip(), izq


def premisa_para(fragmento: str, hipotesis: str, cita: str | None = None,
                 apoyo: str | None = None):
    """La premisa que se le da al NLI y de dónde salió: `(premisa, cobertura, seleccion)`.

    UNA SOLA TUBERÍA para el servicio y para la calibración: si el calibrador construyera la
    premisa por su cuenta, calibraría un instrumento que el servicio no usa. Con ancla localizable
    (la `cita` de una literal degradada, el `apoyo` declarado de una paráfrasis), la premisa es la
    ventana anclada; si el ancla no casa literalmente —inventada, o reescrita más allá de las
    tildes—, se cae a la selección por frases de antes: los mecanismos componen y el peor caso es
    el de ayer. La cobertura devuelta es SIEMPRE la de la hipótesis sobre la premisa elegida: el
    suelo se aplica igual venga de donde venga — la ventana no esquiva ninguna guarda."""
    ph = palabras_de(hipotesis)
    ancla = next((x.strip() for x in (cita, apoyo) if x and x.strip()), None)
    if ancla:
        span = localizar(fragmento, ancla)
        if span:
            ventana = ventana_anclada(fragmento, span, hipotesis=hipotesis)
            cobertura = len(palabras_de(ventana) & ph) / len(ph) if ph else 0.0
            return ventana, cobertura, ("ventana_por_cita" if (cita or "").strip()
                                        else "ventana_por_apoyo")
    frase, cobertura = seleccionar_frase(fragmento, hipotesis, cita)
    return frase, cobertura, ("por_cita" if (cita or "").strip() and frase
                              and (cita or "").strip() in frase else "por_cobertura")


class VerificadorNLI:
    """Carga mDeBERTa una vez por proceso. **CPU por defecto y a propósito.**

    La GPU ya es el cuello —embebedor y reordenador serializan desde el quinto alumno— y meter allí
    un tercer modelo bajaría otra vez el techo de concurrencia. Medido en CPU: 216 ms por par a 16 hilos (4.3, 13/08). **RE-MEDIDO EL 14/08 AL CAMBIAR DE JUEZ, SECUENCIAL Y SIN CARGA: 52,8 ms/par el juez viejo y 59,6 el nuevo** (corrida 45). Los dos numeros miden cosas distintas -aquel, 16 hilos peleandose por la CPU; este, un par detras de otro- y el que vale para el presupuesto de una consulta suelta es el segundo. El de 16 hilos sigue siendo el bueno para razonar sobre concurrencia; a 16
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

    def verificar(self, hipotesis: str, fragmento: str, cita: str | None = None,
                  apoyo: str | None = None) -> dict:
        """Veredicto de UNA paráfrasis contra su fragmento. No lanza.

        Las cuatro salidas, con la política de la sección 8: `entail` por encima del umbral pasa,
        `contradiction` **poda siempre** —sin umbral, porque una contradicción detectada es la señal
        más cara de ignorar—, `neutral` dispara el reintento único con la señal, y lo que no se puede
        juzgar se declara **no verificable** en vez de inventarle un veredicto.

        La premisa la construye `premisa_para`: ventana anclada si `cita` o `apoyo` casan
        literalmente en el fragmento, la selección por frases si no. **Las guardas corren sobre lo
        que salga, venga de donde venga**: una ventana de 100 tokens sin vocabulario de la
        hipótesis se queda bajo el suelo exactamente igual que una frase mala.
        """
        frase, cobertura, seleccion = premisa_para(fragmento, hipotesis, cita, apoyo)
        if frase is None or cobertura < COBERTURA_MINIMA:
            # EL SUELO, y no se le pregunta al NLI. Su modo de fallo ante un par malo no es
            # abstenerse: es `entailment 0.988` sobre nada. Ver COBERTURA_MINIMA.
            return {"veredicto": NO_VERIFICABLE, "motivo": "sin_frase_relacionada",
                    "cobertura": round(cobertura, 2), "suelo": COBERTURA_MINIMA,
                    "seleccion": seleccion, "instrumento": INSTRUMENTO,
                    "calibrado": True, "calibracion": "4.6 + juez nuevo, ADR 0022 (14/08/2026), corridas 44 y 46",
                    "detalle": "ninguna parte del fragmento cubre la afirmacion por encima del "
                               "suelo: no se consulta al NLI, porque su fallo aqui no es dudar "
                               "sino acertar con aplomo por casualidad"}
        if parece_codigo(frase):
            # El 1.8 ya lo decidió con su test y aquí se hereda: un NLI de prosa sobre un bloque de
            # código da ruido con dos decimales. Lo honesto es decir que no se puede juzgar.
            return {"veredicto": NO_VERIFICABLE, "motivo": "contenido_es_codigo",
                    "cobertura": round(cobertura, 2), "frase": frase[:200],
                    "seleccion": seleccion, "instrumento": INSTRUMENTO,
                    "detalle": "la premisa de apoyo es código: el NLI está entrenado en prosa y su "
                               "veredicto aquí no significa nada"}

        etiqueta, probabilidad = self.clasificar(frase, hipotesis)
        base = {"nli": etiqueta, "probabilidad": round(probabilidad, 3), "frase": frase[:200],
                "cobertura": round(cobertura, 2), "umbral": self.umbral,
                # De donde salio la premisa: la traza tiene que poder contar cuantos veredictos
                # llegaron por ventana, cuantos por el ancla de frase y cuantos por cobertura, o
                # el arreglo seria inauditable.
                "seleccion": seleccion, "instrumento": INSTRUMENTO,
                "calibrado": True, "calibracion": "4.6 + juez nuevo, ADR 0022 (14/08/2026), corridas 44 y 46"}
        if etiqueta == CONTRADICCION:
            return {**base, "veredicto": PODADA, "motivo": "contradice_al_fragmento",
                    "detalle": "el fragmento dice lo contrario: se poda sin mirar el umbral"}
        if etiqueta == ENTAILMENT and probabilidad >= self.umbral:
            return {**base, "veredicto": VERIFICADA, "motivo": None,
                    "detalle": "el fragmento sostiene la afirmación"}
        return {**base, "veredicto": REINTENTO, "motivo": "no_se_sigue_del_fragmento",
                "detalle": "el fragmento no sostiene la afirmación; dispara el reintento único"}
