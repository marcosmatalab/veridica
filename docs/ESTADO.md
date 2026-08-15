# Estado del proyecto

> **Qué es este fichero.** La respuesta a *"¿cómo está el proyecto ahora mismo?"*, leíble en dos
> minutos. **Se deriva del código, no de la memoria ni de la guía**, y se regenera al cerrar cada
> bloque de trabajo. Si algo aquí contradice al código, gana el código y este fichero está roto.
>
> **Un encargo está CONSTRUIDO cuando hay una función que lo hace y un test que la cubre.** Aparecer
> en la guía, tener una etiqueta o tener una columna en la base **no** cuenta: una degradación
> declarada que nadie implementó es más peligrosa que una no declarada, porque el documento crea una
> confianza que el código no ha ganado.

- **HEAD:** `267a86e` · **rama:** `prueba-de-jueces` · **¿en `main`?** **NO** — 20 commits por
  delante. Quien clone el repo hoy no ve el trabajo del 14 y el 15 de agosto.
- **Puertas, la última vez que se corrieron enteras:** `ruff` 0 · `pytest` 0 (**606** tests) ·
  `verificar_manifiesto` 0 (2.414 entradas) · `verificar_oro` 0 (94 pares).
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
| Guarda del 4.4 | 200 car. / 1.000 díg. / 30 díg. de argumento | `verificador_calculo` | **Medida**, no solo puesta: peor caso admitido 1,7 ms |
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

> ⚠ **Todo lo de esta sección se midió el 13/08 CON EL REORDENADOR PUESTO**, que es una
> configuración que **ya no corre**: el 3.4 quedó descartado el 14/08. Los números siguen siendo
> ciertos de aquella configuración y **no describen lo que se sirve hoy**. Re-medir sin reordenador
> está pendiente y es lo primero de §6.

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

**Bloquea la sesión del lunes**

1. **La pantalla del alumno**: estado vacío con preguntas sugeridas, la casilla de desarrollo fuera
   de la vista de producto, y los ajustes compactados a barra al empezar la conversación.
2. **`main` no tiene el trabajo de los dos últimos días.** Quien abra el repo ve la fase 3.
3. **La API no tiene autenticación** y el túnel la publica en internet con una clave de pago detrás.

**Deuda de medida — tenemos la vara y no hemos medido**

4. **`fuera_de_temario`, `premisas_falsas` y `fuga_de_solucion` llevan días congelados con su sha y
   sin una sola corrida.** Los conjuntos existen, el arnés existe, y el número no.
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
