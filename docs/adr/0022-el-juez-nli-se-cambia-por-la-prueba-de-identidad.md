# ADR 0022: el juez NLI se cambia por la PRUEBA DE IDENTIDAD, y el umbral se re-deriva desde cero

- **Fecha:** 14 de agosto de 2026
- **Encargo:** 4.3 / 4.6 (revisión del juez), ordenado por el propietario antes del índice padre-hijo
- **Estado:** aceptada
- **Corridas:** **44** (prueba de identidad, GPU), **45** (la misma en CPU, para el coste), **46**
  (plano con el juez nuevo), **47** (plano con el juez viejo sobre los MISMOS pares)

## Contexto: el 0,60 no era robusto, era un techo

El umbral del NLI sobrevivió a **tres** barridos sin moverse —corridas 32, 36 y 38, con la premisa
cambiada dos veces por el medio— y eso se leyó como robustez. Al leer los 61 positivos que se
perdían **con la premisa correcta**, apareció el motivo real.

## La vara: la PRUEBA DE IDENTIDAD

**Se le da al juez una hipótesis que está LITERALMENTE dentro de su premisa.** Es el caso
trivialmente cierto de su tarea, sale del conjunto que ya existe (las `literal` degradadas cuyo
texto es su propia cita) y **no necesita etiquetado, ni humanos, ni desempate**.

Sobre **70 identidades** y **67 negativos** (la misma afirmación contra un fragmento ajeno):

| juez | identidades `entailment` | prob. mediana | peor identidad | negativos que pasan |
|---|---:|---:|---:|---:|
| `mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` (el de hasta hoy) | **59/70 (84 %)** | **0,66** | 0,1385 | 4/67 a 0,60 |
| `mDeBERTa-v3-base-mnli-xnli` | **70/70 (100 %)** | **0,995** | 0,9326 | 3/67 a 0,93 |
| `joeddav/xlm-roberta-large-xnli` | **no compitió** | — | — | — |

El tercero **no cargó** (su tokenizador no convierte en esta instalación, falta el `.model` de
SentencePiece). **Un candidato que no carga no es un candidato que pierde**, y queda escrito en la
lista del script para que la pregunta *"¿por qué no se probó uno grande?"* tenga respuesta donde se
mira.

**El juez viejo decía `neutral` a 11 de 70 textos que se siguen de sí mismos.** Y cuando aprobaba,
su confianza tenía mediana 0,66 — que es exactamente donde estaba clavado el umbral. **El 0,60 no
medía cuánta evidencia hace falta: medía hasta dónde llegaba el modelo.**

## Decisión

**Se cambia el juez a `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` y el umbral se re-deriva desde
cero: 0,90.**

Mismo tamaño (**279 M**), misma arquitectura, mismo empaquetado. Coste medido en CPU, que es donde
corre en servicio: **52,8 ms/par el viejo contra 59,6 ms/par el nuevo** — +6,8 ms por par, con 1-2
pares por respuesta. Irrelevante frente al hueco de ~823 ms en el que el modelo sigue escribiendo.

### El umbral, y la anulación declarada del desempate

El plano con el juez nuevo es **plano entre 0,60 y 0,90**: 112 verificados, 30 perdidos, 1 negativo,
idéntico en las trece celdas. El juez está **polarizado** (identidades en 0,93-0,995, negativos con
mediana 0,008) y casi nunca emite valores intermedios.

El desempate pre-escrito decía *"empate → el umbral más bajo, la configuración menos agresiva que
consigue lo mismo"*, y elegía **0,60**. **No se aplica, y el motivo se escribe:** su razón de ser
era no rechazar positivos gratis, y aquí 0,60 y 0,90 rechazan **exactamente los mismos**. Lo que sí
distingue esos puntos es qué harían con valores que el juez casi nunca emite, y ahí manda la
asimetría declarada de la fase 4 —**el falso positivo es el caro**—. Se toma **el punto más estricto
que no cuesta ni un positivo medido: 0,90** (en 0,91 ya se pierde uno).

Es la regla del propio Apéndice A aplicada: *un criterio pre-escrito protege contra elegir el número
que conviene; no garantiza que el criterio sea correcto*.

## Trade-off, medido PAREADO (mismos 158 positivos y 158 negativos, corridas 46 y 47)

| juez | verificados | perdidos por umbral | bajo el suelo | **negativos aprobados** |
|---|---:|---:|---:|---:|
| viejo | 90 (**57 %**) | 52 | 12 | **0** |
| nuevo | **112 (71 %)** | 30 | 12 | **1** |

- **Se gana**: 22 positivos verificados, +14 puntos, sin tocar premisa, selección ni suelo.
- **Se paga**: **un negativo aprobado**, y va con su caso porque un número sin él no se puede
  discutir: hipótesis *«El salario mínimo interprofesional establece un contenido mínimo»* contra la
  premisa *«SMI salario mínimo interprofesional 900 € sin extras»*, con 0,9919. La hipótesis es vaga
  —viene de una afirmación mal formada— y el fragmento sí habla del SMI: **es un par mal etiquetado
  como negativo antes que una fabricación colándose**. Ninguna celda del plano llega a cero
  negativos; excluirlo exigiría un umbral por encima de 0,9919 y costaría 21 positivos.
- **Y lo que NO cambia**: el suelo sigue en 0,25 y la selección sigue anclando 158 de 158.

## CORRECCIÓN DEL MISMO DÍA: todas las cifras de arriba contaban FILAS, no CASOS

**La pasada adversarial sobre los números del día encontró que los controles estaban dominados por
repeticiones**, y la causa es nuestra: el arnés de evaluación hace las mismas preguntas muchas
veces, así que la misma cita literal genera muchas filas de `afirmaciones`. Recontado por pares
`(fragmento, hipótesis)` distintos:

| lo publicado (filas) | lo que hay (casos distintos) |
|---|---|
| 158 positivos | **74 pares**, y uno solo aparece **20 veces** (12,7 % del denominador) |
| 70 identidades | **22 pares** |
| juez viejo: 59/70 identidades (84 %) | **20/22 (91 %)** |
| juez viejo: 11 `neutral` sobre identidades | **2 textos distintos**, repetidos 11 veces |
| juez viejo: mediana 0,66 | **0,9098** |
| juez nuevo: 70/70, mediana 0,995 | **22/22, mediana 0,9977** |

**Lo que esto tumba: la explicación causal, no la decisión.** La frase *"el 0,60 estaba clavado
justo debajo de la mediana de las identidades (0,66)"* era un **artefacto de las repeticiones**: la
mediana real sobre casos distintos es 0,91, muy por encima del umbral. Esa explicación se retira de
aquí y de la regla del Apéndice A que la citaba, con su corrección escrita al lado.

**Lo que sobrevive, recomputado sobre los 74 pares distintos y a umbral común 0,90:**

| configuración | verificados (distintos) | negativos aprobados |
|---|---:|---:|
| juez viejo, ventana estrecha | 36/74 (**49 %**) | 0 |
| juez nuevo, ventana estrecha | 52/74 (**70 %**) | 1 |
| juez nuevo, ventana ampliada | **56/74 (76 %)** | 1 |

**La decisión de cambiar el juez se refuerza**: +27 puntos sobre casos distintos, y 0 fallos de
identidad contra 2. Lo que cambia es que **el motivo publicado era falso y los porcentajes estaban
inflados**.

**Y una corrección más de la misma pasada**: la columna *"negativos que pasan"* de la tabla de
arriba enfrenta **4/67 a 0,60 contra 3/67 a 0,93** — dos cortes distintos, que se lee como si el
juez nuevo rechazara más. **A corte común, el juez nuevo deja pasar SIEMPRE igual o más** (a 0,60:
4 contra 5; a 0,90: 2 contra 3). No invierte la decisión —lo que se compra son 20 positivos por 1
negativo— pero la tabla, tal como estaba, decía algo que no era.

**El instrumento queda arreglado**: `calibrar_nli.py` y `probar_jueces.py` deduplican por
`(fragmento, hipótesis)` antes de medir e imprimen **los dos números**, ocurrencias y casos.

## Consecuencia que hay que vigilar

El conjunto de negativos **no está etiquetado a mano**: se construye emparejando la afirmación con
otro fragmento de su asignatura, excluyendo el mismo documento y los casi-duplicados del 1.8. Con un
juez mucho mejor calibrado, **los pares mal etiquetados empiezan a notarse** —el caso del SMI es
justo eso—. La lectura correcta de "1 negativo aprobado" no es *"el sistema falla una vez de 158"*
sino *"el control tiene al menos un par que no era negativo"*. Si el ruido del control empieza a
decidir, hay que etiquetar una muestra a mano; hoy no decide.
