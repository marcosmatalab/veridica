# Verificador NLI (encargo 4.3): la ventana no daba, y el detector heredado no transfería

**13 de agosto de 2026.** `app/core/verificador_nli.py`, humo en `scripts/humo_nli.py`.
Modelo `mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`, **en CPU**.

## 1. La ventana: confirmada, y el fallo es PEOR que el previsto

**La ventana de mDeBERTa-v3-base son 512 tokens TOTALES** —premisa más hipótesis— y los fragmentos
se trocearon a 512 **más su línea de contexto**. Medido con el tokenizador del propio NLI sobre 300
fragmentos reales:

| | |
|---|---:|
| Mediana | **480** tokens |
| p95 | **566** |
| Máximo | **598** |
| **Desbordan la ventana ELLOS SOLOS** | **100/300 (33 %)** |

O sea que la librería **trunca en silencio** en un tercio de los casos. La predicción era un falso
negativo: una afirmación sostenida por la **cola** del fragmento saldría `neutral`. Comprobado con un
caso plantado —frase de apoyo puesta al final a propósito—, lo que sale es otra cosa:

```
premisa = fragmento entero, 654 tokens (la frase de apoyo CORTADA)  -> entailment 0.988
CONTROL: premisa = solo el relleno, que no menciona sesiones        -> entailment 0.988
```

**Un falso positivo con dos decimales.** El modelo entailment-ea una hipótesis que la premisa no
sostiene en absoluto, y con la misma confianza que cuando sí la sostiene. Es el lado **caro** de la
asimetría del 4.2: una cita rechazada de más tiene coste acotado; una **aceptada** de más es una
fabricación pasando por verificada.

Con la frase correcta como premisa, el mismo par da `entailment 0.975`; sin ella, `neutral 0.949`.
**La selección de frase no es una optimización: es lo que hace que el veredicto signifique algo.**

Y confirma por segunda vez, desde la otra dirección, lo que el 1.8 ya había pagado: *"a nivel de
trozo marcaba 4.255 contradicciones, entre ellas dos salidas de `ping` con distinta IP"*. Allí el
ruido eran contradicciones falsas; aquí, entailments falsos. **El denominador común es darle trozos
a un modelo entrenado en frases.**

## 2. La maquinaria del 1.8 transfiere; DOS de sus parámetros, no

Se reutiliza `frases_de` y `palabras_de` —movidas a `app/core/frases.py` para que haya **una sola
implementación**, con la lista de vacías **exactamente la del 1.8**: ampliarla "de paso" habría
cambiado en silencio el comportamiento de un código validado por su test—. Pero dos cosas suyas no
sobreviven al cambio de problema:

### a) El tope de 12 frases: correcto allí, destructivo aquí

`mejor_par_de_frases` compara **fragmento contra fragmento** —O(n²)— y acota a las 12 primeras de
cada lado. Aquí la comparación es **fragmento contra hipótesis corta** —O(n)—, y ese tope solo hace
una cosa: **tirar la cola del fragmento**. En el caso plantado, la frase de apoyo estaba en la
posición **42 de 43** y el tope cortaba en 12; el selector elegía otra frase y devolvía `neutral`.

> **Se reutiliza el código validado, pero se comprueba que sus PARÁMETROS transfieren.** Un tope
> puesto para acotar un cuadrático deja de tener sentido cuando el problema pasa a ser lineal, y lo
> único que sigue haciendo es perder datos — sin que nada se ponga rojo.

*(Y una corrección de método, porque la primera hipótesis fue mía y era falsa: culpé a Jaccard de ser
simétrico. Medido, Jaccard elige bien; lo que fallaba era el tope. La medida separó las dos
explicaciones que la intuición había juntado.)*

### b) El detector de código: 4 fallos de 10, y todos del mismo lado

El detector del 1.8 caza `@\w+` y cualquier paréntesis. Es correcto **para su trabajo** —descartar
pares de fragmentos que son bloques de código— y desastroso para este, donde la premisa es **una
frase en prosa que MENCIONA identificadores**. En un corpus medio código, eso es casi toda la prosa
útil: *"Sin `@Valid` la validación no se ejecuta"* salía clasificada como código y por tanto **no
verificable**.

| Detector | Fallos sobre 6 frases de prosa y 4 bloques de código |
|---|---:|
| Heredado del 1.8 (`@\w+`, paréntesis) | **4/10** |
| Por **densidad de estructura** | **1/10** |

La distinción no es la presencia de un identificador sino la **densidad**: una frase menciona una
anotación; un bloque tiene llaves, puntos y coma y varias marcas a la vez. El único fallo que queda
es una lista de opciones tipo test, que la selección de frase descarta igualmente por cobertura.

## 3. El humo, y el aviso que lo motivó

**Y el aviso era el bueno: 3 de los 4 fallos de la primera corrida estaban en los pares con
identificadores.** Mirar a ojo antes de fiarse del umbral encontró un fallo que ningún agregado
habría enseñado — porque el agregado decía 6/10, que parece "el modelo va regular", y la verdad era
"nuestro filtro descarta la prosa de este temario".

| Corrida | Aciertos | **Con identificadores** |
|---|---:|---:|
| Con el detector heredado | 6/10 | **1/4** |
| Con el detector por densidad | **9/10** | **4/4** |

El humo imprime **la probabilidad de las tres etiquetas y la frase elegida**, no solo el veredicto:
un 0,45 de `entailment` contra un 0,44 de `neutral` es un empate disfrazado de decisión, y eso solo
se ve mirando.

**El décimo no es un fallo del sistema sino una expectativa mía mal puesta**, y la corrección se
queda escrita: con **cero** vocabulario en común, el sistema no puede separar *"no viene a cuento"*
de *"el fragmento no lo sostiene"*, así que declara `no_verificable` en vez de elegir uno. Aguas
abajo alimenta la misma decisión —la afirmación no está respaldada—, pero decirlo como veredicto
sería afirmar más de lo que se sabe.

## 4. Dónde corre, y por qué no en la GPU

**CPU**, y no porque sobre: **la GPU ya es el cuello** —embebedor y reordenador serializan desde el
quinto alumno—, así que un tercer modelo allí bajaría otra vez el techo de concurrencia y empeoraría
la degradación medida. En CPU son **216 ms por par a 16 hilos**, y como solo van al NLI las
`parafrasis` y las `literal` degradadas (~40 % medido en el 4.2), son **1-2 pares por respuesta**:
unos 350 ms, que **caben enteros dentro de los ~823 ms en que el modelo aún escribe la prosa**.

## Reproducir

```bash
python scripts/humo_nli.py
```
