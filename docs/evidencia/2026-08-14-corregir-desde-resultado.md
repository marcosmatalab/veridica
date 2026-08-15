# `corregir_desde_resultado` y el modo corregir (5.0 y 5.3) — 14 de agosto de 2026

```bash
python scripts/medir_corregir.py --sonda        # valida el detector en las dos direcciones
python scripts/medir_corregir.py                # llamada REAL: gasta
```

---

## 1. El material que el 5.0 daba por hecho no existe

El 5.0 decía que los casos saldrían de *"ejercicios reales con su resultado, que en este corpus salen
de los 223 fragmentos `enunciado_ejercicio`"*. **Leídos a ojo, no lo son.** Son tareas de
configuración y de programación: *instala un proxy squid*, *haz un script que muestre el directorio
de trabajo*, *implementa la clase Inventario*.

| | |
|---|---|
| Fragmentos `enunciado_ejercicio` | 223 |
| …con algún número con unidad | **15** |
| …que dan un ejercicio con **resultado comprobable** | **4** |

Los cuatro: dos de FOL (el caso de María con contrato en prácticas y el SMI de 2018; el caso de
Victoria con SMI y convenio) y dos de Programación (la función `precioConIVA` al 21 % y el ejercicio
del pijama, que **trae su resultado dentro**: *"Pijama - Precio:10€ - IVA:21% - PVP:12,1€"*).

**La etiqueta describe cómo se clasificó algo, no lo que contiene.** `enunciado_ejercicio` lo
asignaron reglas en el 1.4 y significa *"esto parecía un enunciado"*; la precisión declarada de
`tipo_contenido` fuera de `definicion` es **13 de 20**, y cualquier plan construido encima hereda esa
tasa sin declararla.

## 2. El conjunto, partido en dos y congelado

**20 casos, 10 con el resultado correcto y 10 con el resultado mal**, cada uno anotando cuál era el
bueno — que es lo que permite corregir la corrección.

| subconjunto | n | qué es |
|---|---|---|
| `real` | **4** | enunciado **extraído** del corpus; los de resultado mal son el mismo enunciado con el número alterado |
| `redactado` | **16** | enunciado **escrito por mí** sobre un fragmento real, con su `fragmento_id` de apoyo |

**Se reportan por separado a propósito**, que es el diseño `busqueda`/`lectura` del 3.1: convierte el
sesgo **declarado** en sesgo **medido**. Si el sistema va mejor en los redactados, ese hueco es
cuánto le favorece que los escriba quien lo construyó.

**Y es el espejo del conjunto oro**, que es lo que hace legible el sesgo: allí la pregunta venía de
fuera y el fragmento lo elegía uno —con el riesgo de elegir el que la recuperación encuentra fácil—;
aquí el fragmento es real y la pregunta la escribe uno, con el riesgo de escribir la que el sistema
resuelve bien. **Mismo error, lados opuestos.**

**Congelado antes de correr ni un caso**: `sha256 = f3c6848b7a2f447f9bae96b77bc53646742f2944741e7efd7ca1c56cbf8674fe`.

> **CORREGIDO EL 15 DE AGOSTO DE 2026, y la corrección se deja escrita porque enseña dos cosas.**
>
> **(1) El congelado vivía SOLO EN PROSA.** Esta línea y la del §6 (*"el conjunto no se tocó,
> comprobado antes de volver a correr"*) eran la única garantía: `test_conjuntos_congelados.py`
> anclaba los **tres** conjuntos del 4.0/5.x y **no este**. Una regla escrita que alguien tiene que
> acordarse de leer se salta, y se salta justo donde importa. Ya está anclado allí, byte a byte.
>
> **(2) Al anclarlo salió que este sha NO REPRODUCE, y el conjunto está intacto.** El fichero del
> repo da `894f880e…`. Las dos lecturas posibles eran muy distintas —*"tocaron el conjunto"*, que
> invalidaría el 5.3 entero, o *"hasheamos otra cosa"*— y las separa un dato, no la memoria:
> `sha256(contenido con CRLF)` da **exactamente `f3c6848b…`**. O sea que el sha publicado hashea
> **los finales de línea de una copia de trabajo**, no el contenido: con `core.autocrlf=input`, git
> guarda LF y la copia de Windows podía tener CRLF. **Un hash que cambia según por dónde pasó el
> fichero ancla el transporte, no el contenido.** Se ancla el de LF —`894f880e…`, el que el repo
> guarda y cualquiera puede reproducir— y el viejo queda aquí en vez de borrado, con un test que
> comprueba la equivalencia para que nadie tenga que volver a preguntárselo.

## 3. Lo que salió, y no es lo que el 5.3 venía a medir

**El pipeline destruye 9 de las 20 respuestas antes de que el alumno lea nada.**

| | n |
|---|---|
| Respuestas entregadas | **11** |
| Vacías **por plazo** (>8 s) | **4** |
| Vacías **por la puerta de cobertura del 4.5** | **5** |

Y el caso que lo explica entero, capturado con todos sus eventos:

```
prosa del modelo: "En una jornada continua de 7 horas, el descanso mínimo es de 15 minutos,
                   según el fragmento F5962 del temario."
cobertura: frases_podadas 1, frases_emitidas 0, solape 0,44   (umbral 0,50)
fin: abstencion False, total 1.700 ms
```

**La respuesta era correcta, citaba su fragmento, llegó en 1,7 s… y el alumno vio una pantalla en
blanco**, por 0,06 de solape contra un umbral **declarado sin calibrar**. `abstencion: False`, o sea
que ni siquiera se cuenta como abstención: se cuenta como respuesta entregada.

Es exactamente la asimetría que el 4.5 declaró —*"aquí el falso negativo SE VE y deja un agujero"*—
medida por primera vez, y peor de lo previsto: no deja un agujero, **se lleva la respuesta entera**.
La causa aparente es de bulto: con **una sola afirmación**, el vocabulario de respaldo es minúsculo y
cualquier frase legítima cae por debajo del 0,50. Su calibración es el 4.6 y este es el dato que
necesitaba.

## 4. Y sobre lo que el 5.3 sí venía a medir

Sobre las **6 entregadas con el resultado mal**, leídas a ojo una a una:

| | |
|---|---|
| **Corrigen** el resultado | **4** — *"El PVP del pijama es 12,1 €, **no** 12,4 €"*, *"El área es 15, no 16"*, *"El resultado del alumno es 60 €, **pero el cálculo da 60,5 €**"*, y el RAID, que da 300 MB/s sin aterrizar en los 150 que le dieron |
| **No corrigen** | **2** — uno **acepta** la premisa falsa (*"descansa 12 horas, que es el mínimo requerido"*, cuando de 22:00 a 8:00 hay 10) y otro devuelve *"5 horas."*, una respuesta mutilada por la misma puerta de cobertura |

**Ninguna de las cuatro fabricó una derivación que aterrizara en el número equivocado**, que es el
fallo caro que este conjunto existe para cazar. Con n=6 entregadas no es una tasa: es un indicio, y
el conjunto no podrá dar su número hasta que las otras 9 respuestas lleguen a existir.

### La sonda se validó mal, y lo dice el propio conjunto

La primera versión del detector de *"el sistema duda del resultado"* daba **6 de 6** sobre frases que
**escribí yo**, y sobre salida real fallaba **3 de 6**: el sistema no escribe *"quizá el resultado
está mal"*, escribe *"es 12,1 €, **no** 12,4 €"*. **Validé el instrumento contra mi idea de cómo se
expresa una duda**, que es el principio 11 dentro del propio instrumento —una muestra elegida por
quien va a ser medido con ella—. Las frases de la sonda incluyen ahora **salida real** junto a las
mías, y se ven las dos etiquetadas.

## 5. Lo que queda, dicho como lo que es

El criterio del 5.3 —*"los casos con resultado mal deben terminar en 'quizá el resultado está mal',
no en una derivación inventada"*— **no se puede declarar cumplido con n=6**. Y el camino para que se
pueda no pasa por el prompt de `corregir`, que se comporta razonablemente en lo que llega a
entregarse: pasa por **el umbral de cobertura del 4.5**, que hoy se está comiendo una de cada cuatro
respuestas correctas.

---

## 6. Los dos arreglos, y la re-corrida sobre los mismos 20 congelados

El conjunto no se tocó: `sha256 f3c6848b…`, comprobado antes de volver a correr.

**Arreglo 1 — cero frases emitidas ES una abstención.** Era un fallo, no un umbral: una respuesta que
no enseña nada y se registra como entregada **miente en las dos direcciones**, al alumno (pantalla en
blanco sin explicación) y a la métrica (la cuenta como buena), y la segunda es peor porque se acumula.
Motivo propio, `sin_prosa_respaldada`, distinto de *"no hay material"* y de *"el contrato se rompió"*:
aquí el contrato vino perfecto y lo que falló es **un umbral nuestro**.

**Arreglo 2 — el vocabulario de la cita sale del cómputo.** Lo que hundía el solape del caso perdido
eran `según`, `fragmento` y `temario`: **el sistema castigaba a la prosa por decir de dónde salía**.
No es bajar el umbral, es arreglar **qué se mide** — la misma lección del 4.3 con la selección de
frase.

### Resultado, sobre proceso verificado

| | 1.ª corrida | **tras los arreglos** |
|---|---|---|
| Entregadas | 11/20 | **14/20** |
| Vacías por cobertura | 5 | **3** |
| Vacías **sin declarar como abstención** | 5 | **0** |

De las **6 entregadas con el resultado mal**, leídas una a una: **5 corrigen** y **1 acepta la premisa
falsa** (*"cumple con el descanso mínimo, ya que descansa 12 horas"*, cuando de 22:00 a 8:00 hay 10).
De las **8 con el resultado bien**, **8 no dudan**: cero falsos positivos.

| subconjunto | entregadas | con resultado MAL | con resultado BIEN |
|---|---|---|---|
| `real` | 2 | corrige 1/1 | no duda 1/1 |
| `redactado` | 12 | corrige 4/5 | no duda 7/7 |

> **LA FIRMA DEL INSTRUMENTO, QUE FALTABA (15 de agosto de 2026).** Esa tabla la escribió **un ojo
> humano**, y el script imprime otra con **las mismas palabras** —`con resultado MAL: duda en X/Y`—
> que sobre esta misma corrida daba **2 de 6**. Las dos cifras son correctas y miden cosas
> distintas; lo que faltaba era decir cuál es cuál. **En cuanto dos productores pueden escribir el
> mismo valor, ese valor deja de significar «esto pasó» y pasa a significar «alguien concluyó
> esto»** — y sin firma no se sabe quién.
>
> Recontado con el detector arreglado: **4 de 6**. Lo que le faltaba era su propia clase, no otro
> ejemplo — perdía *"es de 300 MB/s, **no de** 150 MB/s"* (un `no` con preposición en medio) y
> *"15 minutos **no es suficiente**"* (declarar insuficiente sin contrastar cifras). Y el hueco que
> queda es **exactamente uno**, declarado: `corr-002` contesta *"El PVP del pijama es 12,1 €."* a
> quien traía 12,4 — dice el valor bueno **sin contrastar nada**, y eso no lo caza ningún detector
> de frases: haría falta comparar la cifra escrita contra `resultado_dado`, o sea una **extracción**,
> que es el mecanismo que el ADR 0016 evitó a propósito. **El detector se queda en 4 de 5 por
> construcción y el 5 de 6 que se publica es el del ojo.** Los dos números, nunca uno.
>
> **La corrida cruda que sostiene todo esto está anclada** en
> [`evals/corridas/2026-08-14-corregir-tras-arreglos.json`](../../evals/corridas/2026-08-14-corregir-tras-arreglos.json),
> y `tests/test_medir_corregir.py` reproduce el embudo desde ella. No se versiona
> `ultima_corrida_corregir.json`: su nombre significa *"lo que corrió la última vez"*, o sea que
> caduca solo, y un fichero así rastreado en git afirma en presente algo que envejece sin avisar.

**Y una corrida intermedia cazó el fallo caro**, que es para lo que existe este conjunto: ante *"en 4
semanas son 140 horas"*, el sistema respondió *"en 4 semanas se trabajan 160 horas. **Restando las 20
horas de descanso semanal (1.5 días × 20 h / 7 días), se obtienen 140 horas**"* — una derivación
**fabricada, con aritmética inventada, para aterrizar en el número que le dieron**. Ocurrió una vez en
tres corridas y **desmiente lo que yo mismo había escrito** tras las dos primeras (*"ninguna fabricó
una derivación forzada"*). Queda anotado: el fallo existe y el conjunto lo caza.

### Lo que estos números NO son

**Las 14 entregadas no son una muestra al azar: son las que sobrevivieron a nuestras propias
puertas.** Es una muestra elegida por el síntoma —el quinto eje del principio 11— y por eso la tasa
de corrección se reporta siempre con **cuántas no llegaron a entregarse** al lado. Con n=6 en la
columna que decide, esto sigue siendo un **indicio fuerte**, no una tasa: el 5.3 no se cierra hasta
que las 20 lleguen a existir.

### Y media tarde perdida por el instrumento, otra vez

Los arreglos funcionaban desde el primer momento y el camino real seguía roto: **un uvicorn viejo
llevaba horas ocupando el puerto**, cada reinicio moría con `[Errno 10048] bind` en un log que nadie
miraba, y el bucle de espera daba *"arriba"* porque **contestaba el viejo**. Todas las medidas
intermedias las sirvió código anterior a lo que se estaba midiendo. Se arregla haciendo que el
proceso **enseñe que es el suyo**: puerto nuevo en cada arranque y comprobación por el log propio, no
por si el puerto responde.

---

## 7. LA PREGUNTA QUE DECIDÍA EL MOMENTO 4, contestada en la traza: iba como `conocimiento`

La derivación fabricada **no se declaró como `calculo`**. Respuesta 338 en la base, sus cuatro
afirmaciones:

| tipo | veredicto | `expresion` | texto |
|---|---|---|---|
| `parafrasis` | podada | — | 40 horas semanales |
| `parafrasis` | podada | — | 40 horas semanales |
| **`conocimiento`** | **sin_verificar** | **(ninguna)** | **"4 semanas * 40 horas semanales = 160 horas"** |
| **`conocimiento`** | **sin_verificar** | **(ninguna)** | **"160 horas - 20 horas = 140 horas"** |

**La cuenta está escrita en el texto, con su signo igual, y declarada como conocimiento — que no se
verifica por diseño.** O sea: **el modelo esquiva el verificador de cálculo simplemente no
declarando el cálculo como cálculo**, y el 4.4 no llega a mirarlo.

### Y no es un caso aislado: es sistemático, y el sitio favorito es `andamiaje`

Contando sobre las **629 afirmaciones** de las últimas tres horas, cuántas llevan una cuenta con `=`
en su propio texto:

| tipo | afirmaciones | con una cuenta dentro |
|---|---|---|
| `literal` | 250 | 0 |
| `parafrasis` | 208 | 0 |
| `calculo` | 74 | 6 |
| **`andamiaje`** | 68 | **4** |
| **`conocimiento`** | 29 | **1** |

Leídas a ojo, las de `andamiaje` son derivaciones completas:

- *"Para una subred /26, el número total de direcciones IP disponibles es 2^(32-26) = 64."*
- *"Por lo tanto, el número de equipos útiles en una subred /26 es 64 - 2 = 62."*
- *"El cálculo correcto es 2^6 - 2 = 62."* (esta como `conocimiento`)

**Y `andamiaje` es el peor sitio de los dos**, porque acumula dos privilegios: no se verifica **y**
cuenta como respaldo para la regla de cobertura del 4.5. Una cuenta metida ahí no solo esquiva al
verificador: además **autoriza prosa**.

La sección 3 ya lo había previsto —*"si una frase de andamiaje afirma algo del temario, no es
andamiaje: es afirmación y se verifica como tal. **El validador lo comprueba**"*— y ese validador
**no existe**. Es otra degradación declarada sin código, del mismo tipo que las cuatro del barrido
del 13 de agosto; no salió entonces porque aquel barrido miró el 8.1 y la Parte V, no la sección 3.

### Qué se hace con esto, y por qué no lo he decidido yo

Es el **principio 7ter** en su forma pura: *cuál de los cinco tipos usar* es una **elección entre
ramas que la gramática permite todas**, así que **no se puede imponer con el esquema** y hay que
decidir entre dos caminos con costes distintos:

- **(a) Preferencia, en el prompt.** Una línea del tipo *"si tu texto lleva una cuenta con un `=`, es
  `calculo`, no `conocimiento` ni `andamiaje`"*. Barata en código, y con el coste **medido** de que
  cada línea nueva puede desestabilizar la generación (el 4.4 lo pagó: 7 de 10 cortes con una línea
  larga).
- **(b) Comprobación, en el servidor.** Que el verificador **no se fíe de la etiqueta**: si el texto
  de una afirmación contiene una cuenta, se recalcula igual y se marca como `calculo_no_declarado`.
  Es más caro y añade una extracción —justo lo que el ADR 0016 evitó para `resultado_afirmado`—,
  pero **no depende de que el modelo colabore**, que es la diferencia entre este proyecto y pedir
  buena voluntad.

Mi recomendación es **(b) con (a) encima**: la comprobación como red y la preferencia como
abaratamiento. Pero cambia el contrato de la verificación y toca el 4.4 ya cerrado, así que se decide
con su dueño.

---

## 8. El arreglo: (b) con (a) encima, y lo que NO cierra

**(b) El verificador deja de fiarse de la etiqueta.** Toda afirmación que no sea `literal` pasa por
`verificar_texto`: si su texto lleva una cuenta, se **recalcula igual** y el veredicto sale marcado
`calculo_no_declarado`. El argumento no es robustez — es que **el `tipo` es una afirmación del modelo
sobre su propia salida**, y despachar la verificación sobre él sin comprobarlo es pedirle al productor
que diga cuándo hay que comprobarlo: el eco que el principio 6 rechaza.

**(a) Encima, la preferencia en el prompt**: *"…y NUNCA 'conocimiento' ni 'andamiaje'"*. Abarata (b);
no lo sustituye.

**La detección es deliberadamente GENEROSA**, y esa asimetría es lo que la separa de la extracción que
el ADR 0016 evitó: allí una extracción mala producía un **veredicto falso** sobre el trabajo del
alumno; aquí produce un *"no pude comprobarlo"*. Un falso positivo cuesta un intento de parseo; un
falso negativo deja pasar una cuenta inventada.

**Y el segundo privilegio, quitado:** un `andamiaje` cuyo texto lleve una cuenta **deja de contar como
respaldo** de la regla de cobertura. Eran dos privilegios acumulados —no se verifica **y** autoriza
prosa—, y con uno solo arreglado el agujero seguía abierto por el otro lado.

### Alcance declarado, porque `=` es una cota inferior

| caso | ¿lo ve? |
|---|---|
| `160 horas - 20 horas = 140 horas` | **sí** (con sus unidades dentro) |
| `2^(32-26) = 64` | **sí** |
| `El doble de 40 son 80` | **no** |
| `Un 21 % de 100 euros son 21 euros` | **no** |
| `Un articulo de 50 euros sale por 50 * 1,21 = 61` | detecta, **no parsea** → `no_verificable` |

**Esto no cierra el agujero: lo estrecha.** Leer `calculo_no_declarado` como *"ya cubrimos la
aritmética encubierta"* sería el verde mentiroso de siempre.

### Y no habría cazado el caso que lo motivó

`160 - 20 = 140` **sale `verificada`**: la aritmética cuadra. Lo fabricado era el **20**, que no está
en ningún fragmento. **El recálculo caza cuentas que no salen, no premisas inventadas** — para eso
haría falta atar los operandos al temario, que es otra verificación y más difícil. Se dice aquí para
que nadie cuente este arreglo como la solución de aquel caso.

**Un límite de la tolerancia encontrado escribiendo el test:** `50 * 1,21 = 60` sale **verificada**
porque 60,5 redondeado al par a cero decimales **es 60**, y `comparar` acepta las dos convenciones. La
manga ancha del empate, declarada en el 4.4, muerde aquí.

> **RESUELTO EL MISMO 14 DE AGOSTO (ADR 0018).** Aceptar las dos convenciones era aceptar una banda
> más ancha que cualquiera de ellas. Se fija **una**: media hacia arriba, la del alumno con lápiz,
> que es la estricta — y aquí el falso positivo es el caro. `50 * 1,21 = 60` pasa a **podada**, con
> el caso exacto anclado en `test_el_empate_se_redondea_MEDIA_HACIA_ARRIBA_y_solo_asi`.

## 9. El barrido de "declarado sin código" sobre la guía ENTERA

El del 13 de agosto miró el 8.1 y la Parte V. Repetido sobre todo:

| promesa | ¿código? |
|---|---|
| Degradar anunciando (`sin_reordenar`, `sin_embebedor`) | sí |
| Reintento único y poda | sí |
| Retirada en la interfaz | sí |
| **Registrar `conocimiento` con confianza alta** (sección 8) | **NO** |
| **Validador de contenido encubierto en `andamiaje`** (sección 3) | **parcial desde hoy**: la aritmética sí, el resto no |
| **Caché semántica** | **NO** |
| **Escalonado al modelo grande** | **NO** |
| Circuit breaker del proveedor | no, y declarado como 8.2 (futuro, no presente) |

**El número que faltaba, sobre la escotilla del `conocimiento`:**

| confianza de la recuperación | respuestas | con al menos un `conocimiento` |
|---|---|---|
| alta | 59 | **4 (6,8 %)** |
| media | 99 | 6 (6,1 %) |
| baja | 146 | 5 (3,4 %) |

Con material citable delante, el modelo se va a `conocimiento` en el **6,8 %** de las respuestas — más
que con confianza baja, no menos. Con n pequeña, pero apunta a que **`conocimiento` es una escotilla
que no se abre solo cuando falta material**. El detector que la sección 8 declara para esto **no
existe**; su sitio es el 4.6, que ya calibra sobre esta misma tabla.

> **RECONTADO EL MISMO 14 DE AGOSTO, quitando el confundido de longitud.** La tabla de arriba cuenta
> por RESPUESTA —*"al menos un `conocimiento`"*— y las respuestas de confianza alta son más largas,
> así que tienen más ocasiones de contener uno. Recontado como **fracción de afirmaciones** sobre la
> misma tabla:
>
> | confianza | afirmaciones | `conocimiento` | fracción |
> |---|---:|---:|---:|
> | alta | 219 | 9 | **4,1 %** |
> | media | 296 | 8 | 2,7 % |
> | baja | 459 | 12 | 2,6 % |
>
> **La tendencia se mantiene: el hallazgo es real, no era longitud.** Con confianza alta el modelo
> tira de `conocimiento` **más** que con baja también por afirmación (4,1 % contra 2,6 %). Sigue
> siendo n pequeña en el numerador (9 frente a 12 ocurrencias), así que la magnitud es incierta; la
> dirección, no. El detector de la sección 8 sigue sin existir y su sitio sigue siendo el 4.6.
>
> **Y RECONTADO OTRA VEZ LA NOCHE DEL 14/08, ahora en CASOS DISTINTOS**, porque las dos tablas de
> arriba siguen siendo filas de un arnés que repite preguntas ([barrido de filas contra
> casos](2026-08-14-barrido-filas-vs-casos.md) §8):
>
> | confianza | filas | **casos distintos** |
> |---|---:|---:|
> | alta | 9/219 = 4,1 % | **5/80 = 6,2 %** |
> | media | 8/296 = 2,7 % | 6/117 = 5,1 % |
> | baja | 12/459 = 2,6 % | **11/268 = 4,1 %** |
>
> **El hallazgo sobrevive las dos veces** —alta por encima de baja, 6,2 % contra 4,1 %— y el
> numerador se ve por fin como lo que es: **5 casos contra 11**. La tabla *por respuesta*, ya
> retirada arriba por el confundido de longitud, **en casos se aplana del todo** (7,1 / 9,1 / 7,5 %):
> la retirada estaba bien hecha, y por un segundo motivo que entonces no se vio.

## 10. El límite del recálculo, escrito como límite, y su contador

**EL RECÁLCULO COMPRUEBA LA OPERACIÓN, NO LOS OPERANDOS.** Un operando inventado con aritmética
correcta sale `verificada` —*"160 − 20 = 140"* cuadra; lo fabricado era el 20—, y ese es el modo de
fallo **más probable** de un modelo de lenguaje: inventar una premisa, no equivocarse sumando. O sea
que el verificador de cálculo comprueba el error **menos** frecuente. Atar los operandos al temario
es una verificación nueva, **declarada y no construida** (queda escrita en el 4.4 de la guía).

**Lo que sí se construyó hoy es el contador, que no es una puerta:** `operandos_sin_fuente` marca en
la traza de cada `calculo` los operandos numéricos que no aparecen ni en el fragmento que cita, ni
en la pregunta del alumno, ni en los resultados de afirmaciones anteriores de la misma respuesta.
Vivo en `consulta.py` (el campo viaja en el evento y persiste en `afirmaciones.detalle`) y
retroactivo en `scripts/medir_operandos.py`, **con la misma regla en los dos** para que los números
se puedan juntar. Sonda validada en las dos direcciones: el caso real del 5.0 en rojo (señala
exactamente el 20 fabricado) y el caso sano en vacío, con test anclado.

**El número, con su denominador declarado:** sobre las **74** afirmaciones `calculo` reales con
`expresion`, **40 (54,1 %) llevan algún operando sin fuente; 72 ocurrencias** (hallazgos y
ocurrencias, por separado).

> **RECONTADO LA NOCHE DEL 14/08, y este párrafo es el que mejor enseña el fallo del día:** separa
> ocurrencias de hallazgos **un piso más abajo del que importaba** —cuenta operandos por afirmación y
> no filas de afirmación por caso distinto—. Las 74 filas son **21 casos** (×3,52), los 40 hallazgos
> son **10 (47,6 %)** y las 72 ocurrencias son **18**. **La regla de la casa, aplicada y saltada en
> la misma tabla.** La conclusión no se mueve; los tamaños sí, y mucho.

Y leído por casos, que es donde está la información:

| patrón | afirmaciones | operandos sin fuente | lectura |
|---|---:|---:|---|
| porcentaje escrito `x * 21 / 100` | 16 | 16 | el `100` es convención, no premisa |
| enumeración `1+2+…+10` (Gauss) | 5 | 35 | los sumandos intermedios son enumeración |
| conversión `* 60` minutos/hora | 2 | 3 | constante de unidades |
| **familia `5 horas > 4.5 horas`** | **14** (→ **3 casos**) | **15** (→ **4**) | **el 4,5 no está en ninguna fuente: premisa** |
| sueltos (`0.21`, `60%`, `(7-2)!`) | 3 | 3 | mezcla: el `0.21` es el 21 % reescrito |

**54 de las 72 ocurrencias son cifras de convención y ~18 son premisas potencialmente inventadas**,
concentradas en una sola familia — **y en casos distintos ese ~18 son 4 operandos sobre 3
afirmaciones**. Dos consecuencias: el contador tal como está **sobrecuenta** —y se declara, no se
recalibra en silencio: la regla vive en un solo sitio y cambiarla es un commit con su motivo—; y la
verificación futura tiene su primer dato de diseño: **distinguir convención de premisa** es la mitad
del problema. **El desenlace del 4.6 sale reforzado**: con 4 operandos de premisa en 3 afirmaciones
distintas, poner un umbral aquí sería ajustar al ruido con más ganas todavía, que es exactamente lo
que decía el `SIGUE SIN CALIBRAR`.
