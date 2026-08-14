# Evidencia: los 61 positivos que se pierden con la premisa correcta, leídos — y el techo es el JUEZ

- **Fecha:** 14 de agosto de 2026
- **Encargo:** paso 0 del hilo *"subir el 56 %"*, ordenado por el propietario: **leer quince a ojo
  antes de tocar nada** y partirlos en clases
- **Datos:** corrida **38** (138 positivos limpios, ventana anclada, suelo 0,25 / umbral 0,60)

## 0. Por qué esta lectura y no un barrido

Desde la ventana anclada, **138 de 138 positivos anclan**: la selección dejó de ser la pérdida. Así
que los **61** que no se verifican lo hacen **con la premisa correcta delante**, y la pérdida está
en el **juicio**. Optimizar sin saber de qué clase son los fallos es optimizar a ciegas.

## 1. LA PRUEBA DE IDENTIDAD, que es el número que decide

De los 138 positivos, **60 tienen la hipótesis LITERALMENTE dentro de la premisa** (son literales
degradadas cuyo texto es su propia cita). Es el caso más fácil que existe: *A contra A*. Y esto es
lo que hace mDeBERTa-v3-base con ellos:

| | |
|---|---:|
| pares donde la hipótesis está literal en la premisa | **60** |
| el modelo dice **`neutral`** | **12 (20 %)** |
| el modelo dice `entailment` | 48 |
| de esos, probabilidad **mediana** | **0,66** |
| probabilidad **mínima** | **0,545** |
| **aprobados con el umbral 0,60** | **45 de 60 (75 %)** |

**El verificador falla uno de cada cuatro de los casos más fáciles que existen, y en uno de cada
cinco dice que un texto no se sigue de sí mismo.** Eso no es un umbral mal puesto ni una premisa mal
elegida: es **el techo del juez**.

Y explica de paso por qué el 0,60 sobrevivió a tres calibraciones sin moverse: **está clavado justo
debajo de la mediana de las identidades (0,66)**. Subirlo a 0,70 —que es lo que el desempate del
portero habría sugerido por analogía— habría tirado **la mitad de las identidades**. El umbral no
está donde está por bueno: está donde el modelo le deja estar.

**18 de los 61 perdidos son identidades**, o sea que **un tercio de la pérdida es el modelo fallando
en A ⊆ A.**

## 2. El reparto de los 61, por motivo mecánico

```
neutral                          40
bajo el suelo (cobertura < 0,25) 12
entailment por debajo de 0,60     5
no se preguntó (código)           4
```

## 3. Las quince leídas a ojo, en cuatro clases

Salieron **cuatro** clases y no tres: la que faltaba es de las que se arreglan solas cuando se mira.

### (a) Limitación del modelo — 5 de 15

Identidades y paráfrasis directas que el modelo no aprueba:

- *«Un constructor es un método especial que no devuelve nunca un valor…»* contra **la misma frase**:
  `entailment` **0,545** — por debajo del umbral. Tres veces (ids 384, 422, 477).
- premisa *«Esta inicialización automática se lleva a cabo mediante un constructor.»* / hipótesis
  *«Un constructor se utiliza para inicializar automáticamente los objetos cuando se crean.»* →
  `neutral` **0,978**. Es la misma frase con el sujeto y el predicado cambiados de sitio.

### (b) La ventana corta el REFERENTE: deícticos sin antecedente — 4 de 15

La premisa es correcta pero **empieza con un pronombre cuyo antecedente quedó fuera**:

- *«Spring deja los errores de validación aquí»* → ¿dónde es *aquí*? La hipótesis dice
  *«BindingResult es donde…»*. `neutral` 0,774. (dos veces)
- *«Si los invertís, Spring mostrará un error 400…»* → ¿qué es *los*? `neutral` 0,992.
- *«Cuando el ordenador se apaga, se pierde su contenido.»* → ¿el contenido **de qué**? La hipótesis
  habla de la RAM. `neutral` 0,969.

**Esto NO es limitación del modelo: el modelo tiene razón.** Con esa premisa, la hipótesis no se
sigue. Es la ventana anclada cortando por un borde sano que deja al deíctico huérfano — la misma
familia que el partidor de frases, un piso más arriba. **Arreglo barato y concreto: extender la
ventana hacia la izquierda hasta cerrar el antecedente** (o simplemente ampliarla, que ya es
parametrizable).

### (c) No-implicación legítima — 2 de 15: **el producto funcionando**

La hipótesis **dice más** que la premisa, y el `neutral` es correcto:

- premisa: *«El tamaño del array se establece cuando se crea el array (con `new`).»* / hipótesis:
  *«…y no puede cambiarse.»* — eso la premisa no lo dice.
- premisa: *«…Java crea un constructor por defecto y lo llama…»* / hipótesis: *«…que inicializa los
  datos con valores por defecto.»* — tampoco.

**Estos no se cuentan como pérdida.** Son afirmaciones que el 4.2 degradó porque la cita no casaba
letra a letra, y el NLI está diciendo, con razón, que el fragmento no sostiene lo añadido.

### (d) La premisa es CÓDIGO y `parece_codigo` no la caza — 2 de 15

- premisa `return $precio * (1 + $iva);` → 2 marcas de estructura, hace falta 3. `neutral` 0,958.
- premisa `Mkfs .ext4 -L(label) [nombre] -b(blocksize) 2048 -m 10% /dev/vdb1` → un comando de shell,
  que el detector no contempla. `neutral` 0,614.

Un NLI de prosa sobre una línea de código da ruido, que es justo lo que el detector existe para
evitar; aquí se queda corto. **Arreglo acotado**: el detector cuenta marcas pensadas para Java y no
ve ni una línea con `;` sola ni la sintaxis de shell.

## 4. Lo que esto le hace al plan del propietario

El propietario propuso tres cosas para subir el 56 %. Con la lectura delante, **el orden cambia**:

| propuesta | qué dice la lectura |
|---|---|
| **(1) probar otros modelos NLI** | **Sube a primera, y ahora con número**: 20 % de `neutral` sobre identidades y mediana 0,66 son el techo de todo lo demás. Cualquier mejora de premisa o umbral se estrella contra esto |
| **(2) quitar el encuadre de la hipótesis** | Sigue valiendo, pero la lectura enseña que el encuadre que muerde está en la **PREMISA** (deícticos sin antecedente, 4 de 15), no en la hipótesis. Se ataca ampliando la ventana |
| **(0) leer quince** | hecho, y cambió el orden — que es exactamente para lo que servía |

**Y el experimento que la prueba de identidad hace obvio:** *A contra A* no necesita conjunto
etiquetado, ni humanos, ni criterio de desempate. **Es una vara que cualquier modelo candidato pasa
o no pasa**, y se corre sobre los 60 pares que ya están medidos. Un juez que no aprueba una
identidad no puede juzgar una paráfrasis.

## 5. Corrido: el juez cambia (ADR 0022)

La prueba se corrió el mismo día sobre tres candidatos (corridas 44-47). Resultado en una línea:
**`mDeBERTa-v3-base-mnli-xnli` aprueba 70 de 70 identidades con mediana 0,995**, contra 59 de 70 y
mediana 0,66 del juez que había — **mismo tamaño, misma arquitectura, +6,8 ms por par en CPU**.

Comparación **pareada** sobre los mismos 158 positivos y 158 negativos: **de 90 verificados (57 %) a
112 (71 %)**, pagando **un** negativo aprobado que, leído, es un par mal etiquetado (hipótesis vaga
sobre el SMI contra un fragmento que habla del SMI).

El detalle, el umbral re-derivado (0,60 → **0,90**) y la anulación declarada del desempate están en
el [ADR 0022](../adr/0022-el-juez-nli-se-cambia-por-la-prueba-de-identidad.md).

## 6. Y la clase (b): la ventana se amplía hasta cerrar el antecedente

La cuarta clase de la lectura —**la ventana cortaba el antecedente de un deíctico**, 4 de 15— era
un fallo **nuestro**: en esos casos el modelo tenía razón, porque *«Spring deja los errores de
validación aquí»* no sostiene *«BindingResult es donde…»* si no dice qué es *aquí*.

**El arreglo**: cuando la ventana **abre** sin antecedente, se retrocede **un borde más**, una sola
vez, con tope de 600 caracteres. Dos señales lo disparan, y las dos salieron de los casos:

1. un **deíctico** en los primeros 80 caracteres (`aquí`, `su`, `esto`… — lista corta y
   conservadora: `lo/los/las/le/les` quedan fuera porque en español son clíticos **y** artículos, y
   meterlos ampliaría en casi toda frase);
2. la hipótesis **nombra un identificador** (`BindingResult`, `@Valid`, `RAM`) que la ventana no
   contiene — el mismo fallo visto desde el otro lado.

**Medido, pareado, mismo juez y mismos 158 pares (corrida 46 → 48):**

| | sin ampliar | ampliando |
|---|---:|---:|
| positivos verificados | 112 (71 %) | **119 (75 %)** |
| perdidos por umbral | 30 | 24 |
| bajo el suelo | 12 | 11 |
| **negativos aprobados** | 1 | **1** |

Y **cuánto** se amplía, que es lo que distingue un arreglo de un ensanchamiento: **dispara en 32 de
158 (20 %)** y crece **53 caracteres de mediana**. De esas 32, siete pasan a verificarse.

**El efecto colateral que había que vigilar está medido y declarado**: una ventana mayor sube la
cobertura, que es la magnitud con la que decide el SUELO, así que ampliar podría aflojar una guarda
sin decirlo. Movió **un** par (12 → 11 bajo el suelo). Existe, es pequeño, y queda escrito.

### Y un defecto que solo apareció al escribir el test

La primera versión **no ampliaba nada** y el número habría salido plano sin que nada se pusiera
rojo: `.` y `\n` seguidos contaban como **dos** bordes, así que *"retrocede dos"* se quedaba en la
misma frase; y cuando no había bastantes bordes a la izquierda, un `max(0, …)` acotaba al mismo
borde de siempre. Dos formas del mismo error —**el mecanismo corriendo y no haciendo nada**— cazadas
por un test escrito con el caso real delante, no por la medida.

## 7. El acumulado del día sobre los mismos 158 pares

| configuración | verificados |
|---|---:|
| juez viejo, ventana estrecha | 90 (57 %) |
| juez nuevo, ventana estrecha | 112 (71 %) |
| **juez nuevo, ventana ampliada** | **119 (75 %)** |

Con **un** negativo aprobado en las tres, y es el mismo par mal etiquetado del SMI.
