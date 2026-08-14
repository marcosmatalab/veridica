# ADR 0020: el umbral NLI (0,60) y el suelo de cobertura (0,30) salen del plano, con el desempate pre-escrito

- **Fecha:** 14 de agosto de 2026
- **Encargo:** 4.6
- **Estado:** aceptada
- **Evidencia:** [`docs/evidencia/2026-08-14-calibracion-4.6.md`](../evidencia/2026-08-14-calibracion-4.6.md), corrida **32** de `corridas_eval`

## Contexto

El 0,80 del NLI y el 0,20 del suelo estaban **declarados sin calibrar** desde su nacimiento. Los
controles se derivan sin etiquetado humano: **189 positivos** (afirmaciones `literal` que pasan el
4.2: *entailed* por su cita, por construcción) y **189 negativos** (la misma afirmación contra otro
fragmento de su asignatura, excluyendo el mismo documento —el solape de 64 tokens fabrica
casi-duplicados— y los **858 casi-duplicados que el 1.8 ya midió**; emparejado determinista). UNA
corrida por la tubería de servicio, guardando cobertura y puntuación; el plano (suelo × umbral) se
calcula después sin re-llamar.

## Decisión

**Suelo 0,30 y umbral 0,60**, el punto que el desempate **pre-escrito** eligió: cero negativos
aprobados manda (la asimetría del 4.2: el falso positivo es el caro); entre los factibles, máximos
positivos verificados; empate → umbral más bajo, luego suelo más bajo. El punto inicial (0,20/0,80)
**aprobaba un negativo** y verificaba 25 positivos contra 34.

Los positivos perdidos del punto elegido, **declarados**: 18 de 56 en el tramo de umbral (entail
por debajo de 0,60 o etiqueta no-entail sobre cita literal: falso negativo del modelo, medido).

## Trade-off

- **Se gana**: el falso positivo caro queda en cero sobre los controles, con 9 positivos
  verificados más que la configuración inicial.
- **Se paga**: 18 positivos de 56 siguen sin verificarse (van a `reintento`/poda del 4.5, no a
  mentira), y el n del tramo de umbral es **56**, no 189 — pequeño y declarado.
- **El límite que la calibración destapó y que NO es del umbral: 133 de 189 positivos (70 %)
  fallan por SELECCIÓN** — la frase elegida no contiene la cita (citas que cruzan frases, o el
  selector eligiendo otra). Separarlos fue corrección de método del propietario: sin ella, el
  barrido habría movido el umbral para compensar un problema de selección. La selección multi-frase
  o consciente de la cita queda **declarada y no construida**; es la palanca gorda, no el umbral.

## El corolario que el resultado confirma

**SUBIR EL SUELO ES LO QUE HACE SEGURO BAJAR EL UMBRAL.** Filtrar los pares malos —donde el NLI da
tonterías con dos decimales— es lo que permite fiarse de un umbral más laxo con los que quedan.
Ningún barrido en una sola dimensión habría encontrado este punto: con el suelo fijo en 0,20, bajar
el umbral aprobaba un negativo; con el umbral fijo en 0,80, subir el suelo solo perdía positivos.
La condición pre-escrita de barrer los dos JUNTOS queda confirmada por su propio resultado.

## Consecuencia que hay que vigilar

El plano acota con controles **por construcción** (cita literal / fragmento ajeno); el caso difícil
—la paráfrasis dudosa del medio— sigue sin etiqueta, así que 0,60 es un umbral que **ningún control
contradice**, no uno óptimo sobre el medio. Si aparece un conjunto etiquetado del medio, se rebarre
contra la fórmula del desempate, no contra esta cifra.

## Versión 2 (14 de agosto, tarde): re-calibrado sobre el instrumento arreglado

**La regla que obliga a esta versión: se calibra sobre el instrumento arreglado, nunca sobre el
roto** — el plano de la mañana medía la selección SIN ancla de cita, y calibrar sobre él habría
codificado el régimen que el ancla quita (la misma familia que "pares ya seleccionados, no
fragmentos crudos" y que el portero sobre la medida arreglada).

Lo que cambió entre las dos versiones, cada cosa cazada y declarada:

1. **El ancla de cita** (`seleccionar_frase(..., cita=)`): la hipótesis es el texto, no la cita, y
   la frase que contiene la cita es la premisa buena. En servicio la usa toda `literal` degradada.
2. **El contador mentía** (corridas 34-35): comprobaba la contención sobre la frase RECORTADA a
   200 caracteres. Arreglado a la frase entera — el aparato de medir, otra vez.
3. **39 positivos estaban rotos en origen**: `afirmaciones.texto = 'literal'` — el generador
   emitió el TIPO como texto (era 13/08+, ids 393-925). Su hipótesis no es una frase: no miden ni
   selección ni umbral. Excluidos y DECLARADOS; el defecto del generador queda señalado como
   trabajo propio.

**Elección v2 (corrida 36; 150 positivos limpios, 150 negativos): suelo 0,10, umbral 0,60** — 35
verificados, 20 perdidos (declarados), 0 negativos aprobados. Con el ancla puesta y el conjunto
limpio, el suelo puede bajar de 0,30 a 0,10 sin aprobar ni un negativo: el negativo que antes se
colaba estaba emparejado a una fila rota. El umbral no se mueve. La selección sigue fallando en 91
de 150 (61 %): son las citas que CRUZAN frases — la multi-frase sigue siendo la palanca gorda,
declarada y no construida.

## Versión 3 (14 de agosto, la ventana anclada): el 61 % era el partidor, y el suelo SUBE a 0,25

**El diagnóstico del propietario sobre el 61 %, confirmado midiendo: la premisa dejó de salir de
una partición en frases.** `frases_de` parte por `\n+` y descarta fuera de (40, 400): en markdown
eso convierte listas en pseudo-frases y borra candidatas, así que "la cita cruza frases" era en su
mayor parte artefacto del instrumento. La premisa ahora es una **ventana de fragmento CRUDO
anclada en el span** de la cita (o del `apoyo` que la paráfrasis declara y el servidor comprueba
como subcadena literal antes de que el NLI opine): el cruce es imposible por construcción, y
`frases_de` no se toca — es del 1.8, su test la ancla, y queda como respaldo cuando no hay ancla.

**El hallazgo intermedio (corrida 37), cazado mirando a ojo los 12 positivos que no anclaban: el
conjunto de control estaba CONTAMINADO.** `veredicto = 'verificada'` lo escriben DOS verificadores
distintos con el mismo valor — el 4.2 (cadenas) y, desde que está enchufado, el NLI sobre
degradadas —, y la consulta de positivos los distinguía por nada. 12 de los 150 "positivos" eran
literales degradadas verificadas por el propio NLI: su cita NO está en el fragmento por
construcción, y su garantía de positivo era circular (el que comprueba compartiendo el supuesto del
que produce, dentro de nuestro propio conjunto de control). Afectaba también a las corridas 32 y
36, con n pequeño. La consulta exige ahora la firma del 4.2 (`detalle.verificacion.nivel`).

**Elección v3 (corrida 38; 138 positivos del 4.2 puro, 138 negativos): suelo 0,25, umbral 0,60** —
**138/138 anclan por ventana (cero fallos de selección)**, 77 verificados (56 %, contra 35 de 150
en v2), 45 perdidos por umbral (declarados), 12 bajo el suelo, 0 negativos aprobados.

**Y el corolario gana su tercera lectura: el suelo se RE-DERIVA con cada cambio de premisa, y esta
vez SUBE.** Una ventana de ~100 tokens cubre más vocabulario de la hipótesis que una frase, así que
el 0,10 elegido para frases se vuelve laxo con ventanas: **con 0,10, el instrumento nuevo aprobaba
un negativo**; 0,25 deja cero con los mismos 77 positivos. La condición pre-escrita de barrer suelo
y umbral JUNTOS con cada instrumento es la que lo cazó — desplegar la ventana con el suelo viejo
habría envuelto el arreglo en un falso positivo. El 0,60 del umbral sobrevivió a las tres
calibraciones sin moverse (corridas 32, 36 y 38; su tramo ya es n=138).

**La distribución antes/después sobre las filas reales (corrida 40; antes = v2 reconstruido como
espejo declarado, después = `verificar()` real):**

| conjunto | n | antes → después |
|---|---:|---|
| paráfrasis | 216 | **83 verificadas, las mismas**; 45 pasan a `no_verificable` (41 de `reintento`, 4 de `podada`) |
| literales degradadas | 150 | 60 → **55 verificadas**; 18 pasan a `no_verificable` (13 de `reintento`, 5 de `verificada`) |

Lo que pasa a `no_verificable` **no es pérdida, es honestidad**: son los pares por debajo del suelo
nuevo, o sea el régimen donde el plano midió que se colaba un negativo. Y **la ventana solo alcanza
2 de las 150 degradadas almacenadas** —una degradada, por definición, **no localiza su cita**: por
eso se degradó; esas 2 son `solo_tildes`—, así que **la ganancia de la ventana en servicio llega
por el `apoyo` de las paráfrasis futuras, campo que nace hoy y que ninguna fila almacenada lleva:
no es medible sobre datos viejos y se declara en vez de estimarse.** Son **dos números y se citan
por separado**: el **56 % de los controles** (medido, corrida 38) y la tasa **en servicio** (no
medida; se mide cuando existan generaciones con `apoyo`).

Y el recuento de filas rotas del generador sube a **152 de 974 (15,6 %)** —147 con
`texto='literal'` y 5 con `texto='parafrasis'`—; las 39 declaradas en v2 eran solo las que caían
dentro de los positivos del control. La corrida 39 se repitió como 40 porque su filtro de exclusión
estaba escrito a la forma del caso mirado (`texto='literal'`) y dejaba pasar 2 de esas filas: el
plano no se movía —138 positivos con los dos filtros, contado— pero la comparación sí. Detalle
completo del defecto y de qué denominadores publicados lo incluyen, en `corpus/COBERTURA.md`.