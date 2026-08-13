# ADR 0015: el reordenador va en GPU o no va, y la falta de GPU se anuncia

- **Fecha:** 13 de agosto de 2026
- **Encargo:** 3.4 (reordenado)
- **Estado:** aceptada
- **Evidencia:** [`docs/evidencia/2026-08-13-reordenado.md`](../evidencia/2026-08-13-reordenado.md), corridas `4`, `5` y `6` de `corridas_eval`

## Contexto

La guía declaraba el reordenador como *"BGE reranker v2-m3 cuantizado (ONNX int8) en **la CPU del
VPS**"*. Medido antes de construir nada encima, el paso de reordenado sobre 30 candidatos cuesta:

| Dónde (30 candidatos) | p50 | p95 | Contra el presupuesto de **5.000 ms** |
|---|---:|---:|---|
| **GPU RTX 5080** | 419 ms | **554 ms** | **11 %**: cabe con sitio para el resto |
| CPU 16 hilos | 10.776 ms | 13.714 ms | 274 %: se lo come entero, dos veces y media |
| CPU 4 hilos | 45.649 ms | 46.246 ms | 925 % |
| CPU 2 hilos | 64.927 ms | 65.648 ms | **1.313 %** |

Un factor **25**. Y las filas de CPU son **cota inferior**: medidas en un Ryzen 9 9950X3D con caché
3D y AVX-512 que un vCPU compartido no tiene.

**No es un fallo de configuración**, y se comprobó antes de decidir: el modelo es XLM-RoBERTa-large,
568 M parámetros, y una consulta son 21,8 TFLOPs. Eso da 1,6 TFLOPS efectivos en CPU y 52 en GPU,
que es lo que esas máquinas dan de sí en fp32. El coste medido **es el modelo**.

## Decisión

**El reordenador corre en GPU. En la ruta de petición no se reordena en CPU jamás.** Lo impone el
código, no un comentario: `app/core/reordenador.py::para_servicio()` levanta `SinGPU` si no hay CUDA
y **nunca devuelve un reordenador de CPU**, con test que lo comprueba.

**Y cuando no hay GPU, el respaldo no es reordenar más despacio: es NO reordenar.** `/consulta` sirve
el orden de la fusión y **emite una etapa `sin_reordenar`** que lo dice en pantalla. `GET /salud`
trae una sonda `reordenador` que declara cuál de los dos modos está activo, y mirarla entra en el
ritual de arranque del 8.4.

## Por qué la salida "aceptar el p95" no era una salida

El plan B ofrecía *aceptar el p95 y declararlo, que en una demo local no duele*. Se escribió
imaginando 400-900 ms. **El reordenado va antes de la llamada al modelo, o sea en la ruta del TTFT:**
no son 13,7 s de total, son **13,7 s de pantalla muerta** sumados a los 2.267 ms de hoy. El encargo
2.4 existió para matar 1,6 segundos de pantalla en blanco; esto los multiplicaría por nueve.

Y la otra salida vieja —bajar a 12 candidatos— está medida y **tampoco cabía**: 5.295 ms de p95, el
105 % del presupuesto, además de destruir el techo de recall que subir a 30 acababa de comprar. El
coste es lineal en candidatos (≈460 ms cada uno en CPU), así que un presupuesto de 500 ms daría para
**un** candidato, y reordenar uno no es reordenar.

## Trade-off, y es real: una divergencia entre lo que se enseña y lo que se despliega

**La máquina de la demo tiene GPU; el VPS del 8.1 no.** Así que el sistema desplegado no corre la
tubería completa. Es un coste de verdad y se paga con los ojos abiertos, declarándolo en tres sitios
—el 8.1, el README y la Parte V— en vez de descubrirlo el día del cierre.

**Con una distinción que este ADR corrigió el mismo día y que hay que mantener separada: lo
IMPOSIBLE allí es SOLO el reordenado.** El contenedor tampoco lleva torch hoy (`torch NO`,
`transformers NO`, comprobado dentro), pero eso es otra cosa: embeber una consulta son **0,04
TFLOPs** y cuesta **112,9 ms de p50 a 2 hilos**, o sea que cabe de sobra. Reordenar son **21,8
TFLOPs** y no cabe en ninguna CPU. Por tanto **el VPS puede servir todo menos el reordenado —del
orden del 82,7 % de `recall@20`— en cuanto se empaquete torch CPU**, que es una decisión pendiente
con su coste (~2,5 GB de imagen, ~4,3 s de carga) y no un límite del hardware. Decir que allí solo
cabe la léxica sería mentir por defecto.

Esto **no es una excepción al principio 1, es el principio 1 funcionando**: la inferencia vive detrás
de una interfaz y el hardware es donde se la pone; para el generador eso ya está construido con
`INFERENCIA_BASE_URL`, y el reordenador es la misma figura un piso más abajo. Lo que el principio no
autoriza —y por eso hay código y test— es que la falta de hardware se resuelva sola degradando en
silencio.

## Alternativas descartadas, con su motivo

1. **ONNX int8 en CPU.** Descartada **por el tamaño del hueco, no por pereza**: la cuantización
   dinámica da 2-3× y haría falta 25×. 13,7 s entre 3 son 4,6 s, el 96 % del presupuesto **como cota
   inferior**. Se habría pagado una dependencia nueva y su trabajo para seguir sin llegar. La regla
   que queda: **antes de optimizar, medir el suelo; si el suelo está 25× lejos, la respuesta no es
   optimizar, es cambiar de sitio.**
2. **Un cross-encoder más pequeño.** `bge-reranker-base` es ~4× más barato: 3,4 s en la mejor CPU,
   todavía fuera, y con calidad peor sin medir. No compra nada.
3. **Reordenar menos candidatos.** Prohibido por el 3.4 y ahora también por la latencia (arriba).
4. **Caer a CPU cuando falte la GPU.** Es la alternativa que este ADR existe para cerrar: cambiaría
   "ordena peor" por "un minuto de pantalla muerta". Degradar tiene que doler menos que el fallo.

## Lo que este ADR NO decide

**Si el reordenador merece la divergencia.** Eso lo decide su calidad, que **no está medida** porque
el conjunto oro está en reconstrucción (3.0). El criterio ya está escrito en el 3.4, antes de tener
el número, y **es una FÓRMULA y no una cifra**:

```
listón = fusión_sola + (techo_del_pool − fusión_sola) / 2
```

**El reordenador se queda si cierra más de la mitad del hueco entre la fusión sola y el techo del
pool.** Con los valores provisionales de hoy (72,8 % y 88,9 %) eso da **80,9 %**, pero **los tres van
a cambiar con el conjunto reconstruido**: cuando el listón se recalcule parecerá que se mueve la
portería, y no se mueve — la regla es la misma y se escribió antes de medir. Escribir el criterio
como fórmula es lo que le permite sobrevivir a que se corrija el instrumento; escrito como cifra,
quien lo recalcula acaba eligiendo sin querer la cifra que le conviene.

Si cierra menos, la configuración honesta es fusión sin reordenar, con su número declarado y el
objetivo declarado como no alcanzado.
