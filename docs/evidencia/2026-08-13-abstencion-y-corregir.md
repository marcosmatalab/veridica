# Abstención, forma de `corregir` y salud del despliegue — 13 de agosto de 2026

```bash
python scripts/medir_abstencion.py     # lee las trazas; no gasta
```

---

## 1. Abstención: el número grande y el fino, con sus denominadores

**Dos números y no uno, porque quedarse con el fino también es una selección.** El desglose por
motivo solo puede salir de las consultas nuevas —el motivo empezó a persistirse en el 4.5—, y
reportar solo esas sería elegir la muestra por **cuándo**: la forma más común del principio 11 en
software, esta vez con datos de *después* del cambio.

| | valor | denominador |
|---|---|---|
| **Tasa total de abstención** | **49 de 165 → 29,7 %** | todas las respuestas persistidas |
| Con motivo de fallo en la traza | 30 (18,2 %) | idem |
| **Abstenciones SIN motivo registrado** | **19 de 49** | las abstenciones |

**Desglose por motivo (n = 30):**

| clase | n |
|---|---|
| `PlazoAgotado` (el presupuesto de 5 s del 3.4) | **30** |

**Y lo que ese cuadro NO dice, que importa igual:** las otras clases que la sección 8 define
—contrato roto tras el reintento, todo podado, nada que recuperar— **no salen cero: salen ausentes**,
porque hoy **nadie las escribe**. Un cero medido y un campo que nadie rellena se ven idénticos en una
tabla y son cosas distintas; por eso las **19 abstenciones sin motivo** van en su propia fila en vez
de repartirse.

**El único motivo que existe hoy es el plazo**, y son 30 de 165 (18,2 %) consultas que no llegaron en
5 s. Ese es el número que discute si el presupuesto está bien puesto, y es el que el 4.6 tiene que
partir por causa.

## 2. Cuántas respuestas se sostienen solo con `conocimiento` marcado

**0 de 114** respuestas con afirmaciones factuales (**0,0 %**).

Ninguna respuesta con contenido factual se apoya **solo** en conocimiento del modelo: todas citan el
temario al menos una vez. Es el número que el propietario preguntaba, y sale mejor de lo que yo
esperaba. Con la cautela de siempre: son respuestas de antes de la fase 4, así que **nadie ha
comprobado que esas citas sean ciertas** — solo que existen.

## 3. La forma de `corregir`, comprobada por `version_prompt` y no supuesta

`version_prompt` lleva el modo dentro desde el 4.1 (`4.4-2026-08-13/corregir`), así que la muestra se
**filtra por el prompt que de verdad se usó** en lugar de por la columna `modo`, que es lo que el
cliente pidió. Son dos campos distintos y podrían discrepar. **Es la primera vez que ese campo sirve
para algo, y sirve exactamente para lo que se puso.**

| modo | respuestas | afirmaciones (media / máx) | tokens de salida (media / máx) |
|---|---|---|---|
| `corregir` | 6 | **3,0 / 5** | **386 / 615** |
| `responder` | 0 | — | — |
| `acompanar` | 0 | — | — |

(169 consultas anteriores al 4.1 no llevan el modo en `version_prompt` y quedan fuera por definición.)

### Y esto corrige un número mío del mismo día

El desbordamiento de 900 tokens que motivó el `maxItems` (ADR 0017) se midió **sin fragmentos en
contexto**: 7 de 10 en la consulta de IVA. **Por el camino real, con corpus, son 0 de 6**, con
máximo 615 tokens y 5 afirmaciones — bien por debajo del tope.

**Sin material que citar el modelo se explaya; con material se ciñe a él.** Es la tesis del proyecto
vista desde el consumo de tokens, y también el aviso de siempre: *el error viaja en el sumando*. El
tope se queda puesto —es una prohibición barata y n=6 no demuestra ausencia—, pero **declarado sin
calibrar** y no como arreglo de un fuego que en la ruta real no se ha visto arder.

**Consecuencia para la demo, y va al guion:** el momento 4 es el único en modo `corregir`, con el
doble de afirmaciones y el doble de tokens que una consulta normal. Las seis consultas reales
tardaron **entre 2,3 y 4,9 s** de punta a punta: el peor caso **roza** el presupuesto de 5 s sin
pasarse. Será el momento **más lento de la sesión** y se guioniza sabiéndolo.

## 4. `/salud`: degradar anunciando no es estar roto

**El diagnóstico estaba mal, no solo el `--wait` en rojo.** Con todas las dependencias en la misma
lista, el contenedor —que no lleva torch a propósito— devolvía **503**, así que `docker compose up
--wait` no arrancaba por una capacidad que decidimos **nosotros** no empaquetar. Un 503 dice *"no
puedo responder"*.

Ahora: **503 solo para lo que impide responder** (`db`, `extensiones`), **200 con `degradado`** para
lo demás, y la respuesta lista **en texto** qué falta, qué se pierde y el detalle crudo de la sonda:

```
estado: degradado | puede_responder: True
  - embebedor: no hay búsqueda por SIGNIFICADO: se recupera solo por palabras y glosario,
    que el 3.1 midió en 58 % de recall@6 frente al 80,9 % de la fusión
    | RuntimeError: ModuleNotFoundError: No module named 'torch'
```

Quien mire esto un lunes por la mañana necesita distinguir *"falta el reordenador"* de *"falta
torch"*, y un booleano no lo hace.

### Y el arreglo de verdad estaba debajo

La frase *"sin torch se sirve léxica"* **no era cierta**: hasta hoy, `embebedor is None` hacía que
`_recuperar` devolviera **cero fragmentos**, o sea que el sistema respondía de memoria — exactamente
lo que dice no ser. Y no era una consecuencia técnica: `recuperar()` acepta `vector=None` desde el
3.3 y hace léxica y glosario. **Nadie había escrito el respaldo.**

Con él, quedarse sin torch pasa a ser degradación anunciada —una etapa `sin_embebedor` en el SSE y en
la traza—, y la confianza se marca como **no medible** en vez de *medida y baja*, que son dos cosas
que el 4.6 no debe sumar.

Efecto secundario que hay que decir: esta ruta **ahora toca la base** donde antes no la tocaba, así
que una base caída podía llevarse la petición con una excepción cruda a mitad del SSE. Se degrada
igual que el reordenador: se responde sin fragmentos **y se dice**, con el motivo en la traza. Los
dos casos tienen test.

---

## 5. RE-MEDIDO SOLO SOBRE CÓDIGO ACTUAL, que es el número que decide el lunes

Las 165 respuestas de arriba abarcan versiones anteriores al tope de la cita, al vigilante, al plazo
y al respaldo sin embebedor: **una muestra elegida por CUÁNDO**, que es la extensión del principio 11
escrita dos commits antes. Así que se vuelve a medir sobre lo que corre hoy — 26 respuestas con el
prompt del 4.4 (`version_prompt` con el modo dentro), lote de 20 consultas mezclando modos y cinco
asignaturas, **secuenciales** porque una sesión es una persona:

| | histórico | **hoy** |
|---|---|---|
| n | 165 | **26** |
| Abstención | 29,7 % | **11,5 % (3 de 26)** |
| Motivo | 100 % `PlazoAgotado` | 100 % `PlazoAgotado` |
| Total medio | — | 5.004 ms |

**La tasa cae a menos de la mitad**, y sigue siendo el plazo el único motivo: el sistema no se
abstiene porque no sepa, se abstiene porque **no termina a tiempo**. La palanca es la latencia, no la
política de abstención.

Para la demo, con el número delante: en una sesión de **ocho** preguntas, 11,5 % es **una** que se
corta —no dos o tres—. Sigue habiendo que ensayar el salto a la grabación, pero deja de ser el
escenario probable.

### Y la predicción del tope de la cita, resuelta

El 4.1 dejó escrito: *"el corte BAJA pero NO por debajo del 10 %; se espera entre el 15 y el 25 %"*,
con el trato de que si bajaba del 10 % la predicción se declaraba fallada.

**Medido: 11,5 %.** No baja del 10 %, así que el trato no se activa; pero **queda por debajo de la
banda predicha** (15–25 %), o sea que el efecto fue **mayor** de lo estimado. Se apunta como acierto
parcial y con su n=26, que es pequeña.

## 6. Y el lote destapó una congelación de 62 SEGUNDOS

Una de las 20 consultas tardó **61.923 ms** — con el presupuesto en 5.000 y dos mecanismos
construidos justamente para impedirlo. La traza lo dice entera:

```
PlazoAgotado: la respuesta no llego en 5000 ms (van 61924)
```

El plazo **sí** disparó… cuando llegó el trozo siguiente, 62 segundos después. Es el patrón que ya
tiene regla en este repo —*un detector que se alimenta del flujo que vigila es ciego al flujo
AUSENTE*— y el corte de fuera era el `timeout_lectura` del cliente.

**La causa, y es de las que dan vergüenza:** `timeout_lectura` vale **5.0** en el dataclass, pero
`desde_entorno` leía **`TIMEOUT_ETAPA_MS`**, que `compose.yml` trae en **60000** desde el encargo 0.3
—cuando no existían ni el plazo ni el vigilante—. **El código parecía correcto al leerlo y el
contenedor corría con 60 s.** Una constante compartida haciendo dos trabajos con óptimos distintos:
el tope de etapa acota una fase entera; el de lectura acota el **hueco entre trozos**, que hasta en la
peor consulta medida son 250 ms.

Arreglado con variable propia (`TIMEOUT_LECTURA_MS`, 5000 por defecto), en `compose.yml` y en
`.env.example`, con test de regresión y **comprobado dentro del contenedor**:

```
timeout_lectura efectivo en el contenedor: 5.0 s
```

**Lo cazó una medida, no una revisión.** El valor declarado y el valor real llevaban divergiendo
desde que se escribió el arreglo, y leer el código no lo enseñaba.
