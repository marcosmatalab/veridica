# ADR 0017: el número de afirmaciones se acota en la gramática, y su valor NO sale de los datos que tengo

- **Fecha:** 13 de agosto de 2026
- **Encargo:** 4.4 (verificador de cálculo), aplicando lo que ese encargo aprendió del prompt
- **Estado:** aceptada, con el valor **declarado SIN CALIBRAR** (calibración: encargo 4.6)
- **Evidencia:** [`docs/evidencia/2026-08-13-verificador-calculo.md`](../evidencia/2026-08-13-verificador-calculo.md)

## Contexto

Al añadir el tipo `calculo` al prompt —sin esa línea, el verificador del 4.4 no veía una sola
afirmación que juzgar—, las respuestas se alargaron. En la consulta de IVA en modo `corregir` **y sin
fragmentos en contexto**, **7 de 10 corridas** chocaron con `MAX_TOKENS_CONTRATO = 900` y volvieron
**cortadas a media frase** (`fin=length`), contra **0 de 3** sin la línea. Mirando los crudos no es un
bucle degenerado: las que terminan gastan 471–641 tokens con **8 y 9 afirmaciones**.

**Y ahí falta la mitad que casi no escribo.** Por el **camino real** —`/consulta` con su corpus, seis
consultas de `corregir` comprobadas por `version_prompt` y no por la columna `modo`— el
desbordamiento es **0 de 6**: media de **3,0 afirmaciones**, máximo **5**, y **386 tokens de salida
de media con máximo 615**. Sin material que citar el modelo se explaya; con material se ciñe a él, que
es la tesis del proyecto vista desde el consumo de tokens.

O sea que el fuego está medido en una condición **que no es la de producción**. Decir "7 de 10" sin
esa coletilla habría sido heredar un número de otra configuración.

## Decisión

**El tope va en la gramática: `maxItems: 10` sobre `afirmaciones`** — como **prohibición barata**, no
como parche de un incendio: en la ruta real no se ha visto arder, y n=6 tampoco demuestra ausencia.

Y va ahí, y no en el prompt, por el refinamiento del principio 7 que salió de este mismo encargo:
**la gramática prohíbe, no elige.** Elegir *qué tipo* usar entre cinco ramas permitidas no lo decide
el esquema —eso costó que el 4.4 naciera decorativo—, pero una **cardinalidad sí es una prohibición**:
con decodificación restringida, la afirmación número once es **ingramática**. Pedir brevedad por
prompt sería pedir un favor; esto lo impone.

## Y el valor es provisional, con el motivo escrito

**Casi lo derivo de la distribución equivocada.** Las 110 respuestas reales de la base van de **1 a 6
afirmaciones y ninguna pasa de 6**, y ese rango parecía la derivación honesta del tope. No lo es:
esas respuestas son **anteriores a que existieran los modos**, así que no contienen ni una derivación
de `corregir` — y `corregir` es exactamente el modo que encadena pasos y el que está desbordando.
Derivar el tope de esa muestra habría recortado justo lo que motivó el cambio.

Es el **principio 11 con la muestra elegida por CUÁNDO en vez de por el síntoma**, que en software es
la forma más común que toma: **datos de antes del cambio**. Generaliza a cualquier criterio de
selección correlacionado con lo que se mide, y el temporal es el que vuelve siempre.

Así que **10 es provisional y holgado** —por encima del 9 observado en `corregir` y del 6 histórico—,
queda declarado sin calibrar como los demás umbrales del proyecto, y su calibración es el **encargo
4.6**, sobre la distribución de `corregir` que sí se está midiendo.

## Trade-off

- **Se paga** que una respuesta legítimamente larga se corte en la décima afirmación. Con un tope
  holgado el caso es raro; con el tope mal calibrado sería frecuente y **silencioso**, que es el
  motivo de declararlo sin calibrar en vez de darlo por bueno.
- **Se gana** que el desbordamiento de tokens deje de depender de que el modelo colabore, y que la
  respuesta cortada a media frase —que rompe el contrato y gasta el reintento— pase de probable a
  imposible por esa vía.
- **Lo que NO arregla, y por eso no se cierra aquí:** si el desbordamiento viene de afirmaciones
  **largas** en vez de **muchas**, este tope no lo toca. Son dos palancas distintas y la medida de la
  distribución de `corregir` —cuántas afirmaciones y cuántos tokens cada una— es la que dice cuál
  aplicar.
