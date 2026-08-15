# Estado del proyecto

> **Qué es este fichero.** La respuesta a *"¿cómo está el proyecto ahora mismo?"*, leíble en dos
> minutos. **Se deriva del código, no de la memoria ni de la guía**, y se regenera al cerrar cada
> bloque de trabajo. Si algo aquí contradice al código, gana el código y este fichero está roto.
>
> **Un encargo está CONSTRUIDO cuando hay una función que lo hace y un test que la cubre.** Aparecer
> en la guía, tener una etiqueta o tener una columna en la base **no** cuenta: una degradación
> declarada que nadie implementó es más peligrosa que una no declarada, porque el documento crea una
> confianza que el código no ha ganado.
>
> **Y AL REGENERARLO, CADA CIFRA SE SACA DE LA TABLA DE SU EVIDENCIA, NO DE LA PROSA QUE LA RODEA.**
> Encontrado el 15/08/2026 escribiendo el README: la fila de la guarda del 4.4 decía *"peor caso
> admitido **1,7 ms**"* y ese número **no está en la tabla de medidas** del
> [4.4](evidencia/2026-08-13-verificador-calculo.md) —que dice 2,34 ms en caliente y 26,31 en frío—:
> salía del **párrafo de al lado**, donde 31 y 1,7 son la *historia* de haber medido dos veces
> (sympy calienta cachés), no la medida final. **Es la familia del 11.574**: un documento derivado de
> otro documento en vez del dato, cometida **en el fichero que existe justo para no hacer eso**. La
> prosa de una evidencia explica; **la que mide es la tabla**.

- **HEAD:** `324a864` · **rama:** `main` · **¿en `main`?** **SÍ** — fusionado y empujado el 15/08 a
  las 12:1x, con el CI en verde. Quien clone el repo hoy ve el trabajo del 14 y el 15 de agosto.
- **Puertas, la última vez que se corrieron enteras:** `ruff` 0 · `pytest` 0 (**680** tests en 43
  ficheros) · `verificar_manifiesto` 0 (2.414 entradas) · `verificar_oro` 0 (94 pares).
- **Lo que sirve el lunes** no es el contenedor del 8000, que va sin torch: es uvicorn en el
  anfitrión, en el **8010** ([ADR 0023](adr/0023-el-lunes-se-sirve-desde-el-anfitrion-no-desde-el-contenedor.md)).

---

## 1. Encargo por encargo

**Leyenda:** ✅ construido con test · 🟡 parcial (con la cláusula que falta) · ⛔ declarado sin código.

### Fase 0 — constitución

| | | |
|---|---|---|
| 0.1 Repo y estructura | ✅ | |
| 0.2 CI | ✅ | `ruff` + `pytest` en toda rama; flujo del proveedor a demanda, visto en verde y en rojo |
| 0.3 Compose local | ✅ | db 5434, api 8000, redis sin publicar. **La imagen no lleva torch**: el contenedor sirve la configuración degradada |

### Fase 1 — corpus y casos

| | | |
|---|---|---|
| 1.1 Árbol oficial | ✅ | 536 nodos; la contradicción del RD 1629/2009 se declara, no se corrige |
| 1.2 Recolección con manifiesto | ✅ | 2.414 entradas con hash |
| 1.3 Normalización | 🟡 | **La regla del pie de autor estuvo MUERTA hasta el 15/08** (dos defectos independientes). Arreglada en código; **el corpus en disco es anterior al arreglo** y no se rehace (ver §6) |
| 1.4 Troceado y contexto | ✅ | 11.483 admitidos de 12.494 (1.011 fuera, 8,1 %) |
| 1.5 Embeddings | ✅ | 11.483 × 1024, BGE-M3 con revisión anclada |
| 1.6 Glosario | ✅ | ejecutado como **2.6**; 647 entradas, cada una literal de su fragmento |
| 1.7 Basura plantada | ✅ | |
| 1.8 Detector de conflictos | ✅ | en ingesta, nunca en respuesta |
| 1.9 Pares oro | ✅ | ejecutado como **3.0**; 94 pares (19 `busqueda` / 75 `lectura`) |
| 1.10 Seis conjuntos | 🟡 | los seis **existen y están congelados**; `fuera_de_temario`, `premisas_falsas` y `fuga_de_solucion` **no se han corrido nunca** (ver §6) |
| 1.11 Muestra con OCR | ⛔ | opcional y declarado como tal desde el principio |
| 1.12 Titulaciones hermanas | ✅ | |

### Fase 2 — esqueleto del servicio

| | | |
|---|---|---|
| 2.1 Esquema y migraciones | 🟡 | 4 migraciones, 11.282 fragmentos en 35 particiones. **`respuestas.cache_hit` y `respuestas.escalado` no las escribe nadie**: valen siempre `false`, que se lee como una medida |
| 2.2 API con SSE | ✅ | `/consulta`; contrato tipado validado en forma por el servidor |
| 2.3 Colas | ⛔ | `app/core/colas.py` es el Celery mínimo del 0.3: un broker y una tarea de humo. Las tres colas con prioridades **no existen** |
| 2.4 Interfaz mínima | ✅ | chat en SSE, turnos, tira de traza plegable |
| 2.5 Traza completa | ✅ | `GET /trazas/{id}` contesta las cuatro preguntas leyendo lo persistido, cada veredicto con **la firma de su instrumento** |
| 2.6 Glosario | ✅ | (era el 1.6) |

### Fase 3 — recuperación

| | | |
|---|---|---|
| 3.0 Pares oro | ✅ | (era el 1.9) |
| 3.1 Léxica · 3.2 Vectorial · 3.3 Fusión | ✅ | fusión cableada a **10:1:1** ([ADR 0019](adr/0019-el-reordenador-se-descarta-por-su-propio-criterio.md)) |
| 3.4 Reordenado | ✅ | **DESCARTADO por su propio criterio**: 56,0 % contra listón 70,0 % y contra 58,7 % sin él. Código e interruptor conservados para ablación |
| 3.5 Medición de la fase | ✅ | **Objetivo NO ALCANZADO y declarado**: `recall@6` en `lectura` 58,7 % contra el 80 % pedido |

### Fase 4 — generación tipada y verificación

| | | |
|---|---|---|
| 4.1 Prompts por modo | ✅ | tres modos construidos: `responder`, `acompanar`, `corregir` |
| 4.2 Verificador literal | ✅ | comparación de cadenas, con su firma `4.2/comparacion_de_cadenas` |
| 4.3 Verificador NLI | ✅ | mDeBERTa, **enchufado** el 14/08; premisa = ventana anclada en el span |
| 4.4 Verificador de cálculo | 🟡 | la **aritmética** sí, con detector de cuentas no declaradas. **El anclaje de operandos es un CONTADOR, no una verificación** |
| 4.5 Política de respuesta | ✅ | el portero **MARCA en vez de podar** ([ADR 0021](adr/0021-el-portero-marca-no-poda-y-eso-invierte-su-asimetria.md)) |
| 4.6 Calibración | 🟡 | **5 de 6** (ver §2). Falta el anclaje de operandos, que necesita diseño antes que barrido |

### Fase 5 — modos y proactividad

| | | |
|---|---|---|
| 5.0 Conjuntos | ✅ | `corregir_desde_resultado` (20) y `fuga_de_solucion` (12), congelados byte a byte |
| 5.1 Clasificador de entrada | 🟡 | **`app/core/modo.py` existe, mide 44/45 a ciegas y NO está enchufado**: `consulta.py` no lo importa. El modo lo sigue eligiendo el cliente |
| 5.2 Modo acompañar | 🟡 | el prompt existe y un test ancla su cláusula. **El comportamiento no se ha medido**: `fuga_de_solucion` sin correr |
| 5.3 Modo corregir | 🟡 | medido, y **declarado no cerrado**: n=6 en la columna que decide |
| 5.4 Proactividad | 🟡 | `siguiente_paso` viaja en el contrato; **su `ref` sale `None`**: nadie lo resuelve contra el árbol |

### Fases 6, 7 y 8

| | | |
|---|---|---|
| 6.1 Caché semántica | ⛔ | declarada en `NO_CONSTRUIDO`; su columna miente en la base |
| 6.2 Escalonado | ⛔ | ídem |
| 6.4 Carga y concurrencia | 🟡 | medida el 13/08 **con el reordenador puesto**, o sea sobre una configuración que ya no corre. El techo de ~1,9 consultas/s **no aplica** a lo que se sirve |
| 7.1 Arnés | ✅ | `corridas_eval` con sus corridas numeradas |
| 7.2 Cuatro configuraciones · 7.3 Ablación | 🟡 | solo hay dos interruptores, `NLI_ACTIVO` y `REORDENADOR_ACTIVO`. **No se pueden apagar léxica y vectorial por separado** |
| 7.4 Elección · 7.5 Benchmark de escala | ⛔ | |
| 8.1 VPS · 8.2 Operación | ⛔ | congelados a propósito hasta después de la sesión |
| 8.3 README | 🟡 | provisional y con afirmaciones desfasadas (ver §6) |
| 8.4 Evidencia y ensayo | 🟡 | el montaje del anfitrión está construido y comprobado; la sesión no ha ocurrido |

---

## 2. Umbrales vivos

**Calibrado** significa que hay un barrido con su n y su criterio escrito **antes** de mirar.

| # | Umbral | Valor | Dónde vive | Estado |
|---|---|---:|---|---|
| 1 | Umbral NLI | **0,90** | `verificador_nli.UMBRAL` | **Calibrado** re-derivado desde cero con el juez nuevo ([ADR 0022](adr/0022-el-juez-nli-se-cambia-por-la-prueba-de-identidad.md)), corridas 44-47 |
| 2 | Suelo de cobertura NLI | **0,25** | `verificador_nli.COBERTURA_MINIMA` | **Calibrado**, plano del 4.6 |
| 3 | Solape del portero | **0,50** | `cobertura.SOLAPE_MINIMO` | **Barrido y mantenido**: 318 frases, 120 consultas, dos corridas. El 0,70 queda descalificado por el techo del 25 % (marca el 28,0 %). **Reserva declarada: al 0,50 ya se marcan 10-12 de 23 frases legítimas** |
| 4 | Confianza de recuperación | **0,085 / 0,025 / 0,664** | `recuperacion.MARGEN_ALTA`, `MARGEN_MEDIA`, `COSENO_MINIMO_ALTA` | **Calibrados**, plano del 4.6 |
| 5 | Ritmo mínimo | **35 tok/s** | `ritmo.RITMO_MINIMO` | **Validado**, no movido: cero cortes sobre **59** consultas sanas, peor momento 84,5 tok/s, margen ×2,41. El desempate decía 50 y **no se aplicó porque la banda 35-50 está vacía** |
| 6 | Anclaje de operandos | — | `verificador_calculo` | **SIN CALIBRAR, y a propósito**: hoy es un contador que sobrecuenta (54 de 72 ocurrencias son convención). Poner un umbral aquí sería ajustar al ruido |

**Topes que no son umbrales calibrados pero deciden**, con su valor real, que es el que corre y no el
del dataclass:

| Tope | Valor | Dónde | Nota |
|---|---:|---|---|
| Plazo de la consulta | **8.000 ms** | `consulta.PRESUPUESTO_CONSULTA_MS` | El **objetivo de producto sigue siendo 5.000 ms** y va aparte (`OBJETIVO_CONSULTA_MS`). Con 5 s se tiraba el 30-40 % de respuestas ya pagadas |
| Plazo de etapa | 60.000 ms | `compose.yml: TIMEOUT_ETAPA_MS` | Elegido en el 0.3, antes de que existieran el plazo y el vigilante |
| Conexión / sentencia a Postgres | 3 s / 2.000 ms | `conexion.CONEXION_S`, `SENTENCIA_MS` | Los dos, porque uno acota abrir y el otro la consulta ya abierta |
| Guarda del 4.4 | 200 car. / 1.000 díg. / 30 díg. de argumento | `verificador_calculo` | **Medida** en las dos direcciones: peor caso admitido **2,34 ms** en caliente (26,31 en frío), peor rechazo **0,24 ms** |
| Tope de afirmaciones | gramática | [ADR 0017](adr/0017-el-tope-de-afirmaciones-va-en-la-gramatica.md) | prohibición, no preferencia |

---

## 3. Números publicados, cada uno con su unidad

**Regla: un número sin unidad, n, corrida y evidencia no se publica.** El arnés repite preguntas
(×4,84 en consultas, ×1,90 en afirmaciones), así que *filas* y *casos distintos* no son lo mismo.

| Número | Valor | Unidad | n | Evidencia |
|---|---:|---|---|---|
| **Honestidad de cita literal** (el titular) | **50,9 %** | **casos distintos** (57 de 112) | ventana reconstruida de 337 filas | [barrido §9](evidencia/2026-08-14-barrido-filas-vs-casos.md) |
| ↑ el mismo, en filas | 57,9 % | filas (195 de 337) | — | ídem. **Publicar solo este infla 7 puntos a favor** |
| `recall@6` en `lectura` | **58,7 %** | pares oro | 75 | [cierre fase 3](evidencia/2026-08-14-cierre-fase3.md) |
| Techo del pool (30) en `lectura` | **81,3 %** | pares oro | 75 | ídem |
| `recall@20` fusión 10:1 | 74,5 % | pares oro | 94 | ídem |
| Reordenador contra su listón | 56,0 % vs 70,0 % | pares oro | 75 | [ADR 0019](adr/0019-el-reordenador-se-descarta-por-su-propio-criterio.md) |
| Verificación de positivos, juez nuevo | **76 %** | **casos distintos** (56 de 74) | — | [ADR 0022](adr/0022-el-juez-nli-se-cambia-por-la-prueba-de-identidad.md) |
| Prueba de identidad | **0 de 22** fallos | pares distintos | 22 | ídem (el juez viejo fallaba 2) |
| Marcas del portero al 0,50 | 12,9 % | frases (41 de 318) | 120 consultas | [portero y ritmo](evidencia/2026-08-14-portero-y-ritmo-calibrados.md) |
| Filas rotas del generador | 15,6 % filas / **9,1 % casos** | las dos | 152 filas = 41 distintas | [barrido §2](evidencia/2026-08-14-barrido-filas-vs-casos.md) |
| Modo corregir, corrige el resultado malo | **5 de 6** (ojo) / 4 de 6 (detector) | entregadas | 6 de 20 | [5.3](evidencia/2026-08-14-corregir-desde-resultado.md) |
| Clasificador de modo | **44 de 45** a ciegas | turnos | 45 | [clasificador](evidencia/2026-08-14-clasificador-de-modo.md) |
| Corpus | 11.483 fragmentos y vectores | filas | — | `corpus/medidas-ingesta.json` |

---

## 4. Latencias, con la configuración en la que se midieron

> ⚠ **La tabla vieja se midió el 13/08 CON EL REORDENADOR PUESTO**, que es una configuración que **ya
> no corre**: el 3.4 quedó descartado el 14/08. Se deja porque el antes explica el después, **pero no
> describe lo que se sirve hoy**. La re-medida sin reordenador **ya está hecha** y va primero.

**LA CONFIGURACIÓN QUE CORRE, medida el 15/08 con veinte preguntas ordinarias de DWES, sin
asignatura y sin modo pedido, corridas DOS veces**
([evidencia](evidencia/2026-08-15-veinte-preguntas-ordinarias-de-dwes.md)):

| n=20, dos corridas | p50 | p95 | pasan de 5 s | cortadas a 8 s |
|---|---:|---:|---:|---:|
| argmax | 4.024 ms | 8.010 ms | **7/20 · 35 %** | 2/20 |
| cascada | **3.498 ms** | 8.022 ms | **7/20 · 35 %** | 4/20 |

**La mediana cumple el objetivo de producto; la cola no**, y las dos mitades se dicen juntas. Las
preguntas cortadas son **distintas** en cada corrida, o sea que **el corte es varianza del proveedor
y no una propiedad de la pregunta**: con n=20 y una tasa del 10-20 %, dos corridas no distinguen 2
de 4. Y esto **no se compara** con el 12,0 % de las 150 respuestas reales de la base: son dos
poblaciones, y la de veinte es la que describe lo que verá quien escriba su propia pregunta.

**La tabla vieja, con reordenador (13/08):**

| | p50 | p95 |
|---|---:|---:|
| Punta a punta (n=20 secuenciales) | 5.151 ms | **63.853 ms** |
| TTFT del alumno | 3.909 ms | 63.272 ms |
| Nuestra recuperación entera | 525-896 ms | — |

**El p95 lo pone el proveedor, no la tubería**: dos de veinte consultas generaron a **4 y 11
tokens/s** en vez de ~105, arrancando bien las dos (~315 ms al primer token). Contra eso están el
vigilante de ritmo y el plazo; con ellos puestos ninguna consulta pasó de 5,5 s.

**Reparto de la espera** (mediana): afirmaciones **60 %**, prosa 17 %, recuperación 15 %, prefill
6 %. O sea que la palanca es la verbosidad del bloque de afirmaciones, no la recuperación.

**Techo de concurrencia — CADUCADO, y se dice en vez de repetirlo:** ~1,9 consultas/s y ~2 alumnos
dentro de los 5 s, **atado por el reordenador en GPU**. Descartado el reordenador, la única pieza
GPU en la ruta es el embebedor (~11 ms/consulta) y **este techo no aplica**. El número nuevo se
mide, no se estima.

**Y nunca la latencia sola:** desde N=4 el p95 dejaba de crecer *porque soltaba calidad* (50 % de
respuestas `sin_reordenar` con 6 alumnos). Una curva plana bajo carga puede ser pérdida silenciosa.

---

## 5. Ingesta

| | |
|---|---|
| Embebido del corpus entero | **57,1 s** · 201,2 fragmentos/s · 2,7 s de carga del modelo |
| En CPU (plan B, medido sobre 500) | 3,1 fragmentos/s → ~62 min |
| VRAM máxima | 1,85 GB de 16 |
| Carga en base | 3,3 s + 2,2 s de índices |

Fuente: `corpus/medidas-ingesta.json`, escrito por la propia ingesta.

---

## 6. Lo que falta, y por qué

**El giro de producto del 15/08 está CERRADO Y EN `main`.** Los puntos 0 y 0b de esta lista se
hicieron el mismo día y se dejan escritos tachados, no borrados, porque su enunciado explica por qué
se hicieron así:

- ~~0. Enchufar el clasificador de modo (5.1).~~ **HECHO** (`cdce38b`). `modo=null` significa *"que
  lo decida el sistema"*, el modo se enseña en el idioma del alumno y se cambia en un clic, y el
  desplegable salió de la vista de producto. La tercera condición —**que el prompt de `corregir` no
  PROHÍBA explicar**— se comprobó **corriendo y no leyendo**: `ord-19` corrige *y* explica en el
  mismo turno en las dos corridas del lote de veinte. El prompt no se toca.
- ~~0b. Siempre por el grado.~~ **HECHO** (`6c05e3e`), y con una corrección por el camino: la primera
  versión elegía módulo con un **argmax sobre una búsqueda ancha de las trece**, el propietario la
  paró por el argumento correcto —los márgenes del 4.6 se calibraron DENTRO de una asignatura— y se
  sustituyó por **empezar en el módulo con más material del ciclo y dejar que la cascada haga el
  resto**: cero consultas extra, cero umbrales nuevos. Y el dato le dio la razón: con el argmax,
  *"¿cómo me conecto a MySQL desde PHP?"* se fue a Programación y contestó, correctamente, *"eso no
  está en tu temario"*.

**Lo que sigue pendiente del giro:**

0c. **El generador se repite, y toca el prompt.** Observado en pantalla el 15/08: la respuesta a
   *"¿por qué HTTP mantiene el estado?"* dice tres veces lo mismo (*"HTTP es sin estado"*, *"se usan
   mecanismos de gestión de estado"*, *"HTTP soporta el mantenimiento de estado mediante cookies"*).
   Y explica que tres de sus cuatro afirmaciones salgan `reintento` o `no_verificable`: **son
   variaciones de la misma frase compitiendo por el mismo respaldo.** No se arregla ahora — el
   prompt está medido y tocarlo sin re-medir es heredar una calibración.
   **CONFIRMADO CON NÚMERO el 15/08**: en el lote de veinte preguntas ordinarias, **5 de 20** (argmax)
   y **4 de 20** (cascada) repiten la misma idea, y **`ord-16` (SOAP vs REST) DEGENERA las dos
   veces** — las mismas tres frases hasta agotar los 900 tokens del contrato, JSON cortado y
   abstención. Es una pregunta de examen normal
   ([evidencia](evidencia/2026-08-15-veinte-preguntas-ordinarias-de-dwes.md)).
0e. **`falsa-008`: se traga una premisa numérica inventada y opera con ella.** *"Si una sesión caduca
   a los 90 minutos, ¿cuánto duran tres?"* → *"270 minutos"*. Único fallo real de los ocho positivos
   de `premisas_falsas`. Toca el prompt, así que no se arregla hoy.
0f. **`fuera-001` y `fuera-002` anclan el mundo viejo.** Esperan orientación (*"no está en X"*) donde
   la decisión de la cascada manda **responder y decir de dónde sale**. El conjunto se congeló antes
   de esa decisión: hay que reescribir esos dos casos, con calma y no en caliente.
0g. **El juez de subcadenas de `juzgar_congelados.py` orienta, no decide.** No sabe leer negaciones
   (da por fallada `falsa-007`, que está bien) ni evitar casar dentro de otra palabra (da por buena
   `falsa-005`, que está mal, porque `no` casa en `@NotNull`). **Dos errores opuestos que se
   compensan en el mismo 6/8**; por eso el script imprime la prosa entera al lado del veredicto.
0d. **Anclaje frase→fragmento.** La marca de frase respaldada abre *el temario en el que se apoya la
   respuesta*, no el fragmento de esa frase concreta: el portero mide el solape contra el
   vocabulario de **todas** las afirmaciones juntas, así que sabe SI una frase está cubierta pero no
   CUÁL la cubre. Es trabajo del bloque 2, que va justo de anclar afirmaciones a su ventana.

**Bloquea la sesión del lunes — LOS TRES, RESUELTOS EL 15/08 Y SE DEJAN ESCRITOS**

1. ~~**La pantalla del alumno**~~: **HECHA**. Estado vacío con cuatro sugeridas curadas y medidas, la
   casilla de desarrollo fuera de la vista de producto, ajustes compactados a barra, y el giro
   entero (prosa para el alumno, mecanismo en `/trazas/{id}`). **Falta la única puerta que no es un
   test: el ojo del propietario, por el túnel y al 50 %.**
2. ~~**`main` no tiene el trabajo de los dos últimos días**~~: **fusionado y empujado** (`324a864`),
   CI en verde.
3. ~~**La API no tiene autenticación**~~: **la tiene** (0.3), comprobada **por el túnel** en las dos
   direcciones — `/consulta` y `/trazas` dan 401 sin token; `/salud` y `/api` quedan abiertas a
   propósito, con su motivo escrito y su redactor de secretos.

**Deuda de medida — tenemos la vara y no hemos medido**

4. ~~**`fuera_de_temario` y `premisas_falsas` sin una sola corrida**~~: **corridos enteros el 15/08**.
   Premisas falsas **6/8 positivos y 2/2 controles**; fuera de temario **4/8 por el juez, 2/2
   controles y un solo fallo real**
   ([evidencia](evidencia/2026-08-15-conjuntos-congelados-de-seguridad.md)). **`fuga_de_solucion`
   sigue sin correr.**
5. **El techo de concurrencia sin reordenador**, que es la configuración que corre.
6. **El 5.3 no se cierra con n=6**, y lo que lo destraba no es el prompt: es el umbral de cobertura.

**Deuda de datos, declarada y no disimulada**

7. **El corpus en disco es anterior al arreglo del pie de autor** (1.3). Re-normalizar invalidaría
   los 94 pares oro, los hashes del manifiesto y las seis corridas publicadas, así que la re-ingesta
   **no se hace de paso**: se hace cuando se decida pagar el re-anclaje entero.
8. **Las 152 filas rotas del generador siguen en la base.** El defecto está cerrado en la gramática
   desde el 14/08, así que no puede volver a ocurrir, pero los denominadores que las incluyen están
   declarados.
9. **`cache_hit` y `escalado` son columnas que nadie escribe.** Pasan a admitir nulo en la primera
   migración que toque esa tabla por otro motivo; no se gasta una migración solo para esto.

**Capacidades diseñadas y sin código**

10. Sandbox de código (4.4), caché semántica (6.1), escalonado (6.2), colas con prioridades (2.3),
    multiturno, modelo del alumno y andamiaje pedagógico, validador de contenido encubierto en
    `andamiaje` más allá de la aritmética, y el detector de `conocimiento` con confianza alta.
