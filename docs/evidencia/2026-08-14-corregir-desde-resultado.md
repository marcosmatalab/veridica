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
