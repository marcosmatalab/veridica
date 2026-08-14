# Evidencia: el clasificador de modo (5.1) — CONGELADO ANTES DE VER LAS ETIQUETAS

- **Fecha:** 14 de agosto de 2026, noche
- **Encargo:** 5.1, subido de prioridad porque el selector de modo es fricción en la primera pantalla
- **Estado:** **construido y congelado. NO medido.** Las etiquetas no se han abierto todavía.

## 0. El protocolo, y por qué el orden de los pasos ES el experimento

El propietario entrega **dos** ficheros y se queda un tercero:

| fichero | qué es | sha256 |
|---|---|---|
| `rubrica_modos.md` | la **especificación**: 3 reglas y 6 desempates, escritos ANTES de redactar ninguna pregunta | `e69ac9a4…20e43ec` |
| `modos_sin_etiquetar.jsonl` | 45 turnos, **solo el texto** | `8561a5ff…dd71114b` |
| *(no entregado)* | las etiquetas | — |

**Y las preguntas no las escribo yo, que es el cambio que importa.** El razonamiento es el que yo
mismo planteé, llevado un paso más: quien construye el clasificador escribe, sin querer, las
preguntas que su clasificador sabe resolver — **sus puntos ciegos se copian al conjunto y el número
sale bonito por construcción**. Escritas desde fuera, el conjunto no comparte mis puntos ciegos.

**El orden es: construir → congelar en un commit → abrir las etiquetas → comparar.** Este documento
y `evals/casos/modos_prediccion.jsonl` (sha256 `2beda7c7…3a4d3a410`) son la mitad que se congela.

## 1. Reglas, no modelo — decidido antes de medir

Es lo que ya pasó con el detector de código, donde la densidad de marcas ganó al `@\w+` heredado.
Unas reglas sobre rasgos estructurales son **gratis en latencia, inspeccionables y no pueden
alucinar**, y esto corre en cada consulta **antes** de tocar el proveedor. **Un modelo entra solo si
las reglas se quedan cortas Y el número lo justifica**, y esa decisión se toma con la tabla delante.

## 2. La disciplina de implementación, escrita porque es fácil de romper

**Cada cambio del código cita una cláusula.** Leer los 45 turnos y ajustar las reglas es legítimo
**solo** donde una cláusula lo manda; ajustarlas porque *"este caso me parece que debería salir
así"* es ajustar al conjunto que se va a medir, o sea el sesgo entero de vuelta por la puerta de
atrás. Cinco cláusulas estaban mal implementadas en la primera versión y se arreglaron citándolas:

| qué fallaba | cláusula | qué cambió |
|---|---|---|
| `diferencia HAY entre`, `qué partes tiene` no casaban | **R3** | el patrón pedía `diferencia entre` pegado |
| `me han mandado…`, `el profesor pide…`, `¿por dónde empiezo?` salían `responder` | **R2** | lo que hace concreto un ejercicio es que haya **una tarea determinada delante**, no la palabra *ejercicio* |
| *"¿Cómo se calcula una subred? Es para el ejercicio 5"* salía `acompanar` | **D2** | **el orden**: D2 se evalúa ANTES que R2, que es la única forma de que su propio ejemplo se cumpla |
| *"…aún no lo he hecho"* salía `corregir` | **D4** | `no lo he hecho` **contiene** `he hecho`: guarda de negación sobre la ventana anterior al rasgo |
| `ponerme un ejercicio` no levantaba la bandera | **D6** | el patrón no cubría el infinitivo |

**Y una lección de método por el camino, de las baratas:** el primer intento de aplicar estos
arreglos fue un script de reemplazos dentro de un *heredoc*, y **los escapes hicieron que casi
ninguno casara — sin quejarse**. El fichero quedó a medias y `ruff` lo cazó por casualidad (un
nombre indefinido). Es la mutación que no se aplica, otra vez: **un reemplazo que no casa no falla,
calla**. Se rehízo escribiendo el fichero entero.

## 3. Los tres fronterizos que el propietario avisó que dolerían

| turno | lo que dolería | qué sale | cláusula |
|---|---|---|---|
| *"Ayúdame a **corregir** el ejercicio, aún no lo he hecho"* | leer el verbo | `acompanar` | D4 |
| *"Mi diagrama pone que el controlador habla con la base de datos"* | no lleva `?` | `corregir` | R1 |
| *"**Dame la solución** del ejercicio de subredes"* | tentación de `responder` para poder soltarla | `acompanar` | D3 |

Los tres salen como manda la rúbrica. **El tercero es el que defiende una decisión pedagógica desde
el clasificador** y por eso tiene test propio.

## 3-bis. LO QUE PASÓ AL ABRIRSE EL PROTOCOLO — y la rúbrica cambió, no la lectura

**El protocolo se cumplió: commit `12e524d` primero, etiquetas después.** De las dos ambigüedades
declaradas en §4, **una coincidió y la otra no**, y el desacuerdo cayó **exactamente donde estaba
escrito que podía caer**:

| caso | mi implementación | el etiquetado | desenlace |
|---|---|---|---|
| `modo-41` *"creo que entiendo pero no estoy seguro"* | `responder` | `responder` | coinciden: sin proposición concreta no hay nada que evaluar |
| `modo-43` *"…y luego te enseño lo mío"* | `corregir` (letra de R1) | `responder` | **la rúbrica gana una cláusula nueva** |

**Y el arreglo fue de la RÚBRICA, no de la lectura**, porque R1 —*"siempre que el turno afirme que
existe"*— **permitía** mi lectura. Nace **D7**: *"declara" significa que el intento **existe y se
somete AHORA**, no que se promete para luego; el clasificador clasifica **este turno**, y en un turno
donde no hay nada que evaluar no puede haber `corregir` aunque anuncie que lo habrá.*

**Que el desacuerdo cayera justo en un caso declarado por escrito ANTES de abrir el fichero es la
prueba de que el protocolo sirve: se discutió la regla y no el gusto.**

### Y el hallazgo del orden, que es un defecto del enunciado y no de nadie

La rúbrica listaba tres reglas y seis desempates **sin decir en qué orden se evalúan**. Que el
ejemplo de D2 solo se cumpla si D2 va antes que R2 significa que **la especificación estaba
infraespecificada y la ambigüedad solo aparecía al implementarla**. El orden queda escrito dentro de
la rúbrica, con su moraleja: **una rúbrica sin orden de evaluación no es una especificación, es una
lista** — dos personas pueden cumplirla entera y no coincidir.

### Las predicciones, en DOS ficheros y ninguno sobrescrito

| fichero | qué es | sha256 |
|---|---|---|
| `modos_prediccion.jsonl` | **lo congelado antes de las etiquetas**, intacto | `2beda7c7…` |
| `modos_prediccion_v2_con_d7.jsonl` | tras aplicar D7 | `109dcf60…` |

**Cambia exactamente una predicción** (`modo-43`: `corregir` → `responder`), y por eso hay dos
ficheros en vez de uno editado: **una corrección se declara, no se borra**, y sustituir el
congelado dejaría el repo sin la prueba de qué se predijo a ciegas.

## 4. DOS CASOS DONDE LA RÚBRICA ES AMBIGUA, declarados ANTES de ver las etiquetas

Se escriben aquí y no después, porque después serían excusas:

1. **`modo-43`** — *"Explícame cómo lo haría un profesional y luego te enseño lo mío."* R1 dice que
   basta con que el turno **afirme que el intento existe**, y *"lo mío"* lo afirma; pero el intento
   es explícitamente **para un turno posterior** y lo que este turno pide es un concepto. **Mi
   implementación dice `corregir`** por la letra de R1. La lectura contraria es defendible.
2. **`modo-41`** — *"Creo que entiendo las cookies pero no estoy seguro: ¿me lo confirmas?"* No hay
   resultado ni respuesta declarada, solo un estado de comprensión. **Mi implementación dice
   `responder`** (D5). La lectura contraria —que *"creo que entiendo"* es una respuesta a evaluar—
   también es defendible.

**Si el desacuerdo cae en estos dos, es sobre la REGLA y no sobre el gusto**, que es exactamente
para lo que la rúbrica se escribió antes.

## 4-bis. LA TABLA DE FIDELIDAD: NO SE PUEDE CALCULAR TODAVÍA

**Las etiquetas no han llegado.** `modos_sin_etiquetar.jsonl` sigue teniendo dos claves —`id` y
`turno`— y ninguna etiqueta, y no hay ningún otro fichero con ellas en el repo. Se conocen **dos
etiquetas sueltas** porque el propietario las escribió en prosa al comentar las ambigüedades
(`modo-41` → `responder`, `modo-43` → `responder`), y **con dos de 45 no se calcula una tasa**.

Este hueco se deja escrito en vez de rellenarse con una estimación, que es la regla de siempre: **si
el instrumento no lo permite, se escribe que no lo permite.** En cuanto lleguen las 45, la tabla
sale de una corrida y se publica con la limitación del §6 pegada.

## 5. Lo que sale, sin etiquetas al lado

```
responder  15   acompanar  14   corregir  16
```

**Un reparto equilibrado no es una medida de nada** y se dice aquí para que nadie lo lea como una:
solo dice que las tres ramas se usan, o sea que ninguna regla está muerta. Si una hubiera salido a
cero, el clasificador tendría una rama que ningún turno alcanza y eso sí sería un hallazgo.

## 6. Y LO QUE EL NÚMERO NO VA A SIGNIFICAR, escrito antes de tenerlo

**Las etiquetas las pone quien escribió la rúbrica.** Así que lo que se va a medir es **fidelidad a
la rúbrica**, no acuerdo con la intención real de un alumno. El número **no se presenta como
*"acierta el X %"***; se presenta como:

> *"implementa la rúbrica con un X % de fidelidad; el acuerdo con alumnos reales queda sin medir y
> necesita usuarios."*

## 7. Y la condición de despliegue, que es del propietario y va antes que el número

**El clasificador no sustituye al selector hasta que se mida.** Si acierta poco, **se envía igual**
pero con el selector como control primario y la clasificación como **sugerencia visible**: un
clasificador que se equivoca en directo y decide por el alumno es peor fricción que el desplegable
que se quitaba. Y en cualquiera de los dos casos, **el modo elegido se enseña y se cambia en un
clic** — clasificar en silencio sería decidir por el alumno sin decírselo.
