# Reordenado (encargo 3.4): la LATENCIA, medida. La calidad, no — y aquí está por qué

**13 de agosto de 2026.** Corridas `4`, `5` y `6` en `corridas_eval`.
Modelo `BAAI/bge-reranker-v2-m3`, revisión anclada `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`.
Arnés: `scripts/medir_reordenado.py`. Se cronometra **solo el paso de reordenado**, sobre pools de
30 candidatos reales salidos de la fusión del 3.3.

---

## EL HUECO DE CALIDAD ESTÁ VACÍO A PROPÓSITO, y esta es la frase que lo explica

**El `recall@6` con y sin reordenador no está medido, y no se medirá hasta que llegue el conjunto oro
reconstruido.** La calidad de un reordenador se mide contra los pares oro, y **esa vara está rota**:
del orden de 40 de 100 pares están mal etiquetados (3.0). Medir acierto contra ella no daría un
error ni una excepción — daría un número con toda la pinta de un dato, que es la única avería de
esta fase que no se nota mirando el resultado.

**La latencia sí se mide hoy, y por eso está partido así: la latencia no depende de la vara.**
Depende de treinta candidatos y un reloj. Y es la mitad que puede disparar el plan B, así que
enterarse tres días antes de la sesión vale infinitamente más que enterarse el sábado.

**El criterio de aceptación de la calidad ya está escrito** (3.4), y se escribió **antes** de tener el
número, que es el único momento en que escribirlo es decidir: la fusión sola da **72,8 %** de
`recall@6` en `lectura`, el techo del pool 30 es **88,9 %**, y **el reordenador se queda si cierra
más de la mitad del hueco, o sea si llega a 80,9 %**.

---

## Lo medido

| Configuración (30 candidatos) | n | p50 | **p95** | máx |
|---|---:|---:|---:|---:|
| **GPU RTX 5080** | 27 | 419 ms | **554 ms** | 604 ms |
| CPU 16 hilos | 20 | 10.776 ms | **13.714 ms** | 13.794 ms |
| CPU 4 hilos (tipo CX32) | 5 | 45.649 ms | **46.246 ms** | 46.347 ms |
| CPU 2 hilos (tipo CX22) | 4 | 64.927 ms | **65.648 ms** | 65.764 ms |

> **CORREGIDA la columna que esta tabla tenía y que ya no se sostiene.** Llevaba un "+ los 3.076 ms
> del 3.3" con su porcentaje sobre un presupuesto de 8.000 ms, y las dos mitades han caído el mismo
> día: **el presupuesto pasó a 5.000 ms** (requisito de producto) y **los 3.076 ms eran un p50 de
> muestra pequeña y sin reordenador**. Medido después con n=20 y con el reordenador puesto, el total
> real es **p50 5.151 ms y p95 63.853 ms**
> (`docs/evidencia/2026-08-13-concurrencia.md`). Sumar un paso a una base optimista y presentarlo
> como "el 45 % del presupuesto" era exactamente la clase de número que este repo no acepta: la
> aritmética estaba bien y el sumando estaba mal. **Las cifras del paso de reordenado, que son lo
> que este documento mide, no cambian.**

**Factor 25 entre la mejor CPU y la GPU.** En la configuración que de verdad se parece a un VPS
pequeño, **el reordenado de una sola consulta tarda más de un minuto**.

El calentamiento se descarta y se reporta aparte —la primera pasada paga la reserva de buffers de
oneDNN y la resolución de kernels, un coste que en servicio se paga una vez al arrancar—: 10,9 s,
11,0 s y 13,4 s en la fila de 16 hilos, del mismo orden que las medidas, o sea que **descartarlo no
es lo que sostiene la conclusión**.

### El escalado con los hilos es SUBLINEAL, y conviene no leerlo al revés

De 16 a 4 hilos el coste se multiplica por 3,4 (no por 4) y de 4 a 2 por 1,42 (no por 2). Dos causas,
y las dos juegan **a favor** de la máquina de aquí: con menos hilos activos el procesador sube más la
frecuencia, y a 16 hilos ya se está tocando el techo de ancho de banda de memoria. **La lectura
correcta no es "con pocos hilos se defiende bien"**, es que ni siquiera dándole todos los núcleos
llega. La fila de 16 hilos ya está 1,7 veces por encima del presupuesto **ella sola**.

---

## Estos números son COTA INFERIOR, nunca estimación

Están medidos en un **Ryzen 9 9950X3D**: caché 3D apilada y AVX-512 que **un vCPU compartido de
Hetzner no tiene**. Y un vCPU compartido además pelea por el núcleo físico con otros inquilinos, lo
que ensancha la cola justo donde vive el p95. **Igualar el recuento de hilos no hace el número
trasladable**: el de un VPS real solo puede ser peor que el de esta tabla.

Por eso la decisión se toma con la fila de **2 hilos** delante y no con la mejor. Es la misma regla
que se aplicó a la dispersión del 2.2: **manda el peor número, porque es el único que no depende de
dónde se midió**.

---

## La comprobación de que el instrumento no miente: la aritmética del propio modelo

Antes de creerse un 13,7 s hay que descartar que sea un fallo del arnés. `bge-reranker-v2-m3` es
**XLM-RoBERTa-large: 568 M parámetros, 24 capas, oculto 1024, `num_labels` 1**. Una consulta de 30
pares × 640 tokens son **21,8 TFLOPs** (2·N·tokens). De ahí:

| | Tiempo | Rendimiento efectivo |
|---|---:|---:|
| CPU 16 hilos | 13,7 s | **1,6 TFLOPS** |
| GPU 5080 | 0,42 s | **52 TFLOPS** |

Las dos cifras son **exactamente lo que esas máquinas dan de sí** en fp32. O sea que lo medido es el
modelo, no el arnés: no hay un `sleep` escondido ni un lote mal formado. Es el coste real de leer
treinta fragmentos de 500 tokens con un modelo de 568 M parámetros.

---

## Tres decisiones que este número tomó, y una que canceló

### 1. `optimum[onnxruntime]` NO se instala, y el motivo generaliza

El plan original era ONNX int8 desde el principio; se invirtió para **medir fp32 primero**, porque
torch ya estaba en el entorno y la cadena de exportación y cuantización era dependencia nueva y
trabajo nuevo a tres días de la sesión.

**Y el resultado no fue el que esperaba ninguno de los dos.** No es que fp32 quepa: **es que el hueco
es tan grande que ninguna cuantización lo cierra.** La cuantización dinámica int8 da 2-3× en CPU;
13,7 s entre 3 son 4,6 s, que **ya se comen el presupuesto entero de 5.000 ms el paso solo**, sin
dejar nada para la generación — y como cota inferior, en una máquina que no es el destino. Habríamos
pagado la dependencia, el trabajo y el riesgo **para seguir sin llegar**.

> **La regla que sale de aquí, y vale para la próxima:** antes de optimizar, medir el suelo. Si el
> suelo está 25× lejos, la optimización no es la respuesta — **el cambio de sitio lo es**. Optimizar
> se justifica cuando el orden de magnitud ya es el bueno; cuando no lo es, optimizar solo consigue
> llegar tarde y con una dependencia más.

### 2. El plan B viejo estaba doblemente mal, y ahora las dos mitades están medidas

Decía *"si el p95 supera 400 ms, bajar a 12 candidatos"*. Ya se había reescrito porque **destruye el
techo de recall**: con 12 candidatos el 0,8 es inalcanzable por construcción. Medido hoy, resulta que
**tampoco arreglaba la latencia**:

| Candidatos (CPU 16 hilos) | p50 | p95 | Total | Presupuesto |
|---:|---:|---:|---:|---:|
| 30 | 10.776 ms | 13.714 ms | 16.790 ms | 210 % |
| **12 (el plan B viejo)** | 4.089 ms | **5.295 ms** | 8.371 ms | **105 %** |
| 6 (ya no es reordenar) | 2.130 ms | 2.655 ms | 5.731 ms | 72 % |

**El coste es lineal en el número de candidatos** —≈ 460 ms por candidato a 16 hilos—, así que un
presupuesto de 500 ms en CPU da para **un** candidato. Reordenar uno no es reordenar.

### 3. La salida "aceptar el p95 y declararlo" queda tachada por el propio número

El plan B la ofrecía como salida (2), con el argumento de que *en una demo local no duele*. Se
escribió imaginando 400-900 ms. **El reordenado va antes de la llamada al modelo, o sea en la ruta
del TTFT**: no son 13,7 s de total, son **13,7 s de pantalla muerta** añadidos a los 2.267 ms de hoy.
Eso deshace el encargo 2.4 entero, que existió para matar 1,6 s de pantalla en blanco.

### 4. Y en GPU aparece un efecto secundario bueno, que no se buscaba

Hoy las etapas cubren **80 ms de los 2.267** del TTFT: un **3,5 %**, o sea que enseñan trabajo real
pero anuncian el resto de la espera. Con el reordenado visible como etapa pasan a cubrir 633 ms de
2.821: un **22 %**, seis veces más. **El reordenador, en GPU, mejora lo que el 2.4 diseñó** — porque
es trabajo de verdad ocurriendo en el hueco que antes estaba vacío.

---

## Consecuencia de arquitectura: GPU o nada, y el respaldo se anuncia

Está en el [ADR 0015](../adr/0015-el-reordenador-va-en-gpu-o-no-va.md) y declarado en el 8.1, en el
README y en la Parte V. Resumen: **el reordenador va en GPU**; el VPS del 8.1 no la tiene. Y si la
GPU falta en caliente, el sistema **no cae a CPU**: salta el reordenado, sirve el orden de la fusión
y **lo dice en pantalla**.

### CORRECCIÓN DEL MISMO DÍA: lo IMPOSIBLE es solo el reordenado, no toda la tubería

La primera redacción de esta sección decía que en el VPS *"corren la léxica y el glosario y nada
más"*, porque el contenedor no lleva torch (`torch NO`, `transformers NO`, comprobado dentro). **De
que falte torch no se sigue que no quepa**, y las dos cosas se habían juntado en una sola frase:

| | Coste por consulta | ¿Cabe en 2 vCPU? |
|---|---:|---|
| **Embebedor** (~18 tokens, una pasada) | **≈0,04 TFLOPs** → **112,9 ms de p50, 125,6 de p95** a 2 hilos | **sí, de sobra: el 2,5 % de un presupuesto de 5 s** |
| **Reordenado** (30 × 640 tokens) | **21,8 TFLOPs** → 65.648 ms de p95 a 2 hilos | **no, y por tres órdenes de magnitud** |

**Así que el desplegable no es el 58,0 % de la léxica: es del orden del 82,7 % de `recall@20`** —todo
menos el reordenado— **en cuanto la imagen lleve torch CPU**. Lo que falta es una **decisión
pendiente con su coste** (~2,5 GB de imagen, ~4,3 s de carga al arrancar; la rueda solo-CPU es menor
y se mide antes de decidir), no un límite del hardware.

**Y la forma del error, que es la que hay que recordar:** *decir 58 % cuando es 82,7 % es mentir por
defecto, y mentir por defecto también es mentir.* La prudencia mal entendida —"pongo el número malo,
que así no me paso"— produce documentos igual de falsos que el optimismo, con el agravante de que
nadie los audita porque suenan humildes. La distinción operativa que queda: **"no cabe" se demuestra
con una medida; "no está empaquetado" se arregla con una decisión.** No se escriben con la misma
frase.

---

## Detalles del método, para que se pueda repetir y discutir

- **`max_length` = 640, y no es un parámetro de eficiencia.** El truncado de un cross-encoder **no es
  simétrico**: recorta el fragmento, no la pregunta. Medido el corpus (11.483 fragmentos): p50 481
  tokens, p95 509, p99 520, máximo 6.913. Con 512 se recortaría **más de la mitad** de los
  fragmentos por el final — y `oro-001` se responde justamente con la última línea del suyo. Con 640
  se truncó el **2 %** (18 de 900 pares en la corrida de GPU), contado y no supuesto.
- **El conjunto oro roto sirve aquí**, y por eso se usó: aporta 100 preguntas reales con las que
  llenar un pool de 30 candidatos. Lo que se cronometra es el paso, no el acierto.
- **Sesgo declarado a favor de la GPU:** el contador de truncados tokeniza los mismos textos justo
  antes del tramo cronometrado, así que la tokenización entra algo caliente. Son milisegundos:
  irrelevante frente a 13,7 s, y en la fila de GPU (554 ms) podría estar restando algún milisegundo.
  Se dice en vez de callarse; no cambia ninguna conclusión.
- **El embebedor corre en CPU en todas las corridas**, incluidas las de GPU, para que la GPU midiera
  solo el reordenado y no compartiera trabajo con el embebido.

## Reproducir

```bash
DATABASE_URL=... python scripts/medir_reordenado.py --dispositivo cuda --consultas 30
DATABASE_URL=... python scripts/medir_reordenado.py --hilos 2 --consultas 6
```
