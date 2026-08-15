# Veridica

Un profesor por asignatura sobre temario real que **solo afirma lo que puede sostener**: cita
literal comprobada carácter a carácter, paráfrasis verificada contra el fragmento fuente, cálculo
recalculado, y silencio honesto cuando la respuesta no está en el material.

**La tesis: la honestidad del sistema no depende de la brillantez del modelo, depende de la capa de
verificación.** Todo lo de abajo existe para poder decir eso con números en vez de con intención.

> **README provisional.** El definitivo lo produce el encargo 8.3. El estado real, encargo por
> encargo y derivado del código, está en **[docs/ESTADO.md](docs/ESTADO.md)** — que es lo que hay
> que leer para saber qué está construido. Aquí van solo la idea, tres números y los límites.

---

## Los tres números

Cada uno con su **unidad**, porque el arnés de evaluación repite las mismas preguntas (×4,84 en
consultas) y contar filas en vez de casos distintos infla todos los agregados. Los dos recuentos, y
nunca uno solo, están en el [barrido de filas contra casos](docs/evidencia/2026-08-14-barrido-filas-vs-casos.md).

### 1. Solo el **50,9 %** de lo que el modelo llama «cita literal» lo es

**57 de 112 citas distintas** (por filas: 195 de 337 = 57,9 %). Casi la mitad de lo que sale
etiquetado como cita textual **no aparece literalmente en su fragmento**.

**Este número mide al GENERADOR, no a nosotros**, y es importante no confundirlos. No es una tasa de
alucinación: muchas de esas serán paráfrasis correctas mal etiquetadas. **El daño no es que sea
inventado: es que llega etiquetado como cita.** Un alumno que copie eso en un examen creyendo que
son las palabras del libro se equivoca *precisamente por haberse fiado*.

**Nuestro número es el otro, y es el que sostiene la tesis: el 100 % de las mal declaradas se
cazan.** No "es poco probable que mienta" ni "el prompt le pide que no mienta": **no puede**, porque
lo decide una comparación de cadenas **sin ningún modelo en el lazo**. Lo que no cuadra se degrada a
paráfrasis y se verifica como tal, o se poda.
([evidencia](docs/evidencia/2026-08-13-verificador-literal.md))

### 2. La verificación de paráfrasis sube al **76 %** al cambiar de juez

**56 de 74 pares distintos**, contra el 49 % del juez anterior. El cambio no salió de un barrido
sino de **pasarle al instrumento el caso trivialmente cierto de su tarea**: darle una hipótesis que
está literalmente dentro de su premisa. El juez que había fallaba **2 de 22** identidades —textos
que no se siguen de sí mismos—; el nuevo falla **0 de 22**, con el mismo tamaño y +6,8 ms por par.
Lo que no aprueba ahí es su techo, y ninguna mejora de datos lo pasa.
([ADR 0022](docs/adr/0022-el-juez-nli-se-cambia-por-la-prueba-de-identidad.md))

### 3. `recall@6` en `lectura`: **58,7 %** contra un objetivo de 80 % — **NO ALCANZADO**

Sobre **75 pares oro** de `lectura`. Se publica sin adornos porque es el criterio de cierre de la
fase 3 y no se cumplió. **Y el techo del pool dice dónde está el hueco de verdad: 81,3 %** — o sea
que ni un reordenador perfecto llegaría con margen. El camino no es ordenar mejor 30 candidatos, es
que el fragmento correcto **entre** en el pool: troceado, léxica y corpus, con 18 de 94 pares fuera
del pool entero. ([cierre de la fase 3](docs/evidencia/2026-08-14-cierre-fase3.md))

---

## Los límites, dichos enteros

**1. La consulta se corta a los 8 s, y el objetivo de producto sigue siendo 5.** Son dos números
distintos a propósito: `OBJETIVO_CONSULTA_MS=5000` es lo que se quiere y `PRESUPUESTO_CONSULTA_MS=8000`
es donde se corta de verdad. **Con el plazo en 5 s se tiraba entre el 30 y el 40 % de respuestas ya
pagadas**, y el desglose descartó los sospechosos fáciles: no es el prefill (292 ms) ni la
recuperación (~700 ms), **es la verbosidad del bloque de afirmaciones (60 % de la espera)**.
Invertir el orden del contrato emitiría prosa antes de saber si sus afirmaciones verifican, que para
este proyecto es peor que ser lento. **El requisito de 5 s queda declarado NO CUMPLIDO con su
número.**

**2. Las latencias publicadas se midieron con el reordenador puesto, que ya no corre.** El 3.4 quedó
descartado por su propio criterio el 14/08, así que el techo de ~1,9 consultas/s **ya no describe lo
que se sirve**. Están marcadas como caducadas en [ESTADO](docs/ESTADO.md#4-latencias-con-la-configuración-en-la-que-se-midieron)
en vez de repetidas, y el número nuevo se mide, no se estima.

**3. Hay cosas diseñadas y sin código, y se dicen en presente como lo que son:** sandbox de código,
caché semántica, escalonado al modelo grande, colas con prioridades, multiturno y modelo del alumno.
**Y peor que un documento es una columna:** `respuestas.cache_hit` y `respuestas.escalado` llevan
meses en la base valiendo siempre `false` **sin que nada las escriba**, así que cualquier consulta
que las agregue diría *"la caché nunca acierta"* cuando la verdad es *"no hay caché"*.

**4. El corpus en disco es anterior a un arreglo de la normalización.** La regla que quita el pie de
autor llevaba un mes sin poder ejecutarse (dos defectos independientes, uno de ellos un byte de
control invisible). Está arreglada en el código y **el corpus no se ha rehecho**, porque
re-normalizar invalidaría los 94 pares oro, los hashes del manifiesto y las corridas publicadas.

**5. Los umbrales van por 5 de 6 calibrados.** El que falta —el anclaje de operandos— no está sin
calibrar por olvido: hoy es un contador que **sobrecuenta** (54 de 72 ocurrencias son cifras de
convención, no premisas), y poner un umbral encima sería ajustar al ruido. Los seis, con su valor y
su n, en [ESTADO §2](docs/ESTADO.md#2-umbrales-vivos).

---

## Arrancar

```bash
docker compose up -d --wait      # db, redis, api, worker
curl http://127.0.0.1:8000/salud
```

`/salud` **distingue tres cosas y no dos**: lo que impide responder (503), lo que degrada
anunciándolo (200 `degradado` — por ejemplo el contenedor sin torch), y **la pieza que está abajo
pero no la usa ninguna ruta construida**, que no es un rojo. Para parar, `docker compose down`; con
`-v` **se borra la base**.

**La imagen no lleva torch**, así que el contenedor sirve la configuración degradada. Lo que se
enseña se sirve desde el anfitrión, y es un comando que comprueba sus capacidades antes de dar el
puerto por bueno ([ADR 0023](docs/adr/0023-el-lunes-se-sirve-desde-el-anfitrion-no-desde-el-contenedor.md)):

```bash
python scripts/servir_anfitrion.py          # exige embebedor y NLI ARRIBA, o se planta
python scripts/verificar_manifiesto.py      # puerta local: rutas y hashes del corpus
python scripts/verificar_oro.py             # puerta local: los 94 pares oro, por posición Y por texto
```

Las dos últimas son **locales a propósito**: el corpus está fuera de git y el runner de CI no lo
tiene ([ADR 0001](docs/adr/0001-puerta-del-manifiesto-local-no-en-ci.md)). Cuándo hay que correr cada
una está en [CLAUDE.md](CLAUDE.md), y no es un detalle: **un par oro desplazado no da error, da ruido
con aspecto de dato.**

## Dónde está cada cosa

| | |
|---|---|
| **Estado real, encargo por encargo** | **[docs/ESTADO.md](docs/ESTADO.md)** |
| Playbook y fuente de verdad | [guia-definitiva.md](guia-definitiva.md) |
| Reglas de trabajo | [CLAUDE.md](CLAUDE.md) |
| Decisiones, con su trade-off | [docs/adr/](docs/adr/) |
| Medidas, con su corrida y su n | [docs/evidencia/](docs/evidencia/) |
| Qué cubre el corpus | [corpus/COBERTURA.md](corpus/COBERTURA.md) |

## Corpus y licencias

Tres titulaciones —DAW, DAM y ASIR—, **2.414 documentos** en el manifiesto, **11.483 fragmentos** de
512 tokens con su línea de contexto y sus **11.483 vectores** BGE-M3 (57,1 s en la 5080). En base
entran 11.282, repartidos en 35 particiones por asignatura: los 201 que faltan no declaran
asignatura y **no se cargan** ([ADR 0007](docs/adr/0007-los-fragmentos-sin-asignatura-declarada-no-se-cargan.md)).

El corpus **no se versiona** (`corpus/` está en `.gitignore`; solo entran el manifiesto, el mapa de
cobertura y el árbol oficial). Cada documento lleva en `corpus/manifiesto.jsonl` su ruta, fuente,
licencia, hash SHA-256 y marca de plantado: **sin entrada en el manifiesto no entra en el corpus.**
La normativa del BOE es dominio público; los apuntes públicos conservan su licencia y su atribución;
los repos sin licencia declarada están registrados como *"sin licencia declarada, uso local, no
redistribuible"* y no salen de la máquina local.

## La fuente oficial también se contradice

Está aquí porque es la tesis del proyecto vista en pequeño. Al extraer el árbol oficial apareció
esto en el RD 1629/2009, la norma que crea el título de ASIR:

| Dónde lo dice la norma | Cómo llama al módulo 0372 |
|---|---|
| Anexo I, encabezado del módulo | Gestión de **Base** de Datos |
| Articulado, lista de módulos | Gestión de **bases** de datos |

El mismo real decreto, el mismo módulo, dos nombres. **No se corrige: se declara.** Un sistema que
"limpiara" esa incoherencia estaría inventando una norma que no existe, y lo haría en silencio.
**El material real no es coherente, y fingir que lo es es la forma barata de mentir.**
