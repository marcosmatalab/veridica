# Veridica

Un profesor por asignatura sobre temario real que solo afirma lo que puede sostener: cita literal
comprobada carácter a carácter, paráfrasis verificada contra el fragmento fuente, cálculo recalculado
y silencio honesto cuando la respuesta no está en el material. La tesis del proyecto: **la honestidad
del sistema no depende de la brillantez del modelo, depende de la capa de verificación.**

> **README provisional.** El README definitivo, con los números medidos, la configuración elegida y
> la sección "Escala", lo produce el **encargo 8.3**. Hasta entonces este fichero solo declara el
> estado real del repo. Nada de lo que aquí no aparezca como construido lo está.

## Estado (13 de agosto de 2026)

**Fases 0, 1 y 2 cerradas y en `main`.** Hay corpus ingerido, troceado, embebido y cargado en
Postgres; contrato de generación tipada viajando de punta a punta contra Scaleway; interfaz mínima
con los tipos de afirmación separados; y glosario extraído y validado. **No hay todavía**
verificación (fase 4) ni métricas de respuesta: cada afirmación viaja con `veredicto:
"sin_verificar"`, que es literalmente lo que es.

| Qué | Dónde | Estado |
|---|---|---|
| Playbook y fuente de verdad | [guia-definitiva.md](guia-definitiva.md) | escrito |
| Reglas de trabajo | [CLAUDE.md](CLAUDE.md) | escritas |
| Corpus de las tres titulaciones (DAW, DAM, ASIR) | `corpus/` (fuera de git) | descargado, normalizado y en manifiesto |
| Manifiesto del corpus | [corpus/manifiesto.jsonl](corpus/manifiesto.jsonl) | **2.414 entradas**; verificador de rutas y hashes en verde (~1 s) |
| Árbol oficial del BOE de las tres titulaciones | [corpus/arbol_oficial.jsonl](corpus/arbol_oficial.jsonl) | 536 nodos con su referencia legal, y su muestreo humano |
| Índice de fragmentos | `corpus/fragmentos.jsonl` (fuera de git) | **11.483 fragmentos** de 512 tokens con su línea de contexto |
| Embeddings | `corpus/embeddings/` (fuera de git) | **11.483 vectores** BGE-M3 con la revisión anclada; 58 s en la 5080 |
| Base de datos | [migraciones/](migraciones/) | 4 migraciones; **11.282 fragmentos** cargados en **35 particiones** por asignatura |
| Contrato de generación tipada | [app/modelos/contrato.py](app/modelos/contrato.py) | el JSON de la sección 7 pedido con `json_schema` y validado en FORMA por el servidor |
| API e interfaz | [app/api/](app/api/), [web/](web/) | `/` (chat en SSE), `/estilos`, `/salud`, `/api`, `/consulta`, `/asignaturas`, fragmento por procedencia |
| Glosario | tabla `glosario` | **647 entradas**, cada una validada **sin modelo**: literal de su fragmento |
| Pares oro (encargo 3.0) | [evals/casos/](evals/casos/) | 100 pares con su método declarado (**19 `busqueda` / 81 `lectura`**), **en reconstrucción**: ~40 mal etiquetados |
| Reordenador (encargo 3.4) | [app/core/reordenador.py](app/core/reordenador.py) | BGE reranker v2-m3 con revisión anclada, **GPU o nada**; latencia medida, calidad **sin medir** |
| CI (ruff y pytest, todas las ramas) | [.github/workflows/ci.yml](.github/workflows/ci.yml) | en verde, y visto en rojo |
| Flujo del proveedor (gasta) | [.github/workflows/proveedor.yml](.github/workflows/proveedor.yml) | `workflow_dispatch`, visto en verde **y en rojo** con clave mala |
| Entorno local (db, redis, api, worker) | [compose.yml](compose.yml) | levanta y `/salud` en verde (200 con `degradado` cuando falta una pieza opcional; 503 solo si no se puede responder) |
| `respuestas.cache_hit` y `respuestas.escalado` | [migraciones/](migraciones/) | **columnas que NADIE escribe**: no hay caché semántica ni escalonado. Valen siempre `false`, y un `false` persistido se lee como una medida — [COBERTURA](corpus/COBERTURA.md) |

**Números medidos que sostienen lo de arriba:** TTFT del alumno **1,6 s** y total **2,2 s** por
consulta, a **0,000149 EUR**; el glosario entero por **0,043 EUR**; carga del corpus en **3,3 s** más
**2,2 s** de índices.

**Fase 3 abierta en la rama `fase-3`.** Cerrados dentro el **3.1** (léxica), el **3.2** (vectorial),
el **3.3** (fusión) y la mitad de latencia del **3.4** (reordenado). Todos los números salen partidos
por subconjunto desde el primer día — `busqueda` frente a `lectura` —, que es el sesgo del conjunto
de evaluación medido en vez de declarado:

| `recall@20` sobre los pares oro | global | `busqueda` | `lectura` |
|---|---:|---:|---:|
| Léxica (3.1) | 61,0 % | 73,7 % | 58,0 % |
| Vectorial (3.2) | 82,0 % | 78,9 % | 82,7 % |
| Fusión (3.3), techo con pool 30 | — | — | **88,9 %** |

> ### ⚠️ TODOS LOS NÚMEROS DE RECALL DE ESTA PÁGINA SON PROVISIONALES
>
> El conjunto oro **está en reconstrucción** desde el 13 de agosto de 2026: van **51 de 100
> revisados uno a uno y cerca de la mitad están mal etiquetados**. No es un parche, es una
> reconstrucción. Cuando esté rehecho se repiten 3.1, 3.2 y 3.3 con la misma configuración y **se
> publican los dos números, antes y después, con el tamaño del conjunto al lado** —que será menor
> que 100, porque hay pares que se retiran—. El método corregido, en
> [evals/casos/oro_recuperacion.md](evals/casos/oro_recuperacion.md).
>
> **Y no se sabe hacia dónde se moverán.** Los pares mal etiquetados que la recuperación **sí**
> encontraba estaban regalando aciertos, y los que no encontraba los estaban penalizando. Los dos
> efectos empujan en sentidos opuestos.

**Del 3.4 está medida la latencia y NO la calidad, a propósito**: el acierto del reordenador se mide
con `recall@6` contra los pares oro, y esa vara está rota; la latencia solo necesita treinta
candidatos y un reloj. El número obligó a una decisión de arquitectura, abajo.

**El 3.4 queda cerrado a medias por diseño y NO bloquea la fase 4**, que se abre por el 4.1 y el 4.2
mientras el conjunto se reconstruye. Cuando llegue, **3.4 y 3.5 se cierran en la misma tanda**. Y el
criterio de aceptación del reordenador ya está escrito, **como fórmula y no como cifra**: *se queda
si cierra más de la mitad del hueco entre la fusión sola y el techo del pool*. Con los valores
provisionales de hoy son 80,9 %; con el conjunto corregido cambiarán los tres números que la
alimentan y el listón se recalculará, **sin que eso sea mover la portería**: la regla es la misma y
se escribió antes de medir.

**Lo que se movió de sitio, con destino y motivo, no como olvido:** las colas (2.3) van después de
la demo y la traza completa (2.5) después de la fase 4, porque hoy respondería `sin_verificar` a
todo. Está escrito en el cierre de fase 2 de la guía y en el mensaje de su merge.

Todo lo demás —verificadores, arnés de evaluación, tabla de configuraciones y despliegue— está
**diseñado en la guía y no construido**. El orden de construcción es el de la Parte IV de la guía y
no se salta.

## Construido contra declarado: el reordenador necesita GPU, y el VPS no la tiene

**Lo que se enseña y lo que se despliega no son hoy la misma tubería, y esto está aquí para que se
lea antes de descubrirlo.** El reordenador del 3.4 es un cross-encoder de 568 M parámetros
(BGE reranker v2-m3). Medido sobre 30 candidatos, con el paso de reordenado aislado:

| Dónde | p50 | p95 | Del presupuesto de **5.000 ms** |
|---|---:|---:|---:|
| **GPU (RTX 5080)** | 419 ms | **554 ms** | **11 %** |
| CPU, 16 hilos | 10.776 ms | 13.714 ms | 274 % |
| CPU, 4 hilos (tipo CX32) | 45.649 ms | 46.246 ms | 925 % |
| CPU, 2 hilos (tipo CX22) | 64.927 ms | 65.648 ms | **1.313 %** |

**Un factor 25, y el reordenado va antes de la llamada al modelo**, o sea en la ruta del TTFT: en
CPU no serían "trece segundos de total", serían trece segundos de **pantalla en blanco** sumados a
los 2.267 ms de hoy. Las filas de CPU son además **cota inferior**, no estimación: están medidas en
un Ryzen 9 9950X3D con caché 3D y AVX-512 que un vCPU compartido no tiene.

**Consecuencia declarada: el reordenador va en GPU.** El VPS del despliegue (fase 8) no tiene.

**Y hay que separar dos cosas que no son la misma**, porque juntarlas miente:

| | ¿Cabe en los 2 vCPU del VPS? | |
|---|---|---|
| **Embebedor, vectorial y fusión** | **sí, de sobra** | embeber una consulta son **112,9 ms** a 2 hilos, medido |
| **Reordenado** | **no, por tres órdenes de magnitud** | 65.648 ms a 2 hilos |

Embeber son ~18 tokens una vez; reordenar son 30 fragmentos de 640 tokens: **0,04 TFLOPs frente a
21,8**. Así que el VPS puede correr **todo menos el reordenado** —del orden del **82,7 % de
`recall@20`**— **en cuanto la imagen lleve torch CPU**, que hoy no lleva (comprobado dentro del
contenedor). Eso no es un límite del hardware: es una **decisión pendiente con su coste declarado**
(~2,5 GB de imagen y ~4,3 s de carga al arrancar), que se toma en la fase 8 y no antes.

`GET /salud` declara pieza por pieza qué está activo. Es el principio 1 del proyecto funcionando —la
inferencia va donde el hardware la soporta y el contrato no cambia— y el principio 2 obligando a
escribirlo aquí.

**Y si la GPU no responde en caliente, el sistema NO se cae a CPU**: salta el reordenado, sirve el
orden de la fusión y **lo dice en pantalla** con una etapa `sin_reordenar`. Degradar anunciando,
jamás en silencio. El porqué entero, en
[ADR 0015](docs/adr/0015-el-reordenador-va-en-gpu-o-no-va.md).

## Los dos requisitos de producto, y en qué punto están

**1. La consulta no pasa de 5 segundos** (`PRESUPUESTO_CONSULTA_MS=5000`). **HOY NO SE CUMPLE**,
medido con n=20:

| Punta a punta | p50 | p95 |
|---|---:|---:|
| Total | **5.151 ms** | **63.853 ms** |
| TTFT del alumno | 3.909 ms | 63.272 ms |

**Y el culpable no es nuestra tubería:** en las veinte consultas, toda la recuperación —embebido,
tres vías, fusión y reordenado— cayó entre **525 y 896 ms**. La cola la pone el proveedor: dos de
veinte generaron a **4 y 11 tokens/s** en vez de a ~105, empezando rápido las dos (~315 ms hasta el
primer token). Está declarado con su traza en
[docs/evidencia/2026-08-13-concurrencia.md](docs/evidencia/2026-08-13-concurrencia.md).

**Construido contra eso** (`app/core/ritmo.py`): un **vigilante de ritmo** que mide tokens/s sobre
una ventana móvil —después del arranque, porque las dos lentas arrancaron bien— y **corta y
reintenta una vez** por debajo de 35 tokens/s, anunciándolo en pantalla; y el presupuesto **como
plazo de verdad**, que corta y lo dice en vez de dejar la pantalla congelada. Umbrales declarados sin
calibrar, con la calibración en el 4.6. Con ellos puestos, **ninguna consulta pasó de 5,5 s**.

**El precio, medido: con el plazo en 5 s se corta entre el 30 y el 40 % de las consultas**, y el
desglose descarta dos de los tres sospechosos:

| Tramo de la espera | Mediana | Del plazo |
|---|---:|---:|
| Recuperación (embebido, 3 vías, fusión, reordenado) | ~700 ms | 15 % |
| Prefill del proveedor | 292 ms | 6 % |
| **Afirmaciones** | **2.871 ms** | **60 %** |
| Prosa que el alumno lee | 823 ms | 17 % |

No es el prefill (las cortadas tardan lo mismo en arrancar) ni el proveedor (las cortadas generan a
119 tok/s, **más rápido** que las enteras a 110). **Es la verbosidad**: escriben un 56 % más de
tokens antes de llegar a la prosa, y dentro del bloque **la cita literal es el 55 % del contenido**.

**Decisión tomada: se mantiene el orden del contrato y el requisito de 5 s queda declarado como NO
CUMPLIDO con su número.** Invertir el orden emitiría prosa antes de saber si sus afirmaciones
verifican —peor que lento, para un sistema cuya tesis es verificar antes de afirmar—. La palanca que
sí se usa primero es acortar la cita literal, en el 4.1.

**2. Aguantar consultas simultáneas.** Nada bloquea el bucle de eventos —comprobado: `/api`
responde en 1,5 ms con 10 consultas pesadas en vuelo, contra 0,8 ms en reposo—. Lo que serializa es
**la GPU**, que es contención legítima de un recurso único:

**EL TECHO SE REPORTA COMO PAR DE NÚMEROS —latencia Y degradación—, nunca la latencia sola**
(principio 12): decir *"2,7 s con ocho alumnos"* sin decir que la mitad salió sin reordenar es un
número que engaña sin contener una sola cifra falsa.

| Alumnos a la vez | Nuestro p95 | **Sin reordenar** |
|---:|---:|---:|
| 1 | 1.002 ms | 0 % |
| 4 | 2.566 ms | **0 %** |
| **5** | 2.548 ms | **20 %** |
| 6 | 2.168 ms | **50 %** |
| 8 | 2.721 ms | **50 %** |

**Ojo a la columna del medio: desde N=4 el p95 deja de crecer.** No es que escale bien, es que
**está soltando calidad** — las peticiones que habrían tardado más son justo las que se degradan, y
al degradarse salen antes.

| | Medido |
|---|---:|
| Consultas/s sostenidas | **~1,9** |
| Alumnos simultáneos dentro de los 5 s | **~2** |
| Alumnos a partir de los cuales se pierde el reordenado | **5** |
| 30 alumnos a la vez: espera del último en nuestra cola | ~15,8 s |
| Cuota del proveedor (600 pet/min, 2 M tokens/min) | ~9,5 consultas/s |

**Ata el reordenador, unas cinco veces antes que la cuota.** El camino de escalada —lotes en el
reordenador, luego pool de GPU— está declarado con su disparador y **no construido**.

## Entorno local

Requisitos: Docker con Compose v2. Un clon limpio **no trae corpus** (está fuera de git), y no le
hace falta para arrancar:

```bash
docker compose up -d --wait
curl http://127.0.0.1:8000/salud
```

`/salud` devuelve 200 solo si las cuatro dependencias responden: base de datos, extensiones `vector`
y `pg_trgm`, redis y worker. Si alguna falla, devuelve 503 y dice cuál. Para parar,
`docker compose down`; con `-v` **se borra la base**. Re-embeber el corpus entero son 58 segundos medidos en la 5080, así que lo caro no es la GPU: es rehacer la carga y los índices.

## Cómo se trabaja aquí

Por encargos numerados (0.1, 0.2, 1.1...), en orden, cada uno con su verificación y su criterio de
cierre. Una fase, una rama. Las reglas completas están en [CLAUDE.md](CLAUDE.md).

## Corpus y licencias

El corpus **no se versiona en git** (`corpus/` está en `.gitignore`; solo entran el manifiesto y el
mapa de cobertura). Cada documento lleva en `corpus/manifiesto.jsonl` su ruta, fuente, licencia,
versión de corpus, hash SHA-256, densidad y marca de plantado: **sin entrada en el manifiesto no
entra en el corpus.** La normativa del BOE es dominio público; los apuntes públicos conservan su
licencia y su atribución; los repos de apuntes sin licencia declarada están registrados como
"sin licencia declarada, uso local, no redistribuible" y no salen de la máquina local.

## La fuente oficial también se contradice

Merece estar en el README porque es la tesis del proyecto vista en pequeño. Al extraer el árbol
oficial del BOE ([extraer_arbol.py](scripts/extraer_arbol.py)) apareció esto en el RD 1629/2009, la
norma que crea el título de ASIR:

| Dónde lo dice la norma | Cómo llama al módulo 0372 |
|---|---|
| Anexo I, encabezado del módulo | Gestión de **Base** de Datos |
| Articulado, lista de módulos | Gestión de **bases** de datos |

El mismo real decreto, el mismo módulo, dos nombres. **No se corrige: se declara.** El árbol
conserva lo que dice el Anexo I, que es de donde sale el nodo, y la contradicción se imprime en
cada extracción con su motivo escrito ([ADR 0006](docs/adr/0006-el-auditor-no-comparte-patron-con-el-parser.md)).

Un sistema que "limpiara" esa incoherencia estaría inventando una norma que no existe, y lo haría
en silencio. Preferir el ruido al silencio, y la procedencia por campo a la procedencia por
documento, es exactamente para lo que este sistema existe: **el material real no es coherente, y
fingir que lo es es la forma barata de mentir.**

## Verificación del corpus

```bash
python scripts/verificar_manifiesto.py   # cruza disco contra manifiesto en las dos direcciones
python scripts/verificar_oro.py          # los 100 pares oro contra el índice, por posición Y por texto
```

Las dos son puertas **locales**: el corpus está fuera de git y el runner de CI no lo tiene
([ADR 0001](docs/adr/0001-puerta-del-manifiesto-local-no-en-ci.md),
[ADR 0010](docs/adr/0010-el-par-oro-se-ancla-al-texto-no-a-la-posicion.md)). Cuándo hay que correr
cada una está en [CLAUDE.md](CLAUDE.md), y no es un detalle: la del oro se corre **antes de cualquier
medida de la fase 3** y **después de cualquier cambio de troceado, normalización o puerta de
admisión**, porque un par oro desplazado no da error, da ruido con aspecto de dato.
