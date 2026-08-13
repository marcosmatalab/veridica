# Punta a punta y concurrencia: los dos requisitos de producto, medidos

**13 de agosto de 2026.** Corridas `7` (secuencial) y `8` (concurrencia) en `corridas_eval`.
Arnés: `scripts/medir_concurrencia.py`. API local con **embebedor y reordenador los dos en GPU**
(el contenedor no lleva torch, así que la medida se hace contra `uvicorn` en Windows).
**Gasta:** cada consulta es una llamada real al proveedor.

---

## 1. El p95 de punta a punta, que hasta hoy NO EXISTÍA

Requisito de producto: **la consulta no pasa de 5 segundos**. Un tope se cumple en p95, y lo único
que había era una media de pocas corridas (los "3.076 ms" del 3.3).

| n=20 secuenciales | p50 | **p95** | máx |
|---|---:|---:|---:|
| **Total** | **5.151 ms** | **63.853 ms** | 68.743 ms |
| TTFT del alumno | 3.909 ms | 63.272 ms | 67.676 ms |

**No se cumple, y no por poco: el p95 es el 1.277 % del presupuesto. Ni siquiera el p50 cabe.**

### Y el culpable NO es nuestra tubería

En las **veinte** consultas, la etapa `reordenado` —que acumula embebido + léxica + vectorial +
glosario + fusión + reordenado— cayó entre **525 y 896 ms**. Sin una sola excepción. Toda la
dispersión está después, en la generación:

| | Consulta normal (id 21) | Atípica (id 10) | Atípica (id 17) |
|---|---:|---:|---:|
| Nuestra recuperación entera | 527 ms | 727 ms | 585 ms |
| `ttft_proveedor_ms` (primer token) | 304 ms | **317 ms** | **314 ms** |
| Tokens de salida | 183 | 767 | 252 |
| Total | **2.060 ms** | **68.339 ms** | **63.201 ms** |
| Ritmo de generación | ~105 tokens/s | **11 tokens/s** | **4 tokens/s** |

**Lo que pasó está claro en la traza y no hay que suponerlo:** el proveedor **empezó rápido** en las
dos (317 y 314 ms hasta el primer token) y luego **generó entre diez y veinticinco veces más
despacio de lo normal**. Las dos llevan además `intentos_http: 2`, o sea un transitorio previo con
una espera corta (0,206 s y 0,115 s).

**Y aquí este repo se queda sin poder afirmar la causa, así que no la afirma:** la traza contaba
*cuántos* reintentos hubo pero no **de qué código**, así que no se puede decir si aquellos dos
transitorios fueron 429 o 5xx — que son cosas distintas con respuestas distintas. **Arreglado el
mismo día**: `Llamada.codigos` guarda el código de cada transitorio y viaja a la traza como
`codigos_transitorios`. La próxima corrida ya no tendrá que adivinar. Es la misma familia del
instrumento que no mide lo que su nombre dice.

---

## 2. Concurrencia: ¿bloquea algo el bucle de eventos?

**No.** Y está comprobado por el camino que lo separa de todo lo demás: mientras **10 consultas
pesadas estaban en vuelo**, se golpeó un endpoint trivial (`/api`, que no toca base ni modelos):

| `/api` | p50 | máx |
|---|---:|---:|
| En reposo | **0,8 ms** | 6,7 ms |
| Con 10 consultas en vuelo | **1,5 ms** | 11,0 ms |

Un factor **1,9**. Si el bucle estuviera bloqueado por llamadas síncronas dentro de un manejador
`async`, `/api` se habría congelado segundos. **Está libre**, y la razón está en el código:
`/consulta` es un `def` síncrono —FastAPI lo lleva al threadpool— y `_flujo` es un generador
síncrono —Starlette lo itera con `iterate_in_threadpool`—. Nada corre en el bucle.

**Pero eso no significa que escale**, y por eso hacía falta la otra mitad:

| N a la vez | **nuestro tramo** p50 | **nuestro tramo** p95 | total p50 | total p95 | consultas/s |
|---:|---:|---:|---:|---:|---:|
| 1 | 1.001 ms | 1.001 ms | 5.505 ms | 5.505 ms | 0,18 |
| 2 | 1.545 ms | 1.725 ms | 4.306 ms | 4.678 ms | 0,42 |
| 5 | 3.205 ms | 3.262 ms | 7.999 ms | 9.535 ms | 0,52 |
| 10 | 5.252 ms | **5.659 ms** | 9.356 ms | 13.732 ms | 0,67 |

Nuestro p95 crece **×5,65 con N=10** (lineal sería ×10). Serialización **parcial**, y con nombre y
apellidos: **la GPU**. El embebedor y el reordenador son un solo modelo cada uno en una sola tarjeta,
así que las peticiones hacen cola en ella. **Eso no es un fallo: es contención legítima de un
recurso único**, y tiene otra solución que el bloqueo del bucle —que no existe—.

**La distinción importa porque las soluciones son opuestas:** si bloqueara el bucle, la respuesta
sería `asyncio.to_thread`. Como es cola de GPU, meter hilos no arregla nada —la tarjeta sigue siendo
una— y lo que sirve es **agrupar en lotes**.

---

## 3. El techo, declarado

**~1,9 consultas por segundo** en la parte nuestra: 10 consultas concurrentes salen en 5,25 s.

| Pregunta | Respuesta medida |
|---|---|
| Consultas/s sostenidas antes de que la cola crezca | **~1,9** |
| 30 alumnos a la vez: espera del último, solo en nuestra cola | **~15,8 s** |
| Alumnos simultáneos que caben en los 5 s | **~2** |

Con N=2 el total p50 es 4.306 ms y cabe; con N=5 ya son 7.999 ms. **La conjetura previa —"419 ms
serializados dan ~2,4 c/s y treinta alumnos dejan al último en ~12,5 s"— queda confirmada en el
mecanismo y era algo optimista en el número**, porque el embebedor también usa la GPU.

### ¿Ata antes la GPU o la cuota del proveedor? La GPU, y por cinco veces

Los límites, **leídos de las cabeceras de una respuesta real** y no de la documentación (que publica
los nombres pero no los números por modelo):

```
x-ratelimit-limit-requests: 600        x-ratelimit-limit-tokens: 2000000
x-ratelimit-reset-requests: 100ms      x-ratelimit-reset-tokens: 0ms
```

| Cuello | Techo |
|---|---:|
| **Nuestro reordenador en una GPU** | **~1,9 consultas/s** |
| Cuota de peticiones (600/min) | 10 consultas/s |
| Cuota de tokens (2 M/min, ~3.500 por consulta) | ~9,5 consultas/s |

**Ata el reordenador, unas cinco veces antes que la cuota.** Y corrige lo que se había dicho antes
—*"el modelo no es el cuello porque Scaleway escala del otro lado"*—: **la cuota es un techo real y
conocido**, solo que hoy queda lejos porque la GPU ata primero. El día que haya lotes o pool de GPU,
la cuota pasa a ser el siguiente cuello y **ya está el número puesto**.

---

## 4. El camino de escalada, con lo construido y lo declarado

1. **Nada bloqueante en el bucle** — **comprobado hoy** (arriba). No hacía falta cambiar nada, y
   saberlo con una medida vale más que suponerlo leyendo el código.
2. **Lotes en el reordenador: DECLARADO, NO CONSTRUIDO.** Es lo que de verdad multiplica el techo:
   hoy 10 consultas concurrentes son 10 pasadas de GPU de 30 pares cada una; agrupadas serían **una
   pasada de 300 pares**, y una GPU es mucho más eficiente con lotes grandes que con diez pequeños.
   **Disparador: más de 3 alumnos concurrentes previstos**, o el p95 de nuestro tramo pasando de
   2 s.
3. **Pool de GPU: DECLARADO, NO CONSTRUIDO.** Disparador: que los lotes no basten, o sea a partir de
   ~15-20 alumnos concurrentes.

### Dos cosas que no estaban dichas y ahora sí

- **El pool de conexiones de Postgres.** Hoy **no hay pool**: cada consulta abre y cierra su propia
  conexión con `psycopg.connect`. A la escala medida no duele —la base responde en 5 ms— pero es un
  límite sin declarar, y el `max_connections` por defecto de Postgres (100) es el techo real. Va con
  su disparador: **pool explícito cuando se construyan los lotes**, que es cuando la concurrencia
  deja de estar limitada por la GPU.
- **El límite del proveedor**, arriba, con sus dos cuotas y cuál ata primero.

---

## 5. EL VIGILANTE DE RITMO Y EL PLAZO: construidos, y lo que se ve al ponerlos

### Por qué esto era lo más urgente del proyecto

Con la tasa observada —2 de 20, un 10 %—, **una sesión de ocho preguntas tiene un 57 % de
probabilidad de comerse al menos una congelación de un minuto** delante del cliente (1 − 0,9⁸). No
es un caso raro que valga la pena declarar: es **más probable que no**.

**La clave para detectarlo estaba en la propia medida: las dos lentas arrancaron bien.** 317 y 314 ms
hasta el primer token, igual que una sana. Así que ninguna vigilancia del arranque las vería. Lo que
se hundió fue el **ritmo**, y el ritmo solo se puede mirar **mientras llega**.

Construido en `app/core/ritmo.py`: cuenta trozos sobre una **ventana móvil de 2 s**, tras una gracia
de **8 tokens**, y corta por debajo de **35 tokens/s** —un tercio del ritmo sano medido—. Umbral,
ventana y gracia **declarados SIN CALIBRAR**, igual que el 0,80 del NLI, **con la calibración
apuntada al 4.6**.

**Un fallo propio que el test cazó y que conviene no borrar.** La primera versión tenía la gracia en
**24 tokens**, y una gracia contada en tokens se convierte en una gracia contada en **segundos**
cuanto más lento va el flujo: a 4 tokens/s —el peor caso medido— son **6 segundos**, más que el
presupuesto entero. O sea que el vigilante habría llegado tarde **justo en el caso que existe para
cazar**, y a tiempo en los casos donde no hacía falta. Un verde perfectamente creíble haciendo lo
contrario de su trabajo. Con 8, ese mismo flujo se corta a los ~2,2 s, y hay test parametrizado que
lo ancla al revés: **cuanto más lento el flujo, más pronto tiene que cortar**.

**Y la asimetría que justifica inclinarse a cortar**, escrita para que nadie la "arregle" luego
subiendo la gracia: un falso positivo cuesta **~2 s** —se corta, se anuncia y se vuelve a pedir—; un
falso negativo cuesta **~60 s de pantalla congelada**. Treinta veces más. Con esa relación el punto
de equilibrio no está en el medio.

### La segunda muestra, y por qué NO contesta la pregunta de la hora

| n=20 secuenciales | Corrida 7 (13:11 UTC) | Corrida 9 (13:42 UTC) |
|---|---:|---:|
| p50 | 5.151 ms | **4.250 ms** |
| p95 | 63.853 ms | **5.485 ms** |
| máx | 68.743 ms | **5.488 ms** |

**La cola de un minuto desaparece, pero NO se puede atribuir a la hora, y decir lo contrario sería
el error del sumando otra vez.** Entre las dos corridas **cambió el instrumento**: la 9 corre ya con
el plazo puesto, así que el máximo de 5.488 ms **no es lo que tardó el proveedor, es donde cortamos
nosotros**. Comparar las dos como si midieran lo mismo mezclaría el efecto de la hora con el efecto
del arreglo.

**Lo que la corrida 9 sí dice, y es lo importante:** el mecanismo funciona. Ninguna consulta pasó de
5,5 s. La congelación de un minuto **ya no puede ocurrir**.

**Lo que queda pendiente, con su método:** para responder si la cola depende de la hora hacen falta
dos muestras **con la misma configuración** y a franjas de verdad distintas —mañana temprano y
tarde-noche, no dos tomas separadas 31 minutos—, midiendo el **ritmo de generación** de cada consulta
en vez del total, porque el total ya está recortado por diseño. El arnés lo guarda: `etapas.ritmo`
viaja en la traza de cada respuesta.

### EL RESULTADO INCÓMODO: con el plazo en 5 s, se corta el 30 % de las consultas

De las 20 de la corrida 9: **6 cortadas por plazo, 0 reintentos por ritmo.**

Y el motivo **no es el que el vigilante busca**. Las seis no iban lentas de ritmo: iban **lentas hasta
la prosa**, con TTFT de 4,6-4,8 s. La causa es el **orden del contrato**: `afirmaciones` va antes de
`respuesta_redactada`, así que el modelo escribe todas las afirmaciones **antes** del primer carácter
que el alumno ve. Una respuesta con muchas afirmaciones agota el plazo sin haber ido lenta en ningún
momento.

Cuadra con la corrida 7 sin recortar, donde **8 de 20 (40 %)** pasaban de 5 s. **Las dos corridas
dicen lo mismo: entre el 30 y el 40 % de las consultas no caben en 5 segundos**, y eso no es la cola:
es un tercio de la distribución.

**Consecuencia, que es una decisión de producto y no de ingeniería:** el requisito de 5 s, tal como
está implementado, **cuesta un tercio de las respuestas**. Las palancas no están en nuestro código
—la recuperación entera son 79 ms— sino en (a) la **longitud de la respuesta** (`max_tokens`, o
pedirle al modelo menos afirmaciones), (b) el **orden del contrato**, que el 2.2 dejó fijado a
propósito y cuya inversión adelantaría la prosa, o (c) el **modelo**. Queda declarado y sin decidir.

### Un agujero de contabilidad que apareció al cortar, y su arreglo

Las consultas cortadas salían con **`tokens_salida = 0`**: al cortar el flujo, el trozo con `usage`
del proveedor no llega nunca. **Un cero ahí no es "no costó": es "no me enteré".** El proveedor
generó esos tokens y los factura igual, así que la contabilidad del 2.6 y de la fase 6 habría tenido
un hueco silencioso **del 30 %**, y además sesgado: justo en las consultas que peor van, o sea
tirando el coste medio hacia abajo.

Arreglado: el uso se **estima** por longitud del JSON recibido (~3,6 caracteres por token, de las
corridas reales) y **se marca como estimado** en la traza. Un número aproximado y uno inventado no
son lo mismo, y un número aproximado y uno medido, tampoco.

---

## 6. Reproducir

```bash
DATABASE_URL=... python scripts/medir_concurrencia.py --api http://127.0.0.1:8001 --n 20
DATABASE_URL=... python scripts/medir_concurrencia.py --api http://127.0.0.1:8001 --concurrencia 1,2,5,10
```

**Aviso del método, declarado:** el proveedor es la fuente de varianza dominante y las tandas de
concurrencia son de una sola pasada por nivel (N consultas por nivel, no N×repeticiones). Los
percentiles del **total** en esa tabla son por tanto indicativos; los de **nuestro tramo** son
estables y son los que sostienen las conclusiones de serialización y techo. Repetir las tandas
varias veces es trabajo del 6.4, que es donde la guía pone la medida de carga con su método.
