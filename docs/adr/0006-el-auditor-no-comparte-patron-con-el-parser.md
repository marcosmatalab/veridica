# ADR 0006: el auditor del árbol no comparte patrón con el parser

## Contexto

El extractor del árbol oficial (encargo 1.1) tenía una puerta automática: cruzar los **códigos** de
módulo extraídos del Anexo I contra los que la norma lista en su articulado. Esa puerta daba verde
en las tres titulaciones.

Un muestreo **a mano** de diez nodos encontró que el módulo 0373 se llamaba «Lenguajes de marcas y
sistemas de gestión de» cuando la norma dice «...de gestión de información». El nombre venía
cortado por un salto de línea del PDF.

La puerta de códigos no podía verlo: el código era `0373`, correcto, y el nodo existía. Lo que
fallaba era el **contenido de un campo**, no la presencia del nodo.

Al tirar del hilo salieron, por dos mecanismos distintos y los dos silenciosos:

| Mecanismo | Truncaba | Borraba entera |
|---|---|---|
| El nombre se parte en dos líneas y el patrón captura con `[^\n]` | 3 nombres de módulo | 5 unidades |
| El nombre lleva `:` dentro y el patrón captura con `[^\n:]` | 1 nombre de unidad | 3 unidades |

Cuatro nombres truncados y ocho unidades que no estaban, sobre 536 nodos, con la suite en verde.

El primer intento de detección fue buscar nombres terminados en preposición o artículo («de», «en»,
«y»). Encontró 3 de los 4. Falla por construcción: **comparte el sesgo del fallo que persigue**,
porque solo ve el corte cuando cae detrás de una palabra vacía. El cuarto —«Interacción con el
usuario», cortado en los dos puntos— termina en sustantivo y es invisible para ese heurístico.

## Decisión

El árbol se audita con detectores que **no comparten patrón, región ni supuesto** con el parser que
auditan. Concretamente:

1. **Cruce de nombres contra el articulado** (`discrepancias_de_nombre`). La lista de módulos del
   articulado está en otra región del documento (todo lo anterior al `ANEXO I`), con otra
   tipografía y otro patrón (`RE_NOMBRE_EN_LISTA`), y no comparte una sola línea con `RE_MODULO`.
   Si el parser corta, funde o pierde un nombre, el articulado lo desmiente. Es una puerta
   permanente, no un script de una vez: es lo que va a cazar el siguiente fallo de esta familia.

2. **Sonda de encabezados sin unidad** (`encabezados_sin_unidad`). Mira líneas que **terminan** en
   dos puntos y no empiezan por viñeta, sin importarle cómo el parser reconoce un encabezado —que
   es exactamente el supuesto que fallaba. `modulos_mudos`, que ya existía, solo veía el módulo con
   **cero** unidades: el que perdía dos de cinco pasaba en verde.

3. **Las contradicciones de la propia norma se declaran, no se corrigen.**
   `DISCREPANCIAS_DE_LA_NORMA` lleva cada caso con su motivo. Hoy tiene uno: el Anexo I de ASIR
   titula el módulo 0372 «Gestión de Base de Datos» y el articulado de la **misma** norma lo llama
   «Gestión de bases de datos». El árbol conserva el Anexo I, que es de donde sale el nodo, y la
   discrepancia se publica en cada corrida.

4. **El muestreo humano se conserva entero.** La tabla vieja no se sustituye: se guarda con sus
   anotaciones dentro del propio fichero, con fecha. Es la prueba de que diez nodos mirados a ojo
   valieron más que los cientos que el verde daba por buenos. Y la tabla nueva se sortea sobre
   nodos **distintos**: ni los módulos reparados —revisar lo que se acaba de arreglar confirma el
   parche, no el extractor— ni los diez ya comprobados.

## Trade-off

**Lo que cuesta.** Dos detectores más que mantener, y con sus propios modos de fallo: si el BOE
cambiara la tipografía de la lista del articulado, `RE_NOMBRE_EN_LISTA` dejaría de encontrar
nombres y la puerta se volvería muda —por eso el cruce imprime cuántos nombres ha declarado cada
norma, para que un cero cante. La sonda de encabezados es **informativa**, no bloqueante: hay prosa
que también termina en dos puntos, y volverla bloqueante la habría convertido en ruido, que es la
forma que tienen las puertas de morir.

Y la tabla de excepciones es, por construcción, el sitio por donde se le puede colar un fallo de
verdad a la puerta: basta con declarar como «contradicción de la norma» algo que en realidad es un
bug. Por eso cada entrada exige motivo escrito, y por eso las declaradas siguen imprimiéndose en
cada corrida en vez de desaparecer.

**Lo que compra.** Que un campo mal extraído deje de ser invisible. El modo de fallo real de este
extractor no ha sido nunca un nodo de más ni uno de menos —eso ya lo cazaba el cruce de códigos—:
ha sido un nodo presente, con su código correcto y su referencia legal correcta, diciendo algo que
la norma no dice. En un fichero que presume de referencia legal por nodo, eso es el fallo caro.

**Lo que NO compra.** Cobertura de las unidades a nivel de nombre. El articulado lista módulos, no
unidades: para las 238 unidades no hay segunda fuente en el BOE contra la que cruzar. Ahí solo hay
la sonda informativa y el muestreo humano. Es una asimetría real y queda declarada, no disimulada.
